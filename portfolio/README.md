# 持仓分析（本仓库，不大模型）

从仓库根目录跑。用中文名，不要用代码。ETF 是篮子，不会进 66 评委。

## 明天分析南方航空（三步）

```bash
cd /path/to/stock_analyse
.venv/bin/python -m portfolio.collect --name 南方航空 --quotes-only
.venv/bin/python -m portfolio.collect --name 南方航空 --fundamentals
.venv/bin/python -m portfolio.judges --name 南方航空
```

没有 `.venv` 时把命令换成 `python3`。财报写入 `portfolio/collected/<代码>/raw_data.json`（gitignore）。评委笔记写入 `portfolio/analysis/`。

## 一步跑完

```bash
.venv/bin/python -m portfolio.analyze --name 南方航空
```

## 这三步分别做什么

1. **现价**：东财/akshare 现价，份额不改，市值 = 份额 × 现价。
2. **财报 + K 线**：营业额、ROE、负债、分红、均线/Stage。不调用大模型，不进插件目录。
3. **66 评委 / 九派**：`portfolio/engine/` 里的 Python 规则，读上一步的 `raw_data.json`。

东财行情接口在海外环境可能断连。本仓库会依次试：东财 hist → BaoStock → yfinance。K 线来源写在 `raw_data.json` 的 `2_kline.source`。

## 模拟交易

“你的持仓”指助手维护的模拟仓，最新快照保存在 `simulated/HOLDINGS.md` 和 `simulated/holdings.json`。“我的持仓”仍指用户的真实账户，保存在顶层 `HOLDINGS.md` 和 `holdings.json`。两套账本严格分开。

采集助手模拟仓行情：

```bash
.venv/bin/python -m portfolio.collect --simulated --quotes-only
```

- 2026-09-11 降低集中度：`simulations/2026-09-11-1315-risk-reduction.md`
- 同一记录的机器可读账本：`simulations/2026-09-11-1315-risk-reduction.json`
- 2026-09-14 再次降低纳斯达克ETF溢价风险：`simulations/2026-09-14-1338-nasdaq-premium-trim.md`
- 同一记录的机器可读账本：`simulations/2026-09-14-1338-nasdaq-premium-trim.json`
- 2026-09-16 按收盘价降低组合风险：`simulations/2026-09-16-close-risk-reduction.md`
- 同一记录的机器可读账本：`simulations/2026-09-16-close-risk-reduction.json`
- 2026-09-22 开盘限价买入美的集团：`simulations/2026-09-22-0930-midea-limit-buy.md`
- 同一记录的机器可读账本：`simulations/2026-09-22-0930-midea-limit-buy.json`

## 持仓展示格式

以后查看用户真实持仓或助手模拟仓，固定按券商截图顺序展示：

| 名称 | 今日盈亏 | 成本价 | 现价 | 持仓金额 | 持仓量 | 仓位 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |

“今日盈亏”按 `(现价 - 昨收) × 持仓量` 计算，不是累计持仓盈亏。实时昨收缺失时显示“暂不可用”，不能用累计盈亏替代。表格后列现金与总资产；现金已包含在总资产内。
