"""Finding links in a message and naming the platform behind them."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

_URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>\"'`\\]+", re.IGNORECASE)

# Trailing characters that are far more likely to be sentence punctuation
# than part of the link itself.
_TRAILING_JUNK = ".,;:!?،؛؟»«'\"`"

# Hostname suffix -> display name. Checked longest-first so that, say,
# "music.youtube.com" wins over "youtube.com".
_PLATFORMS: dict[str, str] = {
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "music.youtube.com": "YouTube Music",
    "tiktok.com": "TikTok",
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "fb.watch": "Facebook",
    "twitter.com": "X / Twitter",
    "x.com": "X / Twitter",
    "reddit.com": "Reddit",
    "redd.it": "Reddit",
    "snapchat.com": "Snapchat",
    "pinterest.com": "Pinterest",
    "pin.it": "Pinterest",
    "linkedin.com": "LinkedIn",
    "tumblr.com": "Tumblr",
    "vimeo.com": "Vimeo",
    "dailymotion.com": "Dailymotion",
    "twitch.tv": "Twitch",
    "soundcloud.com": "SoundCloud",
    "bilibili.com": "Bilibili",
    "vk.com": "VK",
    "ok.ru": "OK.ru",
    "t.me": "Telegram",
    "threads.net": "Threads",
    "threads.com": "Threads",
    "kick.com": "Kick",
    "rumble.com": "Rumble",
    "odysee.com": "Odysee",
    "9gag.com": "9GAG",
    "imgur.com": "Imgur",
    "likee.video": "Likee",
    "shahid.net": "Shahid",
    "weibo.com": "Weibo",
}


def normalize(url: str) -> str:
    """Trim sentence punctuation and give bare `www.` links a scheme."""
    cleaned = url.strip().rstrip(_TRAILING_JUNK)

    # Keep a closing bracket only when the link actually opened one.
    while cleaned and cleaned[-1] in ")]}":
        opener = {")": "(", "]": "[", "}": "{"}[cleaned[-1]]
        if cleaned.count(opener) >= cleaned.count(cleaned[-1]):
            break
        cleaned = cleaned[:-1].rstrip(_TRAILING_JUNK)

    if cleaned.lower().startswith("www."):
        cleaned = f"https://{cleaned}"
    return cleaned


def extract_urls(text: str | None, limit: int = 10) -> list[str]:
    """Pull every distinct http(s) link out of a message, in order."""
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in _URL_PATTERN.finditer(text):
        url = normalize(match.group(0))
        if len(url) < 11 or not host_of(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
        if len(found) >= limit:
            break
    return found


def host_of(url: str) -> str:
    """The lower-case hostname, without a `www.` prefix or port."""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def platform_name(url: str) -> str:
    """A human-readable platform name, falling back to the hostname."""
    host = host_of(url)
    if not host:
        return "—"
    for suffix in sorted(_PLATFORMS, key=len, reverse=True):
        if host == suffix or host.endswith(f".{suffix}"):
            return _PLATFORMS[suffix]
    return host


def is_known_platform(url: str) -> bool:
    """True for hosts in the table above; yt-dlp supports many more."""
    host = host_of(url)
    return any(
        host == suffix or host.endswith(f".{suffix}") for suffix in _PLATFORMS
    )
