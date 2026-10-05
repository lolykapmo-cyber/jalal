#!/usr/bin/env bash
#
# One-command install on a fresh Debian/Ubuntu VPS.
#
#   sudo bash deploy.sh
#
# Creates a dedicated directory and system user, makes sure a new enough
# Python is present, installs ffmpeg and the dependencies into a virtualenv,
# registers a systemd service, and schedules a nightly yt-dlp update.
# Re-running it is safe: the code is updated in place and the token is kept.
#
# The bot token is typed at a prompt, never passed as an argument, so it
# stays out of your shell history and out of the process list.

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/jalal}"
SERVICE_USER="${SERVICE_USER:-jalalbot}"
SERVICE_NAME="${SERVICE_NAME:-jalal-bot}"
REPO_URL="${REPO_URL:-https://github.com/lolykapmo-cyber/jalal.git}"
BRANCH="${BRANCH:-claude/epic-euler-mfpvcq}"
SCRIPT_REVISION="2026-10-05.11"

# yt-dlp, python-telegram-bot and curl_cffi all require Python 3.10+.
# Ubuntu 20.04 still ships 3.8, where pip quietly resolves to a yt-dlp from
# 2024 that current sites reject.
MIN_PYTHON_MINOR="${MIN_PYTHON_MINOR:-10}"
PYTHON_SERIES="${PYTHON_SERIES:-3.12}"

# Channels a user must join before the bot answers them. Edit in .env later.
REQUIRED_CHANNELS="${REQUIRED_CHANNELS:-@nextgenshop1,@Nexus_tv_1}"

# Re-encoding is CPU-bound, so the worker count tracks the core count.
# More workers than cores makes everyone slower, not faster.
WORKERS="${WORKERS:-$(nproc 2>/dev/null || echo 2)}"

# yt-dlp's stable releases can trail its master branch by over a month, and
# a site-breaking change is usually fixed there within days. Tracking the
# pre-release builds is the difference between the bot recovering by itself
# and sitting broken until the next stable. Set YTDLP_PRE="" for stable.
YTDLP_PRE="${YTDLP_PRE:---pre}"

ENV_FILE="$INSTALL_DIR/.env"
VENV_DIR="$INSTALL_DIR/.venv"
DATA_DIR="$INSTALL_DIR/data"
PYTHON_DIR="$INSTALL_DIR/python"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-/var/lib/jalal/downloads}"

# All progress goes to stderr. Some of these are called from functions whose
# stdout is captured (the interpreter path), and a stray message there would
# be read back as part of the path.
# git refuses to operate on a repository owned by another user. Scoping
# the exception to this one command keeps it out of root's global gitconfig.
git_repo() {
    git -c safe.directory="$INSTALL_DIR" -C "$INSTALL_DIR" "$@"
}

set_env_default() {
    local key="$1" value="$2"
    grep -qE "^${key}=.+" "$ENV_FILE" && return 0
    set_env_var "$key" "$value"
}

set_env_var() {
    local key="$1" value="$2"
    if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
    fi
}

say()  { printf '\n\033[1;36m==>\033[0m %s\n' "$1" >&2; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$1" >&2; }
info() { printf '    %s\n' "$1" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$1" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run this with sudo: sudo bash deploy.sh"
command -v apt-get >/dev/null || die "This script targets Debian/Ubuntu (apt-get not found)."

# shellcheck disable=SC1091
[[ -r /etc/os-release ]] && . /etc/os-release
say "deploy.sh rev $SCRIPT_REVISION on ${PRETTY_NAME:-unknown} (${ID:-?} ${VERSION_ID:-?})"

# ---------------------------------------------------------------- packages
say "Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    ffmpeg git curl ca-certificates build-essential \
    python3 python3-pip python3-venv software-properties-common \
    || die "apt-get could not install the base packages."

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
    # git refuses to work in a repository owned by another user, and an
    # earlier revision of this script chowned the checkout to the service
    # user. The -c safe.directory override below is honoured by current git
    # but not by the 2.25.1 Ubuntu 20.04 ships, so correct the ownership
    # itself: root owning the code is the layout we want regardless. The
    # data directory and .env are given back their owners further down.
    chown -R root:root "$INSTALL_DIR"
    git_repo remote set-url origin "$REPO_URL"
    git_repo fetch --quiet origin "$BRANCH"
    git_repo checkout --quiet -B "$BRANCH" "origin/$BRANCH"
else
    say "Cloning into $INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    # git refuses a non-empty target, so clone first and add the rest after.
    git clone --quiet --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

mkdir -p "$DATA_DIR" "$DOWNLOAD_DIR"

# ----------------------------------------------------------------- python
# Three ways to get a new enough interpreter, cheapest first.

python_is_new_enough() {
    "$1" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, $MIN_PYTHON_MINOR) else 1)" \
        2>/dev/null
}

# 1. Something already on PATH.
find_system_python() {
    local candidate resolved
    for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
        resolved="$(command -v "$candidate" 2>/dev/null)" || continue
        if python_is_new_enough "$resolved"; then
            printf '%s\n' "$resolved"
            return 0
        fi
    done
    return 1
}

# 2. Distro packages. deadsnakes backports current Pythons to older Ubuntu,
#    but it is not available everywhere, so a failure here is not fatal.
install_python_from_apt() {
    local log
    if [[ "${ID:-}" == "ubuntu" ]]; then
        info "Trying the deadsnakes PPA..."
        if log="$(add-apt-repository -y ppa:deadsnakes/ppa 2>&1)"; then
            apt-get update -qq || true
        else
            warn "deadsnakes is unavailable on this host:"
            printf '%s\n' "$log" | tail -4 | sed 's/^/        /'
        fi
    fi
    log="$(apt-get install -y -qq --no-install-recommends \
            "python$PYTHON_SERIES" "python$PYTHON_SERIES-venv" \
            "python$PYTHON_SERIES-dev" 2>&1)" && return 0
    info "apt has no python$PYTHON_SERIES packages:"
    printf '%s\n' "$log" | grep -E '^E:' | head -3 | sed 's/^/        /' || true
    return 1
}

# 3. A standalone CPython build, downloaded by uv. No repositories, no
#    compiling, and it works on any glibc Linux. This is the reliable path.
ensure_uv() {
    export PATH="/root/.local/bin:/usr/local/bin:$PATH"
    command -v uv >/dev/null 2>&1 && return 0
    info "Installing uv..."
    python3 -m pip install --quiet --upgrade uv >/dev/null 2>&1 || true
    command -v uv >/dev/null 2>&1 && return 0
    # Astral's official installer, used only if PyPI did not work.
    curl -LsSf https://astral.sh/uv/install.sh 2>/dev/null | sh >/dev/null 2>&1 || true
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null 2>&1
}

install_python_standalone() {
    ensure_uv || { info "Could not install uv."; return 1; }

    info "Downloading a standalone Python $PYTHON_SERIES (about 30 MB)..."
    mkdir -p "$PYTHON_DIR"
    # Keep it inside the bot's own directory: the service user must be able
    # to read it, and systemd's ProtectHome would hide anything under /root.
    # The "failed to install executable" warning is harmless; the interpreter
    # is located by path below rather than by a shim on PATH.
    UV_PYTHON_INSTALL_DIR="$PYTHON_DIR" uv python install "$PYTHON_SERIES" \
        >/dev/null 2>&1 || true

    local found
    found="$(find "$PYTHON_DIR" -type f -perm -u+x -name "python$PYTHON_SERIES" 2>/dev/null | head -1)"
    if [[ -z "$found" ]]; then
        found="$(find "$PYTHON_DIR" -type f -perm -u+x -name 'python3.*' 2>/dev/null | head -1)"
    fi
    [[ -n "$found" ]] || return 1
    python_is_new_enough "$found" || return 1
    # A venv needs both of these, and a stripped build can lack them.
    "$found" -c 'import venv, ensurepip' 2>/dev/null || return 1
    printf '%s\n' "$found"
}

say "Locating a Python 3.$MIN_PYTHON_MINOR+ interpreter"
PYTHON_BIN="$(find_system_python || true)"

if [[ -z "$PYTHON_BIN" ]]; then
    warn "System Python is older than 3.$MIN_PYTHON_MINOR; installing Python $PYTHON_SERIES"
    install_python_from_apt || true
    PYTHON_BIN="$(find_system_python || true)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
    PYTHON_BIN="$(install_python_standalone || true)"
fi

[[ -n "$PYTHON_BIN" ]] || die "Could not find or install Python 3.$MIN_PYTHON_MINOR+.
   yt-dlp, python-telegram-bot and curl_cffi all require it. Options:
     - Use Docker instead; it bundles its own Python:
         cd $INSTALL_DIR && docker compose up -d
     - Install a Python by hand, then re-run this script.
   If the standalone download failed, this host may not reach
   github.com releases; check its outbound network."

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
say "Using Python $PY_VERSION at $PYTHON_BIN"

# --------------------------------------------------------------- virtualenv
say "Installing Python dependencies"

# A virtualenv built by an older interpreter cannot be upgraded in place,
# so replace it rather than failing on the dependency resolve. This is what
# a re-run after a failed install needs.
if [[ -x "$VENV_DIR/bin/python" ]] && ! python_is_new_enough "$VENV_DIR/bin/python"; then
    warn "Rebuilding the virtualenv on Python $PY_VERSION"
    rm -rf "$VENV_DIR"
fi

[[ -x "$VENV_DIR/bin/python" ]] || "$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip wheel
"$VENV_DIR/bin/pip" install --quiet --upgrade -r "$INSTALL_DIR/requirements.txt" \
    || die "Dependency install failed. The output above says why."

YTDLP_VERSION="$("$VENV_DIR/bin/python" -m yt_dlp --version 2>/dev/null || echo unknown)"
say "yt-dlp $YTDLP_VERSION"
case "$YTDLP_VERSION" in
    2019.*|2020.*|2021.*|2022.*|2023.*|2024.*)
        warn "That build is old enough that many sites will refuse it."
        warn "It means pip fell back for a Python it could satisfy. Re-run with:"
        warn "    sudo PYTHON_SERIES=3.12 bash deploy.sh"
        ;;
esac

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
    set_env_var BOT_TOKEN "$TOKEN"
    unset TOKEN
fi

# The shipped .env.example uses paths relative to the project directory,
# which systemd runs read-only under ProtectSystem=strict. Rewrite them to
# absolute, writable locations. Done on every run, so an .env left over
# from an earlier install is corrected too.
[[ -f "$ENV_FILE" ]] || cp "$INSTALL_DIR/.env.example" "$ENV_FILE"
set_env_var WORK_DIR "$DOWNLOAD_DIR"
set_env_var DATABASE_PATH "$DATA_DIR/bot.sqlite3"

# Defaults only: once set, these are yours to edit in .env.
set_env_default REQUIRED_CHANNELS "$REQUIRED_CHANNELS"
set_env_default MAX_CONCURRENT_DOWNLOADS "$WORKERS"

# --------------------------------------------------------------- ownership
say "Setting ownership and permissions"

# Code, virtualenv and interpreter stay owned by root and are only readable
# by the service user. The bot cannot rewrite the code it runs, and git --
# which is run as root on every update -- is not looking at a repository
# owned by somebody else. Capital X keeps the execute bit on directories
# and on the binaries that already had it, without adding it to sources.
chown -R root:"$SERVICE_USER" "$INSTALL_DIR"
chmod -R u=rwX,g=rX,o= "$INSTALL_DIR"

# The two directories the service genuinely writes.
chown -R "$SERVICE_USER":"$SERVICE_USER" "$DATA_DIR"
chmod 700 "$DATA_DIR"
chown "$SERVICE_USER":"$SERVICE_USER" "$DOWNLOAD_DIR"
# 755, not 750: a local Bot API server reads the finished file off disk and
# runs as its own user, in a container. At 750 it cannot even traverse here
# and reports "Can't get stat about the file" for every upload. These are
# transient downloads, not secrets; the token and database stay private.
chmod 755 "$DOWNLOAD_DIR"

# The token: readable by the service, invisible to every other account.
chown root:"$SERVICE_USER" "$ENV_FILE"
chmod 640 "$ENV_FILE"

# ----------------------------------------------------------------- service
say "Writing the systemd service"
cat > "/etc/systemd/system/$SERVICE_NAME.service" <<UNIT
[Unit]
Description=Telegram social media video downloader bot
Documentation=$REPO_URL
After=network-online.target
Wants=network-online.target
# systemd gives up after 5 restarts in 10s by default. This bot is meant to
# stay up, so let it keep retrying; RestartSec paces the attempts.
StartLimitIntervalSec=0

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
# The code directory is read-only, so skip the futile __pycache__ writes.
Environment=PYTHONDONTWRITEBYTECODE=1
# WORK_DIR and DATABASE_PATH live only in the EnvironmentFile: setting them
# here too left two sources of truth for one key. WORK_DIR is a real shared
# directory rather than a private /tmp, because a local Bot API server reads
# the finished file off disk at the exact path the bot gives it. Leftovers
# from a hard kill are swept at startup.
ExecStart=$VENV_DIR/bin/python -m bot
Restart=always
RestartSec=10
# Do not let a wedged shutdown delay the restart.
TimeoutStopSec=30
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
ReadWritePaths=$DATA_DIR $DOWNLOAD_DIR

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
# --pre matters: without it this is a no-op whenever the newest stable is
# already installed, which is exactly when a site has broken and master
# already carries the fix.
ExecStart=$VENV_DIR/bin/pip install --quiet --upgrade $YTDLP_PRE yt-dlp
ExecStart=$VENV_DIR/bin/pip install --quiet --upgrade curl_cffi
# Harmless when the PO token plugin is not installed; pip just skips it.
ExecStart=-$VENV_DIR/bin/pip install --quiet --upgrade bgutil-ytdlp-pot-provider
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

# ------------------------------------------------------- hourly self-test
# A site changing what it demands leaves the bot running while every
# download fails. Without this, nobody notices until a user complains.
say "Scheduling the hourly self-test"
cat > "/etc/systemd/system/$SERVICE_NAME-selftest.service" <<UNIT
[Unit]
Description=Check that downloading still works, and repair it if not
After=network-online.target $SERVICE_NAME.service
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=$ENV_FILE
Environment=WORK_DIR=$DOWNLOAD_DIR
Environment=DATABASE_PATH=$DATA_DIR/bot.sqlite3
# Runs as root because repairing means pip, docker and systemctl.
ExecStart=$VENV_DIR/bin/python -m bot.selftest
TimeoutStartSec=1800
UNIT

cat > "/etc/systemd/system/$SERVICE_NAME-selftest.timer" <<UNIT
[Unit]
Description=Hourly download self-test

[Timer]
OnBootSec=10min
OnUnitActiveSec=1h
RandomizedDelaySec=10min
Persistent=true

[Install]
WantedBy=timers.target
UNIT

say "Starting services"
systemctl daemon-reload
systemctl enable --quiet --now "$SERVICE_NAME-update.timer"
systemctl enable --quiet --now "$SERVICE_NAME-selftest.timer"
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
  Downloads      $DOWNLOAD_DIR
  Settings       $ENV_FILE
  Python         $PY_VERSION
  yt-dlp         $YTDLP_VERSION
  Self-test      systemctl start $SERVICE_NAME-selftest   (runs hourly)
  Live logs      journalctl -u $SERVICE_NAME -f
  Restart        systemctl restart $SERVICE_NAME
  Stop           systemctl stop $SERVICE_NAME
  Update code    sudo bash $INSTALL_DIR/deploy.sh

INFO
