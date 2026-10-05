import asyncio

import pytest

from bot.downloader import CancelToken
from bot.jobs import JobRegistry


def test_remember_and_recall():
    registry = JobRegistry()
    token = registry.remember("https://a.co/v", title="Clip", heights=(720, 480))

    choice = registry.recall(token)
    assert choice is not None
    assert choice.url == "https://a.co/v"
    assert choice.title == "Clip"
    assert choice.heights == (720, 480)

    # Recall does not consume: a user may pick a second quality.
    assert registry.recall(token) is not None


def test_tokens_are_short_enough_for_callback_data():
    registry = JobRegistry()
    token = registry.remember("https://a.co/v", title="t", heights=())
    # "q|<token>|audio" has to fit inside Telegram's 64-byte budget.
    assert len(f"q|{token}|audio".encode()) <= 64


def test_tokens_are_distinct():
    registry = JobRegistry()
    tokens = {registry.remember(f"https://a.co/{i}", title="t", heights=())
              for i in range(200)}
    assert len(tokens) == 200


def test_recall_of_an_unknown_or_forgotten_token_is_none():
    registry = JobRegistry()
    assert registry.recall("nope") is None

    token = registry.remember("https://a.co/v", title="t", heights=())
    registry.forget(token)
    assert registry.recall(token) is None
    registry.forget(token)  # forgetting twice must not raise


def test_expired_prompts_are_dropped():
    registry = JobRegistry(pending_ttl=-1.0)
    token = registry.remember("https://a.co/v", title="t", heights=())
    assert registry.recall(token) is None


def test_pending_entries_are_capped():
    from bot.jobs import MAX_PENDING

    registry = JobRegistry()
    for i in range(MAX_PENDING + 50):
        registry.remember(f"https://a.co/{i}", title="t", heights=())
    assert len(registry._pending) <= MAX_PENDING


async def test_cancel_flips_the_token_and_the_task():
    registry = JobRegistry()
    cancel_token = CancelToken()

    async def sleeper():
        await asyncio.sleep(30)

    task = asyncio.create_task(sleeper())
    registry.register(1, task=task, cancel_token=cancel_token)
    assert registry.has_active(1)

    assert registry.cancel(1) is True
    assert cancel_token.cancelled is True
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_cancelling_an_idle_user_is_false():
    assert JobRegistry().cancel(999) is False


async def test_unregister_ignores_a_superseded_task():
    registry = JobRegistry()

    async def noop():
        return None

    first = asyncio.create_task(noop())
    second = asyncio.create_task(noop())
    await asyncio.gather(first, second)

    registry.register(1, task=second, cancel_token=CancelToken())
    # The *old* task finishing must not clear the new one's registration.
    registry.unregister(1, task=first)
    assert registry.has_active(1)

    registry.unregister(1, task=second)
    assert not registry.has_active(1)


async def test_cancel_all_stops_every_job():
    registry = JobRegistry()
    tasks = []
    for user_id in (1, 2, 3):
        async def sleeper():
            await asyncio.sleep(30)

        task = asyncio.create_task(sleeper())
        tasks.append(task)
        registry.register(user_id, task=task, cancel_token=CancelToken())

    assert registry.cancel_all() == 3
    for task in tasks:
        with pytest.raises(asyncio.CancelledError):
            await task
