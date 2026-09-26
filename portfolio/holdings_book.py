"""一个仓的账本。读写都走 Holdings。

持仓结果在 data/<仓名>/holdings.jsonl。
买卖动作在 data/<仓名>/ledger.jsonl，一行一笔。
成交后调用 trade()。不要另写一份成交记录，也不要直接改份额。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SHANGHAI = ZoneInfo("Asia/Shanghai")


class Holdings:
    """一个仓。结果在 holdings.jsonl，买卖在 ledger.jsonl。

    读持仓用 load，整本写回用 dump。
    成交后只用 trade()：追加一条买卖，并改份额和现金。
    不要另写一份成交记录，也不要直接改 holdings.jsonl 里的份额。
    """

    def __init__(self, name: str, root: Path | None = None):
        self.name = name
        # root 只在测试里换成临时目录。平时是仓库的 data/。
        self.folder = (root or DATA_DIR) / name

    def load(self) -> list[dict]:
        """按行读出对象。跳过空行。不在对象上缓存，避免内存里再养一份账。"""
        text = (self.folder / "holdings.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def dump(self, records: list[dict]) -> None:
        """把记录写成 JSON Lines，放到 data/<仓名>/holdings.jsonl。"""
        self.folder.mkdir(parents=True, exist_ok=True)
        body = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
        (self.folder / "holdings.jsonl").write_text(body + "\n", encoding="utf-8")

    def book(self) -> dict:
        """账本头。record 为 book 的行应正好一条。"""
        found = [line for line in self.load() if line["record"] == "book"]
        if len(found) != 1:
            raise ValueError(f"{self.folder / 'holdings.jsonl'} 应有且只有一行账本头")
        return found[0]

    def rows(self) -> list[dict]:
        """持仓行。现金在账本头里，不在这里。"""
        return [line for line in self.load() if line["record"] == "position"]

    def cash_cny(self) -> float:
        """两边账本头都用 cash.account_cash_cny。不解释是否已含在总资产里，该标志两本账的字段名不同。"""
        return float(self.book()["cash"]["account_cash_cny"])

    def trades(self) -> list[dict]:
        """买卖记录。没有文件时是空的。不在对象上缓存。"""
        path = self.folder / "ledger.jsonl"
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def begin(self, at: datetime | None = None) -> dict:
        """以当前持仓为起点。已有记录则不另写起点。此前买卖不补记。"""
        existing = self.trades()
        if existing:
            return existing[0]
        return self._append_ledger(_moment_record("start", at) | {
            "note": "以当前持仓为起点，此前买卖不补记",
        })

    def trade(self, *, name: str, side: str, shares: float, price: float, at: datetime | None = None) -> dict:
        """追加一笔买卖，并改持仓份额和现金。仓位比例这次不重算。"""
        if side not in ("买", "卖"):
            raise ValueError("side 只能是买或卖")
        if shares <= 0 or price <= 0:
            raise ValueError("份额和价格要大于 0")

        records = self.load()
        position = next((row for row in records if row.get("record") == "position" and row.get("name") == name), None)
        if side == "卖" and (position is None or float(position["shares"]) < shares):
            raise ValueError(f"{name} 份额不够")
        if position is None:
            position = {
                "record": "position",
                "name": name,
                "shares": 0,
                "cost_price": price,
                "last_price": price,
                "currency": "CNY",
            }
            records.append(position)

        held = float(position["shares"])
        if side == "买":
            cost = float(position.get("cost_price") or price)
            position["cost_price"] = round((held * cost + shares * price) / (held + shares), 6)
            position["shares"] = held + shares
        else:
            position["shares"] = held - shares
        position["last_price"] = price
        if "available" in position:
            position["available"] = position["shares"]

        currency = position.get("currency") or "CNY"
        book = next(row for row in records if row.get("record") == "book")
        rate = float(book["totals"]["hkd_to_cny"]) if currency == "HKD" else 1.0
        cash_delta = round(shares * price * rate, 2)
        if side == "买":
            cash_delta = -cash_delta
        book["cash"]["account_cash_cny"] = round(float(book["cash"]["account_cash_cny"]) + cash_delta, 2)
        if book.get("totals") and "cash_cny" in book["totals"]:
            book["totals"]["cash_cny"] = book["cash"]["account_cash_cny"]

        ticker = position.get("ticker")
        if position["shares"] <= 0:
            records.remove(position)
        else:
            if "market_value" in position:
                position["market_value"] = round(float(position["shares"]) * price, 2)
            if "market_value_hkd" in position and currency == "HKD":
                position["market_value_hkd"] = round(float(position["shares"]) * price, 2)
            if "market_value_cny" in position:
                position["market_value_cny"] = round(float(position["shares"]) * price * rate, 2)
        self.dump(records)

        record = _moment_record("trade", at) | {
            "name": name,
            "side": side,
            "shares": shares,
            "price": price,
            "currency": currency,
        }
        if ticker:
            record["ticker"] = ticker
        return self._append_ledger(record)

    def _append_ledger(self, record: dict) -> dict:
        self.folder.mkdir(parents=True, exist_ok=True)
        with (self.folder / "ledger.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record


def _moment_record(kind: str, at: datetime | None) -> dict:
    moment = datetime.now(SHANGHAI) if at is None else at
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=SHANGHAI)
    else:
        moment = moment.astimezone(SHANGHAI)
    return {
        "record": kind,
        "date": moment.strftime("%Y-%m-%d"),
        "time": moment.strftime("%H:%M:%S"),
        "timezone": "Asia/Shanghai",
    }


MINE = Holdings("我的持仓")
VIRTUAL = Holdings("虚拟仓")


def open_holdings(which: str | None = None) -> Holdings:
    """未指明或「我的持仓」返回 MINE。「虚拟仓」返回 VIRTUAL。"""
    if which is None or which == "我的持仓":
        return MINE
    if which == "虚拟仓":
        return VIRTUAL
    raise ValueError(f"没有这本账: {which}")
