from __future__ import annotations

from portfolio.judges import format_judges, format_markdown, run_book_judges, summarize_panel, write_judges_snapshot


def _fake_panel():
    schools = {
        "A": {"label": "经典价值派", "verdict": "回避", "consensus": 7.7},
        "B": {"label": "成长派", "verdict": "回避", "consensus": 20.0},
        "C": {"label": "宏观派", "verdict": "回避", "consensus": 18.0},
        "D": {"label": "技术派", "verdict": "谨慎", "consensus": 40.0},
        "E": {"label": "中式价投", "verdict": "回避", "consensus": 15.0},
        "F": {"label": "A 股游资", "verdict": "回避", "consensus": 12.0},
        "G": {"label": "量化派", "verdict": "回避", "consensus": 22.0},
        "H": {"label": "科技领袖派", "verdict": "回避", "consensus": 10.0},
        "I": {"label": "AI 卡位/瓶颈猎手", "verdict": "回避", "consensus": 8.0},
    }
    return {
        "panel_consensus": 20.9,
        "signal_distribution": {"bullish": 2, "neutral": 13, "bearish": 26, "skip": 23},
        "school_scores": schools,
        "investors": [
            {"name": "巴菲特", "signal": "bearish", "score": 12, "headline": "杠杆太高"},
            {"name": "欧奈尔", "signal": "neutral", "score": 53, "headline": "趋势一般"},
            {"name": "木头姐", "signal": "bearish", "score": 30, "headline": "不是成长"},
        ],
    }


SAMPLE = {
    "holdings": [
        {"name": "南方航空", "ticker": "600029.SH", "type": "股票"},
        {"name": "科创人工智能ETF易方达", "ticker": "588730.SH", "type": "场内基金"},
    ]
}


def test_skips_etf_and_summarizes_nine_schools():
    payload = run_book_judges(
        SAMPLE,
        score_fn=lambda ticker: {"panel": _fake_panel()},
    )
    assert payload["llm"] is False
    assert payload["skipped_etfs"][0]["name"] == "科创人工智能ETF易方达"
    assert len(payload["stocks"]) == 1
    stock = payload["stocks"][0]
    assert stock["name"] == "南方航空"
    assert stock["n_judges"] == 3
    assert len(stock["schools"]) == 9
    assert stock["schools"][0]["label"] == "经典价值派"
    assert stock["schools"][0]["score"] == 7.7
    text = format_judges(payload)
    assert "南方航空" in text
    assert "科创人工智能ETF易方达" in text
    assert "600029" not in text
    md = format_markdown(payload)
    assert "价值" in md or "经典价值派" in md


def test_only_name_stock():
    payload = run_book_judges(
        SAMPLE,
        only_name="南方航空",
        score_fn=lambda ticker: {"panel": _fake_panel()},
    )
    assert payload["skipped_etfs"] == []
    assert payload["stocks"][0]["name"] == "南方航空"


def test_write_snapshot(tmp_path):
    payload = run_book_judges(SAMPLE, score_fn=lambda ticker: {"panel": _fake_panel()})
    path = write_judges_snapshot(payload, collected_dir=tmp_path)
    assert path.exists()
    assert path.name == "judges-latest.json"
