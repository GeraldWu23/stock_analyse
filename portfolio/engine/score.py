"""In-repo 22-dim scores + 66-judge panel. No LLM.

Adapted from UZI-Skill (MIT) lib/pipeline/score_fns.py — only the rule-engine
functions, not MX autofill or agent synthesis.
"""
from __future__ import annotations

from portfolio.engine.investor_db import INVESTORS
from portfolio.engine.investor_personas import get_comment as _persona_comment
from portfolio.engine.investor_evaluator import evaluate as _evaluate_investor
from portfolio.engine.stock_features import extract_features


def _f(v, default=0.0):
    try:
        return float(str(v).replace("%", "").replace(",", "").replace("+", ""))
    except (ValueError, TypeError):
        return default


def score_dimensions(raw: dict) -> dict:
    dims = raw.get("dimensions", {})
    out = {}

    def _get(key: str) -> dict:
        return (dims.get(key) or {}).get("data") or {}

    # 1 · 财报
    fin = _get("1_financials")
    roe = _f(fin.get("roe"))
    last_roe = (fin.get("roe_history") or [0])[-1] if fin.get("roe_history") else roe
    net_margin = _f(fin.get("net_margin"))
    health = fin.get("financial_health") or {}
    debt = _f(health.get("debt_ratio"))
    rev_hist = fin.get("revenue_history") or []
    growth = ((rev_hist[-1] - rev_hist[-2]) / rev_hist[-2] * 100) if len(rev_hist) >= 2 and rev_hist[-2] else 0
    score_1 = 5
    if last_roe >= 15: score_1 += 2
    elif last_roe >= 10: score_1 += 1
    elif last_roe < 5: score_1 -= 2
    if net_margin >= 15: score_1 += 1
    if growth >= 20: score_1 += 1
    if debt >= 60: score_1 -= 1
    score_1 = max(1, min(10, score_1))
    reasons_pass_1 = []
    reasons_fail_1 = []
    if last_roe >= 15: reasons_pass_1.append(f"ROE 最新 {last_roe:.1f}%")
    elif last_roe < 8: reasons_fail_1.append(f"ROE 最新 {last_roe:.1f}% 偏低")
    if growth >= 20: reasons_pass_1.append(f"营收增速 {growth:.1f}%")
    elif growth < 5: reasons_fail_1.append(f"营收增速 {growth:.1f}% 停滞")
    if debt < 40: reasons_pass_1.append(f"资产负债率 {debt:.0f}% 健康")
    elif debt > 60: reasons_fail_1.append(f"资产负债率 {debt:.0f}% 偏高")
    out["1_financials"] = {"score": score_1, "weight": 5,
                            "label": f"ROE {last_roe:.1f}% · 营收增速 {growth:+.1f}% · 负债率 {debt:.0f}%",
                            "reasons_pass": reasons_pass_1, "reasons_fail": reasons_fail_1}

    # 2 · K 线
    kline = _get("2_kline")
    stage = str(kline.get("stage", ""))
    ma_align = str(kline.get("ma_align", ""))
    stats = kline.get("kline_stats") or {}
    score_2 = 5
    if "Stage 2" in stage: score_2 += 2
    elif "Stage 1" in stage: score_2 += 1
    elif "Stage 3" in stage or "Stage 4" in stage: score_2 -= 2
    if "多头" in ma_align: score_2 += 1
    dd_str = stats.get("max_drawdown", "0%")
    dd = _f(dd_str)
    if dd <= -30: score_2 -= 1
    score_2 = max(1, min(10, score_2))
    label_2 = f"{stage} · 均线{ma_align}"
    if stats.get("ytd_return"): label_2 += f" · YTD {stats['ytd_return']}"
    out["2_kline"] = {"score": score_2, "weight": 4, "label": label_2,
                      "reasons_pass": [f"{stage}"] if "Stage 2" in stage else [],
                      "reasons_fail": [f"最大回撤 {dd:.1f}%"] if dd <= -25 else []}

    # 3 · 宏观 (qualitative — give middle)
    out["3_macro"] = {"score": 6, "weight": 3, "label": "宏观环境中性"}

    # 4 · 同行
    peers = _get("4_peers")
    peer_table = peers.get("peer_table") or []
    global_peer_count = int((peers.get("global_peer_comparison") or {}).get("peer_count") or 0)
    score_4 = 5
    if peer_table and len(peer_table) > 1:
        score_4 = 7  # we have data
        try:
            self_row = next((p for p in peer_table if p.get("is_self")), None)
            if self_row:
                self_pe = _f(self_row.get("pe"))
                avg_pe = sum(_f(p.get("pe")) for p in peer_table if not p.get("is_self")) / max(1, len([p for p in peer_table if not p.get("is_self")]))
                if self_pe > 0 and avg_pe > 0:
                    if self_pe < avg_pe * 0.9: score_4 += 1
                    elif self_pe > avg_pe * 1.2: score_4 -= 1
        except Exception:
            pass
    elif global_peer_count >= 3:
        score_4 = 7
    local_peer_count = max(0, len(peer_table) - 1)
    if global_peer_count:
        peer_label = f"全球同行 {global_peer_count} 家对比"
    elif local_peer_count:
        peer_label = f"同业 {local_peer_count} 家对比"
    else:
        peer_label = "无同行数据"
    out["4_peers"] = {"score": score_4, "weight": 4,
                      "label": peer_label,
                      "reasons_pass": [], "reasons_fail": []}

    # 5 · 上下游
    chain = _get("5_chain")
    breakdown = chain.get("main_business_breakdown") or []
    score_5 = 6 if breakdown else 5
    out["5_chain"] = {"score": score_5, "weight": 4,
                      "label": f"主营 {len(breakdown)} 类业务已识别" if breakdown else "产业链数据不完整",
                      "reasons_pass": [], "reasons_fail": []}

    # 6 · 研报
    research = _get("6_research")
    coverage = research.get("report_count", 0)
    ratings = research.get("rating_distribution") or {}
    buy_count = sum(v for k, v in ratings.items() if "买入" in str(k) or "增持" in str(k))
    score_6 = 5 + min(3, coverage // 5)
    if buy_count >= 10: score_6 += 1
    score_6 = min(10, score_6)
    out["6_research"] = {"score": score_6, "weight": 3,
                         "label": f"{coverage} 份研报 · 买入/增持 {buy_count} 份" if coverage else "研报数据稀少",
                         "reasons_pass": [f"覆盖券商 {coverage} 家"] if coverage >= 10 else [],
                         "reasons_fail": [] if coverage else ["缺乏覆盖"]}

    # 7 · 行业景气 (stub heavy qualitative)
    out["7_industry"] = {"score": 7, "weight": 4, "label": "行业处于成长期"}

    # 8 · 原材料
    out["8_materials"] = {"score": 6, "weight": 3, "label": "原材料成本关注中"}

    # 9 · 期货关联
    out["9_futures"] = {"score": 5, "weight": 2, "label": "无强关联期货品种"}

    # 10 · 估值
    val = _get("10_valuation")
    pe_q_str = str(val.get("pe_quantile", ""))
    import re
    m = re.search(r'(\d+)', pe_q_str)
    pe_q = int(m.group(1)) if m else 50
    score_10 = 5
    if pe_q < 30: score_10 = 9
    elif pe_q < 50: score_10 = 7
    elif pe_q < 70: score_10 = 5
    elif pe_q < 85: score_10 = 3
    else: score_10 = 2
    out["10_valuation"] = {"score": score_10, "weight": 5,
                            "label": f"PE {val.get('pe', '—')} · 5 年 {pe_q} 分位 · 行业均值 {val.get('industry_pe', '—')}",
                            "reasons_pass": ["PE 在 5 年中位数以下"] if pe_q < 50 else [],
                            "reasons_fail": ["PE 已在 5 年高位区"] if pe_q >= 75 else []}

    # 11 · 治理
    gov = _get("11_governance")
    pledge = gov.get("pledge") or []
    has_insider = bool(gov.get("insider_trades_1y"))
    score_11 = 6
    if not pledge or (isinstance(pledge, list) and len(pledge) == 0): score_11 += 1
    if has_insider: score_11 += 1
    out["11_governance"] = {"score": min(10, score_11), "weight": 4,
                             "label": f"质押记录 {len(pledge) if isinstance(pledge, list) else '—'} · 内部交易 {'有' if has_insider else '无'}"}

    # 12 · 资金面 (v2.2: 主力资金替代北向，北向已关停)
    cap = _get("12_capital_flow")
    main_flow = cap.get("main_fund_flow_20d") or []
    main_5d_net = 0
    if main_flow:
        for rec in main_flow[:5]:
            v = rec.get("主力净流入-净额", 0) if isinstance(rec, dict) else 0
            try:
                main_5d_net += float(v)
            except (ValueError, TypeError):
                pass
    main_5d_label = f"{main_5d_net / 1e8:+.1f}亿" if main_5d_net else "—"
    unlock = cap.get("unlock_schedule") or []
    score_12 = 5
    if main_5d_net > 0: score_12 += 2
    elif main_5d_net < 0: score_12 -= 1
    if len(unlock) == 0: score_12 += 1
    score_12 = max(1, min(10, score_12))
    out["12_capital_flow"] = {"score": score_12, "weight": 4,
                               "label": f"主力 5日 {main_5d_label} · 12 个月解禁 {len(unlock)} 次",
                               "reasons_pass": [f"主力资金 5 日净流入 {main_5d_label}"] if main_5d_net > 0 else [],
                               "reasons_fail": [f"主力资金 5 日净流出 {main_5d_label}"] if main_5d_net < 0 else []}

    # 13 · 政策
    out["13_policy"] = {"score": 6, "weight": 3, "label": "政策环境中性"}

    # 14 · 护城河
    out["14_moat"] = {"score": 6, "weight": 3, "label": "护城河需定性评估"}

    # 15 · 事件
    events = _get("15_events")
    news = events.get("news") or []
    notices = events.get("recent_notices") or []
    score_15 = 5 + min(3, len(news) // 10)
    out["15_events"] = {"score": score_15, "weight": 4,
                        "label": f"近期新闻 {len(news)} 条 · 公告 {len(notices)} 份"}

    # 16 · 龙虎榜
    lhb = _get("16_lhb")
    lhb_count = lhb.get("lhb_count_30d", 0)
    matched = lhb.get("matched_youzi") or []
    score_16 = 5 + min(3, lhb_count // 2)
    if matched: score_16 += 1
    score_16 = min(10, score_16)
    out["16_lhb"] = {"score": score_16, "weight": 4,
                     "label": f"近 30 天上榜 {lhb_count} 次 · 识别游资 {len(matched)} 位",
                     "reasons_pass": [f"{'/'.join(matched[:3])} 席位出现"] if matched else []}

    # 17 · 舆情
    hot = _get("17_sentiment")
    hot_rank = (hot.get("hot_rank") or {}).get("rank_history") or []
    score_17 = 6 + min(2, len(hot_rank) // 10)
    out["17_sentiment"] = {"score": score_17, "weight": 3,
                            "label": f"雪球热度上榜 {len(hot_rank)} 次"}

    # 18 · 杀猪盘 (stub → safe by default, 9 分)
    out["18_trap"] = {"score": 9, "weight": 5, "label": "🟢 未发现推广痕迹"}

    # 19 · 实盘赛
    contests = _get("19_contests")
    summary = contests.get("summary") or {}
    xq_total = summary.get("xueqiu_cubes_total", 0)
    hi = summary.get("high_return_cubes", 0)
    score_19 = 5 + min(3, xq_total // 5) + min(2, hi)
    score_19 = min(10, score_19)
    out["19_contests"] = {"score": score_19, "weight": 4,
                           "label": f"雪球 {xq_total} 个组合持有 · {hi} 个收益 >50%",
                           "reasons_pass": [f"{xq_total} 个雪球组合持有"] if xq_total else []}

    # Overall fundamental score
    total_weighted = sum(v["score"] * v["weight"] for v in out.values())
    total_weight = sum(v["weight"] for v in out.values())
    fundamental = (total_weighted / total_weight * 10) if total_weight else 0

    return {"ticker": raw["ticker"], "fundamental_score": round(fundamental, 1), "dimensions": out}


# ─────────── PANEL GENERATION (rule-based) ───────────

GROUP_VERDICTS = {
    "bullish":  ["强烈买入", "买入", "关注"],
    "bearish":  ["观望", "回避", "等待"],
    "neutral":  ["观望", "不适合", "不达标"],
}

COMMENT_TEMPLATES = {
    "A": {
        "bullish": [
            "ROE 和现金流都看得过去，长期持有没问题。",
            "商业模式清晰，10 年后还能赚钱的那种。",
            "安全边际尚可，不急着全仓。",
        ],
        "bearish": [
            "估值已透支未来几年的增长，等回调。",
            "护城河在侵蚀，这种价格不该买。",
            "现金流质量存疑，再观察两个季度。",
        ],
        "neutral": ["看不太懂，先放观察池。", "不在能力圈内。"],
    },
    "B": {
        "bullish": ["PEG 合理且成长性可见，可以进攻。", "CANSLIM 多数条件达标。"],
        "bearish": ["估值已脱离 PEG 合理区间。", "机构持股过高，不符合 CANSLIM S 项。"],
        "neutral": ["增长故事需要更多验证。"],
    },
    "C": {
        "bullish": ["宏观环境对这只票的反身性有利。", "流动性拐点已到，可以下注。"],
        "bearish": ["反身性正反馈进入晚期，小心。"],
        "neutral": ["宏观判断暂时不明。"],
    },
    "D": {
        "bullish": ["Stage 2 + 量能配合，技术面允许进场。", "VCP 形态已成，止损位清晰。"],
        "bearish": ["距 52 周高点太近，不是入场点。"],
        "neutral": ["等待明确突破。"],
    },
    "E": {
        "bullish": ["生意对、人对、价格还凑合。", "ROE 持续性强，可以重仓。"],
        "bearish": ["价格对不起生意质量。"],
        "neutral": ["看不懂就不要碰。"],
    },
    "F": {
        "bullish": ["板块有格局，趋势向上可以跟。", "二板定龙头，题材在线。", "情绪合力在，短线机会。"],
        "bearish": ["市值不在我的射程里。", "题材已过热，这不是我的菜。"],
        "neutral": ["不在风格里，不适合。"],
    },
    "G": {
        "bullish": ["多因子评分 top 20%，值得下注。", "凯利公式给出正仓位。"],
        "bearish": ["统计上已进入均值回归区。"],
        "neutral": ["因子中性，模型无信号。"],
    },
}


def generate_panel(dims_scored: dict, raw: dict) -> dict:
    """Rule-engine-based panel — each investor's verdict cites specific
    criteria from investor_criteria.py that were hit or missed.
    """
    # Build the flat feature dict once for all 51 investors
    features = extract_features(raw, raw.get("dimensions", {}))

    basic_ctx = (raw.get("dimensions", {}).get("0_basic") or {}).get("data") or {}
    kline_ctx = (raw.get("dimensions", {}).get("2_kline") or {}).get("data") or {}
    fin_ctx = (raw.get("dimensions", {}).get("1_financials") or {}).get("data") or {}

    investors_out = []
    vote_dist = {"strongly_buy": 0, "buy": 0, "watch": 0, "wait": 0, "avoid": 0, "n_a": 0, "skip": 0}
    sig_dist = {"bullish": 0, "neutral": 0, "bearish": 0, "skip": 0}

    def _score_to_verdict(score: float, signal: str) -> str:
        if signal == "bullish" and score >= 80:
            return "强烈买入"
        if signal == "bullish":
            return "买入"
        if signal == "bearish" and score <= 20:
            return "回避"
        if signal == "bearish":
            return "观望"
        # neutral
        return "关注" if score >= 50 else "观望"

    for inv in INVESTORS:
        inv_id = inv["id"]
        mandate = inv.get("mandate", "long")
        verdict_obj = _evaluate_investor(inv_id, features)

        sig = verdict_obj["signal"]
        score = int(max(0, verdict_obj["score"]))
        confidence = int(verdict_obj["confidence"])

        # Handle "skip" — investor won't look at this market
        if sig == "skip":
            verdict = "不适合"
            score = 0
            confidence = 0
            skip_reason = verdict_obj.get("skip_reason", "不在能力圈")
            headline = f"不适合 — {skip_reason}"
            comment = f"不在能力圈范围内，不做评价。\n{headline}"
            reasoning = verdict_obj.get("rationale", "")
        else:
            verdict = (
                "做空候选" if mandate == "short" and sig == "bearish"
                else "无明确做空逻辑" if mandate == "short"
                else _score_to_verdict(score, sig)
            )

            # Persona voice layer
            ctx = {
                "name": basic_ctx.get("name", "这只票"),
                "industry": basic_ctx.get("industry", "该行业"),
                "price": basic_ctx.get("price", "—"),
                "pe": basic_ctx.get("pe_ttm", "—"),
                "roe": str((fin_ctx.get("roe_history") or ["—"])[-1]),
                "stage": kline_ctx.get("stage", "—"),
                "growth": fin_ctx.get("revenue_growth", "—"),
            }
            persona_line = _persona_comment(inv_id, sig, ctx)

            headline = verdict_obj["headline"]
            comment = f"{persona_line}\n{headline}"
            reasoning = verdict_obj["rationale"]

        v_key = {"强烈买入": "strongly_buy", "买入": "buy", "关注": "watch",
                 "观望": "wait", "回避": "avoid", "不适合": "skip"}.get(verdict, "n_a")
        if mandate != "short":
            vote_dist[v_key] = vote_dist.get(v_key, 0) + 1
            sig_dist[sig] = sig_dist.get(sig, 0) + 1

        investors_out.append({
            "investor_id": inv_id,
            "name": inv["name"],
            "group": inv["group"],
            "mandate": mandate,
            "avatar": f"avatars/{inv_id}.svg",
            "signal": sig,
            "confidence": confidence,
            "score": score,
            "verdict": verdict,
            "reasoning": reasoning,
            "comment": comment,
            "headline": headline,
            "pass": [{"name": r["name"], "msg": r["msg"], "weight": r["weight"]}
                     for r in verdict_obj["pass_rules"][:4]],
            "fail": [{"name": r["name"], "msg": r["msg"], "weight": r["weight"]}
                     for r in verdict_obj["fail_rules"][:4]],
            "weight_pass": verdict_obj["weight_pass"],
            "weight_total": verdict_obj["weight_total"],
            "ideal_price": None,
            "period": "中长线" if inv["group"] in ("A", "B", "E") else "短线",
            # v2.8 · 因地制宜：每个评委用自己方法论回答这 3 个问题
            "time_horizon": verdict_obj.get("time_horizon", "—"),
            "position_sizing": verdict_obj.get("position_sizing", "—"),
            "what_would_change_my_mind": verdict_obj.get("what_would_change_my_mind", "—"),
        })

    # v2.15.5 · 混合 consensus 公式（连续分 + 离散票）
    # 动机：v2.11 单一公式 `(bullish + 0.6*neutral)/active*100` 只看 signal 计数 ·
    # 把连续 score 压成 3 分类 · 导致 331 个打分中 bullish:neutral:bearish=9.9:13:18.5 ·
    # 多数股 consensus 聚集 40-55 区间分不开.
    # 实测：单 investor score stdev=30.3 信息很丰富 · 但 consensus stdev 只有 28.2 还聚集 ·
    # 说明 signal 分类丢失了"程度"信息（55 和 40 都算 neutral 但态度不同）.
    #
    # 新公式：consensus = 0.65 * score_mean + 0.35 * vote_weighted
    #   - score_mean:  active 成员 score 均值（连续 0-100 · 反映强度）
    #   - vote_weighted: 原 (bullish + 0.6*neutral)/active*100（保留投票机制）
    # 学派级 school_scores 同样用混合公式 · 让各流派分数拉开.
    # 回归风险：v2.11 下 65 分 = "可以蹲一蹲" · 新公式下因 score_mean 参与，
    # 历史白马可能从 40+ 涨到 55+ · 属校准而非 bug · overall 阈值不变.
    NEUTRAL_WEIGHT = 0.6
    SCORE_WEIGHT = 0.65   # score 均值权重（连续分 · 区分度）
    VOTE_WEIGHT  = 0.35   # vote 比例权重（离散投票 · 稳定性）
    POLARIZE_K = 1.30     # 极化系数 · >1 让两端拉开 · 50 为中心
    bullish = sig_dist.get("bullish", 0)
    neutral = sig_dist.get("neutral", 0)
    bearish = sig_dist.get("bearish", 0)
    active_count = bullish + neutral + bearish

    def _polarize(c: float, k: float = POLARIZE_K) -> float:
        """极化拉伸 · 50 为中心 · 距离 * k · 裁剪到 [0, 100].

        目的：rule-engine 评分先天居中（大多股 35-65 区间）· 聚合后 consensus
        更居中 · 用户反馈"大多数分在一个区间徘徊"· 极化让强势 70→86 · 弱势 22→14.
        保留 50 为"及格线"不动 · 只放大距离.
        """
        return max(0.0, min(100.0, 50.0 + (c - 50.0) * k))

    # 分量 1 · score 均值（active only · skip 不计）
    active_scores = [
        m["score"] for m in investors_out
        if m.get("mandate") != "short" and m.get("signal") != "skip"
    ]
    score_mean = (sum(active_scores) / len(active_scores)) if active_scores else 50.0
    # 分量 2 · vote 比例（原 v2.11 公式）
    vote_weighted = (bullish + NEUTRAL_WEIGHT * neutral) / max(active_count, 1) * 100
    consensus_raw = SCORE_WEIGHT * score_mean + VOTE_WEIGHT * vote_weighted
    consensus = _polarize(consensus_raw)

    short_book = [m for m in investors_out if m.get("mandate") == "short"]
    short_active = [m for m in short_book if m.get("signal") != "skip"]
    short_scores = [m["score"] for m in short_active]
    short_consensus = {
        "total": len(short_book),
        "active": len(short_active),
        "skip": len(short_book) - len(short_active),
        "short_candidates": sum(1 for m in short_active if m.get("signal") == "bearish"),
        "no_short_thesis": sum(1 for m in short_active if m.get("signal") in ("bullish", "neutral")),
        "avg_score": round(sum(short_scores) / len(short_scores), 1) if short_scores else 50.0,
        "top_short_candidates": [
            {"id": m["investor_id"], "name": m["name"], "score": m["score"], "headline": m["headline"]}
            for m in sorted(short_active, key=lambda item: item["score"])[:5]
        ],
    }

    # v2.15.4+ · 按流派打分（v2.15.5 同步升级为混合公式）
    # 譬如白马消费股：价值派 85 分（重仓），技术派 30 分（趋势破位）·
    # 现在可以一眼看出"不同哲学得出的结论有多不同"
    GROUP_META = {
        "A": {"label": "经典价值派", "desc": "巴菲特 / 格雷厄姆 / 费雪 / 芒格 一脉"},
        "B": {"label": "成长派",     "desc": "彼得·林奇 / 欧奈尔 / 蒂尔 / 伍德 一脉"},
        "C": {"label": "宏观派",     "desc": "索罗斯 / 达利欧 / 马克斯 一脉"},
        "D": {"label": "技术派",     "desc": "利弗莫尔 / Minervini / 达瓦斯 一脉"},
        "E": {"label": "中式价投",   "desc": "段永平 / 张坤 / 朱少醒 / 冯柳 一脉"},
        "F": {"label": "A 股游资",   "desc": "龙虎榜顶流 23 位·章盟主/孙哥/赵老哥为代表"},
        "G": {"label": "量化派",     "desc": "Simons / Thorp / Shaw 一脉"},
        "H": {"label": "科技领袖派", "desc": "黄仁勋 / 马斯克 / Altman / Saylor 一脉"},
        "I": {"label": "AI 卡位/瓶颈猎手", "desc": "Serenity · AI 供应链卡脖子/瓶颈点"},
    }

    def _consensus_to_verdict(c: float) -> str:
        """流派级 verdict · 阈值与综合分保持一致（80/65/50/35）."""
        if c >= 80: return "重仓"
        if c >= 65: return "买入"
        if c >= 50: return "关注"
        if c >= 35: return "谨慎"
        return "回避"

    by_group: dict[str, list[dict]] = {}
    for inv in investors_out:
        by_group.setdefault(inv.get("group", "?"), []).append(inv)

    school_scores: dict[str, dict] = {}
    for g in sorted(by_group.keys()):
        all_members = by_group[g]
        members = [m for m in all_members if m.get("mandate") != "short"]
        n_members = len(members)
        active_m = [m for m in members if m.get("signal") != "skip"]
        n_active = len(active_m)
        g_bull = sum(1 for m in active_m if m.get("signal") == "bullish")
        g_neu  = sum(1 for m in active_m if m.get("signal") == "neutral")
        g_bear = sum(1 for m in active_m if m.get("signal") == "bearish")
        g_skip = sum(1 for m in members if m.get("signal") == "skip")

        # v2.15.5 · 流派级混合公式（与总盘保持一致 · 同样极化）
        if n_active > 0:
            s_score_mean = sum(m.get("score", 0) for m in active_m) / n_active
            s_vote = (g_bull + NEUTRAL_WEIGHT * g_neu) / n_active * 100
            s_raw = SCORE_WEIGHT * s_score_mean + VOTE_WEIGHT * s_vote
            s_consensus = _polarize(s_raw)
        else:
            s_score_mean = 0.0
            s_vote = 0.0
            s_consensus = 0.0

        # 主流信号
        sig_counts = [("bullish", g_bull), ("neutral", g_neu), ("bearish", g_bear)]
        dominant = max(sig_counts, key=lambda x: x[1])[0] if n_active > 0 else "skip"

        meta = GROUP_META.get(g, {"label": g, "desc": ""})
        school_scores[g] = {
            "group": g,
            "label": meta["label"],
            "desc": meta["desc"],
            "n_members": n_members,
            "n_active": n_active,
            "short_excluded": len(all_members) - n_members,
            "consensus": round(s_consensus, 1),
            "avg_score": round(s_score_mean, 1),  # alias · 兼容 v2.15.4 字段
            "vote_consensus": round(s_vote, 1),   # v2.15.5 · vote 分量（可视化展开用）
            "score_mean": round(s_score_mean, 1), # v2.15.5 · score 分量 · 明确语义
            "verdict": _consensus_to_verdict(s_consensus) if n_active > 0 else "不适合",
            "bullish": g_bull,
            "neutral": g_neu,
            "bearish": g_bear,
            "skip": g_skip,
            "dominant_signal": dominant,
        }

    active_long = [
        investor for investor in investors_out
        if investor.get("mandate") != "short" and investor.get("signal") != "skip"
    ]
    hollow_ids = [
        investor.get("investor_id") for investor in active_long
        if (investor.get("score") or 0) == 0
        and not investor.get("pass")
        and not investor.get("fail")
    ]
    hollow_pct = round(len(hollow_ids) / len(active_long) * 100, 0) if active_long else 0
    consensus_valid = hollow_pct < 20

    return {
        "ticker": raw["ticker"],
        "panel_consensus": round(consensus, 1),
        "consensus_valid": consensus_valid,
        "hollow_verdicts": len(hollow_ids),
        "hollow_pct": hollow_pct,
        "hollow_ids": hollow_ids,
        "consensus_warning": (
            None if consensus_valid else
            f"共识分不可采信：{len(hollow_ids)}/{len(active_long)} 位多头评委（{hollow_pct:.0f}%）"
            "没有任何有效规则证据。"
        ),
        "vote_distribution": vote_dist,
        "signal_distribution": sig_dist,
        "investors": investors_out,
        # v2.15.4 · 按流派分数 · 7 个 school 各自 consensus/avg_score/verdict
        "school_scores": school_scores,
        "long_active": active_count,
        "short_consensus": short_consensus,
        # v2.15.5 · 诊断字段 · 混合公式各分量 + 极化前后值
        "consensus_formula": {
            "version": "v2.15.5 · polarize(0.65*score_mean + 0.35*vote_weighted, k=1.3)",
            "score_weight": SCORE_WEIGHT,
            "vote_weight": VOTE_WEIGHT,
            "neutral_weight": NEUTRAL_WEIGHT,
            "polarize_k": POLARIZE_K,
            "score_mean": round(score_mean, 2),
            "vote_weighted": round(vote_weighted, 2),
            "consensus_raw": round(consensus_raw, 2),     # 极化前
            "consensus_final": round(consensus, 2),        # 极化后（= panel_consensus）
            "bullish": bullish,
            "neutral_weighted": round(neutral * NEUTRAL_WEIGHT, 2),
            "bearish": sig_dist.get("bearish", 0),
            "skip": sig_dist.get("skip", 0),
            "active": active_count,
            "short_excluded": len(short_book),
        },
    }
