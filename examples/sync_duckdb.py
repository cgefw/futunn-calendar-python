import duckdb

from futunn_calendar import CalendarTab, FutunnCalendarClient, sync_calendar_to_duckdb


def main() -> None:
    db_path = "data/futunn_calendar.duckdb"
    client = FutunnCalendarClient(language="zh-cn", max_retries=5, retry_delay=2)

    result = sync_calendar_to_duckdb(
        db_path,
        client=client,
        tab=CalendarTab.ECONOMIC_DATA,
        page_delay=0.5,
    )
    print(result.to_dict())

    con = duckdb.connect(db_path)
    print(con.execute("select count(*) from calendar_events").fetchone()[0])
    print(con.execute("select min(date), max(date) from calendar_events").fetchone())
    con.close()


if __name__ == "__main__":
    main()
