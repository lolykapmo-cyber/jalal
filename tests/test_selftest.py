"""The hourly check that proves downloading still works."""

import functools
import http.server
import threading
from pathlib import Path

import pytest

from bot import media, selftest
from bot.config import load_settings
from bot.selftest import CheckResult, _first_unreadable, _report, canary_urls

needs_ffmpeg = pytest.mark.skipif(
    not media.ffmpeg_available(), reason="ffmpeg/ffprobe not installed"
)


@pytest.fixture(autouse=True)
def base_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "work"))
    monkeypatch.delenv("SELFTEST_URLS", raising=False)
    (tmp_path / "work").mkdir(exist_ok=True)


# ---- which links to check -------------------------------------------


def test_nothing_is_checked_before_anything_has_downloaded(tmp_path, monkeypatch):
    """Falling back to a hardcoded video meant reporting on a link nobody
    could verify was still alive, which produced a false alarm on every
    fresh install. Nothing proven means nothing to check."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "absent.sqlite3"))
    assert canary_urls(load_settings()) == ()


def test_urls_can_be_overridden(monkeypatch):
    monkeypatch.setenv("SELFTEST_URLS", "https://a.co/1, https://b.co/2 ;https://c.co/3")
    assert canary_urls(load_settings()) == (
        "https://a.co/1", "https://b.co/2", "https://c.co/3",
    )


def test_a_blank_override_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "absent.sqlite3"))
    monkeypatch.setenv("SELFTEST_URLS", "   ")
    assert canary_urls(load_settings()) == ()


# ---- the permission class of bug ------------------------------------


def test_a_fully_readable_path_passes(tmp_path):
    tmp_path.chmod(0o755)
    job = tmp_path / "job"
    job.mkdir(mode=0o755)
    clip = job / "v.mp4"
    clip.write_bytes(b"x")
    clip.chmod(0o644)

    assert _first_unreadable(clip, tmp_path) is None


def test_an_unreadable_file_is_named(tmp_path):
    tmp_path.chmod(0o755)
    job = tmp_path / "job"
    job.mkdir(mode=0o755)
    clip = job / "v.mp4"
    clip.write_bytes(b"x")
    clip.chmod(0o600)

    assert _first_unreadable(clip, tmp_path) == clip


def test_an_untraversable_directory_is_named(tmp_path):
    tmp_path.chmod(0o755)
    """Exactly the failure that made every upload return 'Can't get stat
    about the file' while the bot itself saw nothing wrong."""
    job = tmp_path / "job"
    job.mkdir(mode=0o755)
    clip = job / "v.mp4"
    clip.write_bytes(b"x")
    clip.chmod(0o644)
    job.chmod(0o700)

    assert _first_unreadable(clip, tmp_path) == job


def test_a_missing_file_is_reported_not_crashed(tmp_path):
    assert _first_unreadable(tmp_path / "gone.mp4", tmp_path) is not None


def test_a_tight_root_is_reported(tmp_path):
    """work_dir itself must be traversable: if the API server cannot get
    into it, nothing underneath matters."""
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    job = root / "job"
    job.mkdir(mode=0o755)
    clip = job / "v.mp4"
    clip.write_bytes(b"x")
    clip.chmod(0o644)

    assert _first_unreadable(clip, root) == root


def test_the_walk_does_not_climb_above_the_root(tmp_path):
    """Whatever /var or / are set to is not this bot's business."""
    tmp_path.chmod(0o700)           # the grandparent is tight
    root = tmp_path / "root"
    root.mkdir(mode=0o755)
    job = root / "job"
    job.mkdir(mode=0o755)
    clip = job / "v.mp4"
    clip.write_bytes(b"x")
    clip.chmod(0o644)

    assert _first_unreadable(clip, root) is None


# ---- reporting -------------------------------------------------------


def test_a_passing_result_reads_clearly():
    text = CheckResult("https://a.co/1", True, "4.2 MB", "yt/default").summary
    assert text.startswith("ok via yt/default:")
    assert "4.2 MB" in text


def test_a_failing_result_names_the_reason():
    assert CheckResult("https://a.co/1", False, "err_login").summary.startswith("FAILED:")


def test_the_alert_says_what_broke_and_what_was_tried():
    text = _report(
        [CheckResult("https://a.co/1", False, "err_no_formats")],
        ["update yt-dlp: ok", "restart the bot: ok"],
    )
    assert "Self-test failed" in text
    assert "err_no_formats" in text
    assert "update yt-dlp: ok" in text
    # An alert with no next step wastes the reader's time.
    assert "journalctl" in text


def test_the_alert_works_before_any_repair_was_attempted():
    text = _report([CheckResult("https://a.co/1", False, "err_network")])
    assert "Tried to repair" not in text


# ---- end to end, against a local server -----------------------------


@needs_ffmpeg
async def test_a_working_site_reports_ok(tmp_path, monkeypatch):
    serve_dir = tmp_path / "serve"
    serve_dir.mkdir()
    clip = serve_dir / "canary.mp4"
    code, _, stderr = await media._run(
        "ffmpeg", "-nostdin", "-y",
        "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=1",
        "-c:v", "libx264", "-preset", "ultrafast", str(clip),
    )
    assert code == 0, stderr.decode()[-300:]

    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1")
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(var, raising=False)

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(serve_dir)
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/canary.mp4"
        work = Path(load_settings().work_dir)
        result = await selftest.check_one(url, load_settings(), work)

        assert result.ok, result.summary
        assert "MB" in result.detail
    finally:
        server.shutdown()


async def test_an_unreachable_site_fails_without_raising(tmp_path):
    settings = load_settings()
    result = await selftest.check_one(
        "http://127.0.0.1:1/gone.mp4", settings, Path(settings.work_dir)
    )
    assert not result.ok
    assert result.detail


# ---- a dead link is not an outage ------------------------------------


@pytest.mark.parametrize("key", [
    "err_unavailable", "err_private", "err_geo", "err_live", "err_too_long",
])
def test_a_failure_about_the_video_is_not_an_outage(key):
    """These describe the link, not the bot. Repairing on them would mean
    reinstalling yt-dlp hourly over a video somebody deleted."""
    assert CheckResult("https://a.co/1", False, key, failure_key=key).canary_is_gone


@pytest.mark.parametrize("key", [
    "err_no_formats", "err_login", "err_network", "err_generic",
])
def test_a_failure_about_the_bot_still_counts(key):
    assert not CheckResult("https://a.co/1", False, key, failure_key=key).canary_is_gone


def test_a_passing_check_is_never_a_dead_canary():
    assert not CheckResult("https://a.co/1", True, "4 MB").canary_is_gone


def test_the_dead_canary_report_says_what_to_change():
    from bot.selftest import _canary_report

    text = _canary_report([
        CheckResult("https://youtu.be/x", False, "err_unavailable",
                    failure_key="err_unavailable")
    ])
    assert "not the bot" in text
    assert "SELFTEST_URLS" in text
    # It must not read like an outage, or it trains the reader to ignore it.
    assert "Self-test failed" not in text


def test_a_dead_canary_summary_is_labelled_distinctly():
    gone = CheckResult("https://a.co/1", False, "err_unavailable",
                       failure_key="err_unavailable")
    assert gone.summary.startswith("canary gone")
    broken = CheckResult("https://a.co/1", False, "err_no_formats",
                         failure_key="err_no_formats")
    assert broken.summary.startswith("FAILED")


# ---- canaries chosen from real history -------------------------------


async def test_links_that_really_downloaded_become_the_canaries(tmp_path, monkeypatch):
    """Asking an operator to configure this was the wrong design: the bot
    already knows which links worked."""
    from bot.storage import Storage

    db = tmp_path / "b.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db))

    store = Storage(db, default_language="ar", default_quality="best",
                    default_ask_quality=True)
    await store.open()
    await store.record_success("https://youtu.be/proven", "youtube")
    await store.record_success("https://vt.tiktok.com/proven", "tiktok")
    await store.close()

    urls = canary_urls(load_settings())
    assert set(urls) == {"https://youtu.be/proven", "https://vt.tiktok.com/proven"}


async def test_only_the_newest_link_per_site_is_watched(tmp_path, monkeypatch):
    from bot.storage import Storage

    db = tmp_path / "b.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db))

    store = Storage(db, default_language="ar", default_quality="best",
                    default_ask_quality=True)
    await store.open()
    for url in ("https://youtu.be/old", "https://youtu.be/newer"):
        await store.record_success(url, "youtube")
    await store.close()

    urls = canary_urls(load_settings())
    assert urls == ("https://youtu.be/newer",)


async def test_an_existing_install_recovers_canaries_from_its_upload_cache(
    tmp_path, monkeypatch
):
    """The successes table is new, but the upload cache has been keyed by
    URL all along, so an existing install has canaries at once rather than
    after its next download."""
    from bot.storage import Storage

    db = tmp_path / "b.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db))

    store = Storage(db, default_language="ar", default_quality="best",
                    default_ask_quality=True)
    await store.open()
    await store.cache_store("url:https://youtu.be/cached:720",
                            file_id="F", kind="video", title="t")
    await store.cache_store("url:https://vt.tiktok.com/cached:best",
                            file_id="F", kind="video", title="t")
    # An id-shaped key carries no URL and must be ignored.
    await store.cache_store("youtube:abc:720", file_id="F", kind="video", title="t")
    await store.close()

    urls = canary_urls(load_settings())
    assert set(urls) == {"https://youtu.be/cached", "https://vt.tiktok.com/cached"}


def test_recorded_successes_win_over_the_cache(tmp_path, monkeypatch):
    """The cache is only a fallback for installs that predate the table."""
    import asyncio

    from bot.storage import Storage

    db = tmp_path / "b.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db))

    async def seed():
        store = Storage(db, default_language="ar", default_quality="best",
                        default_ask_quality=True)
        await store.open()
        await store.cache_store("url:https://old.site/cached:720",
                                file_id="F", kind="video", title="t")
        await store.record_success("https://youtu.be/recorded", "youtube")
        await store.close()

    asyncio.run(seed())
    assert canary_urls(load_settings()) == ("https://youtu.be/recorded",)


def test_an_explicit_setting_still_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "b.sqlite3"))
    monkeypatch.setenv("SELFTEST_URLS", "https://my.site/x")
    assert canary_urls(load_settings()) == ("https://my.site/x",)


async def test_history_is_capped_so_the_table_cannot_grow_forever(tmp_path):
    from bot.storage import Storage, read_recent_successes

    db = tmp_path / "b.sqlite3"
    store = Storage(db, default_language="ar", default_quality="best",
                    default_ask_quality=True)
    await store.open()
    for i in range(80):
        await store.record_success(f"https://a.co/{i}", f"site{i % 4}")
    rows = store._conn.execute("SELECT COUNT(*) FROM successes").fetchone()[0]
    await store.close()

    assert rows <= 50
    assert len(read_recent_successes(db, limit=10)) <= 4  # one per site


async def test_the_checks_own_scratch_directory_is_not_a_false_positive(
    tmp_path, monkeypatch
):
    """tempfile.TemporaryDirectory creates 0700, while the real pipeline
    uses mkdir() and gets 0755. Without matching that, the check failed on
    its own scratch directory and blamed the Bot API server."""
    work = tmp_path / "work"          # the autouse fixture already made it
    work.mkdir(exist_ok=True)
    work.chmod(0o755)
    monkeypatch.setenv("WORK_DIR", str(work))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "absent.sqlite3"))
    monkeypatch.setenv("SELFTEST_URLS", "http://127.0.0.1:1/nothing.mp4")

    seen: list[int] = []
    real_check = selftest.check_one

    async def spy(url, settings, work_root):
        seen.append(work_root.stat().st_mode & 0o777)
        return await real_check(url, settings, work_root)

    monkeypatch.setattr(selftest, "check_one", spy)
    await selftest.run_checks(load_settings())

    assert seen, "the check never ran"
    for mode in seen:
        assert mode & 0o055 == 0o055, f"scratch dir was {mode:o}, not traversable"
