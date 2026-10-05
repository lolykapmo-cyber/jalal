"""Small formatting helpers shared across modules."""

from __future__ import annotations

import html
import re
import unicodedata

_UNITS = ("B", "KB", "MB", "GB", "TB")


def human_size(num_bytes: float | None) -> str:
    """Render a byte count the way a download client would."""
    if not num_bytes or num_bytes < 0:
        return "—"
    value = float(num_bytes)
    for unit in _UNITS:
        if value < 1024 or unit == _UNITS[-1]:
            precision = 0 if unit == "B" or value >= 100 else 1
            return f"{value:.{precision}f} {unit}"
        value /= 1024
    return f"{value:.1f} {_UNITS[-1]}"


def human_duration(seconds: float | None) -> str:
    """Format seconds as H:MM:SS, dropping the hour when it is zero."""
    if seconds is None or seconds < 0:
        return "—"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def human_speed(bytes_per_second: float | None) -> str:
    if not bytes_per_second or bytes_per_second <= 0:
        return "—"
    return f"{human_size(bytes_per_second)}/s"


def progress_bar(fraction: float | None, width: int = 12) -> str:
    """A text bar; an unknown fraction renders as an empty track."""
    if fraction is None:
        return "░" * width
    clamped = min(1.0, max(0.0, fraction))
    filled = int(round(clamped * width))
    return "█" * filled + "░" * (width - filled)


def escape(text: str | None) -> str:
    """Escape for Telegram's HTML parse mode."""
    return html.escape(text or "", quote=False)


def shorten(text: str | None, limit: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def safe_filename(name: str, fallback: str = "video", limit: int = 80) -> str:
    """Strip anything a filesystem or Telegram client might choke on."""
    normalized = unicodedata.normalize("NFKC", name or "")
    normalized = "".join(
        ch for ch in normalized if ch.isprintable() and unicodedata.category(ch) != "Cc"
    )
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", normalized)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        return fallback
    return cleaned[:limit].strip(" .") or fallback
