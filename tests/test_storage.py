import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

try:
    import duckdb
except ImportError:  # pragma: no cover - optional dependency.
    duckdb = None

from futunn_calendar import CalendarEvent


@unittest.skipIf(duckdb is None, "DuckDB optional dependency is not installed")
class StorageTests(unittest.TestCase):
    def test_failed_sync_rolls_back_event_writes(self) -> None:
        from futunn_calendar.storage import sync_calendar_to_duckdb

        class FailingClient:
            def iter_pages(self, **_kwargs):
                event = CalendarEvent.from_api(
                    "2026/06/07",
                    {
                        "itemType": 1004,
                        "itemData": {
                            "title": "Half-written event",
                            "timestamp": "1780800000",
                        },
                    },
                )
                yield SimpleNamespace(total=1, events=[event])
                raise RuntimeError("network broke after first page")

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "calendar.duckdb"

            with self.assertRaises(RuntimeError):
                sync_calendar_to_duckdb(db_path, client=FailingClient())

            with duckdb.connect(str(db_path)) as conn:
                event_count = conn.execute("SELECT count(*) FROM calendar_events").fetchone()[0]
                failed_runs = conn.execute(
                    "SELECT status, events_written FROM calendar_sync_runs"
                ).fetchall()

        self.assertEqual(event_count, 0)
        self.assertEqual(failed_runs, [("failed", 1)])


if __name__ == "__main__":
    unittest.main()
