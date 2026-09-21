"""schedule_quotes.py 的 cron 解析/匹配离线测试。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import pytest

import fetch_quotes
import schedule_quotes as sq

# 参照: 2026-08-11 是周二, 2026-08-15 周六, 2026-08-09 周日, 2026-08-10 周一。


def dt(*args: int) -> datetime:
    """构造时区感知的时间(matches/next_after 只读挂钟字段, 用哪个时区不影响判断)。"""
    return datetime(*args, tzinfo=timezone.utc)


def test_parse_basic_fields():
    sched = sq.parse_cron("*/5 9-15 * * 1-5")
    assert sched.minute == {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}
    assert sched.hour == {9, 10, 11, 12, 13, 14, 15}
    assert sched.month == set(range(1, 13))
    assert sched.dow == {1, 2, 3, 4, 5}
    assert sched.dom_star is True
    assert sched.dow_star is False


def test_list_and_step_combo():
    sched = sq.parse_cron("0,30 * * * *")
    assert sched.minute == {0, 30}
    sched2 = sq.parse_cron("10-20/5 * * * *")
    assert sched2.minute == {10, 15, 20}


def test_matches_trading_window():
    sched = sq.parse_cron("*/5 9-15 * * 1-5")
    assert sched.matches(dt(2026, 8, 11, 9, 5))   # 周二 09:05
    assert not sched.matches(dt(2026, 8, 11, 9, 7))  # 分钟非 5 的倍数
    assert not sched.matches(dt(2026, 8, 15, 9, 5))  # 周六
    assert not sched.matches(dt(2026, 8, 11, 8, 5))  # 小时不在 9-15


def test_dom_dow_or_semantics():
    # 日==1 或 周日, 12:00
    sched = sq.parse_cron("0 12 1 * 0")
    assert sched.matches(dt(2026, 8, 1, 12, 0))   # 1 号
    assert sched.matches(dt(2026, 8, 9, 12, 0))   # 周日(非1号)
    assert not sched.matches(dt(2026, 8, 10, 12, 0))  # 周一且非1号


def test_sunday_accepts_0_and_7():
    assert sq.parse_cron("0 0 * * 0").dow == sq.parse_cron("0 0 * * 7").dow == {0}


def test_next_after():
    sched = sq.parse_cron("*/5 9-15 * * 1-5")
    nxt = sched.next_after(dt(2026, 8, 11, 9, 3, 30))
    assert nxt == dt(2026, 8, 11, 9, 5)
    # 跨到下一个交易日: 周五 15:59 -> 周一 09:00
    nxt2 = sched.next_after(dt(2026, 8, 14, 15, 59))  # 周五
    assert nxt2 == dt(2026, 8, 17, 9, 0)  # 周一


@pytest.mark.parametrize("expr", ["* * * *", "60 * * * *", "* 24 * * *", "*/0 * * * *", "5-1 * * * *"])
def test_invalid_expressions_raise(expr):
    with pytest.raises(sq.CronError):
        sq.parse_cron(expr)


def test_run_job_passes_empty_list_not_none(monkeypatch):
    # 回归: job_args 为空时必须传 [] 给 fetch_quotes.main, 传 None 会误读父进程 argv。
    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(fetch_quotes, "main", fake_main)
    ns = argparse.Namespace(cmd=None, job_args=[])
    assert sq.run_job(ns) == 0
    assert captured["argv"] == []


def test_next_run_union_of_multiple_crons():
    # 交易时段日程: 9:20 起 / 午休 12-13 停 / 16:00 收盘。
    scheds = [
        sq.parse_cron("20-55/5 9 * * 1-5"),   # 9:20-9:55
        sq.parse_cron("*/5 10,11 * * 1-5"),   # 10:00-11:55
        sq.parse_cron("*/5 13-15 * * 1-5"),   # 13:00-15:55
        sq.parse_cron("0 16 * * 1-5"),        # 16:00
    ]
    # 9:00 -> 首个是 9:20
    assert sq.next_run(scheds, dt(2026, 8, 11, 9, 0)) == dt(2026, 8, 11, 9, 20)
    # 11:55 -> 跳过午休, 下一个是 13:00
    assert sq.next_run(scheds, dt(2026, 8, 11, 11, 55)) == dt(2026, 8, 11, 13, 0)
    # 15:57 -> 收盘 16:00
    assert sq.next_run(scheds, dt(2026, 8, 11, 15, 57)) == dt(2026, 8, 11, 16, 0)
    # 16:00 之后 -> 次日(周三)9:20
    assert sq.next_run(scheds, dt(2026, 8, 11, 16, 0)) == dt(2026, 8, 12, 9, 20)
