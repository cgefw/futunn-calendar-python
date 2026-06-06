# Futunn Calendar Python Client (Unofficial)

**Unofficial, not affiliated with Futu, Futunn, Futubull, Moomoo, 富途 or any related
company. For personal research only. Do not redistribute data.**

This is an experimental wrapper for publicly reachable webpage JSON responses
used by `https://news.futunn.com/new-calendar`. It is not an official API, not
a stable data source, not investment advice, and not a grant of any rights to
third-party data.

Before using this project, review the source site's current Terms of Service
and robots.txt yourself:

- Terms: https://www.futunn.com/about/services?lang=zh-cn
- robots.txt: https://www.futunn.com/robots.txt
- Official supported alternative: https://openapi.futunn.com/futu-api-doc/

See [DATA_NOTICE.md](DATA_NOTICE.md) for the data-use notice. The code is
licensed under the PolyForm Noncommercial License 1.0.0; the license covers the
code only and does not license any third-party data.

## Install

Copy this to Codex or Claude Code for one-command install:

Linux / macOS / Git Bash:

```text
bash -lc 'set -e; cd /tmp; rm -rf futunn-calendar-python-install; git clone https://github.com/cgefw/futunn-calendar-python.git futunn-calendar-python-install; cd futunn-calendar-python-install/skills/install-futunn-calendar-python; bash scripts/install.sh'
```

Windows PowerShell:

```text
powershell -ExecutionPolicy Bypass -Command "Set-StrictMode -Version Latest; $ErrorActionPreference='Stop'; $tmp=Join-Path $env:TEMP 'futunn-calendar-python-install'; if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }; git clone https://github.com/cgefw/futunn-calendar-python.git $tmp; Set-Location (Join-Path $tmp 'skills/install-futunn-calendar-python'); powershell -ExecutionPolicy Bypass -File scripts/install.ps1"
```

The installer asks whether to install DuckDB support and whether to enable
DuckDB sync.

Core install:

```bash
python -m pip install -e .
```

Install with DuckDB sync support:

```bash
python -m pip install -e ".[duckdb]"
```

## Python Usage

```python
from futunn_calendar import CalendarTab, FutunnCalendarClient

client = FutunnCalendarClient()
page = client.list(
    tab=CalendarTab.ECONOMIC_DATA,
    start="2026-06-06",
    end="2026-06-08",
)

for event in page.events:
    print(event.date, event.title, event.timestamp)

detail = client.detail(page.events[0])
print(detail.title, detail.unit)
```

## Command Line

```bash
futunn-calendar list --tab economic-data --start 2026-06-06 --end 2026-06-08 --pretty
futunn-calendar detail 950 --pretty
```

## DuckDB Sync

Install with DuckDB support and sync paginated calendar rows into a local
DuckDB file:

```bash
python -m pip install -e ".[duckdb]"
futunn-calendar sync-duckdb --db data/futunn_calendar.duckdb --pretty
```

Check the saved rows:

```bash
python - <<'PY'
import duckdb
con = duckdb.connect("data/futunn_calendar.duckdb")
print(con.execute("select count(*) from calendar_events").fetchone()[0])
print(con.execute("select min(date), max(date) from calendar_events").fetchone())
PY
```

## Python Surface

- `FutunnCalendarClient.list(...)`: fetch one calendar page.
- `FutunnCalendarClient.iter_pages(...)`: follow webpage pagination metadata.
- `FutunnCalendarClient.iter_events(...)`: stream flattened calendar events.
- `FutunnCalendarClient.detail(...)`: fetch historical data for an indicator.
- `get_calendar(...)` and `get_detail(...)`: convenience one-shot helpers.
- `sync_calendar_to_duckdb(...)`: fetch pages and upsert them into DuckDB.

The webpage JSON responses are not documented by Futu/Futunn as a supported
public API and can change or become unavailable without notice.
