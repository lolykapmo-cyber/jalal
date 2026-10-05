import pytest

from bot import media
from bot.media import MIN_VIDEO_BITRATE, MediaError, plan_shrink

FIFTY_MB = 50 * 1024 * 1024

needs_ffmpeg = pytest.mark.skipif(
    not media.ffmpeg_available(), reason="ffmpeg/ffprobe not installed"
)


def test_plan_shrink_scales_the_frame_to_the_bitrate():
    plan = plan_shrink(FIFTY_MB, 60)
    assert plan is not None
    bitrate, height = plan
    assert bitrate > MIN_VIDEO_BITRATE
    assert height == 1080  # a one-minute clip has bits to spare

    # Ten minutes into the same budget can only justify a smaller frame.
    _, ten_minute_height = plan_shrink(FIFTY_MB, 600)
    assert ten_minute_height < height


def test_plan_shrink_refuses_an_impossible_budget():
    # Four hours into 50 MB would be unwatchable.
    assert plan_shrink(FIFTY_MB, 4 * 3600) is None
    # An unknown duration gives us nothing to compute from.
    assert plan_shrink(FIFTY_MB, None) is None
    assert plan_shrink(FIFTY_MB, 0) is None
    assert plan_shrink(0, 60) is None


def test_plan_shrink_stays_under_the_budget():
    duration = 300
    bitrate, _ = plan_shrink(FIFTY_MB, duration)
    projected_bytes = (bitrate + media.AUDIO_BITRATE_FOR_SHRINK) * duration / 8
    assert projected_bytes <= FIFTY_MB


CLIP_SECONDS = 3

# Deliberately overshoot the bitrate: the synthetic pattern compresses so
# well that a default encode lands below the shrink floor, leaving no room
# to prove anything.
CLIP_BITRATE = "4000k"


@pytest.fixture
async def clip(tmp_path):
    """A real three-second H.264/AAC file to exercise the ffmpeg paths."""
    path = tmp_path / "clip.mp4"
    code, _, stderr = await media._run(
        "ffmpeg", "-nostdin", "-y",
        "-f", "lavfi", "-i", f"testsrc=size=640x360:rate=25:duration={CLIP_SECONDS}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={CLIP_SECONDS}",
        "-shortest", "-codec:v", "libx264", "-preset", "ultrafast",
        "-b:v", CLIP_BITRATE, "-codec:a", "aac",
        "-movflags", "+faststart", str(path),
    )
    assert code == 0, stderr.decode()[-400:]
    return path


@needs_ffmpeg
async def test_probe_reads_streams_and_duration(clip):
    probe = await media.probe(clip)
    assert probe.has_video and probe.has_audio
    assert (probe.width, probe.height) == (640, 360)
    assert probe.duration == pytest.approx(3.0, abs=0.3)


@needs_ffmpeg
async def test_probe_rejects_a_non_media_file(tmp_path):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video")
    with pytest.raises(MediaError):
        await media.probe(junk)


@needs_ffmpeg
async def test_thumbnail_respects_telegram_limits(clip, tmp_path):
    thumb = await media.make_thumbnail(clip, tmp_path / "t.jpg")
    assert thumb is not None
    assert thumb.stat().st_size <= media.THUMBNAIL_MAX_BYTES

    probe = await media.probe(thumb)
    assert max(probe.width, probe.height) <= media.THUMBNAIL_MAX_EDGE


@needs_ffmpeg
async def test_thumbnail_of_a_broken_file_returns_none(tmp_path):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"still not a video")
    assert await media.make_thumbnail(junk, tmp_path / "t.jpg") is None


@needs_ffmpeg
async def test_extract_audio_produces_a_playable_mp3(clip, tmp_path):
    mp3 = await media.extract_audio(clip, tmp_path / "a.mp3")
    assert mp3.stat().st_size > 0
    probe = await media.probe(mp3)
    assert probe.has_audio and not probe.has_video


@needs_ffmpeg
async def test_extract_audio_raises_on_garbage(tmp_path):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"nope")
    with pytest.raises(MediaError):
        await media.extract_audio(junk, tmp_path / "a.mp3")


@needs_ffmpeg
async def test_shrink_actually_lands_under_the_target(clip, tmp_path):
    probe = await media.probe(clip)

    # Sit comfortably between the shrink floor and the source size, so the
    # test fails on a regression rather than on encoder luck.
    floor = (media.MIN_VIDEO_BITRATE + media.AUDIO_BITRATE_FOR_SHRINK) * CLIP_SECONDS / 8
    target = int(floor * 2)
    assert clip.stat().st_size > target  # otherwise the test proves nothing

    out = await media.shrink_to_fit(
        clip, tmp_path / "small.mp4", target_bytes=target,
        duration=probe.duration, source_height=probe.height,
    )
    assert out is not None
    assert out.stat().st_size <= target
    # It must still be a real video, not a truncated file.
    assert (await media.probe(out)).has_video


@needs_ffmpeg
async def test_shrink_gives_up_rather_than_producing_sludge(clip, tmp_path):
    out = await media.shrink_to_fit(
        clip, tmp_path / "tiny.mp4", target_bytes=1_000,
        duration=3.0, source_height=360,
    )
    assert out is None
    assert not (tmp_path / "tiny.mp4").exists()
