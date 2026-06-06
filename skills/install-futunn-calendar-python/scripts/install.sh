#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/futunn-calendar-python}"
DB_PATH="${2:-$HOME/data/futunn_calendar.duckdb}"
REPO_URL="https://github.com/cgefw/futunn-calendar-python.git"

ask_yes_no() {
  local prompt="$1"
  local default_value="$2"
  local value

  while true; do
    if [ "$default_value" = "yes" ]; then
      read -r -p "$prompt [Y/n]: " value
      value="${value:-yes}"
    else
      read -r -p "$prompt [y/N]: " value
      value="${value:-no}"
    fi

    case "${value,,}" in
      y|yes) echo "yes"; return 0 ;;
      n|no) echo "no"; return 0 ;;
      *) echo "Please answer yes or no." >&2 ;;
    esac
  done
}

normalize_yes_no() {
  local value="${1:-}"
  case "${value,,}" in
    y|yes|true|1) echo "yes" ;;
    n|no|false|0) echo "no" ;;
    *) echo "" ;;
  esac
}

INSTALL_DUCKDB="$(normalize_yes_no "${INSTALL_DUCKDB:-}")"
if [ -z "$INSTALL_DUCKDB" ]; then
  INSTALL_DUCKDB="$(ask_yes_no "Install DuckDB support for local sync?" "yes")"
fi

ENABLE_SYNC="$(normalize_yes_no "${ENABLE_SYNC:-}")"
if [ "$INSTALL_DUCKDB" = "yes" ] && [ -z "$ENABLE_SYNC" ]; then
  ENABLE_SYNC="$(ask_yes_no "Enable DuckDB sync now and create a monthly updater when supported?" "no")"
fi
if [ "$INSTALL_DUCKDB" = "no" ]; then
  ENABLE_SYNC="no"
fi

mkdir -p "$(dirname "$PROJECT_DIR")" "$(dirname "$DB_PATH")"

if [ -d "$PROJECT_DIR/.git" ]; then
  git -C "$PROJECT_DIR" pull --ff-only
else
  rm -rf "$PROJECT_DIR"
  git clone "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
if [ "$INSTALL_DUCKDB" = "yes" ]; then
  python -m pip install -e ".[duckdb]"
else
  python -m pip install -e .
fi

python - <<'PY'
from futunn_calendar import FutunnCalendarClient
print("futunn-calendar import OK")
PY

futunn-calendar --help >/dev/null

if [ "$INSTALL_DUCKDB" = "yes" ]; then
  python - <<'PY'
from futunn_calendar import sync_calendar_to_duckdb
print("DuckDB sync import OK")
PY
fi

if [ "$ENABLE_SYNC" = "yes" ]; then
  mkdir -p .local
  cat > .local/update_calendar_duckdb.sh <<EOF_SYNC
#!/usr/bin/env bash
set -euo pipefail

cd "$PROJECT_DIR"
source .venv/bin/activate
futunn-calendar sync-duckdb --db "$DB_PATH" --page-delay 0.5 --pretty
EOF_SYNC
  chmod +x .local/update_calendar_duckdb.sh

  .local/update_calendar_duckdb.sh

  if command -v systemctl >/dev/null 2>&1 && systemctl --user status >/dev/null 2>&1; then
    mkdir -p "$HOME/.config/systemd/user"
    cat > "$HOME/.config/systemd/user/futunn-calendar-update.service" <<EOF_SERVICE
[Unit]
Description=Update local calendar DuckDB

[Service]
Type=oneshot
ExecStart=$PROJECT_DIR/.local/update_calendar_duckdb.sh
EOF_SERVICE

    cat > "$HOME/.config/systemd/user/futunn-calendar-update.timer" <<'EOF_TIMER'
[Unit]
Description=Monthly local calendar DuckDB update

[Timer]
OnCalendar=*-*-01 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF_TIMER

    systemctl --user daemon-reload
    systemctl --user enable --now futunn-calendar-update.timer
    loginctl enable-linger "$USER" >/dev/null 2>&1 || true
  else
    echo "systemd user session is not available; monthly timer was not created." >&2
  fi
fi

cat <<EOF
Installed unofficial calendar Python wrapper.
Project: $PROJECT_DIR
DuckDB:  $DB_PATH
DuckDB support: $INSTALL_DUCKDB
Sync enabled: $ENABLE_SYNC

Verify:
  cd "$PROJECT_DIR"
  source .venv/bin/activate
  futunn-calendar list --tab economic-data --start 2026-06-09 --end 2026-06-09 --star 3 --pretty
EOF
