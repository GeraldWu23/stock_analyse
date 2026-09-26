# 账本域设计

本文件是当前唯一计划。范围只有 XMind「1 账本域」和「哪本账本」。不设计信息采集、衍生规则、主观分析，也不设计证券类型分叉。

图：[stock_analyse_data_flow_refactor.xmind](stock_analyse_data_flow_refactor.xmind)

## 开发准则

1. 简单逻辑简单实现。复杂逻辑先停下来，确认后再加代码，不要一次铺开。
2. 少建中间变量。只用一次、就地能看懂的表达式不要单独命名。排查时真正要盯的值可以留下，变量名要能直接读出含义。
3. 注释写给人，也写给以后的 AI。持仓类建成之后，读持仓、查某一行、以及将来在确认后改份额，都走持仓类的方法。不要另写一套路径常量或 `json.loads` 来维护同一本账。

## 图上的三本账

账本是 JSON Lines，一个文件一行一个 JSON 对象。持仓类不读取、不记录 markdown。每个仓一个文件夹，`dump` 把账本写进 `data/`，`load` 从那里读回来。

- 我的持仓：`data/我的持仓/holdings.jsonl`。未指明账本时用这本。
- 虚拟仓：`data/虚拟仓/holdings.jsonl`。
- 其他仓：节点是空的。不建第三本账，也不做注册表。以后真有第三本，再增加一个 `data/<仓名>/` 文件夹，仍用同一个类。

每个文件正好有一行账本头，后面每行一条持仓。用 `record` 区分，避免只靠行号：

- `record` 为 `book`：原来 JSON 顶层的字段，去掉 `holdings`。现金仍在这一行的 `cash` 里。
- `record` 为 `position`：原来的一条持仓，字段保持该账本里的原样。

两本账的字段仍然不同。真实仓账本头有 `as_of_date`、`included_in_account_total`；模拟仓有 `as_of`、`account_owner`、`ledger_type`、`included_in_total_assets`。持仓行一边写 `market_value`，一边写 `market_value_cny`。不把两边收成同一种结构。

真实仓示意：

```jsonl
{"record":"book","as_of_date":"2026-09-10","account":"普通账户","shares_are_sticky":true,"cash":{"account_cash_cny":43452.12,"included_in_account_total":true,"weight_pct":9.0}}
{"record":"position","name":"科创人工智能ETF易方达","ticker":"588730.SH","shares":70000,"cost_price":1.506,"currency":"CNY","market_value":97720.0}
```

## 持仓类

类名 `Holdings`，放在 `portfolio/holdings_book.py`。我的持仓和虚拟仓是这个类的两个实例，不是两个子类。行为还没有分叉。

```python
class Holdings:
    """一本持仓账，文件是 JSON Lines。真实仓和模拟仓都是这个类，差别只是路径。

    以后读持仓、查某一行，走这个类的方法。
    不要另写路径常量或按行 json.loads 来维护同一本账。
    dump 按给出的记录写文件，不在这里改份额。
    改份额要等用户明确说已成交，到时也加在这个类上，不另开写入入口。
    """

    def __init__(self, name: str, root: Path | None = None):
        self.name = name
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
```

`name` 是这本账的身份，需要留下来。`load()` 的结果不存成属性。`book()` 里的 `found` 要检查条数，所以留下。

模块里直接放两个实例：

```python
MINE = Holdings("我的持仓")
VIRTUAL = Holdings("虚拟仓")


def open_holdings(which: str | None = None) -> Holdings:
    """未指明或「我的持仓」返回 MINE。「虚拟仓」返回 VIRTUAL。"""
```

其他字符串，包括「其他仓」，直接报错。图上没有这本账的文件夹。
