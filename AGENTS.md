# stock_analyse · Agent instructions

This repo vendors the **stock-deep-analyzer** Cursor plugin (UZI-Skill) so Cloud Agents can run A-share / HK / US deep analysis without a marketplace install.

## Plugin location

- Plugin root: `.cursor/plugins/stock-deep-analyzer`
- Upstream: https://github.com/wbh604/UZI-Skill (MIT) — see `.cursor/plugins/stock-deep-analyzer/SOURCE.md`
- Python entry: `python .cursor/plugins/stock-deep-analyzer/run.py <ticker> --no-browser`
- Full playbook: `.cursor/plugins/stock-deep-analyzer/AGENTS.md`
- Core workflow: `.cursor/skills/deep-analysis/SKILL.md`

Always `cd` to `.cursor/plugins/stock-deep-analyzer` before running plugin Python.

## First-time setup

```bash
python3 -m pip install -r .cursor/plugins/stock-deep-analyzer/requirements.txt
# optional, for HTML report screenshots:
python3 -m playwright install chromium
```

Use the repo `.venv` when it exists:

```bash
.venv/bin/pip install -r .cursor/plugins/stock-deep-analyzer/requirements.txt
```

## How to invoke

Use the `/stock-deep-analyzer:` prefix (short names do not always resolve):

| User says | Do this |
|---|---|
| `/stock-deep-analyzer:analyze-stock 贵州茅台` or "深度分析 00700.HK" | Two-stage deep path in `deep-analysis` skill (`stage1` → agent role-play → `stage2`) |
| `/stock-deep-analyzer:quick-scan 002273` or "快速看看" | `python run.py <ticker> --depth lite --no-browser` |
| `/stock-deep-analyzer:dcf 600519` | DCF command in `.cursor/commands/dcf.md` |
| `/stock-deep-analyzer:scan-trap <ticker>` | Trap-detector skill |
| "分析 XXX" with no depth specified | Medium CLI path: `python run.py <ticker> --no-browser` |

Tickers: `600519.SH` / `002273.SZ` / `00700.HK` / `AAPL` / Chinese names.

## Rules

1. Do not invent prices, multiples, or financials. Use script output, cache JSON, or current public sources.
2. `--depth deep` requires the agent review loop (`agent_analysis.json` with `agent_reviewed: true`). Do not skip it.
3. Lite/medium may run CLI-only and summarize the HTML/JSON.
4. This Cloud Agent environment is often overseas. If East Money / akshare time out, say so, keep `_data_gaps.json`, and fall back to `yfinance` / public web sources. Optional `MX_APIKEY` improves A-share coverage (see `.cursor/plugins/stock-deep-analyzer/.env.example`). Never commit secrets.
5. Reports land in `.cursor/plugins/stock-deep-analyzer/skills/deep-analysis/scripts/reports/` (gitignored).

## Personal holdings

Canonical snapshot (date + cash + positions): `portfolio/HOLDINGS.md`. Machine copy: `portfolio/holdings.json`. CSV for `--portfolio`: `portfolio/holdings.csv`.

When the user says 我的持仓 / 我监控的票 / 拿一支我的股票, read `portfolio/HOLDINGS.md` first. **Shares are sticky:** do not change `shares` / 持仓 unless the user says they traded; mark to market with live price × shares. Ordinary-account total already includes cash; do not add cash on top. The 100-share 电力ETF博时 stub is not the 9% cash sleeve.

**Display rule:** in user-facing replies and markdown tables, use Chinese names (科创人工智能ETF、电网设备ETF、绿色电力ETF、南方航空、纳斯达克ETF、黄金ETF、太古地产、长鑫科技、电力ETF博时). Do not show ticker codes unless the user asks. Codes stay in `holdings.json` / CSV only.

ETF/LOF rows are baskets, not single stocks. Do not run the 65-judge equity pipeline on them; analyze the index + top holdings instead.
