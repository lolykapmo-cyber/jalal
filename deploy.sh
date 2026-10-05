#!/usr/bin/env bash
#
# One-command install on a fresh Ubuntu/Debian VPS.
#
#   sudo bash deploy.sh
#
# Creates a dedicated directory and system user, installs ffmpeg and the
# Python dependencies into a virtualenv, registers a systemd service, and
# schedules a nightly yt-dlp update. Re-running it is safe: the service is
# updated in place and an existing token is kept.
#
# The bot token is typed at a prompt, never passed as an argument, so it
# stays out of your shell history and out of the process list.

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/jalal}"
SERVICE_USER="${SERVICE_USER:-jalalbot}"
SERVICE_NAME="${SERVICE_NAME:-jalal-bot}"
REPO_URL="${REPO_URL:-https://github.com/lolykapmo-cyber/jalal.git}"
BRANCH="${BRANCH:-claude/epic-euler-mfpvcq}"

ENV_FILE="$INSTALL_DIR/.env"
VENV_DIR="$INSTALL_DIR/.venv"
DATA_DIR="$INSTALL_DIR/data"

say()  { printf '\n\033[1;36m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$1"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$1" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run this with sudo: sudo bash deploy.sh"
command -v apt-get >/dev/null || die "This script targets Debian/Ubuntu (apt-get not found)."

# ---------------------------------------------------------------- packages
say "Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    python3 python3-venv python3-dev \
    ffmpeg git ca-certificates build-essential

# ------------------------------------------------------------------- user
if id "$SERVICE_USER" &>/dev/null; then
    say "Service user $SERVICE_USER already exists"
else
    say "Creating service user $SERVICE_USER"
    # No login shell and no home of its own: it only ever runs the bot.
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# ------------------------------------------------------------------- code
if [[ -d "$INSTALL_DIR/.git" ]]; then
    say "Updating the existing checkout in $INSTALL_DIR"
    git -C "$INSTALL_DIR" remote set-url origin "$REPO_URL"
    git -C "$INSTALL_DIR" fetch --quiet origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout --quiet -B "$BRANCH" "origin/$BRANCH"
else
    say "Cloning into $INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --quiet --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

mkdir -p "$DATA_DIR"

# --------------------------------------------------------------- virtualenv
say "Installing Python dependencies"
[[ -x "$VENV_DIR/bin/python" ]] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip wheel
"$VENV_DIR/bin/pip" install --quiet --upgrade -r "$INSTALL_DIR/requirements.txt"

# ------------------------------------------------------------------ token
if [[ -f "$ENV_FILE" ]] && grep -qE '^BOT_TOKEN=.+' "$ENV_FILE"; then
    say "Keeping the token already in $ENV_FILE"
else
    say "Bot token"
    TOKEN="${BOT_TOKEN:-}"
    if [[ -z "$TOKEN" ]]; then
        [[ -t 0 ]] || die "No token. Either run interactively or set BOT_TOKEN=... in the environment."
        printf 'Paste the token from @BotFather (it will not be echoed): '
        read -rs TOKEN
        printf '\n'
    fi
    [[ "$TOKEN" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] \
        || die "That does not look like a bot token (expected 123456789:AA...)."

    [[ -f "$ENV_FILE" ]] || cp "$INSTALL_DIR/.env.example" "$ENV_FILE"
    # Replace the placeholder line rather than appending a duplicate.
    if grep -qE '^BOT_TOKEN=' "$ENV_FILE"; then
        sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=$TOKEN|" "$ENV_FILE"
    else
        printf 'BOT_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE"
    fi
    unset TOKEN
fi

# --------------------------------------------------------------- ownership
say "Setting ownership and permissions"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod 750 "$INSTALL_DIR"
chmod 600 "$ENV_FILE"          # the token is readable only by the service user
chmod 700 "$DATA_DIR"

# ----------------------------------------------------------------- service
say "Writing the systemd service"
cat > "/etc/systemd/system/$SERVICE_NAME.service" <<UNIT
[Unit]
Description=Telegram social media video downloader bot
Documentation=$REPO_URL
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
# PrivateTmp gives the service its own /tmp, wiped on every restart, so
# half-finished downloads can never accumulate on disk.
Environment=WORK_DIR=/tmp/jalal-downloads
Environment=DATABASE_PATH=$DATA_DIR/bot.sqlite3
ExecStart=$VENV_DIR/bin/python -m bot
Restart=always
RestartSec=10
# Transcoding is CPU-hungry; stay out of the way of everything else.
Nice=10

# Hardening: the bot needs the network and its own data directory, nothing more.
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictRealtime=true
LockPersonality=true
ReadWritePaths=$DATA_DIR

[Install]
WantedBy=multi-user.target
UNIT

# ------------------------------------------------- nightly yt-dlp refresh
# This is the single most effective reliability measure: when a platform
# changes something, yt-dlp usually ships a fix within days.
say "Scheduling the nightly yt-dlp update"
cat > "/etc/systemd/system/$SERVICE_NAME-update.service" <<UNIT
[Unit]
Description=Update yt-dlp and restart the bot
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$VENV_DIR/bin/pip install --quiet --upgrade yt-dlp curl_cffi
ExecStartPost=/bin/systemctl try-restart $SERVICE_NAME.service
UNIT

cat > "/etc/systemd/system/$SERVICE_NAME-update.timer" <<UNIT
[Unit]
Description=Nightly yt-dlp update

[Timer]
OnCalendar=daily
# Spread the load, and survive a server that was powered off overnight.
RandomizedDelaySec=2h
Persistent=true

[Install]
WantedBy=timers.target
UNIT

say "Starting services"
systemctl daemon-reload
systemctl enable --quiet --now "$SERVICE_NAME-update.timer"
systemctl enable --quiet "$SERVICE_NAME.service"
systemctl restart "$SERVICE_NAME.service"

sleep 4
if systemctl is-active --quiet "$SERVICE_NAME.service"; then
    say "The bot is running. Send it /start on Telegram."
else
    warn "The service is not active. The last 30 log lines:"
    journalctl -u "$SERVICE_NAME.service" -n 30 --no-pager || true
    exit 1
fi

cat <<INFO

  Directory      $INSTALL_DIR
  Settings       $ENV_FILE
  Live logs      journalctl -u $SERVICE_NAME -f
  Restart        systemctl restart $SERVICE_NAME
  Stop           systemctl stop $SERVICE_NAME
  Update code    sudo bash $INSTALL_DIR/deploy.sh

INFO
