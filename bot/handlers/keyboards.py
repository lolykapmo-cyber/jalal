"""Inline keyboards and the callback_data vocabulary.

callback_data is capped at 64 bytes, so every payload is short: a one-letter
verb, then fields separated by `|`.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..i18n import quality_label, t
from ..storage import UserPrefs

# Verbs
PICK_QUALITY = "q"      # q|<token>|<quality>
DISMISS = "d"           # d|<token>
CANCEL_JOB = "x"        # x
SETTINGS_LANG = "sl"    # sl
SETTINGS_ASK = "sa"     # sa
SETTINGS_QUALITY = "sq" # sq
SET_QUALITY = "su"      # su|<quality>


def quality_keyboard(
    language: str, token: str, heights: tuple[int, ...] | list[int]
) -> InlineKeyboardMarkup:
    """Best / concrete heights / MP3, plus a way out."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                t(language, "btn_best"), callback_data=f"{PICK_QUALITY}|{token}|best"
            )
        ]
    ]

    buttons = [
        InlineKeyboardButton(
            t(language, "btn_quality", height=height),
            callback_data=f"{PICK_QUALITY}|{token}|{height}",
        )
        for height in heights
    ]
    for index in range(0, len(buttons), 2):
        rows.append(buttons[index : index + 2])

    rows.append(
        [
            InlineKeyboardButton(
                t(language, "btn_audio"), callback_data=f"{PICK_QUALITY}|{token}|audio"
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton(t(language, "btn_cancel"), callback_data=f"{DISMISS}|{token}")]
    )
    return InlineKeyboardMarkup(rows)


def cancel_keyboard(language: str) -> InlineKeyboardMarkup:
    """Shown beside a live progress message."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(language, "btn_cancel"), callback_data=CANCEL_JOB)]]
    )


def settings_keyboard(language: str, prefs: UserPrefs) -> InlineKeyboardMarkup:
    state = t(language, "settings_on" if prefs.ask_quality else "settings_off")
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t(language, "btn_language"), callback_data=SETTINGS_LANG)],
            [
                InlineKeyboardButton(
                    t(language, "btn_set_quality",
                      quality=quality_label(language, prefs.quality)),
                    callback_data=SETTINGS_QUALITY,
                )
            ],
            [
                InlineKeyboardButton(
                    t(language, "btn_toggle_ask", state=state),
                    callback_data=SETTINGS_ASK,
                )
            ],
        ]
    )


def default_quality_keyboard(language: str) -> InlineKeyboardMarkup:
    """Pick the quality used when the bot doesn't ask."""
    choices = ("best", "1080", "720", "480", "360", "audio")
    buttons = [
        InlineKeyboardButton(
            quality_label(language, choice), callback_data=f"{SET_QUALITY}|{choice}"
        )
        for choice in choices
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)
