"""Shared fixtures. Nothing here touches the network."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bot.storage import Storage  # noqa: E402


@pytest.fixture
async def storage(tmp_path):
    store = Storage(
        tmp_path / "test.sqlite3",
        default_language="ar",
        default_quality="best",
        default_ask_quality=True,
    )
    await store.open()
    try:
        yield store
    finally:
        await store.close()
