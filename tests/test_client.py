import unittest
from typing import Any, Dict, List, Tuple

from futunn_calendar import CalendarEvent, CalendarTab, FutunnCalendarClient


class FakeResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        self.calls: List[Dict[str, Any]] = []

    def get(self, *args: Any, **kwargs: Any) -> FakeResponse:
        self.calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse(self.payload)


class ClientTests(unittest.TestCase):
    def test_list_serializes_arrays_with_bracket_keys(self) -> None:
        session = FakeSession(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "list": {},
                    "total": 0,
                    "hasMore": 0,
                    "seqMark": "",
                },
            }
        )
        client = FutunnCalendarClient(session=session)
        client.list(
            tab=CalendarTab.ECONOMIC_DATA,
            start="2026-06-06",
            countries=[1, 2],
            markets=[1],
            ipo_markets=[2],
            stars=["3,4,5"],
        )

        params: List[Tuple[str, str]] = session.calls[0]["kwargs"]["params"]
        self.assertIn(("nation[]", "1"), params)
        self.assertIn(("nation[]", "2"), params)
        self.assertIn(("marketList[]", "1"), params)
        self.assertIn(("ipoMarketList[]", "2"), params)
        self.assertIn(("star[]", "3,4,5"), params)
        self.assertIn(("startTime", "2026/06/06"), params)

    def test_calendar_page_model_extracts_indicator_id(self) -> None:
        session = FakeSession(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "list": {
                        "2026/06/06": [
                            {
                                "itemType": 1004,
                                "itemData": {
                                    "title": "Example",
                                    "timestamp": "1780678800",
                                    "url": "https://news.futunn.com/new-calendar/detail?indicatorId=950",
                                },
                            }
                        ]
                    },
                    "total": 1,
                    "hasMore": 0,
                    "seqMark": "",
                },
            }
        )
        client = FutunnCalendarClient(session=session)
        page = client.list(start="2026-06-06")

        self.assertEqual(page.total, 1)
        self.assertEqual(page.events[0].title, "Example")
        self.assertEqual(page.events[0].indicator_id, "950")

    def test_detail_accepts_calendar_event(self) -> None:
        session = FakeSession(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "list": [{"eventTime": "1780678800", "previous": "1"}],
                    "title": "Detail",
                    "unit": "%",
                    "hasMore": False,
                },
            }
        )
        client = FutunnCalendarClient(session=session)
        event = CalendarEvent.from_api(
            "2026/06/06",
            {
                "itemType": 1004,
                "itemData": {
                    "url": "https://news.futunn.com/new-calendar/detail?indicatorId=950"
                },
            },
        )
        detail = client.detail(event)

        params: List[Tuple[str, str]] = session.calls[0]["kwargs"]["params"]
        self.assertIn(("indicatorId", "950"), params)
        self.assertEqual(detail.title, "Detail")
        self.assertEqual(detail.records[0].event_time, "1780678800")


if __name__ == "__main__":
    unittest.main()
