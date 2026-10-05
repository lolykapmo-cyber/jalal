"""Retry ladders that get a download through without any login cookies.

Most "blocked" failures are not really about the account: the site dislikes
the client that asked. yt-dlp can present itself as a TV app, a phone app or
a real browser (TLS fingerprint included, via curl_cffi), and a path that
fails on one often succeeds on the next. Each platform therefore gets an
ordered ladder of attempts, cheapest and most reliable first.

Nothing here needs credentials. Deliberately so.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from .urls import host_of

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Strategy:
    """One attempt: a label plus the yt-dlp options it overlays."""

    label: str
    extractor_args: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    impersonate: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def apply_to(self, options: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of `options` with this strategy layered on top."""
        merged = dict(options)

        if self.extractor_args:
            combined = {
                key: dict(value)
                for key, value in (merged.get("extractor_args") or {}).items()
            }
            for extractor, args in self.extractor_args.items():
                combined.setdefault(extractor, {}).update(args)
            merged["extractor_args"] = combined

        if self.impersonate:
            merged["impersonate"] = _impersonate_target(self.impersonate)

        merged.update(self.extra)
        return merged


def _impersonate_target(spec: str):
    """Parse a target like 'chrome' or 'safari-17.2:ios' for yt-dlp."""
    from yt_dlp.networking.impersonate import ImpersonateTarget

    return ImpersonateTarget.from_str(spec)


@lru_cache(maxsize=1)
def impersonation_available() -> bool:
    """True when curl_cffi is installed, so TLS fingerprints can be faked."""
    try:
        from yt_dlp import YoutubeDL

        with YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            return bool(ydl._get_available_impersonate_targets())
    except Exception:  # noqa: BLE001 - an old yt-dlp or missing extra
        logger.debug("impersonation probe failed", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Ladders
#
# YouTube: the TV and embedded-device clients are the ones that still serve
# full formats without a signed-in session. The browser clients come last
# because they are the ones that ask for a bot check.
# ---------------------------------------------------------------------------

_YOUTUBE_LADDER: tuple[Strategy, ...] = (
    # yt-dlp's own client selection goes first. It is maintained against
    # YouTube continuously and knows which clients currently work and what a
    # PO token provider changes; a hardcoded list here is a snapshot of one
    # day's assumptions and ages badly. Pinning player_client overrides that
    # judgement, so the entries below are a fallback for when the maintained
    # default is itself the thing that broke.
    Strategy("yt/default", {}),
    Strategy("yt/default+chrome", {}, impersonate="chrome"),
    Strategy("yt/tv", {"youtube": {"player_client": ["tv"]}}),
    Strategy("yt/tv_simply", {"youtube": {"player_client": ["tv_simply"]}}),
    Strategy("yt/android_vr", {"youtube": {"player_client": ["android_vr"]}}),
    Strategy("yt/ios", {"youtube": {"player_client": ["ios"]}}),
    Strategy(
        "yt/web_safari+chrome",
        {"youtube": {"player_client": ["web_safari"]}},
        impersonate="safari",
    ),
)

# Instagram and Facebook gate hardest on the TLS fingerprint, so a real
# browser impersonation is the first thing worth trying.
_META_LADDER: tuple[Strategy, ...] = (
    Strategy("meta/chrome", impersonate="chrome"),
    Strategy("meta/safari", impersonate="safari"),
    Strategy("meta/default"),
)

_TIKTOK_LADDER: tuple[Strategy, ...] = (
    Strategy("tiktok/default"),
    Strategy("tiktok/chrome", impersonate="chrome"),
    Strategy(
        "tiktok/web",
        {"tiktok": {"api_hostname": ["api22-normal-c-useast2a.tiktokv.com"]}},
        impersonate="chrome",
    ),
)

_X_LADDER: tuple[Strategy, ...] = (
    Strategy("x/syndication", {"twitter": {"api": ["syndication"]}}),
    Strategy("x/graphql", {"twitter": {"api": ["graphql"]}}, impersonate="chrome"),
    Strategy("x/default"),
)

_GENERIC_LADDER: tuple[Strategy, ...] = (
    Strategy("default"),
    Strategy("chrome", impersonate="chrome"),
    Strategy("firefox", impersonate="firefox"),
)

# Hostname suffix -> ladder.
_LADDERS: tuple[tuple[tuple[str, ...], tuple[Strategy, ...]], ...] = (
    (("youtube.com", "youtu.be", "youtube-nocookie.com"), _YOUTUBE_LADDER),
    (("instagram.com", "facebook.com", "fb.watch", "threads.net", "threads.com"), _META_LADDER),
    (("tiktok.com",), _TIKTOK_LADDER),
    (("twitter.com", "x.com"), _X_LADDER),
)


def ladder_for(url: str) -> tuple[Strategy, ...]:
    """The ordered attempts to make for this URL.

    Strategies that need impersonation are dropped when curl_cffi is absent,
    so the ladder degrades instead of erroring.
    """
    host = host_of(url)
    chosen = _GENERIC_LADDER
    for suffixes, ladder in _LADDERS:
        if any(host == suffix or host.endswith(f".{suffix}") for suffix in suffixes):
            chosen = ladder
            break

    if impersonation_available():
        return chosen

    usable = tuple(step for step in chosen if step.impersonate is None)
    # Never hand back an empty ladder: one plain attempt is always possible.
    return usable or (Strategy("default"),)


# Failures worth retrying on a different client. Anything else (a deleted
# video, a private account) will fail identically however we ask.
RETRYABLE_FAILURES = frozenset(
    {"err_login", "err_no_formats", "err_network", "err_generic"}
)


def is_retryable(failure_key: str) -> bool:
    return failure_key in RETRYABLE_FAILURES
