"""JSON Lines 持仓账。读持仓走 Holdings，不要另写一套按行解析。"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class Holdings:
    """一本持仓账，文件是 JSON Lines。真实仓和模拟仓都是这个类，差别只是路径。

    以后读持仓、查某一行，走这个类的方法。
    不要另写路径常量或按行 json.loads 来维护同一本账。
    这个类只读文件。份额、成本和现金保持文件里的原值。
    改份额要等用户明确说已成交，到时也加在这个类上，不另开写入入口。
    """

    def __init__(self, jsonl_path: Path):
        self.jsonl_path = jsonl_path

    def load(self) -> list[dict]:
        """按行读出对象。跳过空行。不在对象上缓存，避免内存里再养一份账。"""
        text = self.jsonl_path.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def book(self) -> dict:
        """账本头。record 为 book 的行应正好一条。"""
        found = [line for line in self.load() if line["record"] == "book"]
        if len(found) != 1:
            raise ValueError(f"{self.jsonl_path} 应有且只有一行账本头")
        return found[0]

    def rows(self) -> list[dict]:
        """持仓行。现金在账本头里，不在这里。"""
        return [line for line in self.load() if line["record"] == "position"]

    def cash_cny(self) -> float:
        """两边账本头都用 cash.account_cash_cny。不解释是否已含在总资产里，该标志两本账的字段名不同。"""
        return float(self.book()["cash"]["account_cash_cny"])


REAL = Holdings(REPO_ROOT / "portfolio" / "holdings.jsonl")
SIMULATED = Holdings(REPO_ROOT / "portfolio" / "simulated" / "holdings.jsonl")


def open_holdings(which: str | None = None) -> Holdings:
    """未指明、「real」、「我的持仓」返回 REAL。「simulated」、「你的持仓」返回 SIMULATED。"""
    if which is None or which in ("real", "我的持仓"):
        return REAL
    if which in ("simulated", "你的持仓"):
        return SIMULATED
    raise ValueError(f"没有这本账: {which}")
