#!/usr/bin/env bash
#
# Give yt-dlp a PO token provider, which is what YouTube now wants from an
# anonymous client.
#
#   bash setup-potoken.sh [test-youtube-url]
#
# Symptoms this addresses, all at once and all without cookies:
#   - "The page needs to be reloaded"
#   - "HTTP Error 403: Forbidden" while fetching the video data
#   - "Requested format is not available" on every client
#
# It runs brainicism/bgutil-ytdlp-pot-provider as a local HTTP service and
# installs the matching yt-dlp plugin into the bot's virtualenv. The service
# is bound to loopback only: it is unauthenticated, so exposing it would let
# anyone who can reach the host generate tokens on your server.

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/jalal}"
SERVICE_NAME="${SERVICE_NAME:-jalal-bot}"
SERVICE_USER="${SERVICE_USER:-jalalbot}"
CONTAINER="${CONTAINER:-bgutil-provider}"
IMAGE="${IMAGE:-brainicism/bgutil-ytdlp-pot-provider}"
PORT="${PORT:-4416}"

VENV_DIR="$INSTALL_DIR/.venv"
TEST_URL="${1:-}"

say()  { printf '\n\033[1;36m==>\033[0m %s\n' "$1" >&2; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$1" >&2; }
info() { printf '    %s\n' "$1" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$1" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run this as root: bash setup-potoken.sh"
[[ -x "$VENV_DIR/bin/python" ]] || die "No virtualenv at $VENV_DIR. Run deploy.sh first."

command -v docker >/dev/null 2>&1 \
    || die "Docker is not installed. Run setup-local-api.sh first, or: apt-get install -y docker.io"
docker info >/dev/null 2>&1 || die "Docker is not running: systemctl start docker"

# ---------------------------------------------------------------- provider
say "Starting the PO token provider"
docker pull "$IMAGE" >/dev/null 2>&1 || warn "Could not pull $IMAGE; using any local copy."

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
# --init reaps the Node child processes the server spawns.
# 127.0.0.1 in the mapping is deliberate: the server is unauthenticated.
docker run -d \
    --name "$CONTAINER" \
    --restart unless-stopped \
    --init \
    -p "127.0.0.1:$PORT:4416" \
    "$IMAGE" >/dev/null \
    || die "Could not start the provider. Check: docker logs $CONTAINER"

say "Waiting for it to listen on 127.0.0.1:$PORT"
listening=0
for _ in $(seq 1 30); do
    if timeout 2 bash -c "cat < /dev/null > /dev/tcp/127.0.0.1/$PORT" 2>/dev/null; then
        listening=1
        break
    fi
    sleep 2
done
[[ "$listening" -eq 1 ]] || die "The provider never opened port $PORT.
   Check: docker logs $CONTAINER"

# ------------------------------------------------------------------ plugin
say "Installing the yt-dlp plugin"
"$VENV_DIR/bin/pip" install --quiet --upgrade bgutil-ytdlp-pot-provider \
    || die "Could not install the plugin into $VENV_DIR."

# ------------------------------------------------------------------ verify
say "Checking that yt-dlp picked the provider up"
probe="$("$VENV_DIR/bin/python" -m yt_dlp --verbose --simulate \
            "https://www.youtube.com/watch?v=BaW_jenozKc" 2>&1 || true)"

if grep -qi 'PO Token Providers:.*bgutil' <<<"$probe"; then
    info "yt-dlp reports: $(grep -i 'PO Token Providers:' <<<"$probe" | head -1 | sed 's/^.*PO Token/PO Token/')"
else
    warn "yt-dlp did not list the bgutil provider. The plugin may not be visible."
    info "Plugin directory check:"
    "$VENV_DIR/bin/python" -c \
        "import yt_dlp_plugins, os; print('   ', os.path.dirname(yt_dlp_plugins.__file__))" 2>&1 \
        | sed 's/^/    /' || info "    yt_dlp_plugins not importable"
fi

# ---------------------------------------------------------------- restart
say "Restarting the bot"
systemctl restart "$SERVICE_NAME"
sleep 4
systemctl is-active --quiet "$SERVICE_NAME" || {
    warn "The bot did not come back:"
    journalctl -u "$SERVICE_NAME" -n 20 --no-pager >&2 || true
    exit 1
}

# ------------------------------------------------------------- real check
if [[ -n "$TEST_URL" ]]; then
    say "Trying your link for real"
    if sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -m yt_dlp \
            --simulate --no-warnings "$TEST_URL" >/dev/null 2>&1; then
        say "It works. Send that link to the bot."
    else
        warn "Still failing. The extractor said:"
        sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -m yt_dlp \
            --simulate "$TEST_URL" 2>&1 | tail -15 | sed 's/^/    /' >&2
        exit 1
    fi
else
    info "Pass a YouTube URL as an argument to test one end to end:"
    info "  bash setup-potoken.sh 'https://youtu.be/...'"
fi

cat <<INFO

  Provider       http://127.0.0.1:$PORT  (container: $CONTAINER, loopback only)
  Provider logs  docker logs -f $CONTAINER
  Bot logs       journalctl -u $SERVICE_NAME -f

  To remove it:
    docker rm -f $CONTAINER
    $VENV_DIR/bin/pip uninstall -y bgutil-ytdlp-pot-provider
    systemctl restart $SERVICE_NAME

INFO
