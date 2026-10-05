"""A Telegram bot that downloads videos from social media links."""

from __future__ import annotations

import sys

__version__ = "1.1.0"

# yt-dlp, python-telegram-bot and curl_cffi all require this. Checking here
# — the package root, imported before anything else — turns an obscure
# ImportError from a transitive dependency into an actionable sentence.
MINIMUM_PYTHON = (3, 10)

if sys.version_info < MINIMUM_PYTHON:  # pragma: no cover - depends on the host
    _needed = ".".join(str(part) for part in MINIMUM_PYTHON)
    _found = ".".join(str(part) for part in sys.version_info[:3])
    raise SystemExit(
        f"This bot needs Python {_needed} or newer, but this is Python {_found}.\n"
        "Older Pythons resolve yt-dlp to a 2024 release that current sites "
        "reject.\n"
        "On Ubuntu 20.04, deploy.sh installs a newer Python for you:\n"
        "    sudo bash deploy.sh"
    )
