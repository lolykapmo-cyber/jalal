"""Startup-time checks on the directories the bot has to write to."""

import os
from pathlib import Path

import pytest

from bot.app import _require_writable
from bot.config import load_settings

ENV_KEYS = ("BOT_TOKEN", "WORK_DIR", "DATABASE_PATH", "COOKIES_FILE")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BOT_TOKEN", "1:x")


def test_relative_paths_become_absolute(monkeypatch):
    """A relative path would otherwise resolve against the service's CWD,
    which under systemd is the read-only project directory."""
    monkeypatch.setenv("WORK_DIR", "downloads")
    monkeypatch.setenv("DATABASE_PATH", "data/bot.sqlite3")

    settings = load_settings()
    assert settings.work_dir.is_absolute()
    assert settings.database_path.is_absolute()


def test_absolute_paths_are_kept(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "dl"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "data" / "bot.sqlite3"))

    settings = load_settings()
    assert settings.work_dir == tmp_path / "dl"
    assert settings.database_path == tmp_path / "data" / "bot.sqlite3"


def test_cookies_path_is_absolute_too(monkeypatch):
    monkeypatch.setenv("COOKIES_FILE", "cookies.txt")
    assert load_settings().cookies_file.is_absolute()


def test_no_cookies_file_stays_none():
    assert load_settings().cookies_file is None


def test_writable_directory_is_created(tmp_path):
    target = tmp_path / "nested" / "downloads"
    _require_writable(target, "download directory")
    assert target.is_dir()


def test_an_existing_directory_is_accepted(tmp_path):
    _require_writable(tmp_path, "download directory")
    assert tmp_path.is_dir()


def test_an_uncreatable_directory_explains_itself(tmp_path):
    """The failure the deployed bot actually hit: a read-only parent.

    Simulated with a regular file as the parent, which fails for root too,
    unlike a permission bit.
    """
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("")

    with pytest.raises(SystemExit) as caught:
        _require_writable(blocker / "downloads", "download directory (WORK_DIR)")

    message = str(caught.value)
    assert "download directory (WORK_DIR)" in message
    assert "absolute path" in message
    # It must name a concrete remedy, not just report the failure.
    assert "/tmp/jalal-downloads" in message
    assert "ReadWritePaths" in message


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses the write bit")
def test_an_unwritable_directory_is_rejected(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir(mode=0o555)
    with pytest.raises(SystemExit, match="cannot write"):
        _require_writable(locked, "download directory")
