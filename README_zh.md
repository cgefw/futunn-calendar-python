# Futunn Calendar Python Client（非官方）

**非官方项目，与 Futu、Futunn、Futubull、富途及其关联公司没有隶属、授权、
认可或合作关系。仅供个人研究使用。不要再分发数据。**

这是一个 experimental wrapper，用于读取
`https://news.futunn.com/new-calendar` 页面可公开访问的网页 JSON 响应。它
不是官方 API，不是稳定数据源，不构成投资建议，也不授予任何第三方数据权利。

使用前请自行确认来源网站当前服务条款和 robots.txt：

- 服务条款：https://www.futunn.com/about/services?lang=zh-cn
- robots.txt：https://www.futunn.com/robots.txt
- 官方支持的替代路径：https://openapi.futunn.com/futu-api-doc/

请阅读 [DATA_NOTICE.md](DATA_NOTICE.md)。本项目代码采用 PolyForm
Noncommercial License 1.0.0；许可证只覆盖代码，不授权任何第三方数据。

## 功能

- 读取财经日历页面 JSON 响应
- 处理页面分页元数据
- 按日期、国家、市场、星级筛选
- 读取经济指标历史详情
- 同步事件数据到本地 DuckDB
- 提供命令行工具 `futunn-calendar`
- 提供事件定时刷新脚本，到事件公布时间后刷新 DuckDB 中的公布值

## 安装

复制给 Codex 或 Claude Code 的一键安装指令：

Linux / macOS / Git Bash：

```text
bash -lc 'set -e; cd /tmp; rm -rf futunn-calendar-python-install; git clone https://github.com/cgefw/futunn-calendar-python.git futunn-calendar-python-install; cd futunn-calendar-python-install/skills/install-futunn-calendar-python; bash scripts/install.sh'
```

Windows PowerShell：

```text
powershell -ExecutionPolicy Bypass -Command "Set-StrictMode -Version Latest; $ErrorActionPreference='Stop'; $tmp=Join-Path $env:TEMP 'futunn-calendar-python-install'; if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }; git clone https://github.com/cgefw/futunn-calendar-python.git $tmp; Set-Location (Join-Path $tmp 'skills/install-futunn-calendar-python'); powershell -ExecutionPolicy Bypass -File scripts/install.ps1"
```

安装脚本会询问：

```text
是否安装 DuckDB 支持
是否启用 DuckDB 同步
```

开发安装：

```bash
python -m pip install -e .
```

如果需要 DuckDB 同步功能：

```bash
python -m pip install -e ".[duckdb]"
```

从 GitHub 安装：

```bash
python -m pip install git+https://github.com/cgefw/futunn-calendar-python.git
```

从 GitHub 安装并启用 DuckDB 支持：

```bash
python -m pip install "futunn-calendar[duckdb] @ git+https://github.com/cgefw/futunn-calendar-python.git"
```

## Python 用法

```python
from futunn_calendar import CalendarTab, FutunnCalendarClient

client = FutunnCalendarClient(language="zh-cn", max_retries=5, retry_delay=2)

page = client.list(
    tab=CalendarTab.ECONOMIC_DATA,
    start="2026-06-09",
    end="2026-06-09",
    stars=["3"],
)

print(page.total)
for event in page.events:
    print(event.date, event.title, event.timestamp)
```

只拉某一天 3 星经济数据并输出原始返回：

```bash
python - <<'PY'
from futunn_calendar import CalendarTab, FutunnCalendarClient

client = FutunnCalendarClient(language="zh-cn", max_retries=5, retry_delay=2)

page = client.list(
    tab=CalendarTab.ECONOMIC_DATA,
    start="2026/06/09",
    end="2026/06/09",
    stars=["3"],
)

print(page.raw)
PY
```

## 命令行

拉取列表：

```bash
futunn-calendar list \
  --tab economic-data \
  --start 2026-06-09 \
  --end 2026-06-09 \
  --star 3 \
  --pretty
```

拉取指标历史详情：

```bash
futunn-calendar detail 950 --pretty
```

## DuckDB 同步

同步财经日历到本地 DuckDB：

```bash
python -m pip install -e ".[duckdb]"
futunn-calendar sync-duckdb \
  --db "$HOME/data/futunn_calendar.duckdb" \
  --page-delay 0.5 \
  --pretty
```

只同步某一天：

```bash
futunn-calendar sync-duckdb \
  --db "$HOME/data/futunn_calendar.duckdb" \
  --start 2026-06-09 \
  --end 2026-06-09 \
  --page-delay 0.5 \
  --pretty
```

同步后会创建或更新这些表：

```text
calendar_events
calendar_indicator_history
calendar_sync_runs
```

核心字段包括：

```text
event_key
date
date_text
title
timestamp
timestamp_utc
indicator_id
country
star
previous
consensus
actual
raw_json
updated_at
```

检查保存结果：

```bash
python - <<'PY'
from pathlib import Path

import duckdb

con = duckdb.connect(str(Path.home() / "data" / "futunn_calendar.duckdb"))
print(con.execute("select count(*) from calendar_events").fetchone()[0])
print(con.execute("select min(date), max(date) from calendar_events").fetchone())
PY
```

## 事件公布值定时刷新

脚本位置：

```text
scripts/event_timer_refresh.py
```

用途：

- 从 DuckDB 读取还没有 `actual` 的未来事件
- 根据 `timestamp_utc` 设置 timer
- 事件时间到后调用本库重新读取当天数据
- 如果公布值还没出来，会按配置重试
- 刷新结果写回 DuckDB

示例：

```bash
PYTHONPATH=src python scripts/event_timer_refresh.py \
  --db "$HOME/data/futunn_calendar.duckdb" \
  --min-star 3 \
  --post-delay 1 \
  --retry-schedule 5,10,30,60x9
```

默认重试逻辑：

```text
事件时间 + 1 秒先刷新一次
没拿到 actual，5 秒后重试
再没拿到，10 秒后重试
再没拿到，30 秒后重试
之后每 60 秒重试，最多 9 次
```

## Python 接口

- `FutunnCalendarClient.list(...)`
- `FutunnCalendarClient.iter_pages(...)`
- `FutunnCalendarClient.iter_events(...)`
- `FutunnCalendarClient.detail(...)`
- `sync_calendar_to_duckdb(...)`
- `init_duckdb(...)`

## 数据说明

本项目读取的是网页 JSON 响应。该响应没有被 Futu/Futunn 作为受支持的公开
API 文档化，未来可能变化、不可用或受来源网站条款限制。
