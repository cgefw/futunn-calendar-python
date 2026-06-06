"""HTTP wrapper for financial-calendar webpage JSON responses."""

from __future__ import annotations

from json import JSONDecodeError as StdJSONDecodeError
from time import sleep
from datetime import date, datetime
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

import requests

from .constants import (
    DEFAULT_COUNTRIES,
    DEFAULT_IPO_MARKETS,
    DEFAULT_MARKETS,
    DEFAULT_STARS,
    LANGUAGE_ALIASES,
    CalendarTab,
    Country,
    Language,
    Market,
    RangeType,
    StockType,
)
from .models import CalendarDetail, CalendarEvent, CalendarPage, extract_indicator_id

DateLike = Union[str, date, datetime]
ParamValue = Union[str, int, bool]


class FutunnCalendarError(RuntimeError):
    """Base exception for this package."""


class FutunnHTTPError(FutunnCalendarError):
    """Raised when the HTTP request itself fails."""


class FutunnAPIError(FutunnCalendarError):
    """Raised when the webpage JSON response returns a non-zero code."""


def _format_date(value: Optional[DateLike]) -> str:
    if value is None:
        return date.today().strftime("%Y/%m/%d")
    if isinstance(value, datetime):
        return value.date().strftime("%Y/%m/%d")
    if isinstance(value, date):
        return value.strftime("%Y/%m/%d")
    text = str(value).strip()
    return text.replace("-", "/")


def _lang_value(value: Union[Language, int, str]) -> int:
    if isinstance(value, Language):
        return int(value)
    if isinstance(value, int):
        return value
    key = value.strip().lower()
    if key not in LANGUAGE_ALIASES:
        raise ValueError(f"Unsupported language: {value!r}")
    return int(LANGUAGE_ALIASES[key])


def _int_values(values: Optional[Iterable[Union[int, Any]]]) -> Optional[List[int]]:
    if values is None:
        return None
    return [int(value) for value in values]


def _star_values(values: Optional[Iterable[Union[str, int]]]) -> Optional[List[str]]:
    if values is None:
        return None
    return [str(value) for value in values]


def _pairs(params: Mapping[str, Any]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            for item in value:
                pairs.append((f"{key}[]", str(item)))
        else:
            pairs.append((key, str(value)))
    return pairs


class FutunnCalendarClient:
    """Small wrapper for webpage JSON responses used by a calendar page."""

    def __init__(
        self,
        *,
        base_url: str = "https://news.futunn.com",
        session: Optional[requests.Session] = None,
        timeout: float = 20.0,
        language: Union[Language, int, str] = Language.ZH_CN,
        time_zone: str = "Asia/Shanghai",
        user_agent: Optional[str] = None,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.language = _lang_value(language)
        self.time_zone = time_zone
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )

    def list(
        self,
        *,
        tab: Union[CalendarTab, int] = CalendarTab.ECONOMIC_DATA,
        start: Optional[DateLike] = None,
        end: Optional[DateLike] = None,
        range_type: Optional[Union[RangeType, int]] = None,
        countries: Optional[Iterable[Union[Country, int]]] = None,
        stars: Optional[Iterable[Union[str, int]]] = None,
        markets: Optional[Iterable[Union[Market, int]]] = None,
        ipo_markets: Optional[Iterable[Union[Market, int]]] = None,
        stock_types: Optional[Iterable[Union[StockType, int]]] = None,
        seq_mark: str = "",
        language: Optional[Union[Language, int, str]] = None,
        time_zone: Optional[str] = None,
    ) -> CalendarPage:
        """Fetch one page of calendar items."""

        params: Dict[str, Any] = {
            "tabs": int(tab),
            "startTime": _format_date(start),
            "endTime": "" if end is None else _format_date(end),
            "rangeType": int(
                range_type
                if range_type is not None
                else (RangeType.CUSTOM if end is not None else RangeType.TODAY_ONWARD)
            ),
            "nation": _int_values(countries) or [int(item) for item in DEFAULT_COUNTRIES],
            "star": _star_values(stars) or list(DEFAULT_STARS),
            "clientLang": self.language if language is None else _lang_value(language),
            "marketList": _int_values(markets) or [int(item) for item in DEFAULT_MARKETS],
            "ipoMarketList": _int_values(ipo_markets)
            or [int(item) for item in DEFAULT_IPO_MARKETS],
            "seqMark": seq_mark,
            "timeZone": time_zone or self.time_zone,
        }
        normalized_stock_types = _int_values(stock_types)
        if normalized_stock_types:
            params["stockType"] = normalized_stock_types

        data = self._get("/api/financial-calendar/list", params)
        return CalendarPage.from_api(data)

    def iter_pages(
        self,
        *,
        max_pages: Optional[int] = None,
        page_delay: float = 0.0,
        **kwargs: Any,
    ) -> Iterator[CalendarPage]:
        """Yield pages, following `seqMark` while the response reports `hasMore`."""

        seq_mark = str(kwargs.pop("seq_mark", ""))
        count = 0
        while True:
            page = self.list(seq_mark=seq_mark, **kwargs)
            yield page
            count += 1
            if not page.has_more or not page.seq_mark:
                return
            if max_pages is not None and count >= max_pages:
                return
            if page_delay > 0:
                sleep(page_delay)
            seq_mark = page.seq_mark

    def iter_events(
        self,
        *,
        max_pages: Optional[int] = None,
        page_delay: float = 0.0,
        **kwargs: Any,
    ) -> Iterator[CalendarEvent]:
        """Yield flattened events from one or more pages."""

        for page in self.iter_pages(
            max_pages=max_pages,
            page_delay=page_delay,
            **kwargs,
        ):
            yield from page.events

    def detail(
        self,
        indicator: Union[str, int, CalendarEvent, Mapping[str, Any]],
        *,
        size: int = 20,
        start: int = 0,
        language: Optional[Union[Language, int, str]] = None,
    ) -> CalendarDetail:
        """Fetch historical values for an economic indicator."""

        indicator_id = extract_indicator_id(indicator)
        if not indicator_id:
            raise ValueError("Could not find an indicatorId in the provided value.")
        params = {
            "indicatorId": indicator_id,
            "size": int(size),
            "start": int(start),
            "clientLang": self.language if language is None else _lang_value(language),
        }
        data = self._get("/api/financial-calendar/detail", params)
        return CalendarDetail.from_api(data)

    def _get(self, path: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{self.base_url}/new-calendar",
            "User-Agent": self.user_agent,
        }
        last_error: Optional[BaseException] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=_pairs(params),
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                break
            except requests.HTTPError as exc:
                last_error = exc
            except requests.RequestException as exc:
                last_error = exc
            except (ValueError, StdJSONDecodeError) as exc:
                text = getattr(response, "text", "")
                snippet = text[:120].replace("\n", " ").strip()
                last_error = FutunnAPIError(
                    f"Calendar page returned a non-JSON response: {snippet!r}"
                )

            if attempt < self.max_retries:
                sleep(self.retry_delay * (attempt + 1))
        else:
            if isinstance(last_error, FutunnAPIError):
                raise last_error
            raise FutunnHTTPError(str(last_error)) from last_error

        code = payload.get("code")
        if code != 0:
            message = payload.get("message") or payload.get("msg") or "unknown response error"
            raise FutunnAPIError(f"Calendar response error {code}: {message}")

        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise FutunnAPIError("Calendar response did not contain an object payload.")
        return data


def get_calendar(**kwargs: Any) -> CalendarPage:
    """Fetch a calendar page with a temporary client."""

    return FutunnCalendarClient().list(**kwargs)


def get_detail(
    indicator: Union[str, int, CalendarEvent, Mapping[str, Any]],
    **kwargs: Any,
) -> CalendarDetail:
    """Fetch indicator detail with a temporary client."""

    return FutunnCalendarClient().detail(indicator, **kwargs)


__all__ = [
    "FutunnAPIError",
    "FutunnCalendarClient",
    "FutunnCalendarError",
    "FutunnHTTPError",
    "get_calendar",
    "get_detail",
]
