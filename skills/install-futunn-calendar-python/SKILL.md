---
name: install-futunn-calendar-python
description: Install, update, verify, or set up the unofficial futunn-calendar Python webpage JSON wrapper from cgefw/futunn-calendar-python. Use when the user asks to install the calendar wrapper, DuckDB sync command, monthly update script, or event-time refresh daemon in a local Python environment.
---

# Install Futunn Calendar Python

This project is unofficial, not affiliated with Futu/Futunn, for personal
research only, and does not grant rights to redistribute data.

## Workflow

Use this skill to install or update the unofficial financial-calendar webpage
JSON wrapper:

```text
https://github.com/cgefw/futunn-calendar-python
```

Default paths:

```text
Unix-like project: $HOME/futunn-calendar-python
Unix-like DuckDB:  $HOME/data/futunn_calendar.duckdb
Windows project:   $HOME\futunn-calendar-python
Windows DuckDB:    $HOME\data\futunn_calendar.duckdb
```

Do not upload or print secrets. This project does not require AI keys.

## Install Or Update

Before installing, ask the user two short questions:

1. Whether to install DuckDB support.
2. If DuckDB support is installed, whether to enable DuckDB sync setup.

Recommended defaults:

```text
Install DuckDB support: yes
Enable DuckDB sync: yes if the user wants a local database, no for core usage
```

Prefer the bundled script for the user's operating system:

```bash
bash scripts/install.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```

Custom paths:

```bash
bash scripts/install.sh \
  "$HOME/futunn-calendar-python" \
  "$HOME/data/futunn_calendar.duckdb"
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1 `
  -ProjectDir "$HOME\futunn-calendar-python" `
  -DbPath "$HOME\data\futunn_calendar.duckdb"
```

The script clones or pulls the repo, creates `.venv`, installs the package editable, verifies imports and CLI, and creates the DuckDB data directory.

For non-interactive installs, pass choices through environment variables:

```bash
INSTALL_DUCKDB=yes ENABLE_SYNC=yes \
bash scripts/install.sh
```

```powershell
$env:INSTALL_DUCKDB = "yes"
$env:ENABLE_SYNC = "yes"
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```

Allowed values are `yes` and `no`. If `INSTALL_DUCKDB=no`, the script installs
core webpage-response wrapping only and skips sync setup.

The GitHub repository is public. Authentication is not required for clone.

## Verify

Run:

```bash
cd "$HOME/futunn-calendar-python"
source .venv/bin/activate
futunn-calendar list --tab economic-data --start 2026-06-09 --end 2026-06-09 --star 3 --pretty
```

DuckDB sync:

```bash
futunn-calendar sync-duckdb \
  --db "$HOME/data/futunn_calendar.duckdb" \
  --page-delay 0.5 \
  --pretty
```

Only run DuckDB sync commands when DuckDB support was installed.

## Event-Time Refresh Daemon

The automatic post-event updater is:

```text
scripts/event_timer_refresh.py
```

Run manually:

```bash
cd "$HOME/futunn-calendar-python"
source .venv/bin/activate
PYTHONPATH=src python scripts/event_timer_refresh.py \
  --db "$HOME/data/futunn_calendar.duckdb" \
  --min-star 3 \
  --post-delay 1 \
  --retry-schedule 5,10,30,60x9
```

It reads events whose `actual` is empty, schedules timers by `timestamp_utc`, refreshes the event day through the Python library after the event time, and writes the updated `actual` back to DuckDB.

## Systemd User Service

Only create startup services when the user asks for boot/startup automation. On systemd systems, use a user service and keep the monthly sync timer intact. On Windows, use Task Scheduler.

Service command:

```bash
PYTHONPATH=<project-dir>/src \
<project-dir>/.venv/bin/python \
<project-dir>/scripts/event_timer_refresh.py \
  --db <duckdb-path> \
  --min-star 3 \
  --post-delay 1 \
  --retry-schedule 5,10,30,60x9
```

Do not disable `futunn-calendar-update.timer`; it is the monthly full sync.
