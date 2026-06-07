# AGENTS: futunn-calendar-python

This file is for AI coding agents maintaining the project.

## Purpose

`futunn-calendar-python` is an unofficial, experimental wrapper for publicly
reachable webpage JSON responses used by this financial calendar page:

```text
https://news.futunn.com/new-calendar
```

It supports core event fetching and optional DuckDB persistence/sync.

Do not describe the project as official, affiliated, stable, commercially
licensed, or as a supported public API. The package provides code only and does
not grant data rights. User-facing docs should keep the first-screen disclaimer:

```text
Unofficial, not affiliated with Futu/Futunn. For personal research only. Do not redistribute data.
```

## Repository

```text
https://github.com/cgefw/futunn-calendar-python
```

The repository is public.

## Package Layout

```text
src/futunn_calendar/client.py      HTTP wrapper and pagination
src/futunn_calendar/models.py      Calendar/event/detail data models
src/futunn_calendar/constants.py   Webpage enum values and aliases
src/futunn_calendar/cli.py         futunn-calendar CLI
src/futunn_calendar/storage.py     Optional DuckDB persistence
scripts/event_timer_refresh.py     Event-time actual-value refresher
examples/demo.py                   Basic usage example
examples/sync_duckdb.py            DuckDB sync example
tests/test_client.py               Unit tests for client/model behavior
```

## Dependency Model

Core install:

```text
requests
```

Optional DuckDB install:

```text
duckdb extra: python -m pip install -e ".[duckdb]"
```

Do not make DuckDB a hard dependency unless the user explicitly asks. Core
usage should keep working without DuckDB installed.

## DuckDB Tables

`sync_calendar_to_duckdb(...)` creates:

```text
calendar_events
calendar_indicator_history
calendar_sync_runs
```

`scripts/event_timer_refresh.py` also creates:

```text
calendar_event_refresh_jobs
```

The durable event identity is `event_key`, currently derived from:

```text
newsUniqueId OR articleId OR date|item_type|timestamp|title
```

## Important Behaviors

- Exact 3-star filtering should use `stars=["3"]`, not `"3,4,5"`.
- Raw webpage JSON output should be available through `page.raw`.
- If DuckDB is not installed, core imports should still work.
- `sync-duckdb` should fail with a clear install-extra message when DuckDB is missing.
- DuckDB event/detail writes should stay transactional; failed syncs must not leave partially refreshed event rows.
- Event-time refresh waits until event time plus `--post-delay`, then retries hourly on absolute `event_time_utc` offsets until `actual` appears or `--max-refresh-hours` expires.
- `--retry-schedule` is still available for explicit legacy fixed-delay behavior, but it is not the default.
- Explicit retry schedules must use positive delays and positive repeat counts; do not allow zero-delay polling loops.

## Validation

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m py_compile src/futunn_calendar/*.py scripts/event_timer_refresh.py examples/*.py
```

If testing optional no-DuckDB behavior, use a clean virtual environment with only `requests` installed.

## Legal/Positioning Notes

- Keep `DATA_NOTICE.md` linked from both READMEs.
- Keep the Terms, robots.txt, and official OpenAPI links in the README first screen.
- Avoid wording such as "official API", "stable data source", "commercial use",
  "redistribute data", or "guaranteed interface".
- Do not add bundled datasets, database files, scraped examples, or large raw
  response dumps to the repository.
- The user explicitly asked not to add anti-abuse guards or crawl-strength
  limits in this revision; do not add behavior changes under the legal-docs
  commit unless they ask again.

## Security

Do not commit:

```text
.env
.venv/
.gh-config/
dist/
*.duckdb
*.duckdb.wal
data/
logs/
```

This library should not contain AI API keys.
