# بوت تليكرام لتحميل الفيديوهات 🎬

بوت تليكرام يحمّل الفيديوهات من مواقع التواصل الاجتماعي. أرسل رابطاً،
اختر الجودة، واستلم الملف في المحادثة.

> English documentation follows the Arabic section below.

---

## ✨ الميزات

- **أكثر من ١٠٠٠ موقع** عبر `yt-dlp`: يوتيوب، تيك توك، إنستغرام، فيسبوك،
  X/تويتر، ريديت، سناب شات، تويتش، فيميو، ساوندكلاود وغيرها.
- **اختيار الجودة** بأزرار تفاعلية — ولا يُعرض إلا ما يوفّره الموقع فعلاً.
- **استخراج الصوت** بصيغة MP3 بجودة 192kbps.
- **شريط تقدّم مباشر** يُحدَّث أثناء التحميل، مع السرعة والوقت المتبقي.
- **تجاوز حد الـ50 ميغابايت**: الملفات الأكبر يُعاد ترميزها تلقائياً
  لتناسب الحد، أو تُرفع كاملة عبر سيرفر Bot API محلي (حتى ٢ غيغابايت).
- **ذاكرة مؤقتة**: الرابط المُحمّل سابقاً يُرسل فوراً عبر `file_id` بدون
  تحميل من جديد.
- **عربي وإنجليزي** بالكامل، مع تبديل فوري للغة.
- **حدود استخدام عادل**: سقف للتحميلات المتوازية، ومهلة بين الطلبات،
  وحد أقصى لمدة الفيديو.
- **إلغاء فوري** لأي تحميل جارٍ عبر زر أو أمر `/cancel`.
- **قائمة بيضاء** اختيارية لقصر البوت على مستخدمين محدّدين.

---

## 🚀 التشغيل السريع

### ١. أنشئ البوت

راسل [@BotFather](https://t.me/BotFather) على تليكرام، أرسل `/newbot`،
واتبع الخطوات. ستحصل على توكن بهذا الشكل:
`123456789:AAE...`

### ٢. جهّز الإعدادات

```bash
git clone https://github.com/lolykapmo-cyber/jalal.git
cd jalal
cp .env.example .env
```

افتح `.env` وضع التوكن في `BOT_TOKEN`.

### ٣. شغّل البوت

**بـ Docker (الأسهل — ffmpeg مُضمَّن):**

```bash
docker compose up -d
docker compose logs -f
```

**محلياً بـ Python:**

```bash
# ffmpeg مطلوب للدمج والصور المصغّرة واستخراج MP3
sudo apt install ffmpeg          # أو: brew install ffmpeg

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m bot
```

ثم أرسل `/start` لبوتك على تليكرام. 🎉

---

## 📋 الأوامر

| الأمر | الوظيفة |
|------|---------|
| `/start` | رسالة الترحيب |
| `/help` | شرح الاستخدام والحدود الحالية |
| `/settings` | الإعدادات (اللغة، الجودة، السؤال عن الجودة) |
| `/quality` | تعيين الجودة الافتراضية |
| `/lang` | التبديل بين العربية والإنجليزية |
| `/cancel` | إلغاء التحميل الجاري |
| `/stats` | إحصائيات الاستخدام (للمشرفين) |

---

## ⚙️ الإعدادات

كل الإعدادات تُقرأ من متغيّرات البيئة، وهي موثّقة بالعربية والإنجليزية
في [`.env.example`](.env.example). أهمّها:

| المتغيّر | الافتراضي | الوصف |
|---------|----------|-------|
| `BOT_TOKEN` | — | **مطلوب.** توكن البوت من BotFather |
| `ALLOWED_USERS` | فارغ | أرقام المسموح لهم؛ فارغ = متاح للجميع |
| `ADMIN_USERS` | فارغ | من يملك `/stats` ورفع الكوكيز |
| `UPLOAD_LIMIT_MB` | `50` | حد الرفع؛ `2000` مع سيرفر محلي |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | التحميلات المتوازية للبوت كله |
| `MAX_USER_DOWNLOADS` | `1` | التحميلات المتوازية لكل مستخدم |
| `COOLDOWN_SECONDS` | `3` | المهلة بين طلبين لنفس المستخدم |
| `MAX_DURATION_SECONDS` | `10800` | أقصى مدة فيديو (٣ ساعات) |
| `DEFAULT_LANGUAGE` | `ar` | `ar` أو `en` |
| `DEFAULT_QUALITY` | `best` | `best` / `1080` / `720` / `480` / `360` / `audio` |
| `ASK_QUALITY` | `true` | `false` = تحميل فوري بالجودة الافتراضية |
| `COOKIES_FILE` | — | ملف كوكيز للمحتوى المحمي |
| `PROXY` | — | بروكسي لتجاوز الحجب الجغرافي |

---

## 📦 حد الـ50 ميغابايت

واجهة Bot API العامة لا تسمح للبوتات برفع أكثر من **٥٠ ميغابايت**. البوت
يتعامل مع هذا تلقائياً:

1. يختار صيغة مناسبة لحجم الحد عند الإمكان.
2. إن تجاوز الملف الحد، يُعاد ترميزه بـ ffmpeg بدقة ومعدل بت أقل ليناسبه.
3. إن كان الفيديو طويلاً لدرجة أن إعادة الترميز ستُفسد الجودة، يخبرك
   البوت ويقترح جودة أقل أو استخراج الصوت.

**لرفع ملفات تصل إلى ٢ غيغابايت**، شغّل سيرفر Bot API محلي: أزل التعليق
عن قسم `telegram-bot-api` في `docker-compose.yml`، واحصل على `api_id`
و`api_hash` من [my.telegram.org](https://my.telegram.org)، ثم ضع في `.env`:

```env
TELEGRAM_API_ROOT=http://telegram-bot-api:8081
```

سيرتفع حد الرفع إلى ٢٠٠٠ ميغابايت تلقائياً.

---

## 🔒 المحتوى الذي يتطلب تسجيل دخول

بعض المنصات (إنستغرام خصوصاً) تطلب جلسة مسجّلة. صدّر الكوكيز بصيغة
Netscape من إضافة متصفح، ثم:

```env
COOKIES_FILE=cookies.txt
```

يمكن للمشرف أيضاً تحديث الملف بإرساله كمستند للبوت مباشرة.

> استخدم حساباً ثانوياً — مشاركة الكوكيز تمنح وصولاً كاملاً للحساب،
> وبعض المنصات تحظر الحسابات على التحميل الآلي.

---

## 🧪 الاختبارات

```bash
pip install -r requirements-dev.txt
python -m pytest
```

١١١ اختباراً، كلها تعمل بدون إنترنت. اختبارات ffmpeg تُتخطّى تلقائياً إن
لم يكن مثبّتاً.

---

## 🗂 بنية المشروع

```
bot/
├── __main__.py        نقطة الدخول: python -m bot
├── app.py             تجميع التطبيق وتسجيل المعالجات
├── config.py          قراءة الإعدادات من البيئة والتحقّق منها
├── downloader.py      غلاف yt-dlp: الصيغ، الإلغاء، تصنيف الأخطاء
├── media.py           ffmpeg: الفحص، المصغّرات، MP3، التصغير
├── storage.py         SQLite: التفضيلات، ذاكرة file_id، العدّادات
├── progress.py        رسالة التقدّم التي تُحدّث نفسها
├── throttle.py        حدود التوازي والمهلة
├── jobs.py            سجلّ الأزرار المعلّقة والمهام الجارية
├── i18n.py            النصوص العربية والإنجليزية
├── urls.py            استخراج الروابط وتحديد المنصّة
├── utils.py           تنسيق الأحجام والمدد وأسماء الملفات
├── services.py        الكائنات المشتركة بين المعالجات
└── handlers/
    ├── download.py    خط الأنابيب: رابط ← جودة ← تحميل ← رفع
    ├── commands.py    الأوامر وقائمة الإعدادات
    ├── keyboards.py   الأزرار التفاعلية
    └── errors.py      معالج الأخطاء الشامل
```

---

## ⚖️ الاستخدام المسؤول

هذه الأداة للمحتوى الذي تملك حق تحميله: أعمالك، أو المحتوى المرخّص، أو
الاستخدام الشخصي حيث يسمح القانون. التزم بشروط خدمة كل منصّة وبحقوق
النشر.

---
---

# Social Media Video Downloader Bot 🎬

A Telegram bot that downloads videos from social media. Send a link, pick a
quality, get the file back in the chat.

## ✨ Features

- **1000+ sites** via `yt-dlp`: YouTube, TikTok, Instagram, Facebook,
  X/Twitter, Reddit, Snapchat, Twitch, Vimeo, SoundCloud and more.
- **Quality picker** that only offers what the site actually has.
- **MP3 extraction** at 192 kbps.
- **Live progress bar** with speed and ETA.
- **Beats the 50 MB cap**: oversized files are re-encoded to fit, or
  uploaded whole (up to 2 GB) through a local Bot API server.
- **Upload cache**: a repeated link is re-sent instantly by `file_id`.
- **Arabic and English** throughout, switchable on the fly.
- **Fair-use limits**: concurrency caps, a per-user cooldown and a maximum
  duration.
- **Instant cancellation** via a button or `/cancel`.
- **Optional allow-list** to keep the bot private.

## 🚀 Quick start

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Configure it:
   ```bash
   git clone https://github.com/lolykapmo-cyber/jalal.git
   cd jalal
   cp .env.example .env     # then put your token in BOT_TOKEN
   ```
3. Run it:
   ```bash
   docker compose up -d                    # ffmpeg included
   # or locally:
   pip install -r requirements.txt && python -m bot
   ```

Running locally needs `ffmpeg` on `PATH` for merging, thumbnails, MP3
extraction and shrinking oversized files.

## 📋 Commands

`/start` · `/help` · `/settings` · `/quality` · `/lang` · `/cancel` ·
`/stats` (admins)

## ⚙️ Configuration

Every setting is an environment variable, documented inline in
[`.env.example`](.env.example). Only `BOT_TOKEN` is required.

## 📦 About the 50 MB limit

The public Bot API caps bot uploads at 50 MB. The bot picks a format that
fits, re-encodes with ffmpeg when it doesn't, and tells you when a video is
too long to shrink without ruining it. To upload up to 2 GB, run a local
Bot API server (see the commented block in `docker-compose.yml`) and set
`TELEGRAM_API_ROOT`; the limit then raises itself to 2000 MB.

## 🔒 Login-walled content

Export cookies in Netscape format and point `COOKIES_FILE` at the file; an
admin can also refresh it by sending it to the bot as a document. Use a
throwaway account — cookies grant full account access, and some platforms
ban accounts for automated downloading.

## 🧪 Tests

```bash
pip install -r requirements-dev.txt && python -m pytest
```

111 tests, all offline. The ffmpeg-backed ones skip themselves if ffmpeg
isn't installed.

## ⚖️ Responsible use

Use this for content you have the right to download: your own work,
licensed material, or personal use where the law allows it. Respect each
platform's terms of service and copyright.
