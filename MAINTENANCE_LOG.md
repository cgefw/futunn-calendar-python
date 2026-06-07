# Maintenance Log

This log is intended for humans and AI agents maintaining the repository.

## 2026-06-06

- Created `futunn-calendar` Python package as an unofficial, experimental
  wrapper for webpage JSON responses used by a financial calendar page.
- Added list/detail wrapper, pagination helpers, models, examples, and CLI.
- Added DuckDB sync support with `calendar_events`, `calendar_indicator_history`, and `calendar_sync_runs`.
- Added event-time refresh daemon in `scripts/event_timer_refresh.py`.
- Published private GitHub repository: `cgefw/futunn-calendar-python`.
- Added Chinese README.
- Added install skill under `skills/install-futunn-calendar-python`.
- Released code state as `0.3.0` and changed DuckDB from hard dependency to optional extra:
  - Core install: `python -m pip install -e .`
  - DuckDB install: `python -m pip install -e ".[duckdb]"`
- Updated install skill to ask whether to install DuckDB support and whether to enable sync setup.
- Added Codex/Claude Code one-command install instructions.
- Changed GitHub repository visibility target to public.
- Removed environment-specific wording from install instructions and skill docs.
- Generalized install defaults to user home paths and added Windows PowerShell install support.
- Added first-screen unofficial/personal-research/data-redistribution warnings.
- Added `DATA_NOTICE.md`.
- Changed package metadata and docs away from official/stable API positioning.
- Changed code license metadata to PolyForm Noncommercial License 1.0.0.

## 2026-06-07

- Renamed `AI_PROJECT_OVERVIEW.md` to `AGENTS.md`.
- Updated `scripts/event_timer_refresh.py` so default retries follow absolute offsets from `event_time_utc`.
- Kept explicit `--retry-schedule` as legacy fixed-delay behavior.
- Added hourly default retry controls through `--retry-interval-seconds` and `--max-refresh-hours`.
- Ensured events stop being tracked once `actual` is populated.
- Ensured missing `actual` jobs expire after the configured max refresh window.
- Updated README files to document event-time actual refresh behavior.
- Checked tracked files for accidental API keys, `.env` content, DuckDB files, local data files, and bundled datasets.
- Fixed duplicate event refresh scheduling race in `scripts/event_timer_refresh.py` by tracking running event keys in `self.running_jobs` and skipping them in `scan_and_schedule()`.

## Maintenance Notes

- Keep core imports free of DuckDB imports.
- Keep DuckDB schema changes backward-compatible when possible.
- Update this log whenever install flow, schema, retry behavior, or GitHub-facing docs change.
- Do not describe the project as affiliated, official, stable, commercially
  licensed, or as a supported public API.
