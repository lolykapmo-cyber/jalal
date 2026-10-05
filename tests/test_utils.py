from bot.utils import (
    escape,
    human_duration,
    human_size,
    human_speed,
    progress_bar,
    safe_filename,
    shorten,
)


def test_human_size_scales_units():
    assert human_size(0) == "—"
    assert human_size(512) == "512 B"
    assert human_size(2048) == "2.0 KB"
    assert human_size(5 * 1024**2) == "5.0 MB"
    assert human_size(3 * 1024**3) == "3.0 GB"


def test_human_duration_drops_a_zero_hour():
    assert human_duration(None) == "—"
    assert human_duration(45) == "0:45"
    assert human_duration(125) == "2:05"
    assert human_duration(3725) == "1:02:05"


def test_human_speed():
    assert human_speed(None) == "—"
    assert human_speed(1024) == "1.0 KB/s"


def test_progress_bar_is_fixed_width_and_clamped():
    assert len(progress_bar(0.5)) == 12
    assert progress_bar(0) == "░" * 12
    assert progress_bar(1) == "█" * 12
    assert progress_bar(5.0) == "█" * 12  # clamped, not overflowing
    assert progress_bar(None) == "░" * 12


def test_escape_protects_html_parse_mode():
    assert escape("<b>&x</b>") == "&lt;b&gt;&amp;x&lt;/b&gt;"
    assert escape(None) == ""


def test_shorten_collapses_whitespace_and_ellipsises():
    assert shorten("a   b\n c") == "a b c"
    assert shorten("x" * 50, 10).endswith("…")
    assert len(shorten("x" * 50, 10)) == 10


def test_safe_filename_strips_path_and_control_characters():
    assert safe_filename("a/b\\c:d*e?f") == "a b c d e f"
    assert safe_filename("") == "video"
    assert safe_filename("   ...   ") == "video"
    assert safe_filename("فيديو جميل") == "فيديو جميل"
    assert len(safe_filename("y" * 300)) <= 80
