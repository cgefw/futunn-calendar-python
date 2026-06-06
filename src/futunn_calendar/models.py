"""Return models for the calendar webpage wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import parse_qs, urlparse


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_indicator_id(value: Any) -> Optional[str]:
    """Extract an economic indicator id from an event, URL, or scalar value."""

    if isinstance(value, CalendarEvent):
        raw = value.data.get("indicatorId") or value.data.get("indicatorid")
        if raw:
            return str(raw)
        value = value.data.get("url")

    if isinstance(value, Mapping):
        raw = value.get("indicatorId") or value.get("indicatorid")
        if raw:
            return str(raw)
        value = value.get("url")

    if value is None:
        return None

    text = str(value)
    if text.isdigit():
        return text

    query = parse_qs(urlparse(text).query)
    raw_values = query.get("indicatorId") or query.get("indicatorid")
    if raw_values:
        return raw_values[0]
    return None


@dataclass(frozen=True)
class CalendarEvent:
    date: str
    item_type: int
    data: Mapping[str, Any]
    raw: Mapping[str, Any]

    @classmethod
    def from_api(cls, date: str, item: Mapping[str, Any]) -> "CalendarEvent":
        data = item.get("itemData") or {}
        return cls(
            date=date,
            item_type=int(item.get("itemType") or 0),
            data=dict(data),
            raw=dict(item),
        )

    @property
    def title(self) -> str:
        return str(self.data.get("title") or self.data.get("shareTitle") or "")

    @property
    def timestamp(self) -> Optional[int]:
        return _to_int(self.data.get("timestamp"))

    @property
    def item_name(self) -> str:
        return str(self.data.get("itemName") or "")

    @property
    def indicator_id(self) -> Optional[str]:
        return extract_indicator_id(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "itemType": self.item_type,
            "itemData": dict(self.data),
            "indicatorId": self.indicator_id,
        }


@dataclass(frozen=True)
class CalendarPage:
    by_date: Mapping[str, List[CalendarEvent]]
    total: int
    has_more: bool
    seq_mark: str
    raw: Mapping[str, Any]

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> "CalendarPage":
        raw_list = payload.get("list") or {}
        by_date = {
            date: [CalendarEvent.from_api(date, item) for item in items]
            for date, items in raw_list.items()
        }
        return cls(
            by_date=by_date,
            total=int(payload.get("total") or 0),
            has_more=int(payload.get("hasMore") or 0) == 1
            or payload.get("hasMore") is True,
            seq_mark=str(payload.get("seqMark") or ""),
            raw=dict(payload),
        )

    @property
    def events(self) -> List[CalendarEvent]:
        result: List[CalendarEvent] = []
        for date in sorted(self.by_date):
            result.extend(self.by_date[date])
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "list": {
                date: [event.to_dict() for event in events]
                for date, events in self.by_date.items()
            },
            "total": self.total,
            "hasMore": self.has_more,
            "seqMark": self.seq_mark,
        }


@dataclass(frozen=True)
class DetailRecord:
    event_time: str
    previous: str
    consensus: str
    actual: str
    raw: Mapping[str, Any]

    @classmethod
    def from_api(cls, item: Mapping[str, Any]) -> "DetailRecord":
        return cls(
            event_time=str(item.get("eventTime") or ""),
            previous=str(item.get("previous") or ""),
            consensus=str(item.get("consensus") or ""),
            actual=str(item.get("actual") or ""),
            raw=dict(item),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventTime": self.event_time,
            "previous": self.previous,
            "consensus": self.consensus,
            "actual": self.actual,
        }


@dataclass(frozen=True)
class CalendarDetail:
    title: str
    unit: str
    has_more: bool
    records: List[DetailRecord]
    raw: Mapping[str, Any]

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> "CalendarDetail":
        return cls(
            title=str(payload.get("title") or ""),
            unit=str(payload.get("unit") or ""),
            has_more=bool(payload.get("hasMore")),
            records=[DetailRecord.from_api(item) for item in payload.get("list") or []],
            raw=dict(payload),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "unit": self.unit,
            "hasMore": self.has_more,
            "list": [record.to_dict() for record in self.records],
        }


def events_to_dicts(events: Iterable[CalendarEvent]) -> List[Dict[str, Any]]:
    return [event.to_dict() for event in events]
