"""Entry point: `python -m bot`."""

from __future__ import annotations

import logging
import sys

from .app import run
from .config import ConfigError, load_settings
from .media import ffmpeg_available

logger = logging.getLogger("bot")


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)-22s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=getattr(logging, level, logging.INFO),
    )
    # httpx logs every API call at INFO, which drowns out everything else.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.Updater").setLevel(logging.WARNING)


def main() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # python-dotenv is optional
        pass

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    _configure_logging(settings.log_level)

    if not ffmpeg_available():
        logger.warning(
            "ffmpeg/ffprobe not found: merging, thumbnails, MP3 extraction and "
            "shrinking oversized files will all be unavailable"
        )

    try:
        run(settings)
    except KeyboardInterrupt:
        logger.info("interrupted; shutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
