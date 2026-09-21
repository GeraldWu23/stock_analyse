from __future__ import annotations

from portfolio.cn_quotes import (
    parse_sina_line,
    parse_tencent_line,
    tencent_request_code,
    ticker_to_cn_code,
)
from portfolio.collector import collect_book, collect_position, fetch_stock_quote


def test_ticker_to_cn_code():
    assert ticker_to_cn_code("01972.HK") == "hk01972"
    assert ticker_to_cn_code("600029.SH") == "sh600029"
    assert ticker_to_cn_code("159632.SZ") == "sz159632"
    assert ticker_to_cn_code("588730.SH") == "sh588730"
    assert tencent_request_code("hk01972") == "r_hk01972"
    assert tencent_request_code("sh600029") == "sh600029"


def _tencent_payload(var_name: str, *, name: str, last: str, prev: str, when: str) -> str:
    fields = [""] * 36
    fields[1] = name
    fields[3] = last
    fields[4] = prev
    fields[30] = when
    fields[33] = last
    fields[34] = prev
    return f'{var_name}="' + "~".join(fields) + '";'


def test_parse_tencent_a_share_and_hk():
    a = parse_tencent_line(
        "sh600029",
        _tencent_payload(
            "v_sh600029",
            name="南方航空",
            last="4.930",
            prev="4.860",
            when="20260918000000",
        ),
    )
    assert a is not None
    assert a["last_price"] == 4.93
    assert a["previous_close"] == 4.86
    assert a["change_pct"] == 1.44
    assert a["source"] == "tencent:qt.gtimg.cn"

    hk = parse_tencent_line(
        "hk01972",
        _tencent_payload(
            "v_r_hk01972",
            name="太古地产",
            last="24.320",
            prev="23.920",
            when="20260918161000",
        ),
    )
    assert hk is not None
    assert hk["last_price"] == 24.32
    assert hk["previous_close"] == 23.92
    assert hk["source"] == "tencent:qt.gtimg.cn"


def test_parse_sina_hk_and_a():
    sina_a = parse_sina_line(
        "sh600029",
        'var hq_str_sh600029="南方航空,4.870,4.860,4.930,4.950,4.860,4.92,4.93,'
        + "0," * 22
        + '2026-09-18,15:00:00,00";',
    )
    assert sina_a is not None
    assert sina_a["last_price"] == 4.93
    assert sina_a["previous_close"] == 4.86
    assert sina_a["source"] == "sina:hq.sinajs.cn"

    sina_hk = parse_sina_line(
        "hk01972",
        'var hq_str_hk01972="SWIREPROPERTIES,太古地产,23.70,23.92,24.46,23.70,24.32,'
        '0.40,1.67,0,0,1000,0,0,0,0,0,2026/09/18,16:08:00";',
    )
    assert sina_hk is not None
    assert sina_hk["last_price"] == 24.32
    assert sina_hk["previous_close"] == 23.92
    assert sina_hk["name"] == "太古地产"


def test_hk_prefers_tencent_over_yahoo():
    cn = {
        "hk01972": {
            "last_price": 24.32,
            "previous_close": 23.92,
            "change_pct": 1.67,
            "source": "tencent:qt.gtimg.cn",
        }
    }

    def boom_ak(*_a, **_k):
        raise AssertionError("HK should not need East Money when Tencent hit")

    class Ak:
        def stock_hk_spot_em(self):
            boom_ak()

        def stock_bid_ask_em(self, symbol):
            raise AssertionError("not A-share")

        def stock_zh_a_hist(self, **kwargs):
            raise AssertionError("not A-share")

    quote = fetch_stock_quote("01972.HK", ak_module=Ak(), cn_quotes=cn)
    assert quote["last_price"] == 24.32
    assert quote["source"] == "tencent:qt.gtimg.cn"


def test_a_share_uses_tencent_when_eastmoney_empty():
    class Ak:
        def stock_bid_ask_em(self, symbol):
            raise RuntimeError("east money down")

        def stock_zh_a_hist(self, **kwargs):
            raise RuntimeError("east money down")

    quote = fetch_stock_quote(
        "600029.SH",
        ak_module=Ak(),
        cn_quotes={
            "sh600029": {
                "last_price": 4.93,
                "previous_close": 4.86,
                "source": "tencent:qt.gtimg.cn",
            }
        },
    )
    assert quote["last_price"] == 4.93
    assert quote["source"] == "tencent:qt.gtimg.cn"


def test_etf_fills_last_from_tencent_when_table_misses():
    row = {
        "name": "纳斯达克ETF华安",
        "ticker": "159632.SZ",
        "code": "159632",
        "type": "场内基金",
        "shares": 22200,
        "cost_price": 2.03,
        "last_price": 2.456,
        "currency": "CNY",
    }
    out = collect_position(
        row,
        etf_table=[],
        quotes_only=True,
        cn_quotes={
            "sz159632": {
                "last_price": 2.489,
                "previous_close": 2.441,
                "source": "tencent:qt.gtimg.cn",
            }
        },
    )
    assert out["last_price"] == 2.489
    assert out["today_pnl"] == 1065.6
    assert out["source"] == "tencent:qt.gtimg.cn"


def test_collect_book_prefetch_uses_injected_cn_loader():
    book = {
        "account": "测试",
        "cash": {"account_cash_cny": 100.0},
        "totals": {"hkd_to_cny": 0.84},
        "holdings": [
            {
                "name": "太古地产",
                "ticker": "01972.HK",
                "code": "01972",
                "type": "港股通",
                "shares": 1200,
                "cost_price": 19.865,
                "last_price": 20.0,
                "currency": "HKD",
            }
        ],
    }

    def loader(codes):
        assert codes == ["hk01972"]
        return {
            "hk01972": {
                "last_price": 24.32,
                "previous_close": 23.92,
                "source": "tencent:qt.gtimg.cn",
            }
        }

    class Ak:
        def stock_hk_spot_em(self):
            raise AssertionError("prefetch should satisfy HK")

    snap = collect_book(book, quotes_only=True, ak_module=Ak(), fetch_cn_quotes_fn=loader)
    pos = snap["positions"][0]
    assert pos["last_price"] == 24.32
    assert pos["today_pnl"] == 480.0
    assert pos["source"] == "tencent:qt.gtimg.cn"
