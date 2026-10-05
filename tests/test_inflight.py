"""Collapsing concurrent requests for the same media into one download."""

import asyncio

import pytest

from bot.inflight import FAILED, InFlight, SharedUpload


def test_nothing_pending_means_nothing_to_follow():
    assert InFlight().follow("k") is None


async def test_leading_then_following():
    flight = InFlight()
    future = flight.lead("k")
    assert flight.follow("k") is future
    assert flight.active == 1

    flight.settle("k", future, SharedUpload(file_id="F"))
    # Once settled the slot is free for the next request.
    assert flight.follow("k") is None
    assert flight.active == 0


async def test_settle_releases_every_waiter():
    flight = InFlight()
    future = flight.lead("k")
    waiters = [asyncio.create_task(flight.wait_for(future)) for _ in range(5)]
    await asyncio.sleep(0)

    flight.settle("k", future, SharedUpload(file_id="F", kind="video", title="T"))
    results = await asyncio.gather(*waiters)

    assert all(r.file_id == "F" for r in results)
    assert all(r.usable for r in results)


async def test_ten_simultaneous_requests_download_once():
    flight = InFlight()
    downloads = 0

    async def request():
        nonlocal downloads
        running = flight.follow("viral")
        if running is not None:
            return await flight.wait_for(running)

        future = flight.lead("viral")
        result = FAILED
        try:
            downloads += 1
            await asyncio.sleep(0.05)
            result = SharedUpload(file_id="F", kind="video")
            return result
        finally:
            flight.settle("viral", future, result)

    results = await asyncio.gather(*(request() for _ in range(10)))

    assert downloads == 1
    assert all(r.file_id == "F" for r in results)
    assert flight.active == 0


async def test_a_follower_giving_up_does_not_abort_the_leader():
    """A follower using /cancel must not cancel the download that other
    followers are still waiting on."""
    flight = InFlight()
    finished = False

    async def leader():
        nonlocal finished
        future = flight.lead("k")
        try:
            await asyncio.sleep(0.15)
            finished = True
            return SharedUpload(file_id="F")
        finally:
            flight.settle("k", future, SharedUpload(file_id="F"))

    lead_task = asyncio.create_task(leader())
    await asyncio.sleep(0.02)

    quitter = asyncio.create_task(flight.wait_for(flight.follow("k")))
    patient = asyncio.create_task(flight.wait_for(flight.follow("k")))
    await asyncio.sleep(0.02)
    quitter.cancel()

    assert (await lead_task).file_id == "F"
    assert finished
    assert (await patient).file_id == "F"


async def test_a_failed_leader_lets_followers_try_for_themselves():
    flight = InFlight()
    future = flight.lead("k")
    waiter = asyncio.create_task(flight.wait_for(future))
    await asyncio.sleep(0)

    flight.settle("k", future)  # defaults to FAILED
    result = await waiter

    assert result is FAILED
    assert not result.usable
    # And the key is free, so a follower can lead the next attempt.
    assert flight.follow("k") is None


async def test_settling_twice_is_harmless():
    flight = InFlight()
    future = flight.lead("k")
    flight.settle("k", future, SharedUpload(file_id="F"))
    flight.settle("k", future, SharedUpload(file_id="OTHER"))
    assert (await future).file_id == "F"


async def test_a_stale_settle_does_not_evict_a_newer_claim():
    """The first request's cleanup must not release a second request's slot."""
    flight = InFlight()
    first = flight.lead("k")
    flight.settle("k", first, FAILED)

    second = flight.lead("k")
    flight.settle("k", first, FAILED)  # late cleanup from the first

    assert flight.follow("k") is second
    flight.settle("k", second, SharedUpload(file_id="F"))
    assert flight.active == 0


async def test_different_keys_do_not_collide():
    flight = InFlight()
    a, b = flight.lead("a"), flight.lead("b")
    assert flight.active == 2
    flight.settle("a", a, SharedUpload(file_id="A"))
    assert flight.follow("b") is b
    flight.settle("b", b, SharedUpload(file_id="B"))


def test_shared_upload_usability():
    assert SharedUpload(file_id="F").usable
    assert not SharedUpload(file_id=None).usable
    assert not FAILED.usable
