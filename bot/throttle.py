"""Fair-use limits: per-user concurrency, a global cap and a cooldown."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator


class UserBusy(RuntimeError):
    """The user already has as many downloads running as they're allowed."""


class Cooldown(RuntimeError):
    """The user asked again too soon."""

    def __init__(self, remaining: float) -> None:
        super().__init__(f"{remaining:.0f}s remaining")
        self.remaining = remaining


class Throttle:
    def __init__(
        self, *, max_global: int, max_per_user: int, cooldown_seconds: float
    ) -> None:
        self._global = asyncio.Semaphore(max_global)
        self._max_per_user = max_per_user
        self._cooldown = cooldown_seconds
        self._active: dict[int, int] = {}
        self._last_start: dict[int, float] = {}
        self._waiting = 0

    # ---- cooldown -----------------------------------------------------

    def cooldown_remaining(self, user_id: int) -> float:
        if self._cooldown <= 0:
            return 0.0
        last = self._last_start.get(user_id)
        if last is None:
            return 0.0
        return max(0.0, self._cooldown - (time.monotonic() - last))

    def check_cooldown(self, user_id: int) -> None:
        remaining = self.cooldown_remaining(user_id)
        if remaining > 0:
            raise Cooldown(remaining)

    # ---- slots --------------------------------------------------------

    def active_for(self, user_id: int) -> int:
        return self._active.get(user_id, 0)

    @property
    def waiting(self) -> int:
        """How many jobs are queued behind the global cap."""
        return self._waiting

    @property
    def global_busy(self) -> bool:
        """True when every worker slot is taken, so a job would queue."""
        return self._global.locked()

    @asynccontextmanager
    async def user_slot(self, user_id: int) -> AsyncIterator[None]:
        """Reserve one of the user's slots, or raise UserBusy immediately.

        No await happens between the check and the increment, so this is
        race-free on a single event loop.
        """
        if self._active.get(user_id, 0) >= self._max_per_user:
            raise UserBusy
        self._active[user_id] = self._active.get(user_id, 0) + 1
        self._last_start[user_id] = time.monotonic()
        try:
            yield
        finally:
            remaining = self._active.get(user_id, 1) - 1
            if remaining > 0:
                self._active[user_id] = remaining
            else:
                self._active.pop(user_id, None)
            # Start the cooldown when the job ends, not when it began.
            self._last_start[user_id] = time.monotonic()

    @asynccontextmanager
    async def global_slot(self) -> AsyncIterator[bool]:
        """Reserve a worker slot; yields True if the caller had to wait."""
        had_to_wait = self._global.locked()
        if had_to_wait:
            self._waiting += 1
        try:
            await self._global.acquire()
        finally:
            if had_to_wait:
                self._waiting -= 1
        try:
            yield had_to_wait
        finally:
            self._global.release()
