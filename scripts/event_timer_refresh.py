#!/usr/bin/env python3
"""Schedule event-time refreshes for calendar rows in DuckDB.

The daemon reads future calendar events from DuckDB, creates in-process timers,
and refreshes the event's calendar day through the futunn-calendar Python client
when the event time arrives. The refreshed values are upserted back into DuckDB
by sync_calendar_to_duckdb().
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from time import sleep
from typing import Dict, Iterable, Optional

import duckdb

from futunn_calendar import CalendarTab, FutunnCalendarClient, sync_calendar_to_duckdb


DEFAULT_DB = str(Path.home() / "data" / "futunn_calendar.duckdb")


@dataclass(frozen=True)
class EventJob:
    event_key: str
    event_date: date
    event_time_utc: datetime
    title: str
    star: Optional[int]


class EventRefreshDaemon:
    def __init__(
        self,
        *,
        db_path: str,
        min_star: Optional[int],
        lookahead_hours: float,
        backfill_minutes: float,
        scan_interval: float,
        post_delay: float,
        retry_schedule: list[float],
        page_delay: float,
    ) -> None:
        self.db_path = db_path
        self.min_star = min_star
        self.lookahead = timedelta(hours=lookahead_hours)
        self.backfill = timedelta(minutes=backfill_minutes)
        self.scan_interval = scan_interval
        self.post_delay = post_delay
        self.retry_schedule = retry_schedule
        self.page_delay = page_delay
        self.client = FutunnCalendarClient(language="zh-cn", max_retries=5, retry_delay=2)
        self.stop_event = threading.Event()
        self.refresh_lock = threading.Lock()
        self.timers: Dict[str, threading.Timer] = {}
        self.last_sync_by_date: Dict[str, datetime] = {}

    def run(self, once: bool = False) -> None:
        self._init_tables()
        self.scan_and_schedule()
        if once:
            return

        while not self.stop_event.wait(self.scan_interval):
            self.scan_and_schedule()

    def stop(self) -> None:
        self.stop_event.set()
        for timer in list(self.timers.values()):
            timer.cancel()

    def scan_and_schedule(self) -> None:
        jobs = list(self._load_candidate_events())
        now = utc_now_naive()
        print(f"[{stamp()}] scan found {len(jobs)} pending events", flush=True)

        for job in jobs:
            if job.event_key in self.timers:
                continue

            run_at = job.event_time_utc + timedelta(seconds=self.post_delay)
            delay = max(0.0, (run_at - now).total_seconds())
            self._record_job(job, "scheduled", scheduled_at=run_at, attempts=None)

            timer = threading.Timer(delay, self._run_job, args=(job, 1))
            timer.daemon = True
            self.timers[job.event_key] = timer
            timer.start()
            print(
                f"[{stamp()}] scheduled {job.event_key} at {run_at.isoformat()} UTC "
                f"delay={delay:.0f}s title={job.title}",
                flush=True,
            )

    def _run_job(self, job: EventJob, attempt: int) -> None:
        self.timers.pop(job.event_key, None)
        self._record_job(job, "running", triggered_at=utc_now_naive(), attempts=attempt)

        try:
            self._refresh_event_day(job.event_date)
            actual = self._load_actual(job.event_key)

            if actual not in (None, ""):
                self._record_job(
                    job,
                    "done",
                    attempts=attempt,
                    last_actual=str(actual),
                )
                print(
                    f"[{stamp()}] done {job.event_key} actual={actual} title={job.title}",
                    flush=True,
                )
                return

            next_delay = self._next_retry_delay(attempt)
            if next_delay is None:
                self._record_job(
                    job,
                    "no_actual",
                    attempts=attempt,
                    last_error="actual is still empty after max attempts",
                )
                print(
                    f"[{stamp()}] no actual after {attempt} attempts {job.event_key}",
                    flush=True,
                )
                return

            self._record_job(
                job,
                "retry_scheduled",
                attempts=attempt,
                last_error="actual is still empty",
            )
            timer = threading.Timer(
                next_delay,
                self._run_job,
                args=(job, attempt + 1),
            )
            timer.daemon = True
            self.timers[job.event_key] = timer
            timer.start()
            print(
                f"[{stamp()}] retry in {next_delay:.0f}s "
                f"{job.event_key} attempt={attempt + 1}",
                flush=True,
            )
        except Exception as exc:
            self._record_job(
                job,
                "error",
                attempts=attempt,
                last_error=str(exc),
            )
            print(f"[{stamp()}] error {job.event_key}: {exc}", file=sys.stderr, flush=True)
            next_delay = self._next_retry_delay(attempt)
            if next_delay is not None:
                timer = threading.Timer(
                    next_delay,
                    self._run_job,
                    args=(job, attempt + 1),
                )
                timer.daemon = True
                self.timers[job.event_key] = timer
                timer.start()

    def _next_retry_delay(self, attempt: int) -> Optional[float]:
        index = attempt - 1
        if index < 0 or index >= len(self.retry_schedule):
            return None
        return self.retry_schedule[index]

    def _refresh_event_day(self, event_date: date) -> None:
        day = event_date.isoformat()
        now = utc_now_naive()

        with self.refresh_lock:
            last_sync = self.last_sync_by_date.get(day)
            if last_sync and (now - last_sync).total_seconds() < 20:
                return

            print(f"[{stamp()}] refreshing day {day}", flush=True)
            sync_calendar_to_duckdb(
                self.db_path,
                client=self.client,
                tab=CalendarTab.ECONOMIC_DATA,
                start=day,
                end=day,
                page_delay=self.page_delay,
            )
            self.last_sync_by_date[day] = utc_now_naive()

    def _init_tables(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendar_event_refresh_jobs (
                    event_key VARCHAR,
                    title VARCHAR,
                    event_date DATE,
                    event_time_utc TIMESTAMP,
                    star INTEGER,
                    status VARCHAR,
                    scheduled_at TIMESTAMP,
                    triggered_at TIMESTAMP,
                    attempts INTEGER,
                    last_actual VARCHAR,
                    last_error VARCHAR,
                    updated_at TIMESTAMP
                )
                """
            )

    def _load_candidate_events(self) -> Iterable[EventJob]:
        now = utc_now_naive()
        lower = now - self.backfill
        upper = now + self.lookahead

        where = """
            timestamp_utc IS NOT NULL
            AND timestamp_utc BETWEEN ? AND ?
            AND (actual IS NULL OR actual = '')
        """
        params = [lower, upper]
        if self.min_star is not None:
            where += " AND star >= ?"
            params.append(self.min_star)

        query = f"""
            SELECT event_key, date, timestamp_utc, title, star
            FROM calendar_events
            WHERE {where}
            ORDER BY timestamp_utc
        """

        with duckdb.connect(self.db_path, read_only=True) as conn:
            rows = conn.execute(query, params).fetchall()

        for event_key, event_date, event_time_utc, title, star in rows:
            if event_time_utc.tzinfo is not None:
                event_time_utc = event_time_utc.astimezone(timezone.utc).replace(tzinfo=None)
            yield EventJob(
                event_key=str(event_key),
                event_date=event_date,
                event_time_utc=event_time_utc,
                title=str(title or ""),
                star=star,
            )

    def _load_actual(self, event_key: str) -> Optional[str]:
        with duckdb.connect(self.db_path, read_only=True) as conn:
            row = conn.execute(
                "SELECT actual FROM calendar_events WHERE event_key = ?",
                [event_key],
            ).fetchone()
        if not row:
            return None
        return row[0]

    def _record_job(
        self,
        job: EventJob,
        status: str,
        *,
        scheduled_at: Optional[datetime] = None,
        triggered_at: Optional[datetime] = None,
        attempts: Optional[int] = None,
        last_actual: Optional[str] = None,
        last_error: Optional[str] = None,
    ) -> None:
        with duckdb.connect(self.db_path) as conn:
            existing = conn.execute(
                """
                SELECT scheduled_at, triggered_at, attempts, last_actual, last_error
                FROM calendar_event_refresh_jobs
                WHERE event_key = ?
                """,
                [job.event_key],
            ).fetchone()

            if existing:
                scheduled_at = scheduled_at if scheduled_at is not None else existing[0]
                triggered_at = triggered_at if triggered_at is not None else existing[1]
                attempts = attempts if attempts is not None else existing[2]
                last_actual = last_actual if last_actual is not None else existing[3]
                last_error = last_error if last_error is not None else existing[4]

            conn.execute(
                "DELETE FROM calendar_event_refresh_jobs WHERE event_key = ?",
                [job.event_key],
            )
            conn.execute(
                """
                INSERT INTO calendar_event_refresh_jobs VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                [
                    job.event_key,
                    job.title,
                    job.event_date,
                    job.event_time_utc,
                    job.star,
                    status,
                    scheduled_at,
                    triggered_at,
                    attempts,
                    last_actual,
                    last_error,
                    utc_now_naive(),
                ],
            )


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def stamp() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def parse_retry_schedule(value: str) -> list[float]:
    schedule: list[float] = []
    for raw_part in value.split(","):
        part = raw_part.strip().lower()
        if not part:
            continue
        if "x" in part:
            delay_text, count_text = part.split("x", 1)
            delay = float(delay_text)
            count = int(count_text)
            if count < 0:
                raise ValueError(f"Invalid retry count in {raw_part!r}")
            schedule.extend([delay] * count)
        else:
            schedule.append(float(part))

    if not schedule:
        raise ValueError("Retry schedule must contain at least one delay.")
    if any(delay < 0 for delay in schedule):
        raise ValueError("Retry delays must be non-negative.")
    return schedule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh calendar DuckDB rows when event timers fire."
    )
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--min-star", type=int, default=3)
    parser.add_argument("--all-stars", action="store_true")
    parser.add_argument("--lookahead-hours", type=float, default=36)
    parser.add_argument("--backfill-minutes", type=float, default=180)
    parser.add_argument("--scan-interval", type=float, default=300)
    parser.add_argument("--post-delay", type=float, default=1)
    parser.add_argument(
        "--retry-schedule",
        default="5,10,30,60x9",
        help="Retry delays after failed initial refresh. Supports values like 5,10,30,60x9.",
    )
    parser.add_argument("--page-delay", type=float, default=0.5)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    daemon = EventRefreshDaemon(
        db_path=args.db,
        min_star=None if args.all_stars else args.min_star,
        lookahead_hours=args.lookahead_hours,
        backfill_minutes=args.backfill_minutes,
        scan_interval=args.scan_interval,
        post_delay=args.post_delay,
        retry_schedule=parse_retry_schedule(args.retry_schedule),
        page_delay=args.page_delay,
    )

    def _handle_stop(_signum: int, _frame: object) -> None:
        print(f"[{stamp()}] stopping", flush=True)
        daemon.stop()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    daemon.run(once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
