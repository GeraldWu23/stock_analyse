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

## 测试

```bash
pytest -q
```

单元测试不依赖网络（对接口返回做解析测试）。
