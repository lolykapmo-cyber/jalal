"""Mandatory channel subscription.

Telegram answers getChatMember for a channel only when the bot is an
administrator there, so a misconfiguration looks exactly like "nobody is
subscribed". Failing closed on that would lock every user out of a working
bot, so an unanswerable check is treated as a pass by default and logged
loudly instead.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Iterable

from telegram import Bot
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden, TelegramError

logger = logging.getLogger(__name__)

# Statuses that mean the user is in the channel. RESTRICTED is included only
# when the member is still present (muted, but subscribed).
_JOINED = frozenset(
    {
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
    }
)

_USERNAME = re.compile(r"^@?([A-Za-z][A-Za-z0-9_]{3,31})$")
_TME_LINK = re.compile(
    r"^(?:https?://)?(?:www\.)?t(?:elegram)?\.me/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,31})/?$",
    re.IGNORECASE,
)
_NUMERIC_ID = re.compile(r"^-100\d{5,}$")


@dataclass(frozen=True)
class Channel:
    """A channel users must join, in the forms Telegram needs."""

    chat_id: str   # what get_chat_member takes: @username or -100...
    url: str       # what the join button opens
    title: str     # what the button says

    @property
    def is_private(self) -> bool:
        """A numeric id has no public link we can derive."""
        return self.chat_id.startswith("-100")


def parse_channel(raw: str) -> Channel | None:
    """Accept @name, a t.me link, or a -100... id, with an optional title.

    `@name|Display Title` and `https://t.me/name|Display Title` both work.
    """
    text = (raw or "").strip()
    if not text:
        return None

    title = ""
    if "|" in text:
        text, _, title = (part.strip() for part in text.partition("|"))

    match = _TME_LINK.match(text) or _USERNAME.match(text)
    if match:
        name = match.group(1)
        return Channel(
            chat_id=f"@{name}",
            url=f"https://t.me/{name}",
            title=title or f"@{name}",
        )

    if _NUMERIC_ID.match(text):
        # A private channel needs an invite link supplied as the title field.
        return Channel(chat_id=text, url=title or "", title=title or text)

    return None


def parse_channels(raw: str | None) -> tuple[Channel, ...]:
    """Parse a comma-separated list, skipping anything unrecognisable."""
    if not raw:
        return ()
    channels: list[Channel] = []
    seen: set[str] = set()
    for chunk in raw.replace(";", ",").split(","):
        channel = parse_channel(chunk)
        if channel is None:
            if chunk.strip():
                logger.warning("ignoring unparseable channel %r", chunk.strip())
            continue
        if channel.chat_id.lower() in seen:
            continue
        seen.add(channel.chat_id.lower())
        channels.append(channel)
    return tuple(channels)


class MembershipGate:
    """Checks, and briefly remembers, whether a user joined every channel."""

    def __init__(
        self,
        channels: Iterable[Channel],
        *,
        cache_seconds: float = 120.0,
        fail_open: bool = True,
    ) -> None:
        self._channels = tuple(channels)
        self._cache_seconds = cache_seconds
        self._fail_open = fail_open
        # user_id -> (checked_at, passed)
        self._verdicts: dict[int, tuple[float, bool]] = {}
        self._warned: set[str] = set()

    @property
    def channels(self) -> tuple[Channel, ...]:
        return self._channels

    @property
    def enabled(self) -> bool:
        return bool(self._channels)

    def forget(self, user_id: int) -> None:
        """Drop a cached verdict, so the next check asks Telegram again."""
        self._verdicts.pop(user_id, None)

    def tracks(self, chat_id: int | str | None, username: str | None = None) -> bool:
        """True when a membership change in this chat concerns the gate."""
        candidates = set()
        if chat_id is not None:
            candidates.add(str(chat_id).lower())
        if username:
            candidates.add(f"@{username.lower()}")
            candidates.add(username.lower())
        return any(
            channel.chat_id.lower() in candidates for channel in self._channels
        )

    def _cached(self, user_id: int) -> bool | None:
        entry = self._verdicts.get(user_id)
        if entry is None:
            return None
        checked_at, passed = entry
        if time.monotonic() - checked_at > self._cache_seconds:
            self._verdicts.pop(user_id, None)
            return None
        return passed

    async def missing_for(self, bot: Bot, user_id: int) -> tuple[Channel, ...]:
        """Channels this user still has to join. Empty means they may pass."""
        if not self._channels:
            return ()

        if self._cached(user_id) is True:
            return ()

        checks = await asyncio.gather(
            *(self._is_member(bot, channel, user_id) for channel in self._channels)
        )
        missing = tuple(
            channel for channel, joined in zip(self._channels, checks) if not joined
        )
        # Only a pass is worth remembering; a failure must re-check promptly
        # so the verify button feels immediate.
        if not missing:
            self._verdicts[user_id] = (time.monotonic(), True)
        return missing

    async def _is_member(self, bot: Bot, channel: Channel, user_id: int) -> bool:
        try:
            member = await bot.get_chat_member(channel.chat_id, user_id)
        except (BadRequest, Forbidden) as exc:
            # Almost always: the bot is not an administrator of that channel.
            self._warn_once(
                channel,
                f"cannot read members of {channel.chat_id} ({exc}). "
                "Add the bot as an administrator there, or the requirement "
                "cannot be enforced.",
            )
            return self._fail_open
        except TelegramError as exc:
            logger.warning("membership check failed for %s: %s", channel.chat_id, exc)
            return self._fail_open

        if member.status in _JOINED:
            return True
        if member.status == ChatMemberStatus.RESTRICTED:
            # Muted but still in the channel counts as subscribed.
            return bool(getattr(member, "is_member", False))
        return False

    def _warn_once(self, channel: Channel, message: str) -> None:
        if channel.chat_id in self._warned:
            return
        self._warned.add(channel.chat_id)
        logger.warning("%s", message)
