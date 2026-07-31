# stock_analyse

简单的股票**行情**工具：抓取 A 股 / 港股 / 美股实时行情并在终端展示。
数据源为 Yahoo Finance 公开接口，无需 API Key。

## 环境准备

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用

```bash
# 默认演示：贵州茅台、平安银行、苹果
python -m stock_analyse

# 指定代码
python -m stock_analyse 600519.SS 0700.HK AAPL
```

代码后缀规则：

| 市场 | 后缀 | 示例 |
| --- | --- | --- |
| 上交所 A 股 | `.SS` | `600519.SS` 贵州茅台 |
| 深交所 A 股 | `.SZ` | `000001.SZ` 平安银行 |
| 港股 | `.HK` | `0700.HK` 腾讯控股 |
| 美股 | 无 | `AAPL` 苹果 |

## 作为库使用

```python
from stock_analyse import fetch_quote

q = fetch_quote("600519.SS")
print(q.price, q.change, q.change_percent)
```

## A 股 / 港股行情脚本 fetch_quotes.py

腾讯 `qt.gtimg.cn` 优先、新浪 `hq.sinajs.cn` 兜底,支持 A 股 / 港股 / ETF,并可定时轮询。

```bash
python fetch_quotes.py                     # 内置自选(南方航空A/太古地产H/兆易创新H/大陆ETF)
python fetch_quotes.py sh600029 hk03986    # 指定代码 (sh/sz/hk 前缀)
python fetch_quotes.py --interval 300       # 每 5 分钟轮询一次 (Ctrl+C 结束)
```

## 让 Cursor 自动调用

两种方式都已内置,任选其一:

- **Skill**:`.cursor/skills/fetch-quotes/SKILL.md`。在 Cursor 里直接问"查一下这些价格 / 看看行情",
  agent 会自动运行 `fetch_quotes.py`(也可手动 `/fetch-quotes` 触发)。
- **MCP 工具**:`.cursor/mcp.json` 会启动 `tools/quotes_mcp_server.py`(FastMCP),暴露结构化工具
  `get_quotes(codes?)` 与 `list_watchlist()`,返回 JSON。首次可能需要在 Cursor 里允许运行该 MCP 工具。

## 测试

```bash
pytest -q
```

单元测试不依赖网络（对接口返回做解析 / mock 网络）。
