"""Build the Telegram application and register every handler."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from telegram import Update
from telegram.ext import (
    AIORateLimiter,
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from . import services
from .config import Settings
from .inflight import InFlight
from .jobs import JobRegistry
from .membership import MembershipGate, parse_channels
from .storage import Storage
from .throttle import Throttle
from .handlers import commands, download, errors, keyboards

logger = logging.getLogger(__name__)

# Uploads are the slow part, so they get a much longer write budget than
# ordinary API calls.
API_READ_TIMEOUT = 60.0
API_WRITE_TIMEOUT = 120.0
API_CONNECT_TIMEOUT = 30.0
MEDIA_WRITE_TIMEOUT = 1800.0


def build_application(settings: Settings) -> Application:
    """Wire storage, limits and handlers into a ready-to-run Application."""
    storage = Storage(
        settings.database_path,
        default_language=settings.default_language,
        default_quality=settings.default_quality,
        default_ask_quality=settings.ask_quality,
    )
    container = services.Services(
        settings=settings,
        storage=storage,
        throttle=Throttle(
            max_global=settings.max_concurrent_downloads,
            max_per_user=settings.max_user_downloads,
            cooldown_seconds=settings.cooldown_seconds,
        ),
        jobs=JobRegistry(),
        gate=MembershipGate(
            parse_channels(settings.required_channels),
            cache_seconds=settings.membership_cache_seconds,
            fail_open=settings.membership_fail_open,
        ),
        inflight=InFlight(),
    )

    builder = (
        ApplicationBuilder()
        .token(settings.token)
        .base_url(settings.api_base_url)
        .base_file_url(settings.api_file_base_url)
        # Without this, a long download would block /cancel.
        .concurrent_updates(True)
        .read_timeout(API_READ_TIMEOUT)
        .write_timeout(API_WRITE_TIMEOUT)
        .connect_timeout(API_CONNECT_TIMEOUT)
        .media_write_timeout(MEDIA_WRITE_TIMEOUT)
        .rate_limiter(AIORateLimiter())
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
    )
    if settings.local_mode:
        builder = builder.local_mode(True)

    application = builder.build()
    services.attach(application, container)
    _register(application)
    return application


def _register(application: Application) -> None:
    """Order matters: commands and callbacks before the catch-all link handler."""
    application.add_handler(CommandHandler("start", commands.start))
    application.add_handler(CommandHandler(["help", "h"], commands.help_command))
    application.add_handler(CommandHandler("settings", commands.settings_command))
    application.add_handler(CommandHandler("lang", commands.lang_command))
    application.add_handler(CommandHandler("quality", commands.quality_command))
    application.add_handler(CommandHandler("stats", commands.stats_command))
    application.add_handler(CommandHandler("cancel", download.cancel_command))

    application.add_handler(
        CallbackQueryHandler(download.on_quality_chosen, pattern=r"^q\|")
    )
    application.add_handler(CallbackQueryHandler(download.on_dismiss, pattern=r"^d\|"))
    application.add_handler(
        CallbackQueryHandler(
            download.on_join_verify, pattern=f"^{keyboards.JOIN_VERIFY}$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            download.on_cancel_button, pattern=f"^{keyboards.CANCEL_JOB}$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            commands.on_settings_language, pattern=f"^{keyboards.SETTINGS_LANG}$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            commands.on_settings_ask, pattern=f"^{keyboards.SETTINGS_ASK}$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            commands.on_settings_quality, pattern=f"^{keyboards.SETTINGS_QUALITY}$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(commands.on_set_quality, pattern=r"^su\|")
    )

    # Channel membership changes, so leaving revokes access immediately.
    application.add_handler(
        ChatMemberHandler(download.on_chat_member, ChatMemberHandler.CHAT_MEMBER)
    )

    application.add_handler(MessageHandler(filters.Document.ALL, commands.on_document))

    # Anything else with text: look for links in it.
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & ~filters.COMMAND, download.handle_link
        )
    )

    application.add_error_handler(errors.on_error)


def _require_writable(path: Path, label: str) -> None:
    """Fail with an actionable sentence rather than an OSError traceback."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(
            f"Cannot create the {label} at {path}: {exc}\n"
            "Point it at an absolute path this service can write to. Under "
            "systemd with ProtectSystem=strict the project directory is "
            "read-only, so use somewhere like /tmp/jalal-downloads and list "
            "any other writable location in ReadWritePaths."
        ) from exc
    if not os.access(path, os.W_OK):
        raise SystemExit(
            f"The {label} at {path} exists but this user cannot write to it."
        )


def _sweep_stale_jobs(work_dir: Path) -> int:
    """Delete job directories left behind by an unclean shutdown."""
    removed = 0
    try:
        entries = list(work_dir.glob("job-*"))
    except OSError:
        return 0
    for entry in entries:
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
    return removed


async def _post_init(application: Application) -> None:
    container = application.bot_data[services.BOT_DATA_KEY]
    settings: Settings = container.settings

    _require_writable(settings.work_dir, "download directory (WORK_DIR)")

    # Nothing is running yet, so every job directory here is debris from a
    # kill -9 or a power cut. Left alone it would fill the disk over time.
    swept = _sweep_stale_jobs(settings.work_dir)
    if swept:
        logger.info("removed %s leftover download director%s",
                    swept, "y" if swept == 1 else "ies")
    _require_writable(settings.database_path.parent, "data directory (DATABASE_PATH)")

    await container.storage.open()

    pruned = await container.storage.cache_prune(ttl_hours=settings.cache_ttl_hours)
    if pruned:
        logger.info("pruned %s expired cache entries", pruned)

    try:
        await application.bot.set_my_commands(
            commands.command_list(settings.default_language)
        )
    except Exception:  # noqa: BLE001 - cosmetic
        logger.debug("set_my_commands failed", exc_info=True)

    if container.gate.enabled:
        logger.info(
            "subscription required for: %s",
            ", ".join(channel.chat_id for channel in container.gate.channels),
        )
        logger.info(
            "the bot must be an administrator of each, or the check cannot "
            "be answered (currently fail-%s)",
            "open" if settings.membership_fail_open else "closed",
        )

    me = application.bot
    logger.info(
        "ready as @%s | upload limit %s MB | workers %s | allow-list %s",
        me.username,
        settings.upload_limit_mb,
        settings.max_concurrent_downloads,
        len(settings.allowed_users) or "open",
    )


async def _post_shutdown(application: Application) -> None:
    container = application.bot_data.get(services.BOT_DATA_KEY)
    if container is None:
        return
    stopped = container.jobs.cancel_all()
    if stopped:
        logger.info("cancelled %s in-flight download(s)", stopped)
    await container.storage.close()


def run(settings: Settings) -> None:
    """Start long polling and block until the process is interrupted."""
    application = build_application(settings)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
