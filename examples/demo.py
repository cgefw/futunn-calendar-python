from futunn_calendar import CalendarTab, FutunnCalendarClient


def main() -> None:
    client = FutunnCalendarClient(language="zh-cn", max_retries=5, retry_delay=2)

    total_printed = 0
    total_available = None

    for page_index, page in enumerate(
        client.iter_pages(tab=CalendarTab.ECONOMIC_DATA, page_delay=0.5),
        start=1,
    ):
        if total_available is None:
            total_available = page.total
            print(f"总数: {total_available}")

        print(f"\n第 {page_index} 页，本页 {len(page.events)} 条")
        for event in page.events:
            total_printed += 1
            print(
                f"{total_printed}. {event.date} | "
                f"{event.title} | "
                f"时间戳={event.timestamp or '-'} | "
                f"指标ID={event.indicator_id or '-'}"
            )

    print(f"\n已输出: {total_printed} 条")


if __name__ == "__main__":
    main()
