"""yt-dlp wrapper: format selection, cancellation and friendly errors."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .strategies import Strategy, is_retryable, ladder_for

logger = logging.getLogger(__name__)

# Quality key -> maximum height. `best` and `audio` are handled separately.
QUALITY_HEIGHTS: dict[str, int | None] = {
    "best": None,
    "1080": 1080,
    "720": 720,
    "480": 480,
    "360": 360,
    "audio": None,
}

QUALITY_CHOICES = tuple(QUALITY_HEIGHTS)

# Heights offered in the keyboard, coarse to fine.
OFFERED_HEIGHTS = (1080, 720, 480, 360)

_MEDIA_SUFFIXES = {
    ".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".ts",
    ".mp3", ".m4a", ".opus", ".ogg", ".aac", ".wav", ".flac",
}

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Matched against the lower-cased error text, first hit wins.
_ERROR_SIGNATURES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("err_login", (
        "sign in to confirm", "sign in to view", "log in", "login required",
        "requires authentication", "use --cookies", "cookies", "rate-limit reached",
        "account is required", "confirm your age",
    )),
    ("err_private", ("private video", "is private", "private account", "protected")),
    ("err_geo", (
        # yt-dlp phrases this several ways, e.g. "The uploader has not made
        # this video available in your country", so match the common tail.
        "available in your country", "available in your location",
        "available in your region", "geo restricted", "geo-restricted",
        "blocked in your country", "blocked it in your country",
        "not available in your area",
    )),
    ("err_live", (
        "is live", "live event will begin", "live stream has not", "premieres in",
        "this live event",
    )),
    ("err_unavailable", (
        "video unavailable", "no longer available", "has been removed",
        "has been deleted", "does not exist", "not found", "404",
        "removed by the uploader", "terminated", "unable to find",
    )),
    ("err_no_formats", (
        "requested format is not available", "no video formats",
        "no formats found", "no media found",
    )),
    ("err_unsupported", (
        "unsupported url", "no suitable extractor", "is not a valid url",
        "unable to extract", "does not look like",
    )),
    ("err_network", (
        "urlopen error", "timed out", "temporary failure in name resolution",
        "connection reset", "connection refused", "network is unreachable",
        "read timed out", "remote end closed", "failed to resolve",
        "name or service not known", "getaddrinfo", "transporterror",
        "unable to download webpage", "no address associated",
        "503", "502", "bad gateway", "service unavailable",
    )),
)


class DownloadCancelled(Exception):
    """Raised from the progress hook to unwind a running download."""


class DownloadFailure(Exception):
    """A failure with an i18n key, ready to show the user."""

    def __init__(self, key: str, **params: Any) -> None:
        super().__init__(key)
        self.key = key
        self.params = params


class CancelToken:
    """A flag the progress hook polls so a thread-bound download can stop."""

    __slots__ = ("_cancelled",)

    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def raise_if_cancelled(self) -> None:
        if self._cancelled:
            raise DownloadCancelled


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    title: str
    uploader: str
    duration: float | None
    width: int | None
    height: int | None
    is_audio: bool
    webpage_url: str
    extractor: str
    video_id: str
    strategy: str = "default"


def format_selector(quality: str) -> str:
    """Build a yt-dlp format expression for a quality key."""
    if quality == "audio":
        return "bestaudio/best"
    height = QUALITY_HEIGHTS.get(quality)
    if height is None:
        return "bestvideo*+bestaudio/best"
    return (
        f"bestvideo*[height<={height}]+bestaudio/"
        f"best[height<={height}]/"
        "bestvideo*+bestaudio/best"
    )


def build_options(
    *,
    quality: str,
    dest_dir: Path,
    cookies_file: Path | None,
    proxy: str | None,
    max_playlist_items: int,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Assemble the yt-dlp options dict for one job."""
    options: dict[str, Any] = {
        "format": format_selector(quality),
        # The id keeps the name short and free of characters that upset
        # filesystems; the pretty title goes in the caption instead.
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "paths": {"home": str(dest_dir)},
        "restrictfilenames": True,
        "windowsfilenames": True,
        "noplaylist": max_playlist_items <= 1,
        "playlist_items": f"1:{max_playlist_items}",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "no_color": True,
        "ignoreerrors": False,
        "retries": 3,
        "fragment_retries": 5,
        "extractor_retries": 2,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
        # Telegram's player is happiest with H.264/AAC in MP4.
        "format_sort": ["res", "vcodec:h264", "acodec:aac", "ext:mp4:m4a"],
        "merge_output_format": "mp4",
        "overwrites": True,
        "postprocessors": [],
    }

    if quality == "audio":
        options["format_sort"] = ["acodec:aac", "abr", "ext:m4a"]
        options.pop("merge_output_format", None)
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {"key": "FFmpegMetadata", "add_metadata": True},
        ]

    if progress_hook is not None:
        options["progress_hooks"] = [progress_hook]
    if cookies_file and cookies_file.exists():
        options["cookiefile"] = str(cookies_file)
    if proxy:
        options["proxy"] = proxy
    return options


def first_entry(info: dict[str, Any]) -> dict[str, Any]:
    """Collapse a playlist result down to the single item we downloaded."""
    current = info
    seen = 0
    while isinstance(current, dict) and current.get("entries") is not None:
        entries = current["entries"]
        if not isinstance(entries, list):
            entries = list(entries)
        entries = [entry for entry in entries if entry]
        if not entries:
            raise DownloadFailure("err_no_formats")
        current = entries[0]
        seen += 1
        if seen > 4:  # guard against a pathological nesting
            break
    if not isinstance(current, dict):
        raise DownloadFailure("err_no_formats")
    return current


def available_heights(info: dict[str, Any]) -> list[int]:
    """Heights the site actually offers, descending, for the keyboard."""
    heights: set[int] = set()
    for fmt in info.get("formats") or ():
        if not isinstance(fmt, dict):
            continue
        if fmt.get("vcodec") in (None, "none"):
            continue
        height = fmt.get("height")
        if isinstance(height, int) and height > 0:
            heights.add(height)
    if not heights:
        height = info.get("height")
        if isinstance(height, int) and height > 0:
            heights.add(height)
    return sorted(heights, reverse=True)


def offered_qualities(info: dict[str, Any]) -> list[int]:
    """Intersect what we offer with what exists, keeping at least one rung."""
    heights = available_heights(info)
    if not heights:
        return []
    tallest = heights[0]
    return [h for h in OFFERED_HEIGHTS if h <= tallest]


def is_live(info: dict[str, Any]) -> bool:
    return bool(info.get("is_live")) or info.get("live_status") in {
        "is_live", "is_upcoming", "post_live",
    }


def describe(info: dict[str, Any]) -> tuple[str, str, float | None]:
    """Title, uploader and duration, with reasonable fallbacks."""
    title = (
        info.get("title")
        or info.get("fulltitle")
        or info.get("description")
        or info.get("id")
        or "video"
    )
    uploader = (
        info.get("uploader")
        or info.get("channel")
        or info.get("creator")
        or info.get("uploader_id")
        or info.get("extractor_key")
        or "—"
    )
    duration = info.get("duration")
    if not isinstance(duration, (int, float)) or duration <= 0:
        duration = None
    return str(title).strip(), str(uploader).strip(), duration


def cache_key(info: dict[str, Any], quality: str) -> str:
    """A stable key for the upload cache: extractor + id + requested quality."""
    extractor = str(info.get("extractor") or info.get("extractor_key") or "generic")
    video_id = str(info.get("id") or info.get("webpage_url") or "")
    return f"{extractor.lower()}:{video_id}:{quality}"


def resolve_output(info: dict[str, Any], dest_dir: Path) -> Path:
    """Find the file yt-dlp just wrote, after any post-processing."""
    candidates: list[Path] = []

    for download in info.get("requested_downloads") or ():
        if isinstance(download, dict):
            for field in ("filepath", "_filename", "filename"):
                value = download.get(field)
                if value:
                    candidates.append(Path(value))

    for field in ("filepath", "_filename"):
        value = info.get(field)
        if value:
            candidates.append(Path(value))

    for candidate in candidates:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
        # A post-processor may have changed the extension under us.
        sibling = _sibling_with_media_suffix(candidate)
        if sibling is not None:
            return sibling

    # Last resort: the biggest media file in this job's private directory.
    found = [
        path
        for path in dest_dir.glob("*")
        if path.is_file()
        and path.suffix.lower() in _MEDIA_SUFFIXES
        and path.stat().st_size > 0
    ]
    if found:
        return max(found, key=lambda path: path.stat().st_size)

    raise DownloadFailure("err_no_formats")


def _sibling_with_media_suffix(candidate: Path) -> Path | None:
    parent = candidate.parent
    if not parent.is_dir():
        return None
    matches = [
        path
        for path in parent.glob(f"{glob_escape(candidate.stem)}.*")
        if path.is_file()
        and path.suffix.lower() in _MEDIA_SUFFIXES
        and path.stat().st_size > 0
    ]
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_size)


def glob_escape(text: str) -> str:
    """Escape glob metacharacters in a literal filename stem."""
    return re.sub(r"([*?\[\]])", r"[\1]", text)


def clean_error(message: str, limit: int = 220) -> str:
    """Turn a raw yt-dlp error into something fit for a chat bubble."""
    text = _ANSI.sub("", message or "").strip()
    text = re.sub(r"^ERROR:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\[[^\]]+\]\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text or "unknown error"


def classify_error(message: str, *, hints: Iterable[str] = ()) -> DownloadFailure:
    """Map an error message onto a user-facing i18n key."""
    haystack = " ".join([message or "", *hints]).lower()
    for key, signatures in _ERROR_SIGNATURES:
        if any(signature in haystack for signature in signatures):
            return DownloadFailure(key)
    return DownloadFailure("err_generic", reason=clean_error(message))


# --------------------------------------------------------------------------
# Async entry points.
#
# yt-dlp is synchronous, so every call runs in a worker thread; cancellation
# reaches it through the progress hook. Each call walks the URL's strategy
# ladder (see strategies.py): if a site rejects one client, the next one is
# tried, which is what replaces needing login cookies.
# --------------------------------------------------------------------------

# Bounds the worst case when every rung fails: a blocked link should report
# back in a reasonable time rather than grinding through every option.
DEFAULT_MAX_ATTEMPTS = 4


def _probe_options(
    *, cookies_file: Path | None, proxy: str | None, max_playlist_items: int
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "noprogress": True,
        "noplaylist": max_playlist_items <= 1,
        "playlist_items": "1:1",
        "skip_download": True,
        "socket_timeout": 30,
        "extractor_retries": 2,
        "retries": 2,
    }
    if cookies_file and cookies_file.exists():
        options["cookiefile"] = str(cookies_file)
    if proxy:
        options["proxy"] = proxy
    return options


def _extract(url: str, options: dict[str, Any], *, download: bool) -> dict[str, Any]:
    """Blocking yt-dlp call; must run off the event loop."""
    import yt_dlp  # imported lazily so the module stays importable without it

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=download)
    if not isinstance(info, dict):
        raise DownloadFailure("err_no_formats")
    return info


def _translate(exc: BaseException, url: str) -> DownloadFailure:
    """Convert any yt-dlp exception into a DownloadFailure."""
    if isinstance(exc, DownloadFailure):
        return exc

    from yt_dlp.utils import (
        DownloadError,
        ExtractorError,
        GeoRestrictedError,
        UnsupportedError,
    )

    if isinstance(exc, UnsupportedError):
        return DownloadFailure("err_unsupported")
    if isinstance(exc, GeoRestrictedError):
        return DownloadFailure("err_geo")
    if isinstance(exc, (DownloadError, ExtractorError)):
        return classify_error(str(exc), hints=(url,))
    return classify_error(str(exc) or exc.__class__.__name__, hints=(url,))


def _attempts(url: str, max_attempts: int) -> tuple[Strategy, ...]:
    ladder = ladder_for(url)
    return ladder[: max(1, max_attempts)]


async def probe_url(
    url: str,
    *,
    cookies_file: Path | None = None,
    proxy: str | None = None,
    max_playlist_items: int = 1,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, Any]:
    """Look up metadata without downloading, walking the strategy ladder."""
    base = _probe_options(
        cookies_file=cookies_file, proxy=proxy, max_playlist_items=max_playlist_items
    )
    attempts = _attempts(url, max_attempts)
    last: DownloadFailure | None = None

    for index, strategy in enumerate(attempts, start=1):
        try:
            info = await asyncio.to_thread(
                _extract, url, strategy.apply_to(base), download=False
            )
        except Exception as exc:  # noqa: BLE001 - every failure becomes a message
            failure = _translate(exc, url)
            last = failure
            if not is_retryable(failure.key) or index == len(attempts):
                raise failure from exc
            logger.info(
                "probe %s/%s via %s failed (%s); trying the next client",
                index, len(attempts), strategy.label, failure.key,
            )
            continue

        entry = first_entry(info)
        entry["_strategy"] = strategy.label
        if index > 1:
            logger.info("probe succeeded via %s on attempt %s", strategy.label, index)
        return entry

    raise last or DownloadFailure("err_no_formats")


async def run_download(
    url: str,
    *,
    quality: str,
    dest_dir: Path,
    cookies_file: Path | None = None,
    proxy: str | None = None,
    max_playlist_items: int = 1,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
    cancel_token: CancelToken | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> DownloadResult:
    """Download `url` into `dest_dir`, retrying with a different client on a block."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    def hook(status: dict[str, Any]) -> None:
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        if progress_hook is not None:
            try:
                progress_hook(status)
            except DownloadCancelled:
                raise
            except Exception:  # noqa: BLE001 - never let the UI kill a download
                logger.debug("progress hook raised", exc_info=True)

    attempts = _attempts(url, max_attempts)
    last: DownloadFailure | None = None

    for index, strategy in enumerate(attempts, start=1):
        # Each attempt gets its own directory, so a half-written file from a
        # failed client can never be mistaken for the finished download.
        attempt_dir = dest_dir / f"try{index}"
        attempt_dir.mkdir(parents=True, exist_ok=True)

        options = strategy.apply_to(
            build_options(
                quality=quality,
                dest_dir=attempt_dir,
                cookies_file=cookies_file,
                proxy=proxy,
                max_playlist_items=max_playlist_items,
                progress_hook=hook,
            )
        )

        try:
            info = await asyncio.to_thread(_extract, url, options, download=True)
        except DownloadCancelled:
            raise
        except Exception as exc:  # noqa: BLE001
            # A cancel surfaces as yt-dlp's own DownloadError wrapping ours.
            if cancel_token is not None and cancel_token.cancelled:
                raise DownloadCancelled from exc

            failure = _translate(exc, url)
            last = failure
            await asyncio.to_thread(shutil.rmtree, attempt_dir, True)

            if not is_retryable(failure.key) or index == len(attempts):
                raise failure from exc
            logger.info(
                "download %s/%s via %s failed (%s); trying the next client",
                index, len(attempts), strategy.label, failure.key,
            )
            continue

        entry = first_entry(info)
        path = resolve_output(entry, attempt_dir)
        title, uploader, duration = describe(entry)
        is_audio = quality == "audio"

        if index > 1:
            logger.info("download succeeded via %s on attempt %s", strategy.label, index)

        return DownloadResult(
            path=path,
            title=title,
            uploader=uploader,
            duration=duration,
            width=entry.get("width") if not is_audio else None,
            height=entry.get("height") if not is_audio else None,
            is_audio=is_audio,
            webpage_url=str(entry.get("webpage_url") or url),
            extractor=str(entry.get("extractor") or entry.get("extractor_key") or "generic"),
            video_id=str(entry.get("id") or ""),
            strategy=strategy.label,
        )

    raise last or DownloadFailure("err_no_formats")
