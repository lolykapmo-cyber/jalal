import time

from bot.storage import Storage


async def test_first_contact_creates_the_row(storage):
    prefs = await storage.get_user(7, language_hint="en")
    assert prefs == await storage.get_user(7)
    assert prefs.language == "en"
    assert prefs.quality == "best"
    assert prefs.ask_quality is True
    assert prefs.downloads == 0


async def test_defaults_apply_without_a_hint(storage):
    assert (await storage.get_user(8)).language == "ar"


async def test_updates_are_partial(storage):
    await storage.get_user(9)
    await storage.update_user(9, quality="720")
    prefs = await storage.get_user(9)
    assert prefs.quality == "720"
    assert prefs.language == "ar"  # untouched

    await storage.update_user(9, ask_quality=False, language="en")
    prefs = await storage.get_user(9)
    assert (prefs.language, prefs.quality, prefs.ask_quality) == ("en", "720", False)


async def test_an_empty_update_is_a_noop(storage):
    before = await storage.get_user(10)
    await storage.update_user(10)
    assert await storage.get_user(10) == before


async def test_download_counters(storage):
    await storage.get_user(11)
    await storage.record_download(11)
    await storage.record_download(11)
    assert (await storage.get_user(11)).downloads == 2
    assert (await storage.stats())["downloads"] == 2


async def test_cache_round_trip_and_overwrite(storage):
    await storage.cache_store("k", file_id="A", kind="video", title="one")
    assert (await storage.cache_lookup("k", ttl_hours=1)).file_id == "A"

    await storage.cache_store("k", file_id="B", kind="audio", title="two")
    hit = await storage.cache_lookup("k", ttl_hours=1)
    assert (hit.file_id, hit.kind, hit.title) == ("B", "audio", "two")


async def test_cache_miss_is_none(storage):
    assert await storage.cache_lookup("absent", ttl_hours=1) is None


async def test_expired_entries_are_dropped_on_read(storage):
    await storage.cache_store("old", file_id="A", kind="video", title=None)
    # Backdate the row past any sane TTL.
    await storage.cache_store("old", file_id="A", kind="video", title=None)
    storage._conn.execute(
        "UPDATE media_cache SET created_at = ? WHERE cache_key = 'old'",
        (time.time() - 10 * 3600,),
    )
    storage._conn.commit()

    assert await storage.cache_lookup("old", ttl_hours=1) is None
    # The read also removed it.
    assert storage._conn.execute(
        "SELECT COUNT(*) FROM media_cache WHERE cache_key='old'"
    ).fetchone()[0] == 0


async def test_a_zero_ttl_never_expires(storage):
    await storage.cache_store("forever", file_id="A", kind="video", title=None)
    storage._conn.execute(
        "UPDATE media_cache SET created_at = ? WHERE cache_key='forever'",
        (time.time() - 10**6,),
    )
    storage._conn.commit()
    assert await storage.cache_lookup("forever", ttl_hours=0) is not None


async def test_forget_and_prune(storage):
    await storage.cache_store("a", file_id="A", kind="video", title=None)
    await storage.cache_forget("a")
    assert await storage.cache_lookup("a", ttl_hours=1) is None

    await storage.cache_store("b", file_id="B", kind="video", title=None)
    storage._conn.execute("UPDATE media_cache SET created_at = ?", (time.time() - 10**6,))
    storage._conn.commit()
    assert await storage.cache_prune(ttl_hours=1) == 1
    assert await storage.cache_prune(ttl_hours=0) == 0


async def test_stats_shape(storage):
    await storage.get_user(1)
    await storage.get_user(2)
    await storage.bump("cache_hits", 3)
    await storage.cache_store("c", file_id="C", kind="video", title=None)
    numbers = await storage.stats()
    assert numbers == {"users": 2, "cache_rows": 1, "downloads": 0, "cached": 3}


async def test_state_survives_a_reopen(tmp_path):
    path = tmp_path / "persist.sqlite3"
    first = Storage(path, default_language="ar", default_quality="best",
                    default_ask_quality=True)
    await first.open()
    await first.get_user(5)
    await first.update_user(5, quality="480")
    await first.close()

    second = Storage(path, default_language="en", default_quality="best",
                     default_ask_quality=True)
    await second.open()
    # The stored preference wins over the new default.
    assert (await second.get_user(5)).quality == "480"
    await second.close()
