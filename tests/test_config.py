import pytest

from bot.config import (
    LOCAL_UPLOAD_LIMIT_MB,
    STANDARD_UPLOAD_LIMIT_MB,
    ConfigError,
    load_settings,
)

ENV_KEYS = (
    "BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_API_ROOT", "LOCAL_BOT_API",
    "UPLOAD_LIMIT_MB", "WORK_DIR", "DATABASE_PATH", "COOKIES_FILE", "PROXY",
    "ALLOWED_USERS", "ADMIN_USERS", "MAX_CONCURRENT_DOWNLOADS",
    "MAX_USER_DOWNLOADS", "COOLDOWN_SECONDS", "MAX_DURATION_SECONDS",
    "MAX_PLAYLIST_ITEMS", "CACHE_TTL_HOURS", "TRANSCODE_OVERSIZED",
    "DEFAULT_LANGUAGE", "DEFAULT_QUALITY", "ASK_QUALITY", "LOG_LEVEL",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_token_is_required(monkeypatch):
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_settings()


def test_accepts_the_alternative_token_name(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "42:abc")
    assert load_settings().token == "42:abc"


def test_defaults(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    settings = load_settings()
    assert settings.upload_limit_mb == STANDARD_UPLOAD_LIMIT_MB
    assert settings.upload_limit_bytes == STANDARD_UPLOAD_LIMIT_MB * 1024 * 1024
    assert settings.default_language == "ar"
    assert settings.default_quality == "best"
    assert settings.ask_quality is True
    assert settings.local_mode is False
    assert settings.api_base_url == "https://api.telegram.org/bot"


def test_a_custom_api_root_implies_local_mode_and_a_bigger_cap(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    monkeypatch.setenv("TELEGRAM_API_ROOT", "http://telegram-api:8081")
    settings = load_settings()
    assert settings.local_mode is True
    assert settings.upload_limit_mb == LOCAL_UPLOAD_LIMIT_MB
    assert settings.api_base_url == "http://telegram-api:8081/bot"
    assert settings.api_file_base_url == "http://telegram-api:8081/file/bot"


def test_explicit_upload_limit_wins(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    monkeypatch.setenv("UPLOAD_LIMIT_MB", "120")
    assert load_settings().upload_limit_mb == 120


def test_id_lists_tolerate_spacing_and_separators(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    monkeypatch.setenv("ALLOWED_USERS", " 10, 20 ;30,")
    settings = load_settings()
    assert settings.allowed_users == frozenset({10, 20, 30})
    assert settings.may_use_bot(10)
    assert not settings.may_use_bot(99)


def test_an_empty_allow_list_opens_the_bot(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    settings = load_settings()
    assert settings.may_use_bot(12345)
    assert not settings.is_admin(12345)


@pytest.mark.parametrize("raw,expected", [
    ("1", True), ("true", True), ("YES", True), ("on", True),
    ("0", False), ("false", False), ("no", False), ("", True),
])
def test_boolean_parsing(monkeypatch, raw, expected):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    monkeypatch.setenv("ASK_QUALITY", raw)
    # An empty value falls through to the default, which is True.
    assert load_settings().ask_quality is expected


def test_rejects_garbage_numbers_and_enums(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    monkeypatch.setenv("MAX_CONCURRENT_DOWNLOADS", "lots")
    with pytest.raises(ConfigError, match="MAX_CONCURRENT_DOWNLOADS"):
        load_settings()

    monkeypatch.delenv("MAX_CONCURRENT_DOWNLOADS")
    monkeypatch.setenv("DEFAULT_QUALITY", "4k")
    with pytest.raises(ConfigError, match="DEFAULT_QUALITY"):
        load_settings()

    monkeypatch.delenv("DEFAULT_QUALITY")
    monkeypatch.setenv("ALLOWED_USERS", "me,you")
    with pytest.raises(ConfigError, match="ALLOWED_USERS"):
        load_settings()


def test_numeric_floors_are_enforced(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    monkeypatch.setenv("MAX_CONCURRENT_DOWNLOADS", "0")
    monkeypatch.setenv("COOLDOWN_SECONDS", "-5")
    settings = load_settings()
    assert settings.max_concurrent_downloads == 1
    assert settings.cooldown_seconds == 0.0
