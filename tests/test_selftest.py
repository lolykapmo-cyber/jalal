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


def test_the_default_canary_is_yt_dlps_own_test_video():
    """A video the extractor project itself tests against outlives whatever
    clip is popular this month."""
    urls = canary_urls(load_settings())
    assert urls == selftest.DEFAULT_TEST_URLS
    assert len(urls) == 1


def test_urls_can_be_overridden(monkeypatch):
    monkeypatch.setenv("SELFTEST_URLS", "https://a.co/1, https://b.co/2 ;https://c.co/3")
    assert canary_urls(load_settings()) == (
        "https://a.co/1", "https://b.co/2", "https://c.co/3",
    )


def test_an_empty_override_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("SELFTEST_URLS", "   ")
    assert canary_urls(load_settings()) == selftest.DEFAULT_TEST_URLS


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
