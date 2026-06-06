param(
    [string]$ProjectDir = (Join-Path $HOME "futunn-calendar-python"),
    [string]$DbPath = (Join-Path (Join-Path $HOME "data") "futunn_calendar.duckdb"),
    [string]$InstallDuckDB = $env:INSTALL_DUCKDB,
    [string]$EnableSync = $env:ENABLE_SYNC
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/cgefw/futunn-calendar-python.git"

function Normalize-YesNo([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    switch ($Value.ToLowerInvariant()) {
        { $_ -in @("y", "yes", "true", "1") } { return "yes" }
        { $_ -in @("n", "no", "false", "0") } { return "no" }
        default { return "" }
    }
}

function Ask-YesNo([string]$Prompt, [string]$DefaultValue) {
    while ($true) {
        $suffix = if ($DefaultValue -eq "yes") { "[Y/n]" } else { "[y/N]" }
        $answer = Read-Host "$Prompt $suffix"
        if ([string]::IsNullOrWhiteSpace($answer)) { $answer = $DefaultValue }
        $normalized = Normalize-YesNo $answer
        if ($normalized) { return $normalized }
        Write-Host "Please answer yes or no."
    }
}

$InstallDuckDB = Normalize-YesNo $InstallDuckDB
if (-not $InstallDuckDB) {
    $InstallDuckDB = Ask-YesNo "Install DuckDB support for local sync?" "yes"
}

$EnableSync = Normalize-YesNo $EnableSync
if ($InstallDuckDB -eq "yes" -and -not $EnableSync) {
    $EnableSync = Ask-YesNo "Enable DuckDB sync now and create a monthly updater when supported?" "no"
}
if ($InstallDuckDB -eq "no") {
    $EnableSync = "no"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ProjectDir) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $DbPath) | Out-Null

if (Test-Path (Join-Path $ProjectDir ".git")) {
    git -C $ProjectDir pull --ff-only
} else {
    if (Test-Path $ProjectDir) { Remove-Item -Recurse -Force $ProjectDir }
    git clone $RepoUrl $ProjectDir
}

Set-Location $ProjectDir

$Python = (Get-Command py -ErrorAction SilentlyContinue)
if ($Python) {
    & py -3 -m venv .venv
} else {
    & python -m venv .venv
}

$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
if ($InstallDuckDB -eq "yes") {
    & $VenvPython -m pip install -e ".[duckdb]"
} else {
    & $VenvPython -m pip install -e .
}

& $VenvPython -c "from futunn_calendar import FutunnCalendarClient; print('futunn-calendar import OK')"

& $VenvPython -m futunn_calendar.cli --help | Out-Null

if ($InstallDuckDB -eq "yes") {
    & $VenvPython -c "from futunn_calendar import sync_calendar_to_duckdb; print('DuckDB sync import OK')"
}

if ($EnableSync -eq "yes") {
    & $VenvPython -m futunn_calendar.cli sync-duckdb --db $DbPath --page-delay 0.5 --pretty

    $taskName = "CalendarMonthlyUpdate"
    $taskCommand = "`"$VenvPython`" -m futunn_calendar.cli sync-duckdb --db `"$DbPath`" --page-delay 0.5 --pretty"
    try {
        schtasks /Create /TN $taskName /SC MONTHLY /D 1 /ST 06:00 /TR $taskCommand /F | Out-Null
        Write-Host "Created monthly Windows Scheduled Task: $taskName"
    } catch {
        Write-Warning "Could not create Windows Scheduled Task. Initial sync completed."
    }
}

Write-Host "Installed unofficial calendar Python wrapper."
Write-Host "Project: $ProjectDir"
Write-Host "DuckDB:  $DbPath"
Write-Host "DuckDB support: $InstallDuckDB"
Write-Host "Sync enabled: $EnableSync"
Write-Host ""
Write-Host "Verify:"
Write-Host "  cd `"$ProjectDir`""
Write-Host "  .\.venv\Scripts\python.exe -m futunn_calendar.cli list --tab economic-data --start 2026-06-09 --end 2026-06-09 --star 3 --pretty"
