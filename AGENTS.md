# AGENTS.md

## Cursor Cloud specific instructions

`stock_analyse` is a small Python 3.12 CLI that fetches stock **行情** (market quotes)
from Yahoo Finance's public chart API (no API key). It supports A-shares (`.SS`/`.SZ`),
HK (`.HK`), and US tickers.

- Dependencies are installed into a project-local virtualenv at `.venv` (gitignored).
  The startup update script recreates/refreshes it, so use `./.venv/bin/python` (or
  activate with `source .venv/bin/activate`) rather than the system Python.
- System package `python3.12-venv` is required to create the venv; it is preinstalled
  in the snapshot, so the update script does not (and should not) reinstall it.
- Standard commands (see `README.md`), run with the venv Python:
  - Run: `./.venv/bin/python -m stock_analyse [SYMBOLS...]`
  - Test: `./.venv/bin/python -m pytest -q`
  - Lint: `./.venv/bin/ruff check stock_analyse tests`
- Network caveat: Yahoo returns HTTP 429 for requests without a browser `User-Agent`.
  For A股/港股, `fetch_quotes.py` uses 腾讯 `qt.gtimg.cn` (primary) and 新浪 `hq.sinajs.cn`
  (fallback, needs a `Referer` header); both return GBK. Unit tests are fully offline
  (they parse sample payloads / mock the network), so tests do not require network access.
- `fetch_quotes.py` (repo root) is the A股/港股/ETF quote script (腾讯优先、新浪兜底);
  supports polling via `--interval <秒>` (+ optional `--count`). See its `--help`.
- Cursor auto-invocation is wired up two ways (both call the same fetch logic):
  - Skill: `.cursor/skills/fetch-quotes/SKILL.md` — agent runs `fetch_quotes.py` when asked for quotes.
  - MCP tool: `.cursor/mcp.json` starts `tools/quotes_mcp_server.py` (FastMCP, `mcp` 1.x), exposing
    `get_quotes` / `list_watchlist`. Run standalone for debugging: `python tools/quotes_mcp_server.py`.
