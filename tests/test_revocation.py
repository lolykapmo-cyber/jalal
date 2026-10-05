"""Leaving a required channel must take effect immediately."""

from types import SimpleNamespace

import pytest
from telegram.constants import ChatMemberStatus

from bot.membership import Channel, MembershipGate

CHANNELS = (
    Channel("@nextgenshop1", "https://t.me/nextgenshop1", "@nextgenshop1"),
    Channel("-1001234567890", "https://t.me/+abc", "VIP"),
)


def gate():
    return MembershipGate(CHANNELS, cache_seconds=300)


def fake_bot(statuses):
    calls = []

    async def get_chat_member(chat_id, user_id):
        calls.append((chat_id, user_id))
        return SimpleNamespace(status=statuses[chat_id], is_member=True)

    return SimpleNamespace(get_chat_member=get_chat_member, calls=calls)


def test_tracks_a_public_channel_by_username():
    g = gate()
    assert g.tracks(-100999, "nextgenshop1")
    assert g.tracks(-100999, "NextGenShop1")  # Telegram's casing varies
    assert g.tracks(None, "@nextgenshop1")


def test_tracks_a_private_channel_by_numeric_id():
    assert gate().tracks(-1001234567890, None)
    assert gate().tracks("-1001234567890", None)


def test_ignores_channels_we_do_not_gate_on():
    g = gate()
    assert not g.tracks(-100555, "some_other_channel")
    assert not g.tracks(None, None)


def test_a_gate_with_no_channels_tracks_nothing():
    assert not MembershipGate(()).tracks(-100999, "anything")


async def test_leaving_revokes_the_cached_pass():
    """The whole point: a user who passed, then left, is blocked at once."""
    g = gate()
    statuses = {
        "@nextgenshop1": ChatMemberStatus.MEMBER,
        "-1001234567890": ChatMemberStatus.MEMBER,
    }
    bot = fake_bot(statuses)

    assert await g.missing_for(bot, 42) == ()
    # Cached, so no second round trip.
    assert await g.missing_for(bot, 42) == ()
    assert len(bot.calls) == 2

    # They leave; the chat_member update drops the cached verdict.
    statuses["@nextgenshop1"] = ChatMemberStatus.LEFT
    g.forget(42)

    missing = await g.missing_for(bot, 42)
    assert [c.chat_id for c in missing] == ["@nextgenshop1"]


async def test_without_revocation_the_cache_would_have_let_them_through():
    """Shows the behaviour the chat_member handler exists to prevent."""
    g = gate()
    statuses = {
        "@nextgenshop1": ChatMemberStatus.MEMBER,
        "-1001234567890": ChatMemberStatus.MEMBER,
    }
    bot = fake_bot(statuses)
    await g.missing_for(bot, 42)

    statuses["@nextgenshop1"] = ChatMemberStatus.LEFT
    # No forget() call: the stale pass is still honoured.
    assert await g.missing_for(bot, 42) == ()


async def test_rejoining_also_forces_a_fresh_check():
    g = gate()
    statuses = {
        "@nextgenshop1": ChatMemberStatus.LEFT,
        "-1001234567890": ChatMemberStatus.MEMBER,
    }
    bot = fake_bot(statuses)
    assert len(await g.missing_for(bot, 42)) == 1

    statuses["@nextgenshop1"] = ChatMemberStatus.MEMBER
    g.forget(42)
    assert await g.missing_for(bot, 42) == ()


async def test_the_cache_window_is_short_by_default():
    """A missed update must not leave a departed member in for long."""
    assert MembershipGate(CHANNELS)._cache_seconds <= 120
