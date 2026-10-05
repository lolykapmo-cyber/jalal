#!/usr/bin/env bash
#
# Raise the upload ceiling from 50 MB to 2 GB.
#
#   sudo bash setup-local-api.sh
#
# The public Bot API refuses uploads above 50 MB. A self-hosted Bot API
# server lifts that to 2000 MB. This runs one in Docker, bound to localhost,
# and points the bot at it.
#
# You need an api_id and api_hash from https://my.telegram.org (log in,
# "API development tools", create an application). They identify the server,
# not your bot, and are unrelated to the bot token.
#
# One-way step: Telegram requires a bot to log out of the public API before
# a self-hosted server will accept it. Moving back means logging out of the
# local server in the same way. The script asks before doing it.

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/jalal}"
SERVICE_NAME="${SERVICE_NAME:-jalal-bot}"
SERVICE_USER="${SERVICE_USER:-jalalbot}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-/var/lib/jalal/downloads}"
CONTAINER="${CONTAINER:-telegram-bot-api}"
IMAGE="${IMAGE:-aiogram/telegram-bot-api:latest}"
BIND_ADDR="${BIND_ADDR:-127.0.0.1}"
PORT="${PORT:-8081}"

ENV_FILE="$INSTALL_DIR/.env"
API_ROOT="http://$BIND_ADDR:$PORT"

say()  { printf '\n\033[1;36m==>\033[0m %s\n' "$1" >&2; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$1" >&2; }
info() { printf '    %s\n' "$1" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$1" >&2; exit 1; }

set_env_var() {
    local key="$1" value="$2"
    if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
    fi
}

[[ $EUID -eq 0 ]] || die "Run this with sudo: sudo bash setup-local-api.sh"
[[ -f "$ENV_FILE" ]] || die "No $ENV_FILE. Run deploy.sh first."

TOKEN="$(grep -E '^BOT_TOKEN=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
[[ -n "$TOKEN" ]] || die "BOT_TOKEN is not set in $ENV_FILE."

# --------------------------------------------------------------- credentials
say "Telegram API credentials"
API_ID="${TELEGRAM_API_ID:-}"
API_HASH="${TELEGRAM_API_HASH:-}"

if [[ -z "$API_ID" || -z "$API_HASH" ]]; then
    [[ -t 0 ]] || die "Run interactively, or set TELEGRAM_API_ID and TELEGRAM_API_HASH."
    info "Get these from https://my.telegram.org -> API development tools."
    [[ -n "$API_ID" ]]   || { printf '    api_id: '; read -r API_ID; }
    [[ -n "$API_HASH" ]] || { printf '    api_hash (not echoed): '; read -rs API_HASH; printf '\n'; }
fi

[[ "$API_ID" =~ ^[0-9]{5,}$ ]] || die "api_id should be a number, got '$API_ID'."
[[ "$API_HASH" =~ ^[a-fA-F0-9]{32}$ ]] || die "api_hash should be 32 hex characters."

# ------------------------------------------------------------------- docker
if command -v docker >/dev/null 2>&1; then
    say "Docker is already installed"
else
    say "Installing Docker"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends docker.io \
        || die "Could not install Docker. Install it yourself, then re-run."
    systemctl enable --now docker
fi

docker info >/dev/null 2>&1 || die "Docker is installed but not running: systemctl start docker"

# ----------------------------------------------------------------- warning
say "About to move this bot off the public Bot API"
cat >&2 <<NOTE
    Telegram requires a bot to log out of the public API before a
    self-hosted server will accept it. After this:

      - uploads up to 2000 MB instead of 50 MB
      - the bot talks only to $API_ROOT
      - going back means logging out of the local server the same way
      - the bot may be unreachable for up to 10 minutes during the switch

NOTE
if [[ -t 0 && "${ASSUME_YES:-}" != "1" ]]; then
    printf '    Type yes to continue: ' >&2
    read -r reply
    [[ "$reply" == "yes" ]] || die "Cancelled. Nothing was changed."
fi

# --------------------------------------------------------------- container
say "Starting the Bot API server"

# The server reads finished files straight off disk, at the exact path the
# bot names, so the download directory is mounted read-only at that same
# path inside the container.
mkdir -p "$DOWNLOAD_DIR"
chown "$SERVICE_USER":"$SERVICE_USER" "$DOWNLOAD_DIR"
# The container reads as its own user, so the directory has to be traversable
# by it. These are transient public videos, not private data.
chmod 755 "$DOWNLOAD_DIR"

docker pull "$IMAGE" >/dev/null 2>&1 || warn "Could not pull $IMAGE; using any local copy."

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d \
    --name "$CONTAINER" \
    --restart unless-stopped \
    -p "$BIND_ADDR:$PORT:8081" \
    -e TELEGRAM_API_ID="$API_ID" \
    -e TELEGRAM_API_HASH="$API_HASH" \
    -e TELEGRAM_LOCAL=1 \
    -v telegram-bot-api-data:/var/lib/telegram-bot-api \
    -v "$DOWNLOAD_DIR:$DOWNLOAD_DIR:ro" \
    "$IMAGE" >/dev/null \
    || die "Could not start the container. Check: docker logs $CONTAINER"

say "Waiting for it to accept connections"
ready=0
for _ in $(seq 1 30); do
    if curl -fsS -m 3 "$API_ROOT/bot$TOKEN/getMe" >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 2
done

# ------------------------------------------------------------------ log out
if [[ "$ready" -eq 0 ]]; then
    say "Logging the bot out of the public API"
    # Expected on the first run: the local server rejects a bot that is
    # still signed in to api.telegram.org.
    curl -fsS -m 30 "https://api.telegram.org/bot$TOKEN/logOut" >/dev/null 2>&1 \
        || warn "logOut did not return cleanly; continuing."

    info "Waiting for the local server to take over..."
    for _ in $(seq 1 45); do
        if curl -fsS -m 3 "$API_ROOT/bot$TOKEN/getMe" >/dev/null 2>&1; then
            ready=1
            break
        fi
        sleep 4
    done
fi

[[ "$ready" -eq 1 ]] || die "The local server never answered for this bot.
   Look at: docker logs $CONTAINER
   A wrong api_id/api_hash, or a logOut that has not propagated yet, are the
   usual causes. Waiting a few minutes and re-running often resolves it."

# ---------------------------------------------------------------- switch over
say "Pointing the bot at the local server"
set_env_var TELEGRAM_API_ROOT "$API_ROOT"
set_env_var WORK_DIR "$DOWNLOAD_DIR"
# UPLOAD_LIMIT_MB is deliberately not set: the bot raises its own ceiling to
# 2000 as soon as it sees a non-default API root.
sed -i '/^UPLOAD_LIMIT_MB=/d' "$ENV_FILE"

systemctl restart "$SERVICE_NAME"
sleep 5

if systemctl is-active --quiet "$SERVICE_NAME"; then
    say "Done. The bot now uploads files up to 2 GB."
else
    warn "The bot did not come back up:"
    journalctl -u "$SERVICE_NAME" -n 30 --no-pager >&2 || true
    exit 1
fi

cat <<INFO

  API server     $API_ROOT  (container: $CONTAINER)
  Downloads      $DOWNLOAD_DIR
  Upload limit   2000 MB
  Server logs    docker logs -f $CONTAINER
  Bot logs       journalctl -u $SERVICE_NAME -f

  To go back to the public API:
    curl "$API_ROOT/bot<TOKEN>/logOut"
    docker rm -f $CONTAINER
    sed -i '/^TELEGRAM_API_ROOT=/d' $ENV_FILE
    systemctl restart $SERVICE_NAME

INFO
