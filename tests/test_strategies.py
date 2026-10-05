"""The cookieless retry ladder, and the downloader's use of it."""

import pytest

from bot import downloader, strategies
from bot.downloader import DownloadCancelled, DownloadFailure, probe_url, run_download
from bot.strategies import Strategy, is_retryable, ladder_for


# ---- ladders ---------------------------------------------------------


@pytest.mark.parametrize("url,first_label", [
    ("https://youtu.be/x", "yt/tv"),
    ("https://www.youtube.com/watch?v=x", "yt/tv"),
    ("https://www.instagram.com/reel/x/", "meta/chrome"),
    ("https://www.tiktok.com/@a/video/1", "tiktok/default"),
    ("https://x.com/u/status/1", "x/syndication"),
    ("https://twitter.com/u/status/1", "x/syndication"),
])
def test_known_platforms_get_their_own_ladder(url, first_label, monkeypatch):
    monkeypatch.setattr(strategies, "impersonation_available", lambda: True)
    assert ladder_for(url)[0].label == first_label


def test_unknown_hosts_fall_back_to_the_generic_ladder(monkeypatch):
    monkeypatch.setattr(strategies, "impersonation_available", lambda: True)
    assert [s.label for s in ladder_for("https://videos.example.org/v")] == [
        "default", "chrome", "firefox",
    ]


def test_every_ladder_has_more_than_one_rung(monkeypatch):
    monkeypatch.setattr(strategies, "impersonation_available", lambda: True)
    for url in ("https://youtu.be/x", "https://www.instagram.com/p/x/",
                "https://www.tiktok.com/@a/video/1", "https://x.com/u/status/1",
                "https://other.example/v"):
        assert len(ladder_for(url)) >= 2, url


def test_ladders_degrade_when_impersonation_is_unavailable(monkeypatch):
    monkeypatch.setattr(strategies, "impersonation_available", lambda: False)

    # Instagram's ladder is impersonation-heavy, so it must not come back empty.
    meta = ladder_for("https://www.instagram.com/reel/x/")
    assert len(meta) >= 1
    assert all(step.impersonate is None for step in meta)

    for url in ("https://youtu.be/x", "https://www.tiktok.com/@a/video/1",
                "https://x.com/u/status/1", "https://other.example/v"):
        rungs = ladder_for(url)
        assert rungs, url
        assert all(step.impersonate is None for step in rungs), url


def test_apply_to_merges_without_mutating_the_original():
    base = {"format": "best", "extractor_args": {"youtube": {"lang": ["en"]}}}
    merged = Strategy(
        "t", {"youtube": {"player_client": ["tv"]}}
    ).apply_to(base)

    assert merged["extractor_args"]["youtube"] == {
        "lang": ["en"], "player_client": ["tv"]
    }
    assert merged["format"] == "best"
    # The caller's dict, and its nested dict, must be untouched.
    assert base["extractor_args"] == {"youtube": {"lang": ["en"]}}


def test_apply_to_sets_an_impersonate_target():
    merged = Strategy("t", impersonate="chrome").apply_to({})
    assert merged["impersonate"] is not None
    assert "chrome" in str(merged["impersonate"]).lower()


def test_apply_to_carries_extra_options():
    assert Strategy("t", extra={"geo_bypass": True}).apply_to({})["geo_bypass"] is True


def test_retryable_covers_blocks_but_not_terminal_failures():
    for key in ("err_login", "err_no_formats", "err_network", "err_generic"):
        assert is_retryable(key), key
    # Asking with a different client cannot undelete a video.
    for key in ("err_private", "err_unavailable", "err_geo", "err_live",
                "err_unsupported", "err_too_big", "err_too_long"):
        assert not is_retryable(key), key


# ---- the downloader walking the ladder -------------------------------


@pytest.fixture
def three_rungs(monkeypatch):
    """A predictable 3-step ladder, so tests don't depend on curl_cffi."""
    ladder = (Strategy("one"), Strategy("two"), Strategy("three"))
    monkeypatch.setattr(downloader, "ladder_for", lambda url: ladder)
    return ladder


def _fake_extract(script, calls):
    """Build a stand-in for yt-dlp that follows `script` call by call."""
    def extract(url, options, *, download):
        calls.append(options)
        outcome = script[len(calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        if download:
            # Leave a real file behind so resolve_output has something to find.
            home = __import__("pathlib").Path(options["paths"]["home"])
            home.mkdir(parents=True, exist_ok=True)
            (home / "v.mp4").write_bytes(b"x" * 64)
            outcome = dict(outcome)
            outcome["requested_downloads"] = [{"filepath": str(home / "v.mp4")}]
        return outcome
    return extract


async def test_probe_retries_past_a_block_and_reports_the_winner(
    three_rungs, monkeypatch
):
    calls = []
    script = [
        DownloadFailure("err_login"),          # rung one is blocked
        {"id": "abc", "title": "Clip"},        # rung two works
    ]
    monkeypatch.setattr(downloader, "_extract", _fake_extract(script, calls))

    info = await probe_url("https://youtu.be/x", max_attempts=3)
    assert info["id"] == "abc"
    assert info["_strategy"] == "two"
    assert len(calls) == 2  # it stopped as soon as one worked


async def test_probe_stops_at_a_terminal_failure(three_rungs, monkeypatch):
    calls = []
    monkeypatch.setattr(
        downloader, "_extract",
        _fake_extract([DownloadFailure("err_private")], calls),
    )

    with pytest.raises(DownloadFailure) as caught:
        await probe_url("https://youtu.be/x", max_attempts=3)

    assert caught.value.key == "err_private"
    assert len(calls) == 1  # no point asking again


async def test_probe_reports_the_last_failure_when_every_rung_fails(
    three_rungs, monkeypatch
):
    calls = []
    script = [
        DownloadFailure("err_login"),
        DownloadFailure("err_login"),
        DownloadFailure("err_no_formats"),
    ]
    monkeypatch.setattr(downloader, "_extract", _fake_extract(script, calls))

    with pytest.raises(DownloadFailure) as caught:
        await probe_url("https://youtu.be/x", max_attempts=3)

    assert caught.value.key == "err_no_formats"
    assert len(calls) == 3


async def test_a_low_cap_never_amputates_a_ladder(three_rungs, monkeypatch):
    """A ladder is an ordered sequence whose later rungs rescue the hardest
    cases, so a low cap must not quietly disable them."""
    calls = []
    monkeypatch.setattr(
        downloader, "_extract",
        _fake_extract([DownloadFailure("err_login")] * 3, calls),
    )

    with pytest.raises(DownloadFailure):
        await probe_url("https://youtu.be/x", max_attempts=2)

    assert len(calls) == 3  # the whole ladder, not the cap


async def test_a_generous_cap_still_stops_at_the_ladder(three_rungs, monkeypatch):
    calls = []
    monkeypatch.setattr(
        downloader, "_extract",
        _fake_extract([DownloadFailure("err_login")] * 3, calls),
    )

    with pytest.raises(DownloadFailure):
        await probe_url("https://youtu.be/x", max_attempts=99)
    assert len(calls) == 3


def test_the_default_cap_covers_every_ladder(monkeypatch):
    """The default must never be the thing that cuts a platform short."""
    from bot.downloader import DEFAULT_MAX_ATTEMPTS

    monkeypatch.setattr(strategies, "impersonation_available", lambda: True)
    for url in ("https://youtu.be/x", "https://www.instagram.com/reel/x/",
                "https://www.tiktok.com/@a/video/1", "https://x.com/u/status/1",
                "https://other.example/v"):
        assert len(ladder_for(url)) <= DEFAULT_MAX_ATTEMPTS, url


def test_youtube_keeps_its_impersonation_rungs(monkeypatch):
    """These are the two that were being dropped by the old cap of 4."""
    monkeypatch.setattr(strategies, "impersonation_available", lambda: True)
    labels = [s.label for s in downloader._attempts("https://youtu.be/x", 4)]
    assert "yt/web_safari+chrome" in labels
    assert "yt/default" in labels


async def test_download_retries_and_records_the_strategy(
    three_rungs, monkeypatch, tmp_path
):
    calls = []
    script = [
        DownloadFailure("err_login"),
        {"id": "abc", "title": "Clip", "duration": 12, "extractor": "youtube"},
    ]
    monkeypatch.setattr(downloader, "_extract", _fake_extract(script, calls))

    result = await run_download(
        "https://youtu.be/x", quality="720", dest_dir=tmp_path, max_attempts=3
    )
    assert result.strategy == "two"
    assert result.title == "Clip"
    assert result.path.exists()


async def test_each_attempt_gets_a_clean_directory(
    three_rungs, monkeypatch, tmp_path
):
    calls = []
    script = [
        DownloadFailure("err_login"),
        {"id": "abc", "title": "Clip", "extractor": "youtube"},
    ]
    monkeypatch.setattr(downloader, "_extract", _fake_extract(script, calls))

    result = await run_download(
        "https://youtu.be/x", quality="best", dest_dir=tmp_path, max_attempts=3
    )

    # Attempt directories are distinct, and the failed one is cleaned up.
    homes = [c["paths"]["home"] for c in calls]
    assert len(set(homes)) == 2
    assert not (tmp_path / "try1").exists()
    assert result.path.parent == tmp_path / "try2"


async def test_a_cancelled_download_is_never_retried(
    three_rungs, monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(
        downloader, "_extract",
        _fake_extract([DownloadCancelled(), {"id": "a"}], calls),
    )

    with pytest.raises(DownloadCancelled):
        await run_download(
            "https://youtu.be/x", quality="best", dest_dir=tmp_path, max_attempts=3
        )
    assert len(calls) == 1


async def test_a_cancel_flag_mid_attempt_wins_over_a_retry(
    three_rungs, monkeypatch, tmp_path
):
    """yt-dlp wraps our cancel in its own error; it must not look retryable."""
    from bot.downloader import CancelToken

    token = CancelToken()
    token.cancel()

    calls = []
    monkeypatch.setattr(
        downloader, "_extract",
        _fake_extract([RuntimeError("wrapped cancel"), {"id": "a"}], calls),
    )

    with pytest.raises(DownloadCancelled):
        await run_download(
            "https://youtu.be/x", quality="best", dest_dir=tmp_path,
            cancel_token=token, max_attempts=3,
        )
    assert len(calls) == 1
