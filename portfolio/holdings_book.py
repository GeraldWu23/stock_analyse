"""一个仓的账本。读写都走 Holdings。

持仓结果在 data/<仓名>/holdings.jsonl。
买卖动作在 data/<仓名>/ledger.jsonl，一行一笔。
成交后调用 trade()。充值或提取调用 cash()。不要另写一份记录，也不要直接改份额或现金。
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
    充值或提取只用 cash()：追加一条现金记录，并改现金和总额。
    不要另写一份记录，也不要直接改 holdings.jsonl 里的份额或现金。
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

    def last_checked_at(self) -> str | None:
        """最近一次检查的时间。旧账本没有这个字段时是 None，不要当成最近一笔交易。"""
        return self.book().get("last_checked_at")

    def mark_checked(self, at: datetime | None = None) -> str:
        """记下检查时间。不改份额、现金、as_of、as_of_date，也不写买卖账。没成交也要记。"""
        moment = datetime.now(SHANGHAI) if at is None else at
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=SHANGHAI)
        else:
            moment = moment.astimezone(SHANGHAI)
        stamp = moment.isoformat(timespec="seconds")
        records = self.load()
        next(row for row in records if row.get("record") == "book")["last_checked_at"] = stamp
        self.dump(records)
        return stamp

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

    def cash(self, *, side: str, amount: float, at: datetime | None = None) -> dict:
        """记一笔充值或提取。只改现金和总额，不改份额，也不改 last_checked_at。"""
        if side not in ("充值", "提取"):
            raise ValueError("side 只能是充值或提取")
        amount = round(float(amount), 2)
        if amount <= 0:
            raise ValueError("金额要大于 0")

        records = self.load()
        header = next(row for row in records if row.get("record") == "book")
        current = float(header["cash"]["account_cash_cny"])
        if side == "提取" and current < amount:
            raise ValueError("现金不够")
        signed = amount if side == "充值" else -amount
        header["cash"]["account_cash_cny"] = round(current + signed, 2)
        totals = header.get("totals") or {}
        if "cash_cny" in totals:
            totals["cash_cny"] = header["cash"]["account_cash_cny"]
        if "total_assets_cny" in totals:
            totals["total_assets_cny"] = round(float(totals["total_assets_cny"]) + signed, 2)
        securities = float(totals.get("securities_cny") or 0)
        total = securities + header["cash"]["account_cash_cny"]
        if total:
            header["cash"]["weight_pct"] = round(header["cash"]["account_cash_cny"] / total * 100, 2)
            for row in records:
                if row.get("record") != "position" or row.get("market_value_cny") is None:
                    continue
                row["weight_pct"] = round(float(row["market_value_cny"]) / total * 100, 2)
        self.dump(records)
        return self._append_ledger(_moment_record("cash", at) | {
            "side": side,
            "amount": int(amount) if amount == int(amount) else amount,
            "currency": "CNY",
        })

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
