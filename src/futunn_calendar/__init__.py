"""Unofficial wrapper for financial-calendar webpage JSON responses."""

from .client import (
    FutunnAPIError,
    FutunnCalendarClient,
    FutunnCalendarError,
    FutunnHTTPError,
    get_calendar,
    get_detail,
)
from .constants import (
    DEFAULT_COUNTRIES,
    DEFAULT_IPO_MARKETS,
    DEFAULT_MARKETS,
    DEFAULT_STARS,
    CalendarTab,
    Country,
    Language,
    Market,
    RangeType,
    StockType,
)
from .models import CalendarDetail, CalendarEvent, CalendarPage, DetailRecord

__all__ = [
    "CalendarDetail",
    "CalendarEvent",
    "CalendarPage",
    "CalendarTab",
    "Country",
    "DEFAULT_COUNTRIES",
    "DEFAULT_IPO_MARKETS",
    "DEFAULT_MARKETS",
    "DEFAULT_STARS",
    "DetailRecord",
    "FutunnAPIError",
    "FutunnCalendarClient",
    "FutunnCalendarError",
    "FutunnHTTPError",
    "Language",
    "Market",
    "RangeType",
    "StockType",
    "SyncResult",
    "get_calendar",
    "get_detail",
    "init_duckdb",
    "sync_calendar_to_duckdb",
]


def __getattr__(name: str):
    if name in {"SyncResult", "init_duckdb", "sync_calendar_to_duckdb"}:
        from . import storage

        return getattr(storage, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
