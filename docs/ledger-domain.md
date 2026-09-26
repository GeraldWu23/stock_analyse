# 账本域设计

本文件是当前唯一计划。范围只有 XMind「1 账本域」和「哪本账本」。不设计信息采集、衍生规则、主观分析，也不设计证券类型分叉。

图：[stock_analyse_data_flow_refactor.xmind](stock_analyse_data_flow_refactor.xmind)

## 开发准则

1. 简单逻辑简单实现。复杂逻辑先停下来，确认后再加代码，不要一次铺开。
2. 少建中间变量。只用一次、就地能看懂的表达式不要单独命名。排查时真正要盯的值可以留下，变量名要能直接读出含义。
3. 注释写给人，也写给以后的 AI。持仓类建成之后，读持仓、查某一行、以及将来在确认后改份额，都走持仓类的方法。不要另写一套路径常量或 `json.loads` 来维护同一本账。

## 图上的三本账

- 真实持仓：`portfolio/HOLDINGS.md`、`portfolio/holdings.json`。未指明账本，或说「我的持仓」，用这本。
- 模拟仓：`portfolio/simulated/HOLDINGS.md`、`portfolio/simulated/holdings.json`。只有「你的持仓」用这本。
- 其他仓：节点是空的。不建第三本账，也不做注册表。以后真有第三本，再增加一对路径，仍用同一个类。

两份 JSON 字段并不相同。真实仓有 `as_of_date`、`included_in_account_total`；模拟仓有 `as_of`、`account_owner`、`ledger_type`、`included_in_total_assets`。持仓行一边写 `market_value`，一边写 `market_value_cny`。持仓类按文件原样读出，不在这一步合并成第三种结构。

Markdown 是给人看的底稿，JSON 是代码读的副本。类记住 markdown 路径，但不解析 markdown。

## 持仓类

类名 `Holdings`，放在 `portfolio/holdings_book.py`。真实仓和模拟仓是这个类的两个实例，不是两个子类。行为还没有分叉。

```python
class Holdings:
    """一本持仓账。真实仓和模拟仓都是这个类，差别只是文件路径。

    以后读持仓、查某一行，走这个类的方法。
    不要另写路径常量或 json.loads 来维护同一本账。
    这个类只读文件。份额、成本和现金保持文件里的原值。
    改份额要等用户明确说已成交，到时也加在这个类上，不另开写入入口。
    """

    def __init__(self, json_path: Path, markdown_path: Path):
        self.json_path = json_path
        self.markdown_path = markdown_path

    def load(self) -> dict:
        """读 JSON 原文。不在对象上缓存，避免内存里再养一份账。"""
        return json.loads(self.json_path.read_text(encoding="utf-8"))

    def rows(self) -> list[dict]:
        """持仓行。现金不在这个列表里。"""
        return list(self.load()["holdings"])

    def cash_cny(self) -> float:
        """两边 JSON 都用 cash.account_cash_cny。不解释是否已含在总资产里，该标志两本账的字段名不同。"""
        return float(self.load()["cash"]["account_cash_cny"])
```

`json_path` 和 `markdown_path` 是这本账的身份，需要留下来。`load()` 的结果不存成属性。

模块里直接放两个实例：

```python
REAL = Holdings(
    REPO_ROOT / "portfolio" / "holdings.json",
    REPO_ROOT / "portfolio" / "HOLDINGS.md",
)
SIMULATED = Holdings(
    REPO_ROOT / "portfolio" / "simulated" / "holdings.json",
    REPO_ROOT / "portfolio" / "simulated" / "HOLDINGS.md",
)


def open_holdings(which: str | None = None) -> Holdings:
    """未指明、「real」、「我的持仓」返回 REAL。「simulated」、「你的持仓」返回 SIMULATED。"""
```

其他字符串，包括「其他仓」，直接报错。图上没有这本账的文件。

## 和现有代码的关系

`portfolio/collector.py` 里的 `load_holdings()` 今天按路径读 JSON，`--simulated` 只在 `portfolio/collect.py` 里选择路径。

持仓类落地时，只做这三件事：

- 新增 `Holdings`、`REAL`、`SIMULATED`、`open_holdings`。
- `load_holdings()` 改成调用对应实例的 `load()`，不再自己 `json.loads`。
- 现有测试仍通过 `load_holdings()` 读到原来的两份文件。

采集怎么拉行情、评委怎么打分，这次都不改。
