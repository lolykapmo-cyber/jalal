"""SQLite-backed user preferences, upload cache and counters.

The bot is I/O bound and low-traffic, so a single connection guarded by a
lock is plenty. Every public method is async and hops to a worker thread so
the event loop never blocks on disk.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    language    TEXT    NOT NULL,
    quality     TEXT    NOT NULL,
    ask_quality INTEGER NOT NULL DEFAULT 1,
    downloads   INTEGER NOT NULL DEFAULT 0,
    created_at  REAL    NOT NULL,
    updated_at  REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS media_cache (
    cache_key  TEXT PRIMARY KEY,
    file_id    TEXT NOT NULL,
    kind       TEXT NOT NULL,
    title      TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS media_cache_created_at
    ON media_cache (created_at);

CREATE TABLE IF NOT EXISTS counters (
    name  TEXT    PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass(frozen=True)
class UserPrefs:
    """A user's saved choices."""

    user_id: int
    language: str
    quality: str
    ask_quality: bool
    downloads: int


@dataclass(frozen=True)
class CachedMedia:
    """A previously uploaded file, reusable by its Telegram file_id."""

    file_id: str
    kind: str
    title: str | None


class Storage:
    def __init__(self, path: Path, *, default_language: str, default_quality: str,
                 default_ask_quality: bool) -> None:
        self._path = path
        self._default_language = default_language
        self._default_quality = default_quality
        self._default_ask_quality = default_ask_quality
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    # ---- lifecycle ----------------------------------------------------

    async def open(self) -> None:
        await asyncio.to_thread(self._open_sync)

    def _open_sync(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(SCHEMA)
        conn.commit()
        self._conn = conn

    async def close(self) -> None:
        await asyncio.to_thread(self._close_sync)

    def _close_sync(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Storage.open() must be awaited before use")
        return self._conn

    # ---- users --------------------------------------------------------

    async def get_user(self, user_id: int, *, language_hint: str | None = None) -> UserPrefs:
        """Fetch a user's prefs, creating the row on first contact."""
        return await asyncio.to_thread(self._get_user_sync, user_id, language_hint)

    def _get_user_sync(self, user_id: int, language_hint: str | None) -> UserPrefs:
        now = time.time()
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row is None:
                language = language_hint or self._default_language
                self._db.execute(
                    "INSERT INTO users (user_id, language, quality, ask_quality,"
                    " downloads, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, 0, ?, ?)",
                    (
                        user_id,
                        language,
                        self._default_quality,
                        int(self._default_ask_quality),
                        now,
                        now,
                    ),
                )
                self._db.commit()
                return UserPrefs(
                    user_id=user_id,
                    language=language,
                    quality=self._default_quality,
                    ask_quality=self._default_ask_quality,
                    downloads=0,
                )
        return UserPrefs(
            user_id=row["user_id"],
            language=row["language"],
            quality=row["quality"],
            ask_quality=bool(row["ask_quality"]),
            downloads=row["downloads"],
        )

    async def update_user(
        self,
        user_id: int,
        *,
        language: str | None = None,
        quality: str | None = None,
        ask_quality: bool | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._update_user_sync, user_id, language, quality, ask_quality
        )

    def _update_user_sync(
        self,
        user_id: int,
        language: str | None,
        quality: str | None,
        ask_quality: bool | None,
    ) -> None:
        assignments: list[str] = []
        values: list[object] = []
        if language is not None:
            assignments.append("language = ?")
            values.append(language)
        if quality is not None:
            assignments.append("quality = ?")
            values.append(quality)
        if ask_quality is not None:
            assignments.append("ask_quality = ?")
            values.append(int(ask_quality))
        if not assignments:
            return
        assignments.append("updated_at = ?")
        values.extend([time.time(), user_id])
        with self._lock:
            self._db.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE user_id = ?",
                values,
            )
            self._db.commit()

    async def record_download(self, user_id: int) -> None:
        await asyncio.to_thread(self._record_download_sync, user_id)

    def _record_download_sync(self, user_id: int) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE users SET downloads = downloads + 1, updated_at = ?"
                " WHERE user_id = ?",
                (time.time(), user_id),
            )
            self._bump_sync("downloads")
            self._db.commit()

    # ---- upload cache -------------------------------------------------

    async def cache_lookup(self, cache_key: str, *, ttl_hours: int) -> CachedMedia | None:
        return await asyncio.to_thread(self._cache_lookup_sync, cache_key, ttl_hours)

    def _cache_lookup_sync(self, cache_key: str, ttl_hours: int) -> CachedMedia | None:
        with self._lock:
            row = self._db.execute(
                "SELECT file_id, kind, title, created_at FROM media_cache"
                " WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if row is None:
                return None
            if ttl_hours > 0 and time.time() - row["created_at"] > ttl_hours * 3600:
                self._db.execute(
                    "DELETE FROM media_cache WHERE cache_key = ?", (cache_key,)
                )
                self._db.commit()
                return None
        return CachedMedia(file_id=row["file_id"], kind=row["kind"], title=row["title"])

    async def cache_store(
        self, cache_key: str, *, file_id: str, kind: str, title: str | None
    ) -> None:
        await asyncio.to_thread(
            self._cache_store_sync, cache_key, file_id, kind, title
        )

    def _cache_store_sync(
        self, cache_key: str, file_id: str, kind: str, title: str | None
    ) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO media_cache (cache_key, file_id, kind, title, created_at)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(cache_key) DO UPDATE SET"
                " file_id = excluded.file_id, kind = excluded.kind,"
                " title = excluded.title, created_at = excluded.created_at",
                (cache_key, file_id, kind, title, time.time()),
            )
            self._db.commit()

    async def cache_forget(self, cache_key: str) -> None:
        """Drop an entry whose file_id Telegram no longer accepts."""
        await asyncio.to_thread(self._cache_forget_sync, cache_key)

    def _cache_forget_sync(self, cache_key: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM media_cache WHERE cache_key = ?", (cache_key,))
            self._db.commit()

    async def cache_prune(self, *, ttl_hours: int) -> int:
        if ttl_hours <= 0:
            return 0
        return await asyncio.to_thread(self._cache_prune_sync, ttl_hours)

    def _cache_prune_sync(self, ttl_hours: int) -> int:
        cutoff = time.time() - ttl_hours * 3600
        with self._lock:
            cursor = self._db.execute(
                "DELETE FROM media_cache WHERE created_at < ?", (cutoff,)
            )
            self._db.commit()
            return cursor.rowcount or 0

    # ---- counters -----------------------------------------------------

    async def bump(self, name: str, amount: int = 1) -> None:
        await asyncio.to_thread(self._bump_locked, name, amount)

    def _bump_locked(self, name: str, amount: int) -> None:
        with self._lock:
            self._bump_sync(name, amount)
            self._db.commit()

    def _bump_sync(self, name: str, amount: int = 1) -> None:
        """Caller holds the lock and commits."""
        self._db.execute(
            "INSERT INTO counters (name, value) VALUES (?, ?)"
            " ON CONFLICT(name) DO UPDATE SET value = value + excluded.value",
            (name, amount),
        )

    async def stats(self) -> dict[str, int]:
        return await asyncio.to_thread(self._stats_sync)

    def _stats_sync(self) -> dict[str, int]:
        with self._lock:
            users = self._db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
            cache_rows = self._db.execute(
                "SELECT COUNT(*) AS n FROM media_cache"
            ).fetchone()["n"]
            counters = {
                row["name"]: row["value"]
                for row in self._db.execute("SELECT name, value FROM counters")
            }
        return {
            "users": users,
            "cache_rows": cache_rows,
            "downloads": counters.get("downloads", 0),
            "cached": counters.get("cache_hits", 0),
        }
