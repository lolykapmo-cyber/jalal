"""A download-progress message that edits itself on a timer."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import InlineKeyboardMarkup, Message
from telegram.constants import ParseMode
from telegram.error import BadRequest, RetryAfter, TelegramError

from .i18n import t
from .utils import human_size, human_speed, progress_bar

logger = logging.getLogger(__name__)

# Telegram tolerates roughly one edit per message per second; staying well
# clear of that keeps us out of flood-wait territory.
EDIT_INTERVAL_SECONDS = 4.0


class ProgressReporter:
    """Renders yt-dlp progress into one Telegram message.

    `hook` is called from yt-dlp's worker thread and only ever swaps a
    reference, so it never blocks the download or touches the event loop.
    """

    def __init__(
        self,
        message: Message,
        language: str,
        *,
        interval: float = EDIT_INTERVAL_SECONDS,
        keyboard: InlineKeyboardMarkup | None = None,
    ) -> None:
        self._message = message
        self._language = language
        self._interval = interval
        self._keyboard = keyboard
        self._status: dict[str, Any] = {}
        self._stage: tuple[str, dict[str, Any]] | None = ("fetching", {})
        self._rendered: str | None = None
        self._task: asyncio.Task | None = None

    # ---- called from the download thread ------------------------------

    def hook(self, status: dict[str, Any]) -> None:
        if status.get("status") == "downloading":
            self._status = status
            self._stage = None
        elif status.get("status") == "finished":
            self._stage = ("processing", {})

    # ---- called from the event loop -----------------------------------

    def set_stage(self, key: str, **params: Any) -> None:
        """Pin the message to a named stage until progress resumes."""
        self._stage = (key, params)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def flush(self) -> None:
        """Push the current text immediately."""
        await self._render()

    async def _loop(self) -> None:
        try:
            while True:
                await self._render()
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - the UI must never kill the job
            logger.debug("progress loop stopped", exc_info=True)

    async def _render(self) -> None:
        text = self._text()
        if text == self._rendered:
            return
        try:
            await self._message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=self._keyboard
            )
            self._rendered = text
        except RetryAfter as exc:
            await asyncio.sleep(float(exc.retry_after) + 0.5)
        except BadRequest as exc:
            # "message is not modified" is routine; anything else is worth a line.
            if "not modified" not in str(exc).lower():
                logger.debug("progress edit rejected: %s", exc)
            self._rendered = text
        except TelegramError as exc:
            logger.debug("progress edit failed: %s", exc)

    def _text(self) -> str:
        if self._stage is not None:
            key, params = self._stage
            return t(self._language, key, **params)

        status = self._status
        downloaded = status.get("downloaded_bytes") or 0
        total = status.get("total_bytes") or status.get("total_bytes_estimate")

        if not total:
            return t(self._language, "downloading_plain", bar=progress_bar(None))

        fraction = min(1.0, downloaded / total) if total else None
        return t(
            self._language,
            "downloading",
            bar=progress_bar(fraction),
            percent=f"{fraction * 100:.0f}%" if fraction is not None else "—",
            done=human_size(downloaded),
            total=human_size(total),
            speed=human_speed(status.get("speed")),
            eta=_format_eta(status.get("eta")),
        )


def _format_eta(eta: Any) -> str:
    if not isinstance(eta, (int, float)) or eta < 0:
        return "—"
    total = int(eta)
    minutes, seconds = divmod(total, 60)
    if minutes:
        return f"{minutes}:{seconds:02d}"
    return f"{seconds}s"
