"""ffmpeg/ffprobe helpers: probing, thumbnails, audio, fitting a size cap."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Telegram rejects thumbnails over 200 KB or larger than 320px per side.
THUMBNAIL_MAX_EDGE = 320
THUMBNAIL_MAX_BYTES = 200 * 1024

# Below this video bitrate a re-encode looks worse than no video at all,
# so we give up and tell the user instead.
MIN_VIDEO_BITRATE = 150_000
AUDIO_BITRATE_FOR_SHRINK = 96_000

# Container and muxing overhead; leaves headroom so the result really fits.
SIZE_SAFETY_FACTOR = 0.92

# Bitrate -> sensible max height, so we don't waste bits on a large frame.
_HEIGHT_LADDER: tuple[tuple[int, int], ...] = (
    (2_500_000, 1080),
    (1_200_000, 720),
    (600_000, 480),
    (300_000, 360),
    (0, 240),
)


class MediaError(RuntimeError):
    """An ffmpeg/ffprobe invocation failed."""


@dataclass(frozen=True)
class MediaProbe:
    duration: float | None
    width: int | None
    height: int | None
    has_video: bool
    has_audio: bool


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


async def _run(*args: str, timeout: float = 3600.0) -> tuple[int, bytes, bytes]:
    """Run a command, killing the child if we're cancelled or it hangs."""
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        if process.returncode is None:
            process.kill()
            await process.wait()
        raise
    return process.returncode or 0, stdout, stderr


async def probe(path: Path) -> MediaProbe:
    """Read duration and stream layout out of a media file."""
    code, stdout, stderr = await _run(
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
        timeout=120,
    )
    if code != 0:
        raise MediaError(stderr.decode("utf-8", "replace").strip() or "ffprobe failed")

    try:
        payload = json.loads(stdout or b"{}")
    except json.JSONDecodeError as exc:
        raise MediaError("ffprobe returned invalid JSON") from exc

    streams = payload.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = _as_float((payload.get("format") or {}).get("duration"))
    if duration is None and video is not None:
        duration = _as_float(video.get("duration"))

    return MediaProbe(
        duration=duration,
        width=_as_int((video or {}).get("width")),
        height=_as_int((video or {}).get("height")),
        has_video=video is not None,
        has_audio=audio is not None,
    )


async def make_thumbnail(source: Path, destination: Path, *, at: float | None = None) -> Path | None:
    """Grab a single frame, scaled to fit Telegram's thumbnail rules."""
    seek = max(0.0, at if at is not None else 1.0)
    scale = (
        f"scale='if(gt(iw,ih),{THUMBNAIL_MAX_EDGE},-2)':"
        f"'if(gt(iw,ih),-2,{THUMBNAIL_MAX_EDGE})'"
    )
    code, _, stderr = await _run(
        "ffmpeg", "-nostdin", "-y",
        "-ss", f"{seek:.3f}",
        "-i", str(source),
        "-frames:v", "1",
        "-vf", scale,
        "-q:v", "6",
        str(destination),
        timeout=120,
    )
    if code != 0 or not destination.exists() or destination.stat().st_size == 0:
        logger.debug("thumbnail failed for %s: %s", source.name,
                     stderr.decode("utf-8", "replace")[-400:])
        return None
    if destination.stat().st_size > THUMBNAIL_MAX_BYTES:
        destination.unlink(missing_ok=True)
        return None
    return destination


async def extract_audio(source: Path, destination: Path, *, bitrate: str = "192k") -> Path:
    """Transcode whatever audio the file has into an MP3."""
    code, _, stderr = await _run(
        "ffmpeg", "-nostdin", "-y",
        "-i", str(source),
        "-vn",
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,
        str(destination),
    )
    if code != 0 or not destination.exists():
        raise MediaError(stderr.decode("utf-8", "replace").strip()[-400:] or "audio extraction failed")
    return destination


def plan_shrink(target_bytes: int, duration: float | None) -> tuple[int, int] | None:
    """Pick a (video_bitrate, max_height) pair that should land under the cap.

    Returns None when the cap can't be met at a watchable bitrate.
    """
    if not duration or duration <= 0:
        return None
    budget_bits = target_bytes * 8 * SIZE_SAFETY_FACTOR
    video_bitrate = int(budget_bits / duration) - AUDIO_BITRATE_FOR_SHRINK
    if video_bitrate < MIN_VIDEO_BITRATE:
        return None
    height = next(h for threshold, h in _HEIGHT_LADDER if video_bitrate >= threshold)
    return video_bitrate, height


async def shrink_to_fit(
    source: Path,
    destination: Path,
    *,
    target_bytes: int,
    duration: float | None,
    source_height: int | None = None,
) -> Path | None:
    """Re-encode `source` so it fits `target_bytes`, or return None if hopeless."""
    plan = plan_shrink(target_bytes, duration)
    if plan is None:
        return None
    video_bitrate, max_height = plan
    if source_height:
        max_height = min(max_height, source_height)

    code, _, stderr = await _run(
        "ffmpeg", "-nostdin", "-y",
        "-i", str(source),
        # Keep the frame even-sized; libx264 requires it.
        "-vf", f"scale=-2:'min({max_height},ih)':flags=bicubic",
        "-codec:v", "libx264",
        "-preset", "veryfast",
        "-profile:v", "main",
        "-pix_fmt", "yuv420p",
        "-b:v", str(video_bitrate),
        "-maxrate", str(int(video_bitrate * 1.4)),
        "-bufsize", str(int(video_bitrate * 2)),
        "-codec:a", "aac",
        "-b:a", str(AUDIO_BITRATE_FOR_SHRINK),
        "-movflags", "+faststart",
        str(destination),
    )
    if code != 0 or not destination.exists() or destination.stat().st_size == 0:
        logger.warning("shrink failed for %s: %s", source.name,
                       stderr.decode("utf-8", "replace")[-400:])
        destination.unlink(missing_ok=True)
        return None
    if destination.stat().st_size > target_bytes:
        logger.info(
            "shrink overshot: %s bytes > %s target", destination.stat().st_size, target_bytes
        )
        destination.unlink(missing_ok=True)
        return None
    return destination


def _as_float(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def _as_int(value: object) -> int | None:
    try:
        result = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None
