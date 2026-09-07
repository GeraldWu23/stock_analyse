#!/usr/bin/env python3
"""定时调度脚本 schedule_quotes.py

用**标准 5 段 cron 表达式**定时执行任务, 默认调用同目录的 ``fetch_quotes.py`` 拉行情,
也可以用 ``--cmd`` 跑任意 shell 命令。纯标准库实现, 无需第三方依赖。

cron 字段 (分 时 日 月 周)::

    ┌── 分钟   0-59
    │ ┌── 小时 0-23
    │ │ ┌── 日   1-31
    │ │ │ ┌── 月 1-12
    │ │ │ │ ┌── 周 0-7 (0 和 7 都表示周日)
    * * * * *

每段支持: ``*``、``a-b`` 范围、``*/n`` 或 ``a-b/n`` 步长、``a,b,c`` 列表。
"日"和"周"都被限定(都不是 ``*``)时, 命中任意一个即算命中(与标准 cron 一致)。

用法::

    # 交易时段(周一到周五 9:00-15:00)每 5 分钟拉一次内置自选
    python schedule_quotes.py --cron "*/5 9-15 * * 1-5"

    # 每天 15:05 拉指定标的(-- 之后的参数会原样传给 fetch_quotes.py)
    python schedule_quotes.py --cron "5 15 * * *" -- sh600029 hk01113

    # 每 10 分钟跑任意命令
    python schedule_quotes.py --cron "*/10 * * * *" --cmd "python other.py"

    # 立即先跑一次再进入定时(便于验证)
    python schedule_quotes.py --cron "*/5 * * * *" --run-now --max-runs 3

    # 多段 --cron 取并集(如交易时段: 9:20起/午休停/16:00收盘)
    python schedule_quotes.py \
        --cron "20-55/5 9 * * 1-5" --cron "*/5 10,11 * * 1-5" \
        --cron "*/5 13-15 * * 1-5" --cron "0 16 * * 1-5"

时间基准为**本机本地时间**。按 Ctrl+C 结束。
"""

from __future__ import annotations

import argparse
import dataclasses
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _now() -> datetime:
    """当前本地时间(时区感知)。"""
    return datetime.now(timezone.utc).astimezone()

# (下界, 上界) 对应 分/时/日/月/周
_FIELD_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
_FIELD_NAMES = ["分钟", "小时", "日", "月", "周"]
# 未来最多向前搜索多少分钟(约 4 年), 用于探测不可能的表达式。
_MAX_LOOKAHEAD_MIN = 4 * 366 * 24 * 60


class CronError(ValueError):
    """cron 表达式非法时抛出。"""


def _parse_field(spec: str, lo: int, hi: int, name: str) -> set[int]:
    """把单个 cron 字段解析成允许值集合。"""
    values: set[int] = set()
    for part in spec.split(","):
        if not part:
            raise CronError(f"{name}字段为空")
        step = 1
        body = part
        if "/" in body:
            body, step_s = body.split("/", 1)
            try:
                step = int(step_s)
            except ValueError:
                raise CronError(f"{name}字段步长非法: {part}") from None
            if step <= 0:
                raise CronError(f"{name}字段步长必须为正: {part}")
        if body == "*":
            start, end = lo, hi
        elif "-" in body:
            a, b = body.split("-", 1)
            try:
                start, end = int(a), int(b)
            except ValueError:
                raise CronError(f"{name}字段范围非法: {part}") from None
        else:
            try:
                start = end = int(body)
            except ValueError:
                raise CronError(f"{name}字段值非法: {part}") from None
        if start < lo or end > hi or start > end:
            raise CronError(f"{name}字段超出范围 [{lo},{hi}]: {part}")
        values.update(range(start, end + 1, step))
    return values


@dataclasses.dataclass
class CronSchedule:
    """解析后的 cron 计划, 可判断某时刻是否命中并求下一次命中时间。"""

    minute: set[int]
    hour: set[int]
    dom: set[int]
    month: set[int]
    dow: set[int]
    dom_star: bool
    dow_star: bool

    def matches(self, dt: datetime) -> bool:
        if dt.minute not in self.minute:
            return False
        if dt.hour not in self.hour:
            return False
        if dt.month not in self.month:
            return False
        # cron 周: 周日=0..周六=6; Python weekday(): 周一=0..周日=6。
        cron_dow = (dt.weekday() + 1) % 7
        dom_ok = dt.day in self.dom
        dow_ok = cron_dow in self.dow
        if self.dom_star and self.dow_star:
            return True
        if self.dom_star:
            return dow_ok
        if self.dow_star:
            return dom_ok
        # 日和周都被限定: 命中其一即可(Vixie cron 行为)。
        return dom_ok or dow_ok

    def next_after(self, dt: datetime) -> datetime:
        """返回严格晚于 ``dt`` 的下一次命中时间(分钟精度)。"""
        cur = dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
        for _ in range(_MAX_LOOKAHEAD_MIN):
            if self.matches(cur):
                return cur
            cur += timedelta(minutes=1)
        raise CronError("未来 4 年内没有匹配的执行时间, 请检查表达式")


def next_run(schedules: list[CronSchedule], after: datetime) -> datetime:
    """多段计划的并集: 返回晚于 ``after`` 的最近一次命中时间。"""
    return min(s.next_after(after) for s in schedules)


def parse_cron(expr: str) -> CronSchedule:
    """解析 5 段 cron 表达式。"""
    fields = expr.split()
    if len(fields) != 5:
        raise CronError(f"需要 5 个字段(分 时 日 月 周), 实际 {len(fields)} 个: {expr!r}")
    sets = [
        _parse_field(f, lo, hi, name)
        for f, (lo, hi), name in zip(fields, _FIELD_RANGES, _FIELD_NAMES)
    ]
    minute, hour, dom, month, dow = sets
    if 7 in dow:  # 7 归一化为 0(都表示周日)
        dow = (dow - {7}) | {0}
    return CronSchedule(
        minute=minute,
        hour=hour,
        dom=dom,
        month=month,
        dow=dow,
        dom_star=(fields[2] == "*"),
        dow_star=(fields[4] == "*"),
    )


def run_job(args: argparse.Namespace) -> int:
    """执行一次任务, 返回退出码。"""
    if args.cmd:
        print(f"$ {args.cmd}", flush=True)
        return subprocess.call(args.cmd, shell=True)
    # 默认: 复用 fetch_quotes 的 main(), job_args 原样透传(如股票代码)。
    # 注意: 必须传列表(可为空), 传 None 会让 argparse 去读父进程的 sys.argv。
    import fetch_quotes

    return fetch_quotes.main(args.job_args)


def _run_and_report(args: argparse.Namespace, scheduled: datetime | None = None) -> None:
    now = _now().strftime("%Y-%m-%d %H:%M:%S")
    tag = f" (计划 {scheduled:%H:%M})" if scheduled else ""
    print(f"\n———— 执行 @ {now}{tag} ————", flush=True)
    try:
        code = run_job(args)
        if code:
            print(f"[任务退出码 {code}]", file=sys.stderr, flush=True)
    except Exception as exc:  # noqa: BLE001 - 单次任务失败不应中断整个调度循环
        print(f"[任务异常] {exc}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="schedule_quotes.py",
        description="用 cron 表达式定时执行 fetch_quotes(或任意命令)",
    )
    parser.add_argument(
        "--cron",
        required=True,
        action="append",
        metavar="表达式",
        help='5 段 cron, 如 "*/5 9-15 * * 1-5"(注意加引号)。可重复多次, 取并集。',
    )
    parser.add_argument(
        "--cmd",
        default=None,
        help="要执行的任意 shell 命令; 缺省则运行 fetch_quotes",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        metavar="N",
        help="最多执行多少次后退出; 0 表示一直运行",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="启动时立即先执行一次, 再进入定时循环",
    )
    parser.add_argument(
        "job_args",
        nargs="*",
        help="传给 fetch_quotes 的参数(用 -- 分隔), 如股票代码",
    )
    args = parser.parse_args(argv)

    try:
        schedules = [parse_cron(expr) for expr in args.cron]
    except CronError as exc:
        print(f"cron 表达式错误: {exc}", file=sys.stderr)
        return 2

    target = args.cmd if args.cmd else "fetch_quotes " + " ".join(args.job_args)
    crons = " | ".join(args.cron)
    print(
        f"已启动定时任务: cron=[{crons}] → {target.strip()}\n"
        f"时间基准: 本地时间 | 结束: Ctrl+C",
        flush=True,
    )

    runs = 0
    try:
        if args.run_now:
            _run_and_report(args)
            runs += 1
            if args.max_runs and runs >= args.max_runs:
                return 0

        while True:
            nxt = next_run(schedules, _now())
            print(f"下次执行: {nxt:%Y-%m-%d %H:%M}", flush=True)
            # 分段 sleep, 便于对系统休眠/改表进行自我校正。
            while True:
                remaining = (nxt - _now()).total_seconds()
                if remaining <= 0:
                    break
                time.sleep(min(remaining, 30))
            _run_and_report(args, scheduled=nxt)
            runs += 1
            if args.max_runs and runs >= args.max_runs:
                break
    except KeyboardInterrupt:
        print("\n已停止定时任务。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
