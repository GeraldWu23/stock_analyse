from __future__ import annotations

from portfolio.analyze import format_stock_report
from portfolio.stock_raw import assemble_raw
from portfolio.engine.score import score_dimensions, generate_panel
from portfolio.judges import summarize_panel


def test_format_stock_report_uses_name_not_ticker():
    raw = assemble_raw(
        "600029.SH",
        "南方航空",
        basic={"name": "南方航空", "price": 5.0, "pe_ttm": -69.0, "pb": 3.0, "market_cap": "906亿"},
        financials={
            "roe_history": [-15.0, 2.44],
            "revenue_history": [1700, 1822],
            "net_profit_history": [-17, 8.5],
            "financial_health": {"debt_ratio": 86.0},
        },
        kline={"stage": "Stage 4 下跌", "ma_align": "非多头", "rsi": "45"},
    )
    dims = score_dimensions(raw)
    panel = generate_panel(dims, raw)
    summary = summarize_panel(panel, name="南方航空", ticker="600029.SH")
    md = format_stock_report(
        "南方航空",
        {"last_price": 5.0, "change_pct": -0.6},
        {"raw": raw, "dimensions": dims},
        summary,
    )
    assert md.startswith("# 南方航空")
    assert "没有调用大模型" in md
    assert "600029" not in md
    assert "经典价值派" in md or "价值" in md
