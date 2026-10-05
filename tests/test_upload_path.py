"""Large uploads must not pass through the bot's memory."""

import pathlib
import tempfile

from telegram import InputFile
from telegram._utils.files import parse_file_input

from bot.handlers.download import _rename_for_telegram


def test_local_mode_sends_a_path_not_the_bytes():
    """With a local Bot API server the server reads the file itself, so a
    2 GB upload never has to be loaded here."""
    with tempfile.TemporaryDirectory() as tmp:
        clip = pathlib.Path(tmp) / "clip.mp4"
        clip.write_bytes(b"x" * (2 * 1024 * 1024))

        sent = parse_file_input(clip, local_mode=True)

        assert isinstance(sent, str)
        assert sent.startswith("file://")
        assert sent.endswith("clip.mp4")


def test_cloud_mode_still_reads_the_file():
    with tempfile.TemporaryDirectory() as tmp:
        clip = pathlib.Path(tmp) / "clip.mp4"
        clip.write_bytes(b"x" * 1024)

        sent = parse_file_input(clip, local_mode=False)

        assert isinstance(sent, InputFile)
        assert len(sent.input_file_content) == 1024


def test_rename_gives_the_recipient_a_readable_name():
    """In local mode the filename comes from the path, so it has to be set
    before sending rather than passed alongside the bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = pathlib.Path(tmp) / "dQw4w9WgXcQ.mp4"
        raw.write_bytes(b"x")

        renamed = _rename_for_telegram(raw, "فيديو رائع جداً", is_audio=False)

        assert renamed.name == "فيديو رائع جداً.mp4"
        assert renamed.exists()
        assert not raw.exists()


def test_rename_sanitises_a_hostile_title():
    with tempfile.TemporaryDirectory() as tmp:
        raw = pathlib.Path(tmp) / "x.mp4"
        raw.write_bytes(b"x")

        renamed = _rename_for_telegram(raw, "../../etc/passwd", is_audio=False)

        # The name must stay inside the job directory.
        assert renamed.parent == raw.parent
        assert "/" not in renamed.name
        assert renamed.exists()


def test_rename_supplies_an_extension_when_there_is_none():
    with tempfile.TemporaryDirectory() as tmp:
        raw = pathlib.Path(tmp) / "track"
        raw.write_bytes(b"x")

        assert _rename_for_telegram(raw, "Song", is_audio=True).name == "Song.mp3"


def test_rename_falls_back_instead_of_losing_the_file():
    """An unusable title must never leave the job without a file to send."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = pathlib.Path(tmp) / "clip.mp4"
        raw.write_bytes(b"x")

        renamed = _rename_for_telegram(raw, "", is_audio=False)

        assert renamed.exists()
        assert renamed.stat().st_size == 1
