"""Short-lived registries for quality prompts and running downloads."""

from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass, field

from .downloader import CancelToken

# A quality keyboard stops being useful long before this, but keeping the
# entry around lets a user tap a second quality for the same link.
PENDING_TTL_SECONDS = 3600.0
MAX_PENDING = 2000


@dataclass(frozen=True)
class PendingChoice:
    """A link we've already probed, waiting on the user to pick a quality."""

    url: str
    title: str
    heights: tuple[int, ...]
    created_at: float = field(default_factory=time.monotonic)


@dataclass
class ActiveJob:
    task: asyncio.Task
    cancel_token: CancelToken


class JobRegistry:
    def __init__(self, *, pending_ttl: float = PENDING_TTL_SECONDS) -> None:
        self._pending: dict[str, PendingChoice] = {}
        self._active: dict[int, ActiveJob] = {}
        self._pending_ttl = pending_ttl

    # ---- pending quality prompts --------------------------------------

    def remember(self, url: str, *, title: str, heights: tuple[int, ...]) -> str:
        """Store a probed link and return a short token for callback_data."""
        token = secrets.token_urlsafe(6)
        while token in self._pending:
            token = secrets.token_urlsafe(6)
        self._pending[token] = PendingChoice(url=url, title=title, heights=heights)
        # Pruning after the insert keeps the dict at or below the cap; doing
        # it first would leave MAX_PENDING + 1 entries behind every time.
        self._prune()
        return token

    def recall(self, token: str) -> PendingChoice | None:
        choice = self._pending.get(token)
        if choice is None:
            return None
        if time.monotonic() - choice.created_at > self._pending_ttl:
            self._pending.pop(token, None)
            return None
        return choice

    def forget(self, token: str) -> None:
        self._pending.pop(token, None)

    def _prune(self) -> None:
        now = time.monotonic()
        stale = [
            token
            for token, choice in self._pending.items()
            if now - choice.created_at > self._pending_ttl
        ]
        for token in stale:
            self._pending.pop(token, None)
        # Hard cap in case a flood outpaces the TTL.
        overflow = len(self._pending) - MAX_PENDING
        if overflow > 0:
            oldest = sorted(self._pending.items(), key=lambda kv: kv[1].created_at)
            for token, _ in oldest[:overflow]:
                self._pending.pop(token, None)

    # ---- running downloads --------------------------------------------

    def register(self, user_id: int, *, task: asyncio.Task, cancel_token: CancelToken) -> None:
        self._active[user_id] = ActiveJob(task=task, cancel_token=cancel_token)

    def unregister(self, user_id: int, *, task: asyncio.Task | None = None) -> None:
        """Drop the user's job, unless a newer task has already replaced it."""
        current = self._active.get(user_id)
        if current is None:
            return
        if task is not None and current.task is not task:
            return
        self._active.pop(user_id, None)

    def has_active(self, user_id: int) -> bool:
        return user_id in self._active

    def cancel(self, user_id: int) -> bool:
        """Ask the user's running download to stop. True if there was one."""
        job = self._active.get(user_id)
        if job is None:
            return False
        # Flip the flag first: yt-dlp notices it inside its progress hook,
        # which unwinds the worker thread cleanly.
        job.cancel_token.cancel()
        job.task.cancel()
        return True

    def cancel_all(self) -> int:
        count = 0
        for user_id in list(self._active):
            if self.cancel(user_id):
                count += 1
        return count
