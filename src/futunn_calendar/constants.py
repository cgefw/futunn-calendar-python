"""Constants and enum values used by the calendar web page."""

from enum import IntEnum
from typing import Dict, Tuple


class CalendarTab(IntEnum):
    EARNINGS = 1
    EXRIGHT = 2
    IPO = 3
    ECONOMIC_DATA = 4
    EVENTS = 5
    HOLIDAYS = 6


class RangeType(IntEnum):
    TODAY_ONWARD = 1
    THIS_WEEK = 2
    THIS_MONTH = 3
    CUSTOM = 4


class Country(IntEnum):
    OTHER = 0
    US = 1
    CN = 2
    SG = 3
    CA = 4
    AU = 5
    JP = 6
    DE = 7
    UK = 8
    FR = 9
    MY = 10
    KR = 11


class Market(IntEnum):
    US = 1
    HK = 2
    SG = 3
    CN = 4
    JP = 5
    CA = 6
    AU = 7
    MY = 8
    KR = 9


class StockType(IntEnum):
    WATCHLIST = 1
    POSITIONS = 2
    STARRED = 3


class Language(IntEnum):
    ZH_CN = 0
    ZH_HK = 1
    EN_US = 2
    JA = 3


DEFAULT_COUNTRIES: Tuple[Country, ...] = (
    Country.US,
    Country.CN,
    Country.SG,
    Country.CA,
    Country.AU,
    Country.JP,
    Country.MY,
    Country.DE,
    Country.UK,
    Country.FR,
    Country.KR,
    Country.OTHER,
)

DEFAULT_MARKETS: Tuple[Market, ...] = (
    Market.HK,
    Market.US,
    Market.CN,
    Market.JP,
    Market.KR,
    Market.SG,
    Market.CA,
    Market.AU,
    Market.MY,
)

DEFAULT_IPO_MARKETS: Tuple[Market, ...] = (
    Market.HK,
    Market.US,
    Market.CN,
    Market.KR,
)

DEFAULT_STARS: Tuple[str, ...] = ("3,4,5", "2", "1")

LANGUAGE_ALIASES: Dict[str, Language] = {
    "zh-cn": Language.ZH_CN,
    "zh_cn": Language.ZH_CN,
    "cn": Language.ZH_CN,
    "simplified": Language.ZH_CN,
    "zh-hk": Language.ZH_HK,
    "zh_hk": Language.ZH_HK,
    "hk": Language.ZH_HK,
    "traditional": Language.ZH_HK,
    "en-us": Language.EN_US,
    "en_us": Language.EN_US,
    "en": Language.EN_US,
    "english": Language.EN_US,
    "ja": Language.JA,
    "jp": Language.JA,
    "japanese": Language.JA,
}

TAB_ALIASES: Dict[str, CalendarTab] = {
    "earnings": CalendarTab.EARNINGS,
    "earning": CalendarTab.EARNINGS,
    "exright": CalendarTab.EXRIGHT,
    "dividend": CalendarTab.EXRIGHT,
    "dividends": CalendarTab.EXRIGHT,
    "ipo": CalendarTab.IPO,
    "economic": CalendarTab.ECONOMIC_DATA,
    "economic-data": CalendarTab.ECONOMIC_DATA,
    "economic_data": CalendarTab.ECONOMIC_DATA,
    "events": CalendarTab.EVENTS,
    "event": CalendarTab.EVENTS,
    "holidays": CalendarTab.HOLIDAYS,
    "holiday": CalendarTab.HOLIDAYS,
}
