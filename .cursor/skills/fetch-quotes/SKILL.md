---
name: fetch-quotes
description: 拉取 A 股 / 港股 / ETF 的实时行情(现价、涨跌、涨跌幅、最高、最低、成交量)。当用户询问股票/标的价格、行情、盘中报价,或提到自选(南方航空A、太古地产H、兆易创新H、电力ETF、1000增强ETF)时使用。数据源腾讯优先、新浪兜底。
---

# Fetch Quotes 行情查询

用仓库里的 `fetch_quotes.py` 拉取股票实时行情。数据源:腾讯 `qt.gtimg.cn` 优先,新浪 `hq.sinajs.cn` 兜底。

## 何时使用 / When to use

- 用户想查某只 A 股 / 港股 / ETF 的价格或涨跌。
- 用户说"看看行情 / 现在多少 / 查一下自选 / 报一下价格"等。

## 如何运行 / Instructions

在仓库根目录运行(优先使用虚拟环境的解释器 `./.venv/bin/python`,没有则用 `python3`):

```bash
# 拉取内置自选(南方航空A / 太古地产H / 兆易创新H / 电力ETF / 1000增强ETF)
python fetch_quotes.py

# 指定代码(前缀:上交所 sh、深交所 sz、港股 hk 补足 5 位)
python fetch_quotes.py sh600029 hk01972 hk03986 sh561700 sh561780

# 每 N 秒轮询一次(如每 2 分钟 = 120,每 5 分钟 = 300),Ctrl+C 结束
python fetch_quotes.py --interval 120
```

## 代码规则 / Symbol format

| 市场 | 前缀 | 示例 |
| --- | --- | --- |
| 上交所 A 股 | `sh` | `sh600029` 南方航空 |
| 深交所 A 股 | `sz` | `sz000001` 平安银行 |
| 港股 | `hk`(5 位) | `hk01972` 太古地产、`hk03986` 兆易创新H |
| ETF | `sh`/`sz` | `sh561700` 电力ETF、`sh561780` 1000增强ETF |

## 输出 / Output

打印一张带时间戳的表格,末列 `来源` 标明该行由腾讯还是新浪返回。把关键结果(现价、涨跌幅)简要汇报给用户即可。

## 备注 / Notes

- 也可用结构化 MCP 工具 `get_quotes`(见 `.cursor/mcp.json` 与 `tools/quotes_mcp_server.py`),返回 JSON,便于程序化处理。
- 港股/A 股为收盘后则展示收盘价快照;成交量已归一化为"股"。
