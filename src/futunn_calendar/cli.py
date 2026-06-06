"""Command line interface for futunn-calendar."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Iterable, List, Optional

from .client import FutunnCalendarClient
from .constants import LANGUAGE_ALIASES, TAB_ALIASES, CalendarTab, Language


def _tab(value: str) -> CalendarTab:
    key = value.strip().lower()
    if key.isdigit():
        return CalendarTab(int(key))
    if key not in TAB_ALIASES:
        choices = ", ".join(sorted(TAB_ALIASES))
        raise argparse.ArgumentTypeError(f"Unknown tab {value!r}. Choices: {choices}")
    return TAB_ALIASES[key]


def _language(value: str) -> Language:
    key = value.strip().lower()
    if key.isdigit():
        return Language(int(key))
    if key not in LANGUAGE_ALIASES:
        choices = ", ".join(sorted(LANGUAGE_ALIASES))
        raise argparse.ArgumentTypeError(f"Unknown language {value!r}. Choices: {choices}")
    return LANGUAGE_ALIASES[key]


def _ints(values: Optional[Iterable[str]]) -> Optional[List[int]]:
    if values is None:
        return None
    result: List[int] = []
    for value in values:
        for piece in value.split(","):
            piece = piece.strip()
            if piece:
                result.append(int(piece))
    return result


def _print(payload: Any, pretty: bool) -> None:
    kwargs = {"ensure_ascii": False}
    if pretty:
        kwargs.update({"indent": 2, "sort_keys": True})
    print(json.dumps(payload, **kwargs))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="futunn-calendar")
    parser.add_argument("--base-url", default="https://news.futunn.com")
    parser.add_argument("--lang", type=_language, default=Language.ZH_CN)
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=2.0)

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Fetch calendar items.")
    list_parser.add_argument("--tab", type=_tab, default=CalendarTab.ECONOMIC_DATA)
    list_parser.add_argument("--start")
    list_parser.add_argument("--end")
    list_parser.add_argument("--range-type", type=int, default=4)
    list_parser.add_argument("--country", action="append")
    list_parser.add_argument("--market", action="append")
    list_parser.add_argument("--ipo-market", action="append")
    list_parser.add_argument("--star", action="append")
    list_parser.add_argument("--stock-type", action="append")
    list_parser.add_argument("--all", action="store_true", help="Follow pagination.")
    list_parser.add_argument("--max-pages", type=int)
    list_parser.add_argument("--pretty", action="store_true")

    detail_parser = subparsers.add_parser("detail", help="Fetch indicator detail.")
    detail_parser.add_argument("indicator")
    detail_parser.add_argument("--size", type=int, default=20)
    detail_parser.add_argument("--start", type=int, default=0)
    detail_parser.add_argument("--pretty", action="store_true")

    sync_parser = subparsers.add_parser("sync-duckdb", help="Sync calendar data into DuckDB.")
    sync_parser.add_argument("--db", default="data/futunn_calendar.duckdb")
    sync_parser.add_argument("--tab", type=_tab, default=CalendarTab.ECONOMIC_DATA)
    sync_parser.add_argument("--start")
    sync_parser.add_argument("--end")
    sync_parser.add_argument("--max-pages", type=int)
    sync_parser.add_argument("--page-delay", type=float, default=0.5)
    sync_parser.add_argument("--include-details", action="store_true")
    sync_parser.add_argument("--detail-size", type=int, default=20)
    sync_parser.add_argument("--detail-delay", type=float, default=0.2)
    sync_parser.add_argument("--pretty", action="store_true")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    client = FutunnCalendarClient(
        base_url=args.base_url,
        language=args.lang,
        time_zone=args.timezone,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
    )

    if args.command == "list":
        kwargs = {
            "tab": args.tab,
            "start": args.start,
            "end": args.end,
            "range_type": args.range_type,
            "countries": _ints(args.country),
            "markets": _ints(args.market),
            "ipo_markets": _ints(args.ipo_market),
            "stars": args.star,
            "stock_types": _ints(args.stock_type),
            "language": args.lang,
            "time_zone": args.timezone,
        }
        if args.all:
            pages = [
                page.to_dict()
                for page in client.iter_pages(max_pages=args.max_pages, **kwargs)
            ]
            _print({"pages": pages}, args.pretty)
        else:
            page = client.list(**kwargs)
            _print(page.to_dict(), args.pretty)
        return 0

    if args.command == "detail":
        detail = client.detail(
            args.indicator,
            size=args.size,
            start=args.start,
            language=args.lang,
        )
        _print(detail.to_dict(), args.pretty)
        return 0

    if args.command == "sync-duckdb":
        try:
            from .storage import sync_calendar_to_duckdb
        except ImportError as exc:
            if exc.name == "duckdb" or "DuckDB support is not installed" in str(exc):
                print(
                    "DuckDB support is not installed. Install it with: "
                    "python -m pip install 'futunn-calendar[duckdb]'",
                    file=sys.stderr,
                )
                return 1
            raise

        result = sync_calendar_to_duckdb(
            args.db,
            client=client,
            tab=args.tab,
            start=args.start,
            end=args.end,
            max_pages=args.max_pages,
            page_delay=args.page_delay,
            include_details=args.include_details,
            detail_size=args.detail_size,
            detail_delay=args.detail_delay,
        )
        _print(result.to_dict(), args.pretty)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
