"""Runtime configuration, read once from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# The public Bot API refuses uploads above 50 MiB. A self-hosted Bot API
# server raises the ceiling to 2000 MiB, so the limit is configurable
# instead of hard-coded.
STANDARD_UPLOAD_LIMIT_MB = 50
LOCAL_UPLOAD_LIMIT_MB = 2000


class ConfigError(RuntimeError):
    """Raised when the environment is missing something the bot needs."""


def _text(name: str, default: str = "") -> str:
    return (os.getenv(name) or "").strip() or default


def _flag(name: str, default: bool = False) -> bool:
    raw = _text(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on", "y"}


def _number(name: str, default: int, minimum: int = 0) -> int:
    raw = _text(name)
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _decimal(name: str, default: float, minimum: float = 0.0) -> float:
    raw = _text(name)
    if not raw:
        return default
    try:
        return max(minimum, float(raw))
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _id_set(name: str) -> frozenset[int]:
    raw = _text(name)
    if not raw:
        return frozenset()
    ids: set[int] = set()
    for chunk in raw.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.add(int(chunk))
        except ValueError as exc:
            raise ConfigError(f"{name} must be a comma-separated list of numeric IDs, got {chunk!r}") from exc
    return frozenset(ids)


@dataclass(frozen=True)
class Settings:
    """Everything the bot reads from the environment."""

    token: str
    api_base_url: str
    api_file_base_url: str
    local_mode: bool
    upload_limit_mb: int
    work_dir: Path
    database_path: Path
    cookies_file: Path | None
    proxy: str | None
    allowed_users: frozenset[int]
    admin_users: frozenset[int]
    max_concurrent_downloads: int
    max_user_downloads: int
    cooldown_seconds: float
    max_duration_seconds: int
    max_playlist_items: int
    max_attempts: int
    cache_ttl_hours: int
    transcode_oversized: bool
    default_language: str
    default_quality: str
    ask_quality: bool
    log_level: str

    @property
    def upload_limit_bytes(self) -> int:
        return self.upload_limit_mb * 1024 * 1024

    def may_use_bot(self, user_id: int) -> bool:
        """An empty allow-list means the bot is open to everyone."""
        return not self.allowed_users or user_id in self.allowed_users

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_users


def load_settings(*, require_token: bool = True) -> Settings:
    """Build a `Settings` from the current environment."""
    token = _text("BOT_TOKEN") or _text("TELEGRAM_BOT_TOKEN")
    if require_token and not token:
        raise ConfigError(
            "BOT_TOKEN is not set. Create a bot with @BotFather and put its token in .env"
        )

    api_root = _text("TELEGRAM_API_ROOT", "https://api.telegram.org").rstrip("/")
    local_mode = _flag("LOCAL_BOT_API", api_root != "https://api.telegram.org")

    default_limit = LOCAL_UPLOAD_LIMIT_MB if local_mode else STANDARD_UPLOAD_LIMIT_MB
    upload_limit_mb = _number("UPLOAD_LIMIT_MB", default_limit, minimum=1)

    work_dir = Path(_text("WORK_DIR", "downloads")).expanduser()
    database_path = Path(_text("DATABASE_PATH", "data/bot.sqlite3")).expanduser()

    cookies_raw = _text("COOKIES_FILE")
    cookies_file = Path(cookies_raw).expanduser() if cookies_raw else None

    quality = _text("DEFAULT_QUALITY", "best").lower()
    if quality not in {"best", "1080", "720", "480", "360", "audio"}:
        raise ConfigError(
            "DEFAULT_QUALITY must be one of: best, 1080, 720, 480, 360, audio"
        )

    language = _text("DEFAULT_LANGUAGE", "ar").lower()
    if language not in {"ar", "en"}:
        raise ConfigError("DEFAULT_LANGUAGE must be 'ar' or 'en'")

    return Settings(
        token=token,
        api_base_url=f"{api_root}/bot",
        api_file_base_url=f"{api_root}/file/bot",
        local_mode=local_mode,
        upload_limit_mb=upload_limit_mb,
        work_dir=work_dir,
        database_path=database_path,
        cookies_file=cookies_file,
        proxy=_text("PROXY") or None,
        allowed_users=_id_set("ALLOWED_USERS"),
        admin_users=_id_set("ADMIN_USERS"),
        max_concurrent_downloads=_number("MAX_CONCURRENT_DOWNLOADS", 3, minimum=1),
        max_user_downloads=_number("MAX_USER_DOWNLOADS", 1, minimum=1),
        cooldown_seconds=_decimal("COOLDOWN_SECONDS", 3.0),
        max_duration_seconds=_number("MAX_DURATION_SECONDS", 3 * 60 * 60),
        max_playlist_items=_number("MAX_PLAYLIST_ITEMS", 1, minimum=1),
        max_attempts=_number("MAX_DOWNLOAD_ATTEMPTS", 4, minimum=1),
        cache_ttl_hours=_number("CACHE_TTL_HOURS", 72),
        transcode_oversized=_flag("TRANSCODE_OVERSIZED", True),
        default_language=language,
        default_quality=quality,
        ask_quality=_flag("ASK_QUALITY", True),
        log_level=_text("LOG_LEVEL", "INFO").upper(),
    )
