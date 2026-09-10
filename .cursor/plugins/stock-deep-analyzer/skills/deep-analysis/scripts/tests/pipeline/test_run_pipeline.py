"""v3.0.0 Phase 6a · pipeline.run_pipeline · delegate wrapper smoke test."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS))


def test_run_pipeline_exported():
    """run_pipeline 可从 lib.pipeline 顶层 import."""
    from lib.pipeline import run_pipeline
    assert callable(run_pipeline)


def test_score_from_cache_exists():
    from lib.pipeline.score import score_from_cache
    assert callable(score_from_cache)


def test_synthesize_and_render_exists():
    from lib.pipeline.synthesize import synthesize_and_render
    assert callable(synthesize_and_render)


def test_pipeline_run_has_load_and_write_cache():
    """run.py 内部 helper 存在 · 用于 resume + 落地 raw_data.json."""
    from lib.pipeline.run import _load_cache, _write_cache
    assert callable(_load_cache)
    assert callable(_write_cache)


def test_run_pipeline_signature():
    """run_pipeline(ticker, resume=True, collect_only=False) · 签名稳定."""
    import inspect
    from lib.pipeline.run import run_pipeline
    sig = inspect.signature(run_pipeline)
    params = list(sig.parameters.keys())
    assert "ticker" in params
    assert "resume" in params
    assert "collect_only" in params


def test_collect_only_skips_score_and_html(monkeypatch, tmp_path):
    """collect_only 只写 raw_data.json，不打分、不合成 HTML。"""
    import lib.pipeline.run as pipeline_run

    monkeypatch.setattr(pipeline_run, "_preflight_guards", lambda ticker: None)
    monkeypatch.setattr(pipeline_run, "_load_cache", lambda ticker: {})
    monkeypatch.setattr(pipeline_run, "pipeline_collect", lambda ticker, raw_previous=None, max_workers=6: {
        "0_basic": {"name": "南方航空", "price": 5.0, "market": "A"},
    })

    wrote = {}

    def fake_write(ticker, raw):
        wrote["raw"] = raw

    monkeypatch.setattr(pipeline_run, "_write_cache", fake_write)
    monkeypatch.setattr(pipeline_run, "_raw_cache_path", lambda ticker: tmp_path / "raw_data.json")

    scored = []
    rendered = []
    monkeypatch.setattr(pipeline_run, "score_from_cache", lambda ticker: scored.append(ticker))
    monkeypatch.setattr(pipeline_run, "synthesize_and_render", lambda ticker: rendered.append(ticker) or "nope.html")

    out = pipeline_run.run_pipeline("600029.SH", collect_only=True)
    assert scored == []
    assert rendered == []
    assert wrote["raw"]["ticker"] == "600029.SH"
    assert wrote["raw"]["execution_path"] == "pipeline"
    assert str(tmp_path / "raw_data.json") == out
