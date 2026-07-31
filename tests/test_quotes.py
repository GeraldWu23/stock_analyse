"""行情解析与展示的单元测试 (不依赖网络)。"""

from __future__ import annotations

import pytest

from stock_analyse.cli import render_table
from stock_analyse.quotes import QuoteError, _parse_chart_payload

_SAMPLE_PAYLOAD = {
    "chart": {
        "result": [
            {
                "meta": {
                    "symbol": "600519.SS",
                    "longName": "Kweichow Moutai",
                    "currency": "CNY",
                    "regularMarketPrice": 1500.0,
                    "chartPreviousClose": 1450.0,
                    "regularMarketDayHigh": 1520.0,
                    "regularMarketDayLow": 1480.0,
                    "regularMarketVolume": 3_000_000,
                    "regularMarketTime": 1785393753,
                }
            }
        ],
        "error": None,
    }
}


def test_parse_chart_payload_computes_change():
    quote = _parse_chart_payload("600519.SS", _SAMPLE_PAYLOAD)
    assert quote.symbol == "600519.SS"
    assert quote.name == "Kweichow Moutai"
    assert quote.currency == "CNY"
    assert quote.price == 1500.0
    assert quote.change == pytest.approx(50.0)
    assert quote.change_percent == pytest.approx(50.0 / 1450.0 * 100.0)


def test_parse_chart_payload_missing_previous_close():
    payload = {"chart": {"result": [{"meta": {"regularMarketPrice": 10.0}}]}}
    quote = _parse_chart_payload("X", payload)
    assert quote.change is None
    assert quote.change_percent is None


def test_parse_chart_payload_error_raises():
    payload = {"chart": {"error": {"description": "Not Found"}, "result": None}}
    with pytest.raises(QuoteError):
        _parse_chart_payload("BAD", payload)


def test_parse_chart_payload_empty_result_raises():
    with pytest.raises(QuoteError):
        _parse_chart_payload("BAD", {"chart": {"result": []}})


def test_render_table_contains_symbol_and_headers():
    quote = _parse_chart_payload("600519.SS", _SAMPLE_PAYLOAD)
    table = render_table([quote])
    assert "600519.SS" in table
    assert "代码" in table
    assert "涨跌幅" in table
