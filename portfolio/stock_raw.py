"""Collect A-share fundamentals + K-line into project raw_data.json. No LLM.

Output shape matches portfolio.engine.stock_features.extract_features.
ETF rows are rejected: they are baskets, not 66-judge targets.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from portfolio.collector import (
    COLLECTED_DIR,
    _import_ak,
    _num,
    fetch_stock_quote,
    parse_ticker,
    position_kind,
)

STAGE_LABEL = {
    0: "—",
    1: "Stage 1 底部",
    2: "Stage 2 上升",
    3: "Stage 3 顶部",
    4: "Stage 4 下跌",
}


def stock_cache_dir(ticker: str, collected_dir: Path | None = None) -> Path:
    return (collected_dir or COLLECTED_DIR) / ticker


def raw_data_path(ticker: str, collected_dir: Path | None = None) -> Path:
    return stock_cache_dir(ticker, collected_dir) / "raw_data.json"


def _to_float(v: Any, default: float = 0.0) -> float:
    n = _num(v)
    return default if n is None else n


def _to_yi(v: Any) -> float:
    n = _to_float(v)
    return round(n / 1e8, 2) if abs(n) >= 1_000_000 else round(n, 2)


def _dim(data: dict, source: str, *, error: str | None = None) -> dict:
    return {
        "data": data or {},
        "source": source,
        "fallback": not bool(data),
        "error": error,
    }


def _empty_dim() -> dict:
    return {"data": {}, "source": "skipped", "fallback": True}


def _ema(values: list[float], n: int) -> list[float]:
    k = 2 / (n + 1)
    out: list[float] = []
    prev = None
    for v in values:
        prev = v if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out


def _ma(closes: list[float], n: int) -> list[float]:
    return [sum(closes[max(0, i - n + 1): i + 1]) / min(i + 1, n) for i in range(len(closes))]


def _rsi(closes: list[float], n: int = 14) -> float | None:
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = mean(gains[-n:])
    avg_loss = mean(losses[-n:]) or 1e-9
    return 100 - 100 / (1 + avg_gain / avg_loss)


def _kdj(closes, highs, lows, n=9):
    if len(closes) < n:
        return None, None, None
    k, d = 50.0, 50.0
    for i in range(n - 1, len(closes)):
        hh = max(highs[i - n + 1: i + 1])
        ll = min(lows[i - n + 1: i + 1])
        rsv = (closes[i] - ll) / (hh - ll) * 100 if hh > ll else 50.0
        k = 2 / 3 * k + 1 / 3 * rsv
        d = 2 / 3 * d + 1 / 3 * k
    return round(k, 1), round(d, 1), round(3 * k - 2 * d, 1)


def _obv(closes, vols):
    if len(closes) < 2:
        return None, None
    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + vols[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - vols[i])
        else:
            obv.append(obv[-1])
    trend_up = obv[-1] > obv[-20] if len(obv) >= 20 else None
    return round(obv[-1], 0), trend_up


def _williams_r(closes, highs, lows, n=14):
    if len(closes) < n:
        return None
    hh = max(highs[-n:])
    ll = min(lows[-n:])
    if hh <= ll:
        return -50.0
    return round((hh - closes[-1]) / (hh - ll) * -100, 1)


def _stage(closes: list[float], ma200: list[float] | None) -> int:
    if len(closes) < 60 or not ma200:
        return 0
    last = closes[-1]
    ma_now = ma200[-1]
    ma_ago = ma200[-60] if len(ma200) >= 60 else ma200[0]
    above = last > ma_now
    rising = ma_now > ma_ago
    if above and rising:
        return 2
    if not above and rising:
        return 1
    if above and not rising:
        return 3
    return 4


def fetch_basic_a(ticker: str, name: str, ak_module: Any | None = None) -> dict:
    ak = _import_ak(ak_module)
    code, _market = parse_ticker(ticker)
    code6 = code.zfill(6)
    data: dict[str, Any] = {"code": ticker, "name": name}
    quote = fetch_stock_quote(ticker, ak_module=ak)
    data["price"] = quote.get("last_price")
    data["change_pct"] = quote.get("change_pct")
    data["pe_ttm"] = quote.get("pe_ttm")
    data["pb"] = quote.get("pb")
    data["open"] = quote.get("open")
    if ak is None:
        data["_quote_source"] = quote.get("source")
        return data
    try:
        info = ak.stock_individual_info_em(symbol=code6)
        if info is not None and not getattr(info, "empty", True):
            mapping = dict(zip(info["item"].astype(str), info["value"]))
            data["name"] = str(mapping.get("股票简称") or mapping.get("名称") or name)
            data["industry"] = mapping.get("行业")
            listed = mapping.get("上市时间")
            if listed:
                text = str(listed)
                if len(text) == 8 and text.isdigit():
                    data["listed_date"] = f"{text[:4]}-{text[4:6]}-{text[6:]}"
                else:
                    data["listed_date"] = text[:10]
            mcap = _num(mapping.get("总市值"))
            circ = _num(mapping.get("流通市值"))
            if mcap is not None:
                data["market_cap_raw"] = mcap
                data["market_cap"] = f"{_to_yi(mcap)}亿" if mcap > 1_000_000 else f"{mcap}亿"
            if circ is not None:
                data["circulating_cap_raw"] = circ
                data["circulating_cap"] = f"{_to_yi(circ)}亿" if circ > 1_000_000 else f"{circ}亿"
            pe = _num(mapping.get("市盈率") or mapping.get("市盈率-动态"))
            pb = _num(mapping.get("市净率"))
            if pe is not None:
                data["pe_ttm"] = pe
            if pb is not None:
                data["pb"] = pb
            if data.get("price") is None:
                data["price"] = _num(mapping.get("最新"))
    except Exception as exc:
        data["_info_err"] = f"{type(exc).__name__}: {exc}"[:160]
    if data.get("price") is None or data.get("market_cap") is None:
        yf_basic = _basic_from_yfinance(ticker)
        for key, value in yf_basic.items():
            if data.get(key) is None and value is not None:
                data[key] = value
        if yf_basic:
            data["_yf_basic"] = True
    if data.get("market_cap") and not data.get("market_cap_yi"):
        data["market_cap_yi"] = _to_float(str(data["market_cap"]).replace("亿", ""))
    return data


def fetch_financials_a(ticker: str, ak_module: Any | None = None) -> dict:
    ak = _import_ak(ak_module)
    if ak is None:
        return {}
    code, market = parse_ticker(ticker)
    code6 = code.zfill(6)
    prefix = "SH" if market == "SH" else "SZ"
    out: dict[str, Any] = {}

    try:
        df_abs = ak.stock_financial_abstract(symbol=code6)
        if df_abs is not None and not getattr(df_abs, "empty", True):
            period_cols = [c for c in df_abs.columns if c not in ("选项", "指标")]
            annual = sorted(c for c in period_cols if str(c).endswith("1231"))[-6:]

            def _row(keyword: str) -> list:
                row = df_abs[df_abs["指标"].astype(str).str.contains(keyword, na=False, regex=False)]
                if row.empty:
                    return []
                return [_to_yi(row[c].iloc[0]) for c in annual]

            if annual:
                out["revenue_history"] = _row("营业总收入")
                out["net_profit_history"] = _row("归属于母公司所有者的净利润") or _row("净利润")
                out["financial_years"] = [str(c)[:4] for c in annual]
    except Exception as exc:
        out["_abstract_error"] = f"{type(exc).__name__}: {exc}"[:160]

    try:
        df_ind = ak.stock_financial_analysis_indicator(symbol=code6, start_year="2018")
        if df_ind is not None and not getattr(df_ind, "empty", True):
            date_col = "日期" if "日期" in df_ind.columns else df_ind.columns[0]
            df_ind = df_ind.sort_values(date_col)
            df_annual = df_ind[df_ind[date_col].astype(str).str.endswith("12-31")]
            if df_annual.empty:
                df_annual = df_ind
            for col_key in ("加权净资产收益率(%)", "净资产收益率加权(%)", "ROE"):
                if col_key in df_ind.columns:
                    out["roe_history"] = [_to_float(v) for v in df_annual[col_key].tail(6).tolist()]
                    break
            last = df_ind.iloc[-1]
            last_annual = df_annual.iloc[-1]
            health: dict[str, Any] = {}
            for src_key, dst_key, source_row in (
                ("流动比率", "current_ratio", last),
                ("资产负债率(%)", "debt_ratio", last),
                ("总资产净利率(%)", "roic", last_annual),
                ("销售净利率(%)", "net_margin_pct", last_annual),
            ):
                if src_key in df_ind.columns:
                    v = _to_float(source_row.get(src_key))
                    if v:
                        health[dst_key] = v
            if health:
                out["financial_health"] = health
            if "加权净资产收益率(%)" in df_ind.columns:
                out["roe"] = f"{_to_float(last_annual['加权净资产收益率(%)']):.1f}%"
            if "销售净利率(%)" in df_ind.columns:
                out["net_margin"] = f"{_to_float(last_annual['销售净利率(%)']):.1f}%"
                out["gross_margin"] = _to_float(last_annual.get("销售毛利率(%)"))
            if "销售毛利率(%)" in df_ind.columns and not out.get("gross_margin"):
                out["gross_margin"] = _to_float(last_annual.get("销售毛利率(%)"))
            yoy_cols = (
                "主营业务收入增长率(%)",
                "营业总收入同比增长(%)",
                "营业收入同比增长率(%)",
                "营业收入增长率(%)",
            )
            for column in yoy_cols:
                if column not in df_ind.columns:
                    continue
                for _, row in df_ind.sort_values(date_col, ascending=False).iterrows():
                    value = _num(row.get(column))
                    if value is not None:
                        out["revenue_growth_yoy"] = round(value, 2)
                        out["revenue_growth"] = f"{value:+.1f}%"
                        out["revenue_growth_period"] = str(row.get(date_col))[:10]
                        out["revenue_growth_basis"] = "reported_yoy"
                        break
                if "revenue_growth_yoy" in out:
                    break
            np_cols = ("净利润同比增长率(%)", "归属母公司股东的净利润同比增长率(%)")
            for column in np_cols:
                if column not in df_ind.columns:
                    continue
                for _, row in df_ind.sort_values(date_col, ascending=False).iterrows():
                    value = _num(row.get(column))
                    if value is not None:
                        out["net_profit_growth_yoy"] = round(value, 2)
                        break
                if "net_profit_growth_yoy" in out:
                    break
            try:
                df_bs = ak.stock_balance_sheet_by_report_em(symbol=f"{prefix}{code6}")
                if df_bs is not None and not getattr(df_bs, "empty", True):
                    last_bs = df_bs.iloc[-1]
                    extra = {}
                    for src, dst in (
                        ("MONETARYFUNDS", "cash"),
                        ("TOTAL_LIABILITIES", "total_debt"),
                        ("TOTAL_PARENT_EQUITY", "equity"),
                    ):
                        if src in df_bs.columns:
                            v = _to_float(last_bs.get(src))
                            if v:
                                extra[dst] = round(v / 1e8, 2)
                    if extra:
                        out.setdefault("financial_health", {}).update(extra)
            except Exception as exc:
                out["_balance_sheet_error"] = f"{type(exc).__name__}: {exc}"[:80]
    except Exception as exc:
        out["_indicator_error"] = f"{type(exc).__name__}: {exc}"[:160]

    rh = out.get("revenue_history") or []
    if "revenue_growth_yoy" not in out and len(rh) >= 2 and rh[-2]:
        growth = (rh[-1] - rh[-2]) / rh[-2] * 100
        out["revenue_growth_yoy"] = round(growth, 2)
        out["revenue_growth"] = f"{growth:+.1f}%"

    try:
        df_cf = ak.stock_cash_flow_sheet_by_report_em(symbol=f"{prefix}{code6}")
        if df_cf is not None and not getattr(df_cf, "empty", True) and "经营活动产生的现金流量净额" in df_cf.columns:
            ocf_history = [_to_yi(v) for v in df_cf["经营活动产生的现金流量净额"].tolist()]
            ocf_history = [v for v in ocf_history if v != 0]
            if ocf_history:
                ocf_latest = ocf_history[0]
                out["operating_cash_flow_yi"] = round(ocf_latest, 2)
                out["ocf"] = f"{ocf_latest:.1f}亿"
                np_latest = (out.get("net_profit_history") or [0])[-1]
                if np_latest:
                    ratio = round(ocf_latest / np_latest, 2)
                    out["ocf_to_net_income_ratio"] = ratio
                    out.setdefault("financial_health", {})["ocf_to_net_income_ratio"] = ratio
    except Exception as exc:
        out["_cash_flow_error"] = f"{type(exc).__name__}: {exc}"[:160]

    try:
        df_div = ak.stock_history_dividend_detail(symbol=code6, indicator="分红")
        if df_div is not None and not getattr(df_div, "empty", True):
            by_year: dict[str, float] = defaultdict(float)
            for _, row in df_div.head(30).iterrows():
                date_str = str(row.get("公告日期", row.get("除权除息日", "")))
                year = date_str[:4] if date_str and len(date_str) >= 4 else ""
                amount = _to_float(row.get("派息", row.get("现金分红-派息(税前)(元/10股)", 0)))
                if year and amount:
                    by_year[year] += amount
            if by_year:
                years_sorted = sorted(by_year.keys())[-5:]
                out["dividend_years"] = years_sorted
                out["dividend_amounts"] = [round(by_year[y], 2) for y in years_sorted]
    except Exception as exc:
        out["_dividend_error"] = f"{type(exc).__name__}: {exc}"[:160]

    return out


def _yf_symbol(ticker: str) -> str:
    code, market = parse_ticker(ticker)
    code6 = code.zfill(6) if code.isdigit() else code
    if market == "SH":
        return f"{code6}.SS"
    if market == "SZ":
        return f"{code6}.SZ"
    if market == "HK":
        return f"{int(code6)}.HK"
    return ticker


def _basic_from_yfinance(ticker: str) -> dict:
    try:
        import yfinance as yf  # type: ignore
        info = yf.Ticker(_yf_symbol(ticker))
        fast = getattr(info, "fast_info", None)
        last = getattr(fast, "last_price", None) if fast is not None else None
        meta = getattr(info, "info", None) or {}
        if last is None:
            hist = info.history(period="5d")
            if hist is not None and not getattr(hist, "empty", True):
                last = float(hist["Close"].iloc[-1])
        mcap = getattr(fast, "market_cap", None) if fast is not None else None
        if mcap is None:
            mcap = meta.get("marketCap")
        out: dict[str, Any] = {}
        if last is not None:
            out["price"] = _num(last)
        pe = meta.get("trailingPE")
        pb = meta.get("priceToBook")
        if pe is not None:
            out["pe_ttm"] = _num(pe)
        if pb is not None:
            out["pb"] = _num(pb)
        if mcap is not None:
            out["market_cap_raw"] = _num(mcap)
            out["market_cap"] = f"{_to_yi(mcap)}亿"
            out["market_cap_yi"] = _to_yi(mcap)
        industry = meta.get("industry") or meta.get("sector")
        if industry:
            out["industry"] = industry
        return out
    except Exception:
        return {}


def _records_from_baostock(ticker: str) -> list[dict]:
    import baostock as bs  # type: ignore

    code, market = parse_ticker(ticker)
    code6 = code.zfill(6)
    prefix = "sh" if market == "SH" else "sz"
    lg = bs.login()
    if str(getattr(lg, "error_code", "1")) != "0":
        return []
    try:
        rs = bs.query_history_k_data_plus(
            f"{prefix}.{code6}",
            "date,open,high,low,close,volume",
            start_date="2018-01-01",
            frequency="d",
            adjustflag="2",
        )
        rows: list[dict] = []
        while rs.error_code == "0" and rs.next():
            date, open_, high, low, close, volume = rs.get_row_data()
            rows.append({
                "日期": date,
                "开盘": _to_float(open_),
                "最高": _to_float(high),
                "最低": _to_float(low),
                "收盘": _to_float(close),
                "成交量": _to_float(volume),
            })
        return rows
    finally:
        bs.logout()


def _records_from_yfinance(ticker: str) -> list[dict]:
    import yfinance as yf  # type: ignore

    hist = yf.Ticker(_yf_symbol(ticker)).history(period="5y")
    if hist is None or getattr(hist, "empty", True):
        return []
    rows = []
    for idx, rec in hist.iterrows():
        rows.append({
            "日期": str(idx)[:10],
            "开盘": _to_float(rec.get("Open")),
            "最高": _to_float(rec.get("High")),
            "最低": _to_float(rec.get("Low")),
            "收盘": _to_float(rec.get("Close")),
            "成交量": _to_float(rec.get("Volume")),
        })
    return rows


def _load_kline_records(ticker: str, ak_module: Any | None = None) -> tuple[list[dict], str]:
    ak = _import_ak(ak_module)
    code, _market = parse_ticker(ticker)
    code6 = code.zfill(6)
    errors: list[str] = []
    if ak is not None:
        for adjust in ("qfq", ""):
            try:
                hist = ak.stock_zh_a_hist(symbol=code6, period="daily", adjust=adjust)
                if hist is not None and not getattr(hist, "empty", True):
                    return hist.to_dict("records"), f"akshare:stock_zh_a_hist:{adjust or 'raw'}"
            except Exception as exc:
                errors.append(f"akshare:{type(exc).__name__}")
    try:
        rows = _records_from_baostock(ticker)
        if rows:
            return rows, "baostock"
    except Exception as exc:
        errors.append(f"baostock:{type(exc).__name__}")
    try:
        rows = _records_from_yfinance(ticker)
        if rows:
            return rows, "yfinance"
    except Exception as exc:
        errors.append(f"yfinance:{type(exc).__name__}")
    raise RuntimeError("K线全失败: " + ",".join(errors) if errors else "K线为空")


def fetch_kline_a(ticker: str, ak_module: Any | None = None) -> dict:
    records, source = _load_kline_records(ticker, ak_module)
    out = _kline_from_records(records)
    out["_source"] = source
    return out


def _kline_from_records(records: list[dict]) -> dict:
    closes = [_to_float(r.get("收盘")) for r in records]
    opens = [_to_float(r.get("开盘")) for r in records]
    highs = [_to_float(r.get("最高")) for r in records]
    lows = [_to_float(r.get("最低")) for r in records]
    vols = [_to_float(r.get("成交量")) for r in records]
    dates = [str(r.get("日期") or "")[:10] for r in records]
    if not closes:
        return {}

    ma5, ma10, ma20, ma60, ma120, ma200 = (_ma(closes, n) for n in (5, 10, 20, 60, 120, 200))
    ema12, ema26 = _ema(closes, 12), _ema(closes, 26)
    dif = [a - b for a, b in zip(ema12, ema26)]
    dea = _ema(dif, 9)
    macd_hist = [(d - e) * 2 for d, e in zip(dif, dea)]
    last = closes[-1]
    avg_vol_5 = mean(vols[-5:]) if len(vols) >= 5 else 0
    avg_vol_20 = mean(vols[-20:]) if len(vols) >= 20 else 0
    kdj_k, kdj_d, kdj_j = _kdj(closes, highs, lows)
    obv_last, obv_up = _obv(closes, vols)
    stage_n = _stage(closes, ma200)
    rsi_val = _rsi(closes, 14)
    golden = bool(len(dif) > 1 and dif[-1] > dea[-1] and dif[-2] <= dea[-2])
    ma_bull = ma5[-1] > ma10[-1] > ma20[-1] > ma60[-1] > ma120[-1]
    macd_label = (
        "金叉水上" if golden and dif[-1] > 0 else
        "死叉水上" if dif[-1] > 0 and macd_hist[-1] < 0 else
        "水下" if dif[-1] < 0 else "中性"
    )
    last_n = min(60, len(records))
    candles_60d = []
    for i in range(len(records) - last_n, len(records)):
        candles_60d.append({
            "date": dates[i],
            "open": round(opens[i], 2),
            "close": round(closes[i], 2),
            "high": round(highs[i], 2),
            "low": round(lows[i], 2),
        })
    ma20_full = _ma(closes, 20)
    ma60_full = _ma(closes, 60)
    stats: dict[str, Any] = {}
    if len(closes) >= 20:
        ytd_idx = max(0, len(closes) - 252)
        ytd_return = (closes[-1] - closes[ytd_idx]) / closes[ytd_idx] * 100 if closes[ytd_idx] else 0
        stats["ytd_return"] = f"{ytd_return:+.1f}%"
        rets = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes)) if closes[i - 1]]
        if len(rets) >= 2:
            import statistics as _st
            try:
                vol = _st.stdev(rets[-252:] if len(rets) >= 252 else rets) * (252 ** 0.5) * 100
                stats["volatility"] = f"{vol:.1f}%"
            except _st.StatisticsError:
                pass
        window = closes[-252:] if len(closes) >= 252 else closes
        peak = window[0]
        max_dd = 0.0
        for c in window:
            if c > peak:
                peak = c
            dd = (c - peak) / peak
            if dd < max_dd:
                max_dd = dd
        stats["max_drawdown"] = f"{max_dd * 100:.1f}%"

    indicators = {
        "last_close": last,
        "ma5": ma5[-1], "ma10": ma10[-1], "ma20": ma20[-1],
        "ma60": ma60[-1], "ma120": ma120[-1], "ma200": ma200[-1] if ma200 else None,
        "above_ma20": last > ma20[-1],
        "above_ma200": last > ma200[-1] if ma200 else None,
        "ma_bull_alignment": ma_bull,
        "macd_dif": dif[-1], "macd_dea": dea[-1], "macd_hist": macd_hist[-1],
        "macd_golden_cross": golden,
        "rsi_14": rsi_val,
        "kdj_k": kdj_k, "kdj_d": kdj_d, "kdj_j": kdj_j,
        "obv": obv_last, "obv_trend_up": obv_up,
        "williams_r": _williams_r(closes, highs, lows),
        "stage": stage_n,
        "vol_5_vs_20": (avg_vol_5 / avg_vol_20) if avg_vol_20 else None,
    }
    return {
        "kline_count": len(records),
        "indicators": indicators,
        "stage": STAGE_LABEL.get(stage_n, "—"),
        "ma_align": "多头排列" if ma_bull else "非多头",
        "macd": macd_label,
        "rsi": f"{rsi_val:.0f}" if rsi_val is not None else "—",
        "candles_60d": candles_60d,
        "ma20_60d": [round(v, 2) if i >= 19 else None for i, v in enumerate(ma20_full)][-last_n:],
        "ma60_60d": [round(v, 2) if i >= 59 else None for i, v in enumerate(ma60_full)][-last_n:],
        "close_60d": [round(c, 2) for c in closes[-last_n:]],
        "kline_stats": stats,
    }


def fetch_valuation(basic: dict) -> dict:
    pe = basic.get("pe_ttm")
    pb = basic.get("pb")
    return {
        "pe": pe,
        "pb": pb,
        "pe_quantile": "未知分位",
        "industry_pe": None,
        "dcf": None,
        "dividend_yield": basic.get("dividend_yield_ttm"),
    }


def assemble_raw(
    ticker: str,
    name: str,
    *,
    basic: dict,
    financials: dict,
    kline: dict,
    errors: dict[str, str] | None = None,
) -> dict:
    code, market = parse_ticker(ticker)
    market_code = "A" if market in ("SH", "SZ") else market
    return {
        "ticker": ticker,
        "market": market_code,
        "code": code,
        "name": name,
        "llm": False,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "execution_path": "portfolio.stock_raw",
        "errors": errors or {},
        "dimensions": {
            "0_basic": _dim(basic, basic.get("_quote_source") or "quote+info"),
            "1_financials": _dim(financials, "akshare:financial_abstract+indicator"),
            "2_kline": _dim(
                {k: v for k, v in kline.items() if k != "_source"},
                kline.get("_source") or "kline",
            ),
            "3_macro": _empty_dim(),
            "4_peers": _empty_dim(),
            "5_chain": _empty_dim(),
            "6_research": _empty_dim(),
            "7_industry": _empty_dim(),
            "8_materials": _empty_dim(),
            "9_futures": _empty_dim(),
            "10_valuation": _dim(fetch_valuation(basic), "derived:basic"),
            "11_governance": _empty_dim(),
            "12_capital_flow": _empty_dim(),
            "13_policy": _empty_dim(),
            "14_moat": _empty_dim(),
            "15_events": _empty_dim(),
            "16_lhb": _empty_dim(),
            "17_sentiment": _empty_dim(),
            "18_trap": _empty_dim(),
            "19_contests": _empty_dim(),
        },
    }


def collect_stock_raw(
    ticker: str,
    name: str,
    *,
    kind: str | None = None,
    ak_module: Any | None = None,
    seed_quote: dict | None = None,
    fetch_basic_fn=None,
    fetch_financials_fn=None,
    fetch_kline_fn=None,
) -> dict:
    if kind == "etf":
        raise ValueError(f"{name} 是篮子，不采集个股财报评委数据")
    errors: dict[str, str] = {}

    def _run(label: str, fn, fallback):
        try:
            return fn()
        except Exception as exc:
            errors[label] = f"{type(exc).__name__}: {exc}"[:200]
            return fallback

    basic_fn = fetch_basic_fn or (lambda: fetch_basic_a(ticker, name, ak_module))
    fin_fn = fetch_financials_fn or (lambda: fetch_financials_a(ticker, ak_module))
    kline_fn = fetch_kline_fn or (lambda: fetch_kline_a(ticker, ak_module))
    basic = _run("0_basic", basic_fn, {"code": ticker, "name": name})
    if seed_quote:
        if basic.get("price") is None and seed_quote.get("last_price") is not None:
            basic["price"] = seed_quote.get("last_price")
        if basic.get("change_pct") is None and seed_quote.get("change_pct") is not None:
            basic["change_pct"] = seed_quote.get("change_pct")
        if basic.get("pe_ttm") is None and seed_quote.get("pe_ttm") is not None:
            basic["pe_ttm"] = seed_quote.get("pe_ttm")
        if basic.get("pb") is None and seed_quote.get("pb") is not None:
            basic["pb"] = seed_quote.get("pb")
    financials = _run("1_financials", fin_fn, {})
    kline = _run("2_kline", kline_fn, {})
    raw = assemble_raw(ticker, name, basic=basic, financials=financials, kline=kline, errors=errors)
    raw["ok"] = bool(financials.get("roe_history") or financials.get("revenue_history")) and bool(
        kline.get("kline_count") or kline.get("stage")
    )
    return raw


def write_raw_data(raw: dict, collected_dir: Path | None = None) -> Path:
    ticker = raw["ticker"]
    dest = stock_cache_dir(ticker, collected_dir)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "raw_data.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)
    return path


def collect_holdings_fundamentals(
    holdings: dict | None = None,
    *,
    only_name: str | None = None,
    ak_module: Any | None = None,
    collected_dir: Path | None = None,
    collect_fn=None,
) -> dict:
    from portfolio.collector import load_holdings

    book = holdings or load_holdings()
    rows = list(book.get("holdings") or [])
    if only_name:
        needle = only_name.strip()
        rows = [r for r in rows if r.get("name") == needle]
        if not rows:
            raise ValueError(f"持仓里没有叫 {only_name!r} 的标的")

    collect_fn = collect_fn or collect_stock_raw
    results = []
    skipped = []
    for row in rows:
        name = row["name"]
        ticker = row["ticker"]
        if position_kind(row) == "etf":
            skipped.append({"name": name, "reason": "ETF 是篮子，不采集个股财报"})
            continue
        try:
            raw = collect_fn(
                ticker,
                name,
                kind=position_kind(row),
                ak_module=ak_module,
                seed_quote={
                    "last_price": row.get("last_price"),
                    "pe_ttm": row.get("pe_ttm"),
                    "pb": row.get("pb"),
                },
            )
            path = write_raw_data(raw, collected_dir)
            results.append({
                "name": name,
                "ticker": ticker,
                "ok": raw.get("ok"),
                "path": str(path),
                "errors": raw.get("errors") or {},
            })
        except Exception as exc:
            results.append({
                "name": name,
                "ticker": ticker,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}"[:200],
            })
    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "llm": False,
        "stocks": results,
        "skipped_etfs": skipped,
    }
