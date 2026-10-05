"""The download pipeline: link -> quality -> fetch -> fit -> upload."""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from telegram import InputFile, Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from .. import media, services
from ..downloader import (
    DownloadCancelled,
    DownloadFailure,
    DownloadResult,
    CancelToken,
    cache_key,
    describe,
    is_live,
    offered_qualities,
    probe_url,
    run_download,
)
from ..i18n import t
from ..progress import ProgressReporter
from ..storage import UserPrefs
from ..throttle import Cooldown, UserBusy
from ..urls import extract_urls, platform_name
from ..utils import escape, human_duration, human_size, safe_filename, shorten
from . import keyboards

logger = logging.getLogger(__name__)

# One message can only kick off so many jobs before it's abuse.
MAX_LINKS_PER_MESSAGE = 5

# Telegram truncates captions beyond this.
CAPTION_LIMIT = 1024

# Generous, because a slow upstream plus a 2 GB upload is a long wait.
UPLOAD_READ_TIMEOUT = 180.0
UPLOAD_WRITE_TIMEOUT = 1800.0


async def guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> UserPrefs | None:
    """Resolve the user's prefs, or refuse them if they're not allowed."""
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return None

    svc = services.of(context)
    prefs = await svc.storage.get_user(user.id, language_hint=_language_hint(user))

    if not svc.settings.may_use_bot(user.id):
        await message.reply_text(
            t(prefs.language, "not_allowed"), parse_mode=ParseMode.HTML
        )
        logger.info("rejected user %s (not on allow-list)", user.id)
        return None
    return prefs


def _language_hint(user: Any) -> str | None:
    from ..i18n import normalize_language

    code = getattr(user, "language_code", None)
    return normalize_language(code) if code else None


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for any plain message that might carry a link."""
    prefs = await guard(update, context)
    if prefs is None:
        return

    message = update.effective_message
    assert message is not None

    urls = extract_urls(message.text or message.caption)
    if not urls:
        await message.reply_text(t(prefs.language, "no_url"), parse_mode=ParseMode.HTML)
        return

    for url in urls[:MAX_LINKS_PER_MESSAGE]:
        if prefs.ask_quality:
            await _offer_qualities(update, context, url, prefs)
        else:
            placeholder = await message.reply_text(
                t(prefs.language, "fetching"), parse_mode=ParseMode.HTML
            )
            await _spawn_job(context, placeholder, url, prefs.quality, prefs)


async def _offer_qualities(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    url: str,
    prefs: UserPrefs,
) -> None:
    """Probe the link, then show what qualities it actually has."""
    message = update.effective_message
    assert message is not None
    svc = services.of(context)

    placeholder = await message.reply_text(
        t(prefs.language, "fetching"), parse_mode=ParseMode.HTML
    )

    try:
        info = await probe_url(
            url,
            cookies_file=svc.settings.cookies_file,
            proxy=svc.settings.proxy,
            max_playlist_items=svc.settings.max_playlist_items,
            max_attempts=svc.settings.max_attempts,
        )
    except DownloadFailure as failure:
        await _show_failure(placeholder, prefs.language, failure)
        return
    except Exception:  # noqa: BLE001
        logger.exception("probe crashed for %s", url)
        await _edit(placeholder, t(prefs.language, "err_generic", reason="probe failed"))
        return

    if is_live(info):
        await _show_failure(placeholder, prefs.language, DownloadFailure("err_live"))
        return

    title, uploader, duration = describe(info)

    limit = svc.settings.max_duration_seconds
    if limit and duration and duration > limit:
        await _show_failure(
            placeholder,
            prefs.language,
            DownloadFailure(
                "err_too_long",
                duration=human_duration(duration),
                limit=human_duration(limit),
            ),
        )
        return

    heights = tuple(offered_qualities(info))
    token = svc.jobs.remember(url, title=title, heights=heights)

    await _edit(
        placeholder,
        t(
            prefs.language,
            "info_card",
            title=escape(shorten(title, 160)),
            platform=escape(platform_name(url)),
            uploader=escape(shorten(uploader, 60)),
            duration=human_duration(duration),
        ),
        reply_markup=keyboards.quality_keyboard(prefs.language, token, heights),
    )


async def on_quality_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """A tap on one of the quality buttons."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()

    prefs = await guard(update, context)
    if prefs is None:
        return

    svc = services.of(context)
    parts = query.data.split("|")
    if len(parts) != 3:
        return
    _, token, quality = parts

    choice = svc.jobs.recall(token)
    if choice is None:
        await _edit(query.message, t(prefs.language, "expired"))
        return

    await _spawn_job(context, query.message, choice.url, quality, prefs)


async def on_dismiss(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The user closed a quality prompt."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()

    svc = services.of(context)
    parts = query.data.split("|")
    if len(parts) == 2:
        svc.jobs.forget(parts[1])

    if query.message is not None:
        try:
            await query.message.delete()
        except TelegramError:
            user = update.effective_user
            language = (
                (await svc.storage.get_user(user.id)).language
                if user is not None
                else svc.settings.default_language
            )
            await _edit(query.message, t(language, "cancelled"))


async def on_cancel_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The cancel button next to a live progress message."""
    query = update.callback_query
    if query is None:
        return

    svc = services.of(context)
    user = update.effective_user
    if user is None:
        await query.answer()
        return

    prefs = await svc.storage.get_user(user.id)
    cancelled = svc.jobs.cancel(user.id)
    await query.answer(
        t(prefs.language, "cancelled" if cancelled else "nothing_to_cancel")
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cancel — stop whatever this user has running."""
    prefs = await guard(update, context)
    if prefs is None:
        return
    message = update.effective_message
    assert message is not None

    svc = services.of(context)
    cancelled = svc.jobs.cancel(prefs.user_id)
    await message.reply_text(
        t(prefs.language, "cancelled" if cancelled else "nothing_to_cancel"),
        parse_mode=ParseMode.HTML,
    )


# --------------------------------------------------------------------------
# Job plumbing
# --------------------------------------------------------------------------


async def _spawn_job(
    context: ContextTypes.DEFAULT_TYPE,
    status_message: Message | None,
    url: str,
    quality: str,
    prefs: UserPrefs,
) -> None:
    """Validate the fair-use limits, then run the job as a tracked task."""
    if status_message is None:
        return

    svc = services.of(context)
    user_id = prefs.user_id

    if svc.jobs.has_active(user_id):
        await _edit(status_message, t(prefs.language, "busy"))
        return

    try:
        svc.throttle.check_cooldown(user_id)
    except Cooldown as cooldown:
        await _edit(
            status_message,
            t(prefs.language, "cooldown", seconds=int(cooldown.remaining) + 1),
        )
        return

    cancel_token = CancelToken()
    task = context.application.create_task(
        _run_job(context, status_message, url, quality, prefs, cancel_token)
    )
    svc.jobs.register(user_id, task=task, cancel_token=cancel_token)
    task.add_done_callback(lambda done: svc.jobs.unregister(user_id, task=done))


async def _run_job(
    context: ContextTypes.DEFAULT_TYPE,
    status_message: Message,
    url: str,
    quality: str,
    prefs: UserPrefs,
    cancel_token: CancelToken,
) -> None:
    """Download, fit to the upload cap, and send. Always cleans up."""
    svc = services.of(context)
    language = prefs.language
    chat_id = status_message.chat_id
    key = None

    reporter = ProgressReporter(
        status_message, language, keyboard=keyboards.cancel_keyboard(language)
    )
    job_dir = svc.settings.work_dir / f"job-{uuid.uuid4().hex[:12]}"

    try:
        async with svc.throttle.user_slot(prefs.user_id):
            # A cached upload skips the network entirely.
            key = f"{_cache_namespace(url)}:{quality}"
            if await _try_cached(context, chat_id, status_message, key, language):
                return

            if svc.throttle.global_busy:
                reporter.set_stage("queued", position=svc.throttle.waiting + 1)
                await reporter.flush()

            async with svc.throttle.global_slot():
                reporter.set_stage("fetching")
                await reporter.start()

                result = await run_download(
                    url,
                    quality=quality,
                    dest_dir=job_dir,
                    cookies_file=svc.settings.cookies_file,
                    proxy=svc.settings.proxy,
                    max_playlist_items=svc.settings.max_playlist_items,
                    progress_hook=reporter.hook,
                    cancel_token=cancel_token,
                    max_attempts=svc.settings.max_attempts,
                )

                # Now that we know the real id, use the precise cache key.
                key = f"{result.extractor.lower()}:{result.video_id}:{quality}"

                reporter.set_stage("processing")
                await reporter.flush()

                payload = await _prepare_upload(
                    result, job_dir, svc.settings, reporter, language
                )

                reporter.set_stage("uploading")
                await reporter.flush()
                await reporter.stop()

                sent = await _upload(
                    context, chat_id, url, result, payload, language
                )

        await _finish(
            context, status_message, sent, key, result, language, prefs.user_id
        )

    except DownloadCancelled:
        await reporter.stop()
        await _edit(status_message, t(language, "cancelled"))
    except asyncio.CancelledError:
        await reporter.stop()
        await _edit(status_message, t(language, "cancelled"))
        raise
    except UserBusy:
        await reporter.stop()
        await _edit(status_message, t(language, "busy"))
    except DownloadFailure as failure:
        await reporter.stop()
        await _show_failure(status_message, language, failure)
    except media.MediaError as exc:
        await reporter.stop()
        logger.warning("ffmpeg failed for %s: %s", url, exc)
        await _edit(status_message, t(language, "err_generic", reason=escape(str(exc)[:200])))
    except TelegramError as exc:
        await reporter.stop()
        logger.warning("telegram rejected the upload for %s: %s", url, exc)
        await _edit(status_message, t(language, "err_generic", reason=escape(str(exc)[:200])))
    except Exception as exc:  # noqa: BLE001 - last line of defence
        await reporter.stop()
        logger.exception("job crashed for %s", url)
        await _edit(status_message, t(language, "err_generic", reason=escape(str(exc)[:200])))
    finally:
        await reporter.stop()
        await asyncio.to_thread(shutil.rmtree, job_dir, True)


def _cache_namespace(url: str) -> str:
    """A pre-download cache key; coarse, but enough for a repeat paste."""
    return f"url:{url}"


async def _try_cached(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    status_message: Message,
    key: str,
    language: str,
) -> bool:
    """Re-send a previously uploaded file by its file_id."""
    svc = services.of(context)
    cached = await svc.storage.cache_lookup(key, ttl_hours=svc.settings.cache_ttl_hours)
    if cached is None:
        return False

    try:
        if cached.kind == "audio":
            await context.bot.send_audio(chat_id, audio=cached.file_id)
        else:
            await context.bot.send_video(
                chat_id, video=cached.file_id, supports_streaming=True
            )
    except BadRequest as exc:
        # file_ids do expire; drop the row and download for real.
        logger.info("stale cache entry %s: %s", key, exc)
        await svc.storage.cache_forget(key)
        return False

    await svc.storage.bump("cache_hits")
    await _edit(status_message, t(language, "cached"))
    return True


@dataclass
class UploadPayload:
    """The file and metadata we're about to hand to Telegram."""

    path: Path
    thumbnail: Path | None
    duration: int | None
    width: int | None
    height: int | None
    is_audio: bool


async def _prepare_upload(
    result: DownloadResult,
    job_dir: Path,
    settings: Any,
    reporter: ProgressReporter,
    language: str,
) -> UploadPayload:
    """Probe the file, shrink it if Telegram would refuse it, make a thumb."""
    path = result.path
    duration = result.duration
    width, height = result.width, result.height

    probe: media.MediaProbe | None = None
    if media.ffmpeg_available():
        try:
            probe = await media.probe(path)
        except media.MediaError as exc:
            logger.debug("probe of %s failed: %s", path.name, exc)

    if probe is not None:
        duration = duration or probe.duration
        width = width or probe.width
        height = height or probe.height

    limit = settings.upload_limit_bytes
    size = path.stat().st_size

    if size > limit:
        shrunk = None
        if settings.transcode_oversized and not result.is_audio and media.ffmpeg_available():
            reporter.set_stage("compressing", limit=human_size(limit))
            await reporter.flush()
            shrunk = await media.shrink_to_fit(
                path,
                job_dir / f"fit-{path.stem}.mp4",
                target_bytes=limit,
                duration=duration,
                source_height=height,
            )
        if shrunk is None:
            raise DownloadFailure(
                "err_too_big", size=human_size(size), limit=human_size(limit)
            )
        path = shrunk
        # The re-encode changed the geometry, so re-read it.
        if media.ffmpeg_available():
            try:
                reprobe = await media.probe(path)
                duration = reprobe.duration or duration
                width, height = reprobe.width or width, reprobe.height or height
            except media.MediaError:
                pass

    thumbnail = None
    if not result.is_audio and media.ffmpeg_available():
        thumbnail = await media.make_thumbnail(
            path,
            job_dir / "thumb.jpg",
            at=min(2.0, (duration or 2.0) / 2),
        )

    return UploadPayload(
        path=path,
        thumbnail=thumbnail,
        duration=int(duration) if duration else None,
        width=width,
        height=height,
        is_audio=result.is_audio,
    )


def _caption(language: str, url: str, result: DownloadResult) -> str:
    text = t(
        language,
        "caption",
        title=escape(shorten(result.title, 200)),
        platform=escape(platform_name(url)),
        uploader=escape(shorten(result.uploader, 60)),
        url=escape(result.webpage_url or url),
    )
    if len(text) <= CAPTION_LIMIT:
        return text
    # Trim the title rather than losing the source link.
    return t(
        language,
        "caption",
        title=escape(shorten(result.title, 60)),
        platform=escape(platform_name(url)),
        uploader=escape(shorten(result.uploader, 30)),
        url=escape(result.webpage_url or url),
    )[:CAPTION_LIMIT]


async def _upload(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    url: str,
    result: DownloadResult,
    payload: UploadPayload,
    language: str,
) -> Message:
    """Send the finished file, giving it a readable filename."""
    caption = _caption(language, url, result)
    suffix = payload.path.suffix or (".mp3" if payload.is_audio else ".mp4")
    filename = f"{safe_filename(result.title)}{suffix}"

    timeouts: dict[str, float] = {
        "read_timeout": UPLOAD_READ_TIMEOUT,
        "write_timeout": UPLOAD_WRITE_TIMEOUT,
        "connect_timeout": 60.0,
    }

    with payload.path.open("rb") as handle:
        upload = InputFile(handle, filename=filename)

        if payload.is_audio:
            return await context.bot.send_audio(
                chat_id,
                audio=upload,
                caption=caption,
                parse_mode=ParseMode.HTML,
                title=shorten(result.title, 64),
                performer=shorten(result.uploader, 64),
                duration=payload.duration,
                **timeouts,
            )

        thumb_handle = None
        try:
            thumbnail = None
            if payload.thumbnail is not None:
                thumb_handle = payload.thumbnail.open("rb")
                thumbnail = InputFile(thumb_handle, filename="thumb.jpg")
            return await context.bot.send_video(
                chat_id,
                video=upload,
                caption=caption,
                parse_mode=ParseMode.HTML,
                duration=payload.duration,
                width=payload.width,
                height=payload.height,
                thumbnail=thumbnail,
                supports_streaming=True,
                **timeouts,
            )
        finally:
            if thumb_handle is not None:
                thumb_handle.close()


async def _finish(
    context: ContextTypes.DEFAULT_TYPE,
    status_message: Message,
    sent: Message,
    key: str | None,
    result: DownloadResult,
    language: str,
    user_id: int,
) -> None:
    """Record the upload, cache its file_id and clear the status message."""
    svc = services.of(context)

    file_id = None
    kind = "audio" if result.is_audio else "video"
    if sent.video is not None:
        file_id, kind = sent.video.file_id, "video"
    elif sent.audio is not None:
        file_id, kind = sent.audio.file_id, "audio"
    elif sent.document is not None:
        file_id, kind = sent.document.file_id, "document"

    if file_id and key:
        await svc.storage.cache_store(
            key, file_id=file_id, kind=kind, title=result.title
        )

    await svc.storage.record_download(user_id)

    try:
        await status_message.delete()
    except TelegramError:
        await _edit(status_message, t(language, "processing"))


async def _show_failure(
    message: Message | None, language: str, failure: DownloadFailure
) -> None:
    if message is None:
        return
    await _edit(message, t(language, failure.key, **failure.params))


async def _edit(message: Message | None, text: str, **kwargs: Any) -> None:
    """Edit a message, treating 'nothing changed' and races as success."""
    if message is None:
        return
    try:
        await message.edit_text(text, parse_mode=ParseMode.HTML, **kwargs)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            logger.debug("edit failed: %s", exc)
    except TelegramError as exc:
        logger.debug("edit failed: %s", exc)
