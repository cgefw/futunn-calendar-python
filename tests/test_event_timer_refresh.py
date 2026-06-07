import importlib
import unittest

try:
    import duckdb  # noqa: F401
except ImportError:  # pragma: no cover - optional dependency.
    event_timer_refresh = None
else:
    event_timer_refresh = importlib.import_module("scripts.event_timer_refresh")


@unittest.skipIf(event_timer_refresh is None, "DuckDB optional dependency is not installed")
class EventTimerRefreshTests(unittest.TestCase):
    def test_parse_retry_schedule_expands_counts(self) -> None:
        self.assertEqual(
            event_timer_refresh.parse_retry_schedule("5,60x2"),
            [5.0, 60.0, 60.0],
        )

    def test_parse_retry_schedule_rejects_zero_delay(self) -> None:
        with self.assertRaises(ValueError):
            event_timer_refresh.parse_retry_schedule("0")

    def test_parse_retry_schedule_rejects_zero_count(self) -> None:
        with self.assertRaises(ValueError):
            event_timer_refresh.parse_retry_schedule("60x0")


if __name__ == "__main__":
    unittest.main()
