"""Collapse concurrent requests for the same media into one download.

A link that spreads arrives from many people within the same minute. Without
this, each of them starts a separate download of identical bytes, which is
the fastest way to exhaust a small server. The first requester downloads;
everyone else waits on that same result and is sent the finished file by its
Telegram file_id, costing one API call instead of one download.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SharedUpload:
    """What a follower needs to re-send the leader's upload."""

    file_id: str | None
    kind: str = "video"
    title: str | None = None

    @property
    def usable(self) -> bool:
        return bool(self.file_id)


# A failed leader resolves to this, so followers fall back to downloading
# themselves rather than inheriting an exception.
FAILED = SharedUpload(file_id=None)


class InFlight:
    """Tracks one download per key, with everyone else waiting on it."""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[SharedUpload]] = {}

    def follow(self, key: str) -> asyncio.Future[SharedUpload] | None:
        """The running download for `key`, if another request owns it."""
        future = self._pending.get(key)
        if future is None or future.done():
            return None
        return future

    def lead(self, key: str) -> asyncio.Future[SharedUpload]:
        """Claim `key`. The caller must settle it, in a finally block."""
        future: asyncio.Future[SharedUpload] = asyncio.get_running_loop().create_future()
        self._pending[key] = future
        return future

    def settle(
        self,
        key: str,
        future: asyncio.Future[SharedUpload],
        result: SharedUpload = FAILED,
    ) -> None:
        """Release waiters and drop the claim.

        Always resolves with a value rather than an exception: an unretrieved
        future exception would be logged by asyncio even though a follower
        falling back is the expected, handled path.
        """
        if not future.done():
            future.set_result(result)
        # Only clear the slot if a later request has not already replaced it.
        if self._pending.get(key) is future:
            self._pending.pop(key, None)

    async def wait_for(self, future: asyncio.Future[SharedUpload]) -> SharedUpload:
        """Await a leader's result without being able to cancel the leader."""
        try:
            # shield: a follower giving up (or /cancel) must not abort the
            # download that other followers are still waiting on.
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - a follower just downloads for itself
            logger.debug("shared download did not produce a file", exc_info=True)
            return FAILED

    @property
    def active(self) -> int:
        return sum(1 for future in self._pending.values() if not future.done())
