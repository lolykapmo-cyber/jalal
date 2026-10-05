"""Catch-all error handler, so one bad update never stops the bot."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import Forbidden, NetworkError, TelegramError

from .. import services
from ..i18n import t

logger = logging.getLogger(__name__)


async def on_error(update: object, context) -> None:
    error = context.error

    if isinstance(error, Forbidden):
        # The user blocked the bot; nothing to tell them.
        logger.info("forbidden: %s", error)
        return
    if isinstance(error, NetworkError):
        logger.warning("network error talking to Telegram: %s", error)
        return

    logger.error("unhandled error while processing an update", exc_info=error)

    if not isinstance(update, Update) or update.effective_message is None:
        return

    language = services.of(context).settings.default_language
    user = update.effective_user
    if user is not None:
        try:
            language = (await services.of(context).storage.get_user(user.id)).language
        except Exception:  # noqa: BLE001 - keep the apology best-effort
            pass

    try:
        await update.effective_message.reply_text(
            t(language, "err_generic", reason="internal error"),
            parse_mode=ParseMode.HTML,
        )
    except TelegramError:
        logger.debug("could not deliver the error notice")
