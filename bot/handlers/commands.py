"""Slash commands, the settings menu and the admin cookies upload."""

from __future__ import annotations

import logging

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .. import services
from ..downloader import QUALITY_CHOICES
from ..i18n import quality_label, t
from ..utils import escape, human_duration, human_size
from . import keyboards
from .download import guard

logger = logging.getLogger(__name__)

# A cookies export is a few KB of text; anything larger isn't one.
MAX_COOKIES_BYTES = 2 * 1024 * 1024


def command_list(language: str) -> list[BotCommand]:
    """What appears in Telegram's command menu."""
    descriptions = {
        "ar": {
            "start": "بدء الاستخدام",
            "help": "المساعدة",
            "settings": "الإعدادات",
            "quality": "الجودة الافتراضية",
            "lang": "تغيير اللغة",
            "cancel": "إلغاء التحميل الحالي",
        },
        "en": {
            "start": "get started",
            "help": "help",
            "settings": "settings",
            "quality": "default quality",
            "lang": "change language",
            "cancel": "cancel current download",
        },
    }
    labels = descriptions.get(language, descriptions["en"])
    return [BotCommand(name, text) for name, text in labels.items()]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = await guard(update, context)
    if prefs is None:
        return
    user = update.effective_user
    name = escape((user.first_name if user else None) or "👋")
    await update.effective_message.reply_text(
        t(prefs.language, "start", name=name), parse_mode=ParseMode.HTML
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = await guard(update, context)
    if prefs is None:
        return
    settings = services.of(context).settings
    await update.effective_message.reply_text(
        t(
            prefs.language,
            "help",
            limit=human_size(settings.upload_limit_bytes),
            duration=human_duration(settings.max_duration_seconds),
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = await guard(update, context)
    if prefs is None:
        return
    await update.effective_message.reply_text(
        _settings_text(prefs),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.settings_keyboard(prefs.language, prefs),
    )


def _settings_text(prefs) -> str:
    return t(
        prefs.language,
        "settings",
        language="العربية" if prefs.language == "ar" else "English",
        quality=quality_label(prefs.language, prefs.quality),
        ask=t(prefs.language, "settings_on" if prefs.ask_quality else "settings_off"),
    )


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/lang flips between the two supported languages."""
    prefs = await guard(update, context)
    if prefs is None:
        return
    await _switch_language(update, context, prefs)


async def quality_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = await guard(update, context)
    if prefs is None:
        return
    await update.effective_message.reply_text(
        t(prefs.language, "quality_prompt"),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.default_quality_keyboard(prefs.language),
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = await guard(update, context)
    if prefs is None:
        return
    svc = services.of(context)
    if not svc.settings.is_admin(prefs.user_id):
        await update.effective_message.reply_text(
            t(prefs.language, "admin_only"), parse_mode=ParseMode.HTML
        )
        return
    numbers = await svc.storage.stats()
    await update.effective_message.reply_text(
        t(prefs.language, "stats", **numbers), parse_mode=ParseMode.HTML
    )


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/health - download a known video right now and report what happened."""
    prefs = await guard(update, context)
    if prefs is None:
        return

    svc = services.of(context)
    message = update.effective_message
    if not svc.settings.is_admin(prefs.user_id):
        await message.reply_text(
            t(prefs.language, "admin_only"), parse_mode=ParseMode.HTML
        )
        return

    notice = await message.reply_text("🔍 ...")

    async def run() -> None:
        from ..selftest import run_checks

        try:
            results = await run_checks(svc.settings)
        except Exception as exc:  # noqa: BLE001 - the report is the product
            await notice.edit_text(f"⚠️ {type(exc).__name__}: {exc}")
            return

        if not results:
            await notice.edit_text(
                "ℹ️ لم يُحمَّل شيء بعد.\n"
                "حمّل مقطعاً وسيبدأ الفحص بمراقبته تلقائياً."
                if prefs.language == "ar" else
                "ℹ️ Nothing has been downloaded yet.\n"
                "Download something and the check starts watching it."
            )
            return

        head = "✅" if all(r.ok for r in results) else "⚠️"
        body = "\n\n".join(r.summary for r in results)
        await notice.edit_text(f"{head}\n\n{body}"[:4000],
                               disable_web_page_preview=True)

    # Downloading takes a while; do not hold the handler open for it.
    context.application.create_task(run())


# ---- settings callbacks ----------------------------------------------


async def on_settings_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    prefs = await guard(update, context)
    if prefs is None:
        return
    await _switch_language(update, context, prefs, via_callback=True)


async def _switch_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prefs,
    *,
    via_callback: bool = False,
) -> None:
    svc = services.of(context)
    new_language = "en" if prefs.language == "ar" else "ar"
    await svc.storage.update_user(prefs.user_id, language=new_language)
    updated = await svc.storage.get_user(prefs.user_id)

    text = f"{t(new_language, 'language_set')}\n\n{_settings_text(updated)}"
    markup = keyboards.settings_keyboard(new_language, updated)

    if via_callback and update.callback_query.message is not None:
        await _safe_edit(update.callback_query.message, text, markup)
    else:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=markup
        )

    try:
        await context.bot.set_my_commands(command_list(new_language))
    except Exception:  # noqa: BLE001 - cosmetic only
        logger.debug("set_my_commands failed", exc_info=True)


async def on_settings_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    prefs = await guard(update, context)
    if prefs is None:
        return

    svc = services.of(context)
    await svc.storage.update_user(prefs.user_id, ask_quality=not prefs.ask_quality)
    updated = await svc.storage.get_user(prefs.user_id)

    state = t(updated.language, "settings_on" if updated.ask_quality else "settings_off")
    text = (
        f"{t(updated.language, 'ask_toggled', state=state)}\n\n"
        f"{_settings_text(updated)}"
    )
    await _safe_edit(
        query.message, text, keyboards.settings_keyboard(updated.language, updated)
    )


async def on_settings_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    prefs = await guard(update, context)
    if prefs is None:
        return
    await _safe_edit(
        query.message,
        t(prefs.language, "quality_prompt"),
        keyboards.default_quality_keyboard(prefs.language),
    )


async def on_set_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
    prefs = await guard(update, context)
    if prefs is None:
        return

    parts = query.data.split("|")
    if len(parts) != 2 or parts[1] not in QUALITY_CHOICES:
        return

    svc = services.of(context)
    await svc.storage.update_user(prefs.user_id, quality=parts[1])
    updated = await svc.storage.get_user(prefs.user_id)

    text = (
        f"{t(updated.language, 'quality_set', quality=quality_label(updated.language, parts[1]))}"
        f"\n\n{_settings_text(updated)}"
    )
    await _safe_edit(
        query.message, text, keyboards.settings_keyboard(updated.language, updated)
    )


# ---- admin: cookies upload -------------------------------------------


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """An admin can refresh cookies.txt by sending it as a document."""
    prefs = await guard(update, context)
    if prefs is None:
        return

    message = update.effective_message
    document = message.document
    svc = services.of(context)

    if not svc.settings.is_admin(prefs.user_id):
        await message.reply_text(
            t(prefs.language, "admin_only"), parse_mode=ParseMode.HTML
        )
        return

    target = svc.settings.cookies_file
    if target is None:
        await message.reply_text(
            t(prefs.language, "err_generic", reason="COOKIES_FILE is not configured"),
            parse_mode=ParseMode.HTML,
        )
        return

    name = (document.file_name or "").lower()
    if not name.endswith(".txt") or (document.file_size or 0) > MAX_COOKIES_BYTES:
        await message.reply_text(
            t(prefs.language, "cookies_hint"), parse_mode=ParseMode.HTML
        )
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    telegram_file = await context.bot.get_file(document.file_id)
    await telegram_file.download_to_drive(custom_path=target)
    target.chmod(0o600)

    await message.reply_text(
        t(prefs.language, "cookies_saved", size=human_size(target.stat().st_size)),
        parse_mode=ParseMode.HTML,
    )
    logger.info("cookies refreshed by admin %s", prefs.user_id)


async def _safe_edit(message, text: str, markup) -> None:
    from telegram.error import BadRequest, TelegramError

    if message is None:
        return
    try:
        await message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=markup
        )
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            logger.debug("settings edit failed: %s", exc)
    except TelegramError as exc:
        logger.debug("settings edit failed: %s", exc)
