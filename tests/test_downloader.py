import pytest

from bot.downloader import (
    OFFERED_HEIGHTS,
    QUALITY_CHOICES,
    CancelToken,
    DownloadCancelled,
    DownloadFailure,
    available_heights,
    cache_key,
    classify_error,
    clean_error,
    describe,
    first_entry,
    format_selector,
    glob_escape,
    is_live,
    offered_qualities,
    resolve_output,
)


def test_format_selector_per_quality():
    assert format_selector("best") == "bestvideo*+bestaudio/best"
    assert format_selector("audio") == "bestaudio/best"
    assert "height<=720" in format_selector("720")
    # Every selector ends in an unconstrained fallback so a download still
    # happens when the preferred rung is missing.
    for quality in QUALITY_CHOICES:
        assert format_selector(quality).endswith("best")


def test_build_options_shape(tmp_path):
    from bot.downloader import build_options

    options = build_options(
        quality="720", dest_dir=tmp_path, cookies_file=None, proxy=None,
        max_playlist_items=1,
    )
    assert options["noplaylist"] is True
    assert options["merge_output_format"] == "mp4"
    assert str(tmp_path) in options["outtmpl"]
    assert options["postprocessors"] == []

    audio = build_options(
        quality="audio", dest_dir=tmp_path, cookies_file=None, proxy=None,
        max_playlist_items=1,
    )
    # Audio must not be remuxed into mp4, and needs the extract-audio pass.
    assert "merge_output_format" not in audio
    assert audio["postprocessors"][0]["key"] == "FFmpegExtractAudio"
    assert audio["postprocessors"][0]["preferredcodec"] == "mp3"


def test_build_options_playlists_and_extras(tmp_path):
    from bot.downloader import build_options

    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# netscape")
    options = build_options(
        quality="best", dest_dir=tmp_path, cookies_file=cookies,
        proxy="socks5://127.0.0.1:9050", max_playlist_items=5,
    )
    assert options["noplaylist"] is False
    assert options["playlist_items"] == "1:5"
    assert options["cookiefile"] == str(cookies)
    assert options["proxy"] == "socks5://127.0.0.1:9050"


def test_a_missing_cookies_file_is_ignored(tmp_path):
    from bot.downloader import build_options

    options = build_options(
        quality="best", dest_dir=tmp_path, cookies_file=tmp_path / "nope.txt",
        proxy=None, max_playlist_items=1,
    )
    assert "cookiefile" not in options


@pytest.mark.parametrize("message,expected", [
    ("ERROR: [youtube] x: Video unavailable", "err_unavailable"),
    ("Sign in to confirm you are not a bot", "err_login"),
    ("Please use --cookies for this video", "err_login"),
    ("This video is private", "err_private"),
    ("The uploader has not made this video available in your country", "err_geo"),
    ("ERROR: Unsupported URL: https://a.b/c", "err_unsupported"),
    ("This live event will begin in 2 hours", "err_live"),
    ("Requested format is not available", "err_no_formats"),
    ("<urlopen error timed out>", "err_network"),
    ("Failed to resolve 'x.invalid' (Name or service not known)", "err_network"),
    ("HTTP Error 503: Service Unavailable", "err_network"),
])
def test_error_classification(message, expected):
    assert classify_error(message).key == expected


def test_unknown_errors_carry_a_cleaned_reason():
    failure = classify_error("ERROR: \x1b[0;31mweird thing\x1b[0m happened")
    assert failure.key == "err_generic"
    assert failure.params["reason"] == "weird thing happened"


def test_clean_error_strips_noise_and_truncates():
    assert clean_error("ERROR: [generic] oops") == "oops"
    assert clean_error("a\n\n   b") == "a b"
    assert clean_error("") == "unknown error"
    long = clean_error("x" * 500)
    assert len(long) == 220 and long.endswith("…")


def test_cancel_token_raises_once_flipped():
    token = CancelToken()
    token.raise_if_cancelled()  # no-op while clear
    assert token.cancelled is False
    token.cancel()
    assert token.cancelled is True
    with pytest.raises(DownloadCancelled):
        token.raise_if_cancelled()


def test_available_and_offered_heights():
    info = {"formats": [
        {"vcodec": "avc1", "height": 1080},
        {"vcodec": "avc1", "height": 480},
        {"vcodec": "none", "height": None},     # audio-only rung
        {"vcodec": "vp9", "height": 0},         # junk
    ]}
    assert available_heights(info) == [1080, 480]
    assert offered_qualities(info) == [1080, 720, 480, 360]


def test_offered_heights_never_exceed_the_source():
    assert offered_qualities({"formats": [{"vcodec": "h264", "height": 480}]}) == [480, 360]
    assert offered_qualities({"height": 720}) == [720, 480, 360]
    # An audio-only link offers no video rungs at all.
    assert offered_qualities({"formats": [{"vcodec": "none"}]}) == []


def test_offered_heights_are_a_subset_of_what_we_advertise():
    info = {"formats": [{"vcodec": "h264", "height": 4320}]}
    assert set(offered_qualities(info)) <= set(OFFERED_HEIGHTS)


def test_first_entry_unwraps_playlists():
    assert first_entry({"id": "a"})["id"] == "a"
    assert first_entry({"entries": [{"id": "b"}, {"id": "c"}]})["id"] == "b"
    # Nested playlists (a channel of playlists) still resolve.
    assert first_entry({"entries": [{"entries": [{"id": "d"}]}]})["id"] == "d"
    # Blank entries are skipped.
    assert first_entry({"entries": [None, {"id": "e"}]})["id"] == "e"


def test_first_entry_rejects_an_empty_playlist():
    with pytest.raises(DownloadFailure) as caught:
        first_entry({"entries": []})
    assert caught.value.key == "err_no_formats"


def test_describe_falls_back_sensibly():
    title, uploader, duration = describe(
        {"title": " Clip ", "channel": "Chan", "duration": 61.5}
    )
    assert (title, uploader, duration) == ("Clip", "Chan", 61.5)

    title, uploader, duration = describe({"id": "xyz"})
    assert (title, uploader, duration) == ("xyz", "—", None)

    # A zero or negative duration is treated as unknown, not as 0:00.
    assert describe({"id": "a", "duration": 0})[2] is None


def test_is_live_covers_upcoming_streams():
    assert is_live({"is_live": True})
    assert is_live({"live_status": "is_upcoming"})
    assert not is_live({"live_status": "not_live"})
    assert not is_live({})


def test_cache_key_is_stable_and_quality_scoped():
    info = {"extractor": "YouTube", "id": "abc"}
    assert cache_key(info, "720") == "youtube:abc:720"
    assert cache_key(info, "720") == cache_key(dict(info), "720")
    assert cache_key(info, "audio") != cache_key(info, "720")


def test_resolve_output_prefers_the_reported_path(tmp_path):
    produced = tmp_path / "v.mp4"
    produced.write_bytes(b"x" * 10)
    info = {"requested_downloads": [{"filepath": str(produced)}]}
    assert resolve_output(info, tmp_path) == produced


def test_resolve_output_follows_a_post_processed_extension(tmp_path):
    # yt-dlp reported .webm but FFmpegExtractAudio left an .mp3 behind.
    (tmp_path / "song.mp3").write_bytes(b"x" * 20)
    info = {"requested_downloads": [{"filepath": str(tmp_path / "song.webm")}]}
    assert resolve_output(info, tmp_path).name == "song.mp3"


def test_resolve_output_falls_back_to_the_largest_media_file(tmp_path):
    (tmp_path / "small.mp4").write_bytes(b"x" * 5)
    (tmp_path / "big.mkv").write_bytes(b"x" * 500)
    (tmp_path / "notes.txt").write_bytes(b"x" * 9000)  # not media
    assert resolve_output({}, tmp_path).name == "big.mkv"


def test_resolve_output_ignores_empty_files(tmp_path):
    (tmp_path / "empty.mp4").write_bytes(b"")
    with pytest.raises(DownloadFailure) as caught:
        resolve_output({}, tmp_path)
    assert caught.value.key == "err_no_formats"


def test_glob_escape_protects_literal_brackets(tmp_path):
    assert glob_escape("a[1].mp4") == "a[[]1[]].mp4"
    # A real filename with brackets must still be found.
    (tmp_path / "clip [HD].mp4").write_bytes(b"x" * 10)
    info = {"requested_downloads": [{"filepath": str(tmp_path / "clip [HD].webm")}]}
    assert resolve_output(info, tmp_path).name == "clip [HD].mp4"


@pytest.mark.parametrize("message,expected", [
    # Both phrasings are real. Matching only the first sent a deleted video
    # to err_generic, which made the self-test call it an outage.
    ("Video unavailable", "err_unavailable"),
    ("BaW_jenozKc: This video is unavailable", "err_unavailable"),
    ("This content is unavailable", "err_unavailable"),
    # And the broader phrase must not swallow a transient server error.
    ("HTTP Error 503: Service Unavailable", "err_network"),
    ("Requested format is not available", "err_no_formats"),
])
def test_unavailable_phrasings(message, expected):
    assert classify_error(message).key == expected
