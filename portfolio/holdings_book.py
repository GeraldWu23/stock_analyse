"""一个仓的账本。读写都走 Holdings，文件在 data/<仓名>/holdings.jsonl。

以后读这个仓、把这个仓写回去，用 load 和 dump。
不要在别的目录再保存一份同一个仓的账本。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


class Holdings:
    """一个仓。账本是 data/<仓名>/holdings.jsonl，一行一个 JSON 对象。

    读用 load，写用 dump。
    不要在别的目录再保存一份这个仓的账本。
    dump 按给出的记录写文件，不在这里改份额。
    改份额要等用户明确说已成交，到时也加在这个类上，不另开写入入口。
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


MINE = Holdings("我的持仓")
VIRTUAL = Holdings("虚拟仓")


def open_holdings(which: str | None = None) -> Holdings:
    """未指明或「我的持仓」返回 MINE。「虚拟仓」返回 VIRTUAL。"""
    if which is None or which == "我的持仓":
        return MINE
    if which == "虚拟仓":
        return VIRTUAL
    raise ValueError(f"没有这本账: {which}")
