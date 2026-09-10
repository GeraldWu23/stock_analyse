# stock_analyse

Hong Kong market snapshots plus the vendored **stock-deep-analyzer** Cursor plugin (UZI-Skill) for A-share / HK / US fundamental analysis.

## Stock deep analyzer

Installed at `.cursor/plugins/stock-deep-analyzer` from [wbh604/UZI-Skill](https://github.com/wbh604/UZI-Skill) (MIT). Cloud Agents load the skills from `.cursor/skills/`.

### Setup

```bash
python3 -m pip install -r .cursor/plugins/stock-deep-analyzer/requirements.txt
```

### Run

```bash
# quick / medium report (no agent jury)
python .cursor/plugins/stock-deep-analyzer/run.py 00700.HK --no-browser
python .cursor/plugins/stock-deep-analyzer/run.py AAPL --depth lite --no-browser
```

In Cursor Agent chat (always use the prefix):

- `/stock-deep-analyzer:analyze-stock 贵州茅台` — 22-dimension deep analysis
- `/stock-deep-analyzer:quick-scan 002273` — ~30s scan
- `/stock-deep-analyzer:dcf 600519` — DCF
- `/stock-deep-analyzer:scan-trap 002217` — pump-and-dump check

See `AGENTS.md` for agent workflow and `.cursor/plugins/stock-deep-analyzer/README.md` for the upstream manual.

Personal holdings snapshot (dated): `portfolio/HOLDINGS.md`.
