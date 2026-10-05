# بوت تليكرام لتحميل الفيديوهات 🎬

بوت تليكرام يحمّل الفيديوهات من مواقع التواصل الاجتماعي. أرسل رابطاً،
اختر الجودة، واستلم الملف في المحادثة.

> English documentation follows the Arabic section below.

---

## ✨ الميزات

- **أكثر من ١٠٠٠ موقع** عبر `yt-dlp`: يوتيوب، تيك توك، إنستغرام، فيسبوك،
  X/تويتر، ريديت، سناب شات، تويتش، فيميو، ساوندكلاود وغيرها.
- **بدون كوكيز ولا تسجيل دخول**: عند الرفض، يعيد البوت المحاولة منتحلاً
  عميلاً مختلفاً — تطبيق تلفاز، ثم هاتف، ثم متصفح حقيقي ببصمة TLS كاملة.
- **تحديث تلقائي لـ yt-dlp** كل ليلة، وهو أهم عامل في استمرار العمل.
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
- **اشتراك إجباري** في قنوات تحدّدها، مع أزرار انضمام وزر تحقّق.
- **تحميل واحد لعدة طالبين**: الرابط المنتشر الذي يرسله عشرة أشخاص في وقت
  واحد يُحمَّل مرة واحدة ويُرسل للجميع.
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

**على سيرفر VPS بأمر واحد (الأسهل والموصى به):**

```bash
curl -fsSL https://raw.githubusercontent.com/lolykapmo-cyber/jalal/claude/epic-euler-mfpvcq/deploy.sh -o deploy.sh
less deploy.sh          # اقرأه قبل تشغيله بصلاحيات root
sudo bash deploy.sh
```

يُنشئ السكربت مجلداً خاصاً (`/opt/jalal`) ومستخدم نظام مخصّصاً، ويثبّت
ffmpeg والاعتماديات، ويسجّل خدمة systemd تعمل تلقائياً عند الإقلاع، ويجدول
تحديث yt-dlp الليلي. يطلب التوكن في موجّه مخفي — فلا يظهر في سجل الأوامر
ولا في قائمة العمليات. تشغيله مرة ثانية يحدّث الكود ويحفظ التوكن.

```bash
journalctl -u jalal-bot -f      # متابعة السجلات
systemctl restart jalal-bot     # إعادة التشغيل
```

**بـ Docker (ffmpeg مُضمَّن):**

```bash
docker compose up -d
docker compose logs -f
```

**محلياً بـ Python:**

> يتطلب **Python 3.10 أو أحدث**. يوتيوب-dlp وpython-telegram-bot وcurl_cffi
> كلها أسقطت ما قبلها. سكربت النشر يثبّت نسخة حديثة تلقائياً عند الحاجة.

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
| `MAX_DOWNLOAD_ATTEMPTS` | `4` | عدد العملاء المختلفين قبل الاستسلام |
| `REQUIRED_CHANNELS` | فارغ | قنوات الاشتراك الإجباري |
| `MEMBERSHIP_FAIL_OPEN` | `true` | السماح بالمرور إن تعذّر التحقّق |
| `MIN_FREE_DISK_MB` | `1024` | أقل مساحة حرة قبل بدء التحميل |
| `DEFAULT_LANGUAGE` | `ar` | `ar` أو `en` |
| `DEFAULT_QUALITY` | `best` | `best` / `1080` / `720` / `480` / `360` / `audio` |
| `ASK_QUALITY` | `true` | `false` = تحميل فوري بالجودة الافتراضية |
| `COOKIES_FILE` | — | اختياري وغير مستحسن؛ البوت لا يحتاجه |
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

## 🛡 الموثوقية بدون كوكيز

معظم حالات "الرفض" ليست عن الحساب، بل عن **العميل الذي طلب**. فنفس الرابط
الذي يُرفض من متصفح عادي ينجح غالباً إذا طُلب كتطبيق تلفاز. البوت يستغل هذا:
لكل منصّة سلّم محاولات مرتّب، وعند الفشل ينزل للدرجة التالية تلقائياً.

| المنصّة | ترتيب المحاولات |
|--------|----------------|
| يوتيوب | تلفاز → تلفاز مبسّط → Android VR → iOS → Safari بانتحال Chrome |
| إنستغرام وفيسبوك | انتحال Chrome → انتحال Safari → الافتراضي |
| تيك توك | الافتراضي → انتحال Chrome → مضيف API بديل |
| X/تويتر | syndication → graphql بانتحال → الافتراضي |

الانتحال هنا ليس مجرد تغيير `User-Agent`، بل **بصمة TLS كاملة** عبر
`curl_cffi` — وهو ما يتجاوز معظم الحجب القائم على كشف الأتمتة.

**والأهم: التحديث التلقائي.** حين تغيّر منصّة شيئاً، يصدر إصلاح في `yt-dlp`
خلال أيام. سكربت النشر يجدول تحديثاً ليلياً — هذا وحده يمنع أغلب الانقطاعات.

### ما لا يمكن حلّه هندسياً

لأكون صريحاً: **لا توجد طريقة مضمونة ١٠٠٪.** المحتوى الخاص فعلاً (حساب
مُقفل، منشور لمتابعين فقط، فيديو محذوف) لا يمكن تحميله بدون بيانات دخول —
وهذا ليس قيداً أستطيع هندسته، بل هو الغرض من الخصوصية. البوت يميّز الحالتين:
يعيد المحاولة عند الحجب، ويتوقف فوراً ويشرح السبب عند الخصوصية الحقيقية.

> الكوكيز ما زالت مدعومة عبر `COOKIES_FILE` لكنها **معطّلة افتراضياً وغير
> مستحسنة**: تمنح وصولاً كاملاً للحساب، وتنتهي صلاحيتها، وقد تُحظر عليها
> المنصّة.

---

## 🔐 الاشتراك الإجباري

لمنع المستخدم من استخدام البوت قبل الاشتراك في قنواتك:

```env
REQUIRED_CHANNELS=@nextgenshop1,@Nexus_tv_1
```

تقبل أيضاً روابط `t.me`، وقناة خاصة بصيغة `-100123...|https://t.me/+رابط_الدعوة`،
وعنواناً مخصّصاً للزر بصيغة `@اسم|العنوان`.

> **شرط لا غنى عنه:** البوت يجب أن يكون **مشرفاً** في كل قناة. تليكرام لا
> يسمح لبوت غير مشرف بقراءة أعضاء القناة، فلا يستطيع التحقّق أصلاً.

عند الفشل في التحقّق (البوت ليس مشرفاً مثلاً) يسمح البوت بالمرور ويسجّل
تحذيراً واضحاً، لأن خطأً في الإعداد يجب ألا يُغلق بوتاً سليماً أمام الجميع.
لعكس ذلك: `MEMBERSHIP_FAIL_OPEN=false`.

ويُتذكّر الاشتراك المُتحقَّق منه ٥ دقائق (`MEMBERSHIP_CACHE_SECONDS`) تقليلاً
للضغط على تليكرام. أما عدم الاشتراك فلا يُحفظ أبداً، ليعمل زر «تحققت» فوراً.

---

## 📈 عند الاستخدام الكثيف

ثلاث نقاط تحدّد سلوك البوت تحت الحمل:

1. **إعادة الترميز هي عنق الزجاجة**، وليست الشبكة. ffmpeg يستهلك المعالج
   بشدة. اجعل `MAX_CONCURRENT_DOWNLOADS` قريباً من عدد أنوية المعالج —
   ورفعه أكثر من ذلك يُبطئ الجميع بدل أن يُسرّعهم.
2. **سيرفر Bot API محلي يُلغي الحاجة لإعادة الترميز** أصلاً (حد ٢ غيغابايت
   بدل ٥٠ ميغابايت). هذا أكبر تحسين ممكن للأداء تحت الحمل، وليس مجرد
   زيادة في الحد الأقصى.
3. **عنوان IP واحد لمركز بيانات يُحجب أسرع** من عنوان منزلي. إن بدأت ترى
   `err_login` بكثرة على يوتيوب تحديداً، فذلك سببه الأرجح — عالجه بـ
   `PROXY` أو بـ `COOLDOWN_SECONDS` أعلى، لا بالكوكيز.

**توحيد التحميلات** هو أهم ما يحمي السيرفر تحت الضغط: حين يرسل عشرة أشخاص
نفس الرابط في نفس الدقيقة، يُحمَّل مرة واحدة ويُرسل للتسعة الباقين عبر
`file_id` — عشرة تحميلات تصير واحداً. ويبقى محفوظاً بعدها في الذاكرة المؤقتة.

ويرفض البوت التحميل بأدب إن قلّت المساحة الحرة عن `MIN_FREE_DISK_MB`، بدل
أن يملأ القرص ويُسقط الخدمة.

**البقاء بعد إعادة التشغيل** مضمون: الخدمة مُفعّلة عبر systemd وتبدأ تلقائياً
مع الإقلاع (`systemctl is-enabled jalal-bot`)، و`Restart=always` يعيدها بعد أي
انهيار، و`StartLimitIntervalSec=0` يمنع systemd من الاستسلام بعد عدة محاولات
متتالية — وهو سلوكه الافتراضي الذي كان سيوقف البوت نهائياً.

---

## 🧪 الاختبارات

```bash
pip install -r requirements-dev.txt
python -m pytest
```

١٧٨ اختباراً، كلها تعمل بدون إنترنت — بما فيها اختبارات تُثبت أن سلّم إعادة
المحاولة يتجاوز الحجب، وأن عشرة طلبات متزامنة تُنتج تحميلاً واحداً، وأن فشل
التحقّق من الاشتراك لا يُغلق البوت أمام الجميع. اختبارات ffmpeg تُتخطّى
تلقائياً إن لم يكن مثبّتاً.

---

## 🗂 بنية المشروع

```
deploy.sh              تثبيت كامل على VPS بأمر واحد
bot/
├── __main__.py        نقطة الدخول: python -m bot
├── app.py             تجميع التطبيق وتسجيل المعالجات
├── config.py          قراءة الإعدادات من البيئة والتحقّق منها
├── downloader.py      غلاف yt-dlp: الصيغ، الإلغاء، تصنيف الأخطاء
├── strategies.py      سلالم إعادة المحاولة التي تُغني عن الكوكيز
├── membership.py      بوابة الاشتراك الإجباري
├── inflight.py        توحيد التحميلات المتزامنة لنفس الرابط
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

## 🔧 حل المشكلات

**`No matching distribution found for yt-dlp>=2025.1.15`**

Python لديك قديم (أقل من 3.10). يحدث هذا على Ubuntu 20.04 الذي يأتي بـ 3.8.
pip يتراجع صامتاً لآخر نسخة تدعم 3.8 — وهي من 2024 ولم تعد تعمل مع المواقع
الحالية. أعد تشغيل السكربت:

```bash
sudo bash deploy.sh
```

يجرّب السكربت ثلاث طرق بالترتيب للحصول على Python حديث:

1. مفسّر موجود على النظام أصلاً
2. حزم التوزيعة (مستودع deadsnakes على أوبنتو)
3. **نسخة CPython جاهزة يُنزّلها `uv`** — حوالي ٣٠ ميغابايت، بلا مستودعات
   ولا تصريف، وتعمل على أي توزيعة Linux. تُثبَّت داخل `/opt/jalal/python`
   ليقرأها مستخدم الخدمة.

الطريقة الثالثة هي شبكة الأمان: إن فشلت الأولى والثانية — كما يحدث حين لا
يصل سيرفرك لمستودع deadsnakes — فهي تعمل على أي حال.

ولتحديد نسخة أخرى: `sudo PYTHON_SERIES=3.11 bash deploy.sh`

**البوت لا يرد على تليكرام**

```bash
systemctl status jalal-bot
journalctl -u jalal-bot -n 50 --no-pager
```

السبب الأشيع توكن خاطئ في `/opt/jalal/.env`.

**`err_login` كثيراً على يوتيوب**

عنوان IP الخاص بمركز البيانات محجوب. عالجه بـ `PROXY` أو `COOLDOWN_SECONDS`
أعلى — لا بالكوكيز.

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
- **No cookies, no login**: when a site refuses, the bot retries as a
  different client — TV app, then phone app, then a real browser with a
  full TLS fingerprint.
- **Nightly yt-dlp updates**, the single biggest factor in staying working.
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
- **Mandatory channel subscription**, with join buttons and a verify button.
- **One download for many askers**: a link ten people send at once is
  fetched once and re-sent to the rest by `file_id`.
- **Optional allow-list** to keep the bot private.

## 🚀 Quick start

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Configure it:
   ```bash
   git clone https://github.com/lolykapmo-cyber/jalal.git
   cd jalal
   cp .env.example .env     # then put your token in BOT_TOKEN
   ```
3. Run it — on a VPS, one command does everything:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/lolykapmo-cyber/jalal/claude/epic-euler-mfpvcq/deploy.sh -o deploy.sh
   less deploy.sh          # read it before running it as root
   sudo bash deploy.sh
   ```
   It creates `/opt/jalal` and a dedicated system user, installs ffmpeg and
   the dependencies, registers a systemd service that survives reboots, and
   schedules the nightly yt-dlp update. The token is read from a hidden
   prompt, so it never reaches your shell history or the process list.
   Re-running it updates the code and keeps the token.

   Or with Docker, or locally:
   ```bash
   docker compose up -d                    # ffmpeg included
   pip install -r requirements.txt && python -m bot
   ```

Running locally needs **Python 3.10+** (yt-dlp, python-telegram-bot and
curl_cffi all dropped anything older) and `ffmpeg` on `PATH` for merging,
thumbnails, MP3 extraction and shrinking oversized files. `deploy.sh`
installs a newer Python itself when the system one is too old — which it is
on Ubuntu 20.04, where `python3` is still 3.8.

## 📋 Commands

`/start` · `/help` · `/settings` · `/quality` · `/lang` · `/cancel` ·
`/stats` (admins)

## ⚙️ Configuration

Every setting is an environment variable, documented inline in
[`.env.example`](.env.example). Only `BOT_TOKEN` is required.

`MAX_DOWNLOAD_ATTEMPTS` (default 4) controls how many different clients
the bot tries before giving up.

## 📦 About the 50 MB limit

The public Bot API caps bot uploads at 50 MB. The bot picks a format that
fits, re-encodes with ffmpeg when it doesn't, and tells you when a video is
too long to shrink without ruining it. To upload up to 2 GB, run a local
Bot API server (see the commented block in `docker-compose.yml`) and set
`TELEGRAM_API_ROOT`; the limit then raises itself to 2000 MB.

## 🛡 Reliability without cookies

Most "blocked" failures are not about the account — they are about **which
client asked**. The same link a browser gets refused for will often serve
fine to a TV app. The bot leans on that: every platform has an ordered
ladder of attempts, and a rejection drops it to the next rung automatically.

| Platform | Attempt order |
|----------|---------------|
| YouTube | tv → tv_simply → android_vr → ios → web_safari w/ Chrome impersonation |
| Instagram, Facebook | Chrome impersonation → Safari impersonation → default |
| TikTok | default → Chrome impersonation → alternate API host |
| X/Twitter | syndication → graphql w/ impersonation → default |

Impersonation here is not a swapped `User-Agent`: it is a **full TLS
fingerprint** via `curl_cffi`, which is what gets past most
automation-detection blocking.

**The bigger lever is the nightly update.** When a platform changes
something, a `yt-dlp` fix usually lands within days. The deploy script
schedules a nightly refresh; that alone prevents most outages.

### What engineering cannot fix

To be straight about it: **there is no 100% guaranteed method.** Genuinely
private content — a locked account, a followers-only post, a deleted video
— cannot be fetched without credentials, and that is the point of privacy
rather than a limitation to engineer around. The bot distinguishes the two
cases: it retries on a block, and stops immediately with an explanation on
real privacy.

> Cookies are still supported via `COOKIES_FILE`, but they are **off by
> default and not recommended**: they grant full account access, they
> expire, and platforms do ban the accounts behind them.

---

## 🔐 Mandatory subscription

```env
REQUIRED_CHANNELS=@nextgenshop1,@Nexus_tv_1
```

Also accepts `t.me` links, a private channel as
`-100123...|https://t.me/+invite`, and a custom button label as `@name|Label`.

> **The bot must be an administrator of every listed channel.** Telegram
> refuses the membership query otherwise, so the requirement simply cannot
> be checked.

When the check cannot be answered the bot lets the user through and logs a
loud warning, because one misconfiguration should not lock everybody out of
a working bot. Set `MEMBERSHIP_FAIL_OPEN=false` to invert that. A verified
membership is remembered for `MEMBERSHIP_CACHE_SECONDS`; a failure is never
cached, so the verify button reacts immediately.

---

## 📈 Under heavy use

Three things decide how the bot behaves at load:

1. **Transcoding is the bottleneck**, not bandwidth. ffmpeg is CPU-bound,
   so keep `MAX_CONCURRENT_DOWNLOADS` near your core count — pushing it
   higher makes everyone slower, not faster.
2. **A local Bot API server removes transcoding entirely** (2 GB instead of
   50 MB). That is the single largest throughput win available, not merely
   a bigger size cap.
3. **One datacenter IP gets blocked faster** than a residential one. Lots of
   `err_login` on YouTube specifically is usually this — address it with
   `PROXY` or a higher `COOLDOWN_SECONDS`, not with cookies.

**Download coalescing** is what protects the server at load: when ten people
send the same link in the same minute, it is fetched once and the other nine
are sent the finished file by `file_id`. Ten downloads become one, and the
result stays in the upload cache afterwards.

The bot also refuses politely when free space falls below `MIN_FREE_DISK_MB`
rather than filling the volume and taking the service down with it.

**Surviving a reboot** is handled: the unit is enabled, so it starts at boot
(`systemctl is-enabled jalal-bot`), `Restart=always` brings it back after a
crash, and `StartLimitIntervalSec=0` stops systemd giving up after a few
rapid restarts, which is its default and would otherwise stop the bot for
good.

## 🧪 Tests

```bash
pip install -r requirements-dev.txt && python -m pytest
```

178 tests, all offline — including ones that prove the retry ladder gets
past a block, that ten simultaneous requests cause one download, and that a
subscriber check which cannot be answered does not lock anyone out. The ffmpeg-backed
tests skip themselves if ffmpeg isn't installed.

## 🔧 Troubleshooting

**`No matching distribution found for yt-dlp>=2025.1.15`** — your Python is
older than 3.10 (Ubuntu 20.04 ships 3.8). pip quietly falls back to the last
release that supported it, from 2024, which current sites reject. Re-run
`sudo bash deploy.sh`: it tries the system Python, then distro packages
(deadsnakes on Ubuntu), then downloads a standalone CPython with `uv` — about
30 MB, no repositories and no compiling, into `/opt/jalal/python` where the
service user can read it. That third rung is the safety net for hosts that
cannot reach deadsnakes. Pick another series with
`sudo PYTHON_SERIES=3.11 bash deploy.sh`.

**The bot doesn't answer** — check `systemctl status jalal-bot` and
`journalctl -u jalal-bot -n 50`. Usually a wrong token in `/opt/jalal/.env`.

**Frequent `err_login` on YouTube** — your datacenter IP is blocked. Use
`PROXY` or a higher `COOLDOWN_SECONDS`, not cookies.

---

## ⚖️ Responsible use

Use this for content you have the right to download: your own work,
licensed material, or personal use where the law allows it. Respect each
platform's terms of service and copyright.
