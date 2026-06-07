"""DuckDB persistence for calendar event data."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import Any, Dict, Iterable, Mapping, Optional, Union

try:
    import duckdb
except ImportError as exc:  # pragma: no cover - depends on optional extra.
    raise ImportError(
        "DuckDB support is not installed. Install it with: "
        "python -m pip install 'futunn-calendar[duckdb]'"
    ) from exc

from .client import DateLike, FutunnCalendarClient
from .constants import CalendarTab
from .models import CalendarDetail, CalendarEvent, extract_indicator_id


@dataclass(frozen=True)
class SyncResult:
    db_path: str
    run_id: str
    tab: int
    total_available: int
    pages_read: int
    events_written: int
    details_written: int
    started_at: str
    finished_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "db_path": self.db_path,
            "run_id": self.run_id,
            "tab": self.tab,
            "total_available": self.total_available,
            "pages_read": self.pages_read,
            "events_written": self.events_written,
            "details_written": self.details_written,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


def init_duckdb(db_path: Union[str, Path]) -> None:
    """Create the DuckDB schema if it does not exist."""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_sync_runs (
                run_id VARCHAR,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                status VARCHAR,
                tab INTEGER,
                total_available INTEGER,
                pages_read INTEGER,
                events_written INTEGER,
                details_written INTEGER,
                params_json VARCHAR,
                error VARCHAR
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_events (
                event_key VARCHAR,
                run_id VARCHAR,
                date DATE,
                date_text VARCHAR,
                item_type INTEGER,
                item_name VARCHAR,
                title VARCHAR,
                share_title VARCHAR,
                timestamp BIGINT,
                timestamp_utc TIMESTAMP,
                indicator_id VARCHAR,
                country VARCHAR,
                star INTEGER,
                previous VARCHAR,
                consensus VARCHAR,
                actual VARCHAR,
                url VARCHAR,
                article_id VARCHAR,
                news_unique_id VARCHAR,
                raw_json VARCHAR,
                updated_at TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_indicator_history (
                history_key VARCHAR,
                indicator_id VARCHAR,
                title VARCHAR,
                unit VARCHAR,
                event_time BIGINT,
                event_time_utc TIMESTAMP,
                previous VARCHAR,
                consensus VARCHAR,
                actual VARCHAR,
                raw_json VARCHAR,
                updated_at TIMESTAMP
            )
            """
        )


def sync_calendar_to_duckdb(
    db_path: Union[str, Path],
    *,
    client: Optional[FutunnCalendarClient] = None,
    tab: Union[CalendarTab, int] = CalendarTab.ECONOMIC_DATA,
    start: Optional[DateLike] = None,
    end: Optional[DateLike] = None,
    max_pages: Optional[int] = None,
    page_delay: float = 0.5,
    include_details: bool = False,
    detail_size: int = 20,
    detail_delay: float = 0.2,
    list_kwargs: Optional[Mapping[str, Any]] = None,
) -> SyncResult:
    """Fetch calendar pages and upsert them into DuckDB."""

    path = Path(db_path)
    init_duckdb(path)

    active_client = client or FutunnCalendarClient(max_retries=5, retry_delay=2)
    run_id = str(uuid.uuid4())
    started_at = _now()
    pages_read = 0
    events_written = 0
    details_written = 0
    total_available = 0
    seen_indicators = set()
    params: Dict[str, Any] = {
        "tab": int(tab),
        "start": str(start) if start is not None else None,
        "end": str(end) if end is not None else None,
        "max_pages": max_pages,
        "page_delay": page_delay,
        "include_details": include_details,
        "detail_size": detail_size,
        "detail_delay": detail_delay,
        **dict(list_kwargs or {}),
    }

    with duckdb.connect(str(path)) as conn:
        conn.execute("BEGIN TRANSACTION")
        try:
            for page in active_client.iter_pages(
                tab=tab,
                start=start,
                end=end,
                max_pages=max_pages,
                page_delay=page_delay,
                **dict(list_kwargs or {}),
            ):
                pages_read += 1
                if pages_read == 1:
                    total_available = page.total
                for event in page.events:
                    _upsert_event(conn, event, run_id)
                    events_written += 1

                    indicator_id = event.indicator_id
                    if include_details and indicator_id and indicator_id not in seen_indicators:
                        detail = active_client.detail(indicator_id, size=detail_size)
                        details_written += _upsert_detail(conn, indicator_id, detail)
                        seen_indicators.add(indicator_id)
                        if detail_delay > 0:
                            sleep(detail_delay)

            finished_at = _now()
            _insert_run(
                conn,
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                status="success",
                tab=int(tab),
                total_available=total_available,
                pages_read=pages_read,
                events_written=events_written,
                details_written=details_written,
                params=params,
                error=None,
            )
            conn.execute("COMMIT")
            return SyncResult(
                db_path=str(path),
                run_id=run_id,
                tab=int(tab),
                total_available=total_available,
                pages_read=pages_read,
                events_written=events_written,
                details_written=details_written,
                started_at=started_at,
                finished_at=finished_at,
            )
        except Exception as exc:
            conn.execute("ROLLBACK")
            finished_at = _now()
            _insert_run(
                conn,
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                status="failed",
                tab=int(tab),
                total_available=total_available,
                pages_read=pages_read,
                events_written=events_written,
                details_written=details_written,
                params=params,
                error=str(exc),
            )
            raise


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_date(value: str) -> Optional[str]:
    if not value:
        return None
    return value.replace("/", "-")


def _timestamp(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _timestamp_iso(value: Any) -> Optional[str]:
    ts = _timestamp(value)
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None).isoformat()


def _event_key(event: CalendarEvent) -> str:
    data = event.data
    return str(
        data.get("newsUniqueId")
        or data.get("articleId")
        or "|".join(
            [
                event.date,
                str(event.item_type),
                str(data.get("timestamp") or ""),
                str(data.get("title") or ""),
            ]
        )
    )


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _upsert_event(conn: duckdb.DuckDBPyConnection, event: CalendarEvent, run_id: str) -> None:
    key = _event_key(event)
    data = event.data
    conn.execute("DELETE FROM calendar_events WHERE event_key = ?", [key])
    conn.execute(
        """
        INSERT INTO calendar_events VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        [
            key,
            run_id,
            _parse_date(event.date),
            event.date,
            event.item_type,
            data.get("itemName"),
            data.get("title"),
            data.get("shareTitle"),
            _timestamp(data.get("timestamp")),
            _timestamp_iso(data.get("timestamp")),
            event.indicator_id,
            data.get("country"),
            _timestamp(data.get("star")),
            data.get("previous"),
            data.get("consensus"),
            data.get("actual"),
            data.get("url"),
            data.get("articleId"),
            data.get("newsUniqueId"),
            _json(event.raw),
            _now(),
        ],
    )


def _upsert_detail(
    conn: duckdb.DuckDBPyConnection,
    indicator_id: str,
    detail: CalendarDetail,
) -> int:
    count = 0
    for record in detail.records:
        key = f"{indicator_id}|{record.event_time}"
        conn.execute("DELETE FROM calendar_indicator_history WHERE history_key = ?", [key])
        conn.execute(
            """
            INSERT INTO calendar_indicator_history VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                key,
                indicator_id,
                detail.title,
                detail.unit,
                _timestamp(record.event_time),
                _timestamp_iso(record.event_time),
                record.previous,
                record.consensus,
                record.actual,
                _json(record.raw),
                _now(),
            ],
        )
        count += 1
    return count


def _insert_run(
    conn: duckdb.DuckDBPyConnection,
    *,
    run_id: str,
    started_at: str,
    finished_at: str,
    status: str,
    tab: int,
    total_available: int,
    pages_read: int,
    events_written: int,
    details_written: int,
    params: Mapping[str, Any],
    error: Optional[str],
) -> None:
    conn.execute(
        """
        INSERT INTO calendar_sync_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            started_at,
            finished_at,
            status,
            tab,
            total_available,
            pages_read,
            events_written,
            details_written,
            _json(params),
            error,
        ],
    )
