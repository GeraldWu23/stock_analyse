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
- Network caveat: Yahoo returns HTTP 429 for requests without a browser `User-Agent`,
  and Chinese endpoints (eastmoney/sina) are not reliably reachable from the VM. The
  code already sets a browser UA and retries with backoff. Unit tests are fully offline
  (they parse sample payloads), so tests do not require network access.
