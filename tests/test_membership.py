"""The mandatory-subscription gate."""

from types import SimpleNamespace

import pytest
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden

from bot.membership import Channel, MembershipGate, parse_channel, parse_channels


# ---- parsing ---------------------------------------------------------


@pytest.mark.parametrize("raw,chat_id,url", [
    ("@nextgenshop1", "@nextgenshop1", "https://t.me/nextgenshop1"),
    ("nextgenshop1", "@nextgenshop1", "https://t.me/nextgenshop1"),
    ("https://t.me/Nexus_tv_1", "@Nexus_tv_1", "https://t.me/Nexus_tv_1"),
    ("http://telegram.me/Nexus_tv_1", "@Nexus_tv_1", "https://t.me/Nexus_tv_1"),
    ("t.me/some_chan/", "@some_chan", "https://t.me/some_chan"),
])
def test_public_channel_forms(raw, chat_id, url):
    channel = parse_channel(raw)
    assert channel is not None
    assert (channel.chat_id, channel.url) == (chat_id, url)
    assert not channel.is_private


def test_a_title_can_be_supplied():
    channel = parse_channel("@chan_name|قناتنا")
    assert channel.title == "قناتنا"
    assert channel.chat_id == "@chan_name"


def test_private_channel_uses_the_supplied_invite_link():
    channel = parse_channel("-1001234567890|https://t.me/+abc")
    assert channel.is_private
    assert channel.chat_id == "-1001234567890"
    assert channel.url == "https://t.me/+abc"


@pytest.mark.parametrize("raw", ["", "   ", "not a channel!", "@ab", "12345", None])
def test_unparseable_values_are_rejected(raw):
    assert parse_channel(raw) is None


def test_parse_channels_dedupes_and_skips_junk():
    channels = parse_channels("@a_channel, garbage!, @A_CHANNEL, @b_channel, ,")
    assert [c.chat_id for c in channels] == ["@a_channel", "@b_channel"]


def test_no_channels_means_no_gate():
    assert parse_channels(None) == ()
    assert MembershipGate(()).enabled is False


# ---- the gate --------------------------------------------------------


def fake_bot(statuses, *, raises=None):
    """A stand-in bot: chat_id -> status, or an exception to raise."""
    calls = []

    async def get_chat_member(chat_id, user_id):
        calls.append((chat_id, user_id))
        if raises is not None:
            raise raises
        status = statuses[chat_id]
        return SimpleNamespace(
            status=status,
            is_member=status == ChatMemberStatus.RESTRICTED and statuses.get("_in", True),
        )

    return SimpleNamespace(get_chat_member=get_chat_member, calls=calls)


CHANNELS = (
    Channel("@one", "https://t.me/one", "@one"),
    Channel("@two", "https://t.me/two", "@two"),
)


async def test_a_fully_subscribed_user_passes():
    gate = MembershipGate(CHANNELS)
    bot = fake_bot({"@one": ChatMemberStatus.MEMBER, "@two": ChatMemberStatus.OWNER})
    assert await gate.missing_for(bot, 1) == ()


async def test_the_missing_channels_are_named():
    gate = MembershipGate(CHANNELS)
    bot = fake_bot({"@one": ChatMemberStatus.MEMBER, "@two": ChatMemberStatus.LEFT})
    missing = await gate.missing_for(bot, 1)
    assert [c.chat_id for c in missing] == ["@two"]


@pytest.mark.parametrize("status", [
    ChatMemberStatus.LEFT, ChatMemberStatus.BANNED,
])
async def test_non_members_are_caught(status):
    gate = MembershipGate(CHANNELS[:1])
    bot = fake_bot({"@one": status})
    assert len(await gate.missing_for(bot, 1)) == 1


async def test_a_muted_but_present_member_counts_as_joined():
    gate = MembershipGate(CHANNELS[:1])
    bot = fake_bot({"@one": ChatMemberStatus.RESTRICTED, "_in": True})
    assert await gate.missing_for(bot, 1) == ()


async def test_a_restricted_user_who_left_does_not_count():
    gate = MembershipGate(CHANNELS[:1])
    bot = fake_bot({"@one": ChatMemberStatus.RESTRICTED, "_in": False})
    assert len(await gate.missing_for(bot, 1)) == 1


async def test_a_pass_is_cached_so_telegram_is_not_hammered():
    gate = MembershipGate(CHANNELS[:1], cache_seconds=300)
    bot = fake_bot({"@one": ChatMemberStatus.MEMBER})

    assert await gate.missing_for(bot, 7) == ()
    assert await gate.missing_for(bot, 7) == ()
    assert len(bot.calls) == 1  # the second answer came from the cache


async def test_a_failure_is_not_cached_so_verifying_feels_instant():
    gate = MembershipGate(CHANNELS[:1], cache_seconds=300)
    bot = fake_bot({"@one": ChatMemberStatus.LEFT})

    await gate.missing_for(bot, 7)
    await gate.missing_for(bot, 7)
    assert len(bot.calls) == 2


async def test_forget_forces_a_fresh_check():
    gate = MembershipGate(CHANNELS[:1], cache_seconds=300)
    bot = fake_bot({"@one": ChatMemberStatus.MEMBER})

    await gate.missing_for(bot, 7)
    gate.forget(7)
    await gate.missing_for(bot, 7)
    assert len(bot.calls) == 2


async def test_an_expired_cache_rechecks():
    gate = MembershipGate(CHANNELS[:1], cache_seconds=-1)
    bot = fake_bot({"@one": ChatMemberStatus.MEMBER})
    await gate.missing_for(bot, 7)
    await gate.missing_for(bot, 7)
    assert len(bot.calls) == 2


@pytest.mark.parametrize("error", [
    BadRequest("Chat not found"),
    Forbidden("bot is not a member of the channel chat"),
])
async def test_fail_open_lets_users_through_when_the_check_is_impossible(error):
    """A bot that is not an admin cannot read members. Locking everyone out
    of a working bot is worse than letting them through."""
    gate = MembershipGate(CHANNELS, fail_open=True)
    bot = fake_bot({}, raises=error)
    assert await gate.missing_for(bot, 1) == ()


async def test_fail_closed_blocks_instead():
    gate = MembershipGate(CHANNELS, fail_open=False)
    bot = fake_bot({}, raises=BadRequest("Chat not found"))
    assert len(await gate.missing_for(bot, 1)) == 2


async def test_a_gate_with_no_channels_never_calls_telegram():
    gate = MembershipGate(())
    bot = fake_bot({})
    assert await gate.missing_for(bot, 1) == ()
    assert bot.calls == []
