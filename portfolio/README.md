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

不要跑 `python run.py`，那条会走插件 HTML / 评委长文（大模型）。
