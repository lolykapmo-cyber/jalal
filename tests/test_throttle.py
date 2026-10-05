import asyncio

import pytest

from bot.throttle import Cooldown, Throttle, UserBusy


def make(max_global=2, max_per_user=1, cooldown=0.0):
    return Throttle(
        max_global=max_global, max_per_user=max_per_user, cooldown_seconds=cooldown
    )


async def test_a_user_slot_is_released_on_exit():
    throttle = make()
    async with throttle.user_slot(1):
        assert throttle.active_for(1) == 1
    assert throttle.active_for(1) == 0


async def test_a_second_concurrent_job_is_refused():
    throttle = make(max_per_user=1)
    async with throttle.user_slot(1):
        with pytest.raises(UserBusy):
            async with throttle.user_slot(1):
                pass
        # A different user is unaffected.
        async with throttle.user_slot(2):
            assert throttle.active_for(2) == 1


async def test_a_higher_per_user_cap_allows_parallel_jobs():
    throttle = make(max_per_user=2)
    async with throttle.user_slot(1):
        async with throttle.user_slot(1):
            assert throttle.active_for(1) == 2
        assert throttle.active_for(1) == 1


async def test_slots_are_released_even_when_the_job_raises():
    throttle = make()
    with pytest.raises(ValueError):
        async with throttle.user_slot(1):
            raise ValueError("job blew up")
    assert throttle.active_for(1) == 0


async def test_cooldown_blocks_a_rapid_second_request():
    throttle = make(cooldown=60.0)
    assert throttle.cooldown_remaining(1) == 0.0
    throttle.check_cooldown(1)  # first request is always fine

    async with throttle.user_slot(1):
        pass

    with pytest.raises(Cooldown) as caught:
        throttle.check_cooldown(1)
    assert 0 < caught.value.remaining <= 60.0
    # Another user is not penalised.
    throttle.check_cooldown(2)


async def test_a_zero_cooldown_never_blocks():
    throttle = make(cooldown=0.0)
    async with throttle.user_slot(1):
        pass
    throttle.check_cooldown(1)
    assert throttle.cooldown_remaining(1) == 0.0


async def test_the_global_cap_queues_extra_jobs():
    throttle = make(max_global=1)
    assert throttle.global_busy is False

    async with throttle.global_slot() as waited:
        assert waited is False
        assert throttle.global_busy is True

        started = asyncio.Event()

        async def second():
            async with throttle.global_slot() as had_to_wait:
                started.set()
                return had_to_wait

        task = asyncio.create_task(second())
        await asyncio.sleep(0)  # let it reach the semaphore
        assert not started.is_set()
        assert throttle.waiting == 1

    assert await task is True
    assert throttle.waiting == 0
    assert throttle.global_busy is False
