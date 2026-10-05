"""Bilingual message catalogue (Arabic default, English fallback)."""

from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "ar"
LANGUAGES = ("ar", "en")

STRINGS: dict[str, dict[str, str]] = {
    "ar": {
        "start": (
            "<b>مرحباً {name} 👋</b>\n\n"
            "أرسل لي أي رابط فيديو وسأحمّله لك.\n\n"
            "<b>المنصات المدعومة:</b> يوتيوب، تيك توك، إنستغرام، فيسبوك، "
            "X/تويتر، ريديت، سناب شات، تويتش، ساوندكلاود وأكثر من ١٠٠٠ موقع.\n\n"
            "<b>الأوامر:</b>\n"
            "/help — المساعدة\n"
            "/settings — الإعدادات\n"
            "/cancel — إلغاء التحميل الحالي"
        ),
        "help": (
            "<b>كيف أستخدم البوت؟</b>\n\n"
            "١. انسخ رابط الفيديو من أي تطبيق.\n"
            "٢. أرسله لي هنا.\n"
            "٣. اختر الجودة، أو <b>🎵 صوت MP3</b> لاستخراج الصوت فقط.\n\n"
            "<b>ملاحظات:</b>\n"
            "• الحد الأقصى للرفع عبر تليكرام هو <b>{limit}</b>؛ الملفات الأكبر "
            "يُعاد ترميزها تلقائياً لتناسب الحد.\n"
            "• أقصى مدة مسموحة: <b>{duration}</b>.\n"
            "• المحتوى الخاص أو المحدود لمتابعين لا يمكن تحميله.\n"
            "• أرسل عدة روابط في رسالة واحدة وسأعالجها بالترتيب.\n\n"
            "<b>الأوامر:</b>\n"
            "/settings — الإعدادات\n"
            "/lang — تغيير اللغة\n"
            "/quality — الجودة الافتراضية\n"
            "/cancel — إلغاء التحميل الحالي"
        ),
        "must_join": (
            "<b>🔐 اشترك أولاً</b>\n\n"
            "لاستخدام البوت، اشترك في القنوات التالية ثم اضغط "
            "<b>تحققت ✅</b>:"
        ),
        # Shown in a popup alert, which renders plain text only.
        "still_missing": "⚠️ لم تشترك بعد في جميع القنوات. اشترك ثم اضغط «تحققت ✅» مرة أخرى.",
        "join_verified": "✅ تم التحقق، أهلاً بك! أرسل رابط الفيديو الآن.",
        "btn_join": "📢 {title}",
        "btn_verify": "تحققت ✅",
        "err_disk": (
            "💾 مساحة السيرفر ممتلئة مؤقتاً. حاول بعد قليل."
        ),
        "shared_wait": "⏳ هذا الفيديو قيد التحميل لمستخدم آخر، سيصلك فور جهوزه...",
        "not_allowed": "🚫 هذا البوت خاص، ولا تملك صلاحية استخدامه.",
        "admin_only": "🚫 هذا الأمر للمشرفين فقط.",
        "no_url": (
            "لم أجد رابطاً في رسالتك 🤔\n"
            "أرسل رابط فيديو مثل: <code>https://youtu.be/...</code>"
        ),
        "fetching": "🔎 جاري فحص الرابط...",
        "info_card": (
            "<b>{title}</b>\n\n"
            "🌐 {platform}\n"
            "👤 {uploader}\n"
            "⏱ {duration}\n\n"
            "اختر الجودة المطلوبة:"
        ),
        "queued": "⏳ في الانتظار... ({position} في الصف)",
        "downloading": (
            "⬇️ <b>جاري التحميل</b>\n\n"
            "<code>{bar}</code> {percent}\n"
            "{done} / {total}  •  {speed}\n"
            "⏱ متبقٍ: {eta}"
        ),
        "downloading_plain": "⬇️ <b>جاري التحميل...</b>\n\n<code>{bar}</code>",
        "processing": "⚙️ جاري المعالجة...",
        "compressing": "🗜 الملف أكبر من {limit}، جاري إعادة الترميز...",
        "uploading": "⬆️ جاري الرفع إلى تليكرام...",
        "caption": "<b>{title}</b>\n\n🌐 {platform}  •  👤 {uploader}\n🔗 <a href=\"{url}\">المصدر</a>",
        "cached": "⚡️ أُرسل من الذاكرة المؤقتة.",
        "cancelled": "❌ تم إلغاء التحميل.",
        "nothing_to_cancel": "لا يوجد تحميل جارٍ لإلغائه.",
        "expired": "⌛️ انتهت صلاحية هذا الخيار. أرسل الرابط مرة أخرى.",
        "cooldown": "⏱ تمهّل قليلاً — انتظر {seconds} ثانية قبل الطلب التالي.",
        "busy": "⏳ لديك تحميل جارٍ بالفعل. انتظر حتى ينتهي أو استخدم /cancel.",
        "btn_best": "🎬 أفضل جودة",
        "btn_quality": "📺 {height}p",
        "btn_audio": "🎵 صوت MP3",
        "btn_cancel": "✖️ إلغاء",
        "settings": (
            "<b>⚙️ الإعدادات</b>\n\n"
            "🌐 اللغة: <b>{language}</b>\n"
            "📺 الجودة الافتراضية: <b>{quality}</b>\n"
            "❓ السؤال عن الجودة: <b>{ask}</b>"
        ),
        "settings_on": "مُفعّل",
        "settings_off": "معطّل",
        "btn_toggle_ask": "❓ السؤال عن الجودة: {state}",
        "btn_language": "🌐 English",
        "btn_set_quality": "📺 الجودة: {quality}",
        "language_set": "✅ تم تعيين اللغة إلى العربية.",
        "quality_set": "✅ الجودة الافتراضية الآن: <b>{quality}</b>",
        "quality_prompt": "اختر الجودة الافتراضية:",
        "ask_toggled": "✅ السؤال عن الجودة: <b>{state}</b>",
        "stats": (
            "<b>📊 الإحصائيات</b>\n\n"
            "👥 المستخدمون: <b>{users}</b>\n"
            "📥 التحميلات الناجحة: <b>{downloads}</b>\n"
            "⚡️ من الذاكرة المؤقتة: <b>{cached}</b>\n"
            "💾 حجم الذاكرة المؤقتة: <b>{cache_rows}</b> عنصر"
        ),
        "cookies_saved": "✅ تم حفظ ملف الكوكيز ({size}).",
        "cookies_hint": "أرسل ملف <code>cookies.txt</code> كمستند لتحديثه.",
        "err_login": (
            "🔒 تعذّر الوصول لهذا المحتوى بعد تجربة عدة طرق.\n"
            "عادةً يعني أنه خاص، أو محدود لمتابعين، أو محمي بتسجيل دخول."
        ),
        "err_private": "🔒 هذا الفيديو خاص أو محمي ولا يمكن الوصول إليه.",
        "err_geo": "🌍 هذا المحتوى محجوب جغرافياً في منطقة السيرفر.",
        "err_unavailable": "🚫 الفيديو غير متاح أو محذوف.",
        "err_unsupported": "🤷 لا أدعم هذا الرابط. تأكد أنه رابط فيديو صحيح.",
        "err_live": "📡 لا يمكنني تحميل بث مباشر قيد العمل.",
        "err_too_long": "⏱ المدة {duration} تتجاوز الحد المسموح ({limit}).",
        "err_too_big": (
            "📦 الملف ({size}) أكبر من حد تليكرام ({limit}) ولا يمكن تصغيره "
            "بجودة مقبولة.\nجرّب جودة أقل أو <b>🎵 صوت MP3</b>."
        ),
        "err_no_formats": "🤷 لم أجد صيغة قابلة للتحميل لهذا الرابط.",
        "err_network": "🌐 تعذّر الوصول إلى الموقع. جرّب مرة أخرى بعد قليل.",
        "err_generic": "⚠️ حدث خطأ غير متوقع:\n<code>{reason}</code>",
    },
    "en": {
        "start": (
            "<b>Hi {name} 👋</b>\n\n"
            "Send me any video link and I'll download it for you.\n\n"
            "<b>Supported:</b> YouTube, TikTok, Instagram, Facebook, X/Twitter, "
            "Reddit, Snapchat, Twitch, SoundCloud and 1000+ more sites.\n\n"
            "<b>Commands:</b>\n"
            "/help — help\n"
            "/settings — settings\n"
            "/cancel — cancel the current download"
        ),
        "help": (
            "<b>How to use this bot</b>\n\n"
            "1. Copy a video link from any app.\n"
            "2. Send it to me here.\n"
            "3. Pick a quality, or <b>🎵 MP3</b> for audio only.\n\n"
            "<b>Notes:</b>\n"
            "• Telegram caps uploads at <b>{limit}</b>; bigger files are "
            "re-encoded automatically to fit.\n"
            "• Maximum duration: <b>{duration}</b>.\n"
            "• Private or followers-only posts can't be downloaded.\n"
            "• Send several links in one message and I'll queue them.\n\n"
            "<b>Commands:</b>\n"
            "/settings — settings\n"
            "/lang — change language\n"
            "/quality — default quality\n"
            "/cancel — cancel the current download"
        ),
        "must_join": (
            "<b>🔐 Join first</b>\n\n"
            "To use this bot, join the channels below and then tap "
            "<b>I joined ✅</b>:"
        ),
        # Shown in a popup alert, which renders plain text only.
        "still_missing": "⚠️ You haven't joined all of them yet. Join, then tap \"I joined\" again.",
        "join_verified": "✅ Verified, welcome! Send a video link now.",
        "btn_join": "📢 {title}",
        "btn_verify": "I joined ✅",
        "err_disk": "💾 The server is temporarily out of space. Try again shortly.",
        "shared_wait": "⏳ Someone else is already downloading this; you'll get it as soon as it's ready...",
        "not_allowed": "🚫 This bot is private and you're not on the allow-list.",
        "admin_only": "🚫 This command is for admins only.",
        "no_url": (
            "I couldn't find a link in your message 🤔\n"
            "Send a video URL like <code>https://youtu.be/...</code>"
        ),
        "fetching": "🔎 Inspecting the link...",
        "info_card": (
            "<b>{title}</b>\n\n"
            "🌐 {platform}\n"
            "👤 {uploader}\n"
            "⏱ {duration}\n\n"
            "Choose a quality:"
        ),
        "queued": "⏳ Waiting... (#{position} in queue)",
        "downloading": (
            "⬇️ <b>Downloading</b>\n\n"
            "<code>{bar}</code> {percent}\n"
            "{done} / {total}  •  {speed}\n"
            "⏱ ETA: {eta}"
        ),
        "downloading_plain": "⬇️ <b>Downloading...</b>\n\n<code>{bar}</code>",
        "processing": "⚙️ Processing...",
        "compressing": "🗜 Bigger than {limit}, re-encoding...",
        "uploading": "⬆️ Uploading to Telegram...",
        "caption": "<b>{title}</b>\n\n🌐 {platform}  •  👤 {uploader}\n🔗 <a href=\"{url}\">source</a>",
        "cached": "⚡️ Served from cache.",
        "cancelled": "❌ Download cancelled.",
        "nothing_to_cancel": "Nothing is downloading right now.",
        "expired": "⌛️ That option expired. Send the link again.",
        "cooldown": "⏱ Easy there — wait {seconds}s before the next request.",
        "busy": "⏳ You already have a download running. Wait for it or use /cancel.",
        "btn_best": "🎬 Best quality",
        "btn_quality": "📺 {height}p",
        "btn_audio": "🎵 MP3 audio",
        "btn_cancel": "✖️ Cancel",
        "settings": (
            "<b>⚙️ Settings</b>\n\n"
            "🌐 Language: <b>{language}</b>\n"
            "📺 Default quality: <b>{quality}</b>\n"
            "❓ Ask for quality: <b>{ask}</b>"
        ),
        "settings_on": "on",
        "settings_off": "off",
        "btn_toggle_ask": "❓ Ask for quality: {state}",
        "btn_language": "🌐 العربية",
        "btn_set_quality": "📺 Quality: {quality}",
        "language_set": "✅ Language set to English.",
        "quality_set": "✅ Default quality is now <b>{quality}</b>",
        "quality_prompt": "Pick your default quality:",
        "ask_toggled": "✅ Ask for quality: <b>{state}</b>",
        "stats": (
            "<b>📊 Stats</b>\n\n"
            "👥 Users: <b>{users}</b>\n"
            "📥 Successful downloads: <b>{downloads}</b>\n"
            "⚡️ Served from cache: <b>{cached}</b>\n"
            "💾 Cache size: <b>{cache_rows}</b> entries"
        ),
        "cookies_saved": "✅ Cookies file saved ({size}).",
        "cookies_hint": "Send a <code>cookies.txt</code> document to update it.",
        "err_login": (
            "🔒 Couldn't reach this content after trying several methods.\n"
            "That usually means it's private, followers-only or login-walled."
        ),
        "err_private": "🔒 This video is private or protected.",
        "err_geo": "🌍 This content is geo-blocked in the server's region.",
        "err_unavailable": "🚫 The video is unavailable or has been removed.",
        "err_unsupported": "🤷 I don't support that link. Check it's a real video URL.",
        "err_live": "📡 I can't download an in-progress live stream.",
        "err_too_long": "⏱ Duration {duration} exceeds the limit ({limit}).",
        "err_too_big": (
            "📦 The file ({size}) is larger than Telegram's limit ({limit}) and "
            "can't be shrunk at acceptable quality.\nTry a lower quality or "
            "<b>🎵 MP3</b>."
        ),
        "err_no_formats": "🤷 I couldn't find a downloadable format for that link.",
        "err_network": "🌐 Couldn't reach the site. Try again in a moment.",
        "err_generic": "⚠️ Something unexpected happened:\n<code>{reason}</code>",
    },
}

QUALITY_LABELS: dict[str, dict[str, str]] = {
    "ar": {
        "best": "أفضل جودة",
        "1080": "1080p",
        "720": "720p",
        "480": "480p",
        "360": "360p",
        "audio": "صوت فقط",
    },
    "en": {
        "best": "Best",
        "1080": "1080p",
        "720": "720p",
        "480": "480p",
        "360": "360p",
        "audio": "Audio only",
    },
}


def normalize_language(language: str | None) -> str:
    """Map an arbitrary Telegram language code onto a supported one."""
    code = (language or "").lower().replace("_", "-")
    if code.startswith("ar"):
        return "ar"
    if code.split("-")[0] in LANGUAGES:
        return code.split("-")[0]
    return DEFAULT_LANGUAGE if not code else "en"


def t(language: str | None, key: str, /, **params: Any) -> str:
    """Look up a string, falling back to English and then to the key.

    The two leading parameters are positional-only. Without that, a string
    carrying a {language} or {key} placeholder cannot be rendered at all:
    the keyword argument collides with the parameter name and raises
    TypeError. /settings carried exactly that collision and had never once
    worked.
    """
    lang = language if language in STRINGS else DEFAULT_LANGUAGE
    template = STRINGS[lang].get(key) or STRINGS["en"].get(key) or key
    if not params:
        return template
    try:
        return template.format(**params)
    except (KeyError, IndexError):
        return template


def quality_label(language: str | None, quality: str, /) -> str:
    lang = language if language in QUALITY_LABELS else DEFAULT_LANGUAGE
    return QUALITY_LABELS[lang].get(quality, quality)
