# SEO Search Console MCP

MCP Server برای اتصال Claude / ChatGPT به Google Search Console — تحلیل عملکرد صفحات، پیدا کردن فرصت‌های بهبود، خوندن سایت‌مپ و محتوای صفحات.

**مدل استقرار:** self-host. هر کسی این ریپو رو clone می‌کنه، با Google Cloud project خودش وصل می‌کنه، و روی سرور خودش بالا می‌آره. هیچ سرویس مرکزی‌ای در کار نیست — داده‌ی GSC شما فقط روی سرور خودتون می‌مونه.

---

## پیش‌نیازها

- یک سرور یا حتی یک سیستم شخصی (لپ‌تاپ/سرور خونگی) با Docker و docker-compose نصب‌شده
- یک اکانت Google که در Search Console مالک/کاربر سایت(های) موردنظر باشه
- **بدون نیاز به دامنه** — از [Tailscale](https://tailscale.com) (رایگان) برای گرفتن یک آدرس HTTPS پایدار استفاده می‌کنیم

---

## مرحله ۱: ساخت Google Cloud Project و OAuth Client

1. برو به [Google Cloud Console](https://console.cloud.google.com) و یک project جدید بساز (یا از یکی موجود استفاده کن).
2. از منوی **APIs & Services > Library**، دنبال **Google Search Console API** بگرد و Enable کن.
3. برو به **APIs & Services > OAuth consent screen**:
   - User type: **External**
   - اطلاعات پایه (نام اپ، ایمیل) رو پر کن
   - Scope: `https://www.googleapis.com/auth/webmasters.readonly` رو اضافه کن
   - **⚠️ نکته‌ی حیاتی:** بعد از ساخت، publishing status رو از "Testing" به **"In Production"** تغییر بده (بدون نیاز به تکمیل verification کامل چون زیر ۱۰۰ کاربر هستی). اگه این کار رو نکنی، هر ۷ روز یک‌بار مجبور می‌شی دوباره لاگین کنی چون refresh token در حالت Testing منقضی می‌شه.
4. فعلاً از **Create Credentials > OAuth Client ID** صرف‌نظر کن — Client ID رو بعد از گرفتن آدرس Tailscale (مرحله‌ی ۲) می‌سازیم، چون redirect URI باید از قبل معلوم باشه.

---

## مرحله ۲: نصب Tailscale و گرفتن آدرس ثابت

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

بعد از اجرا کردن پروژه (مرحله‌ی ۴)، سرویس رو با یک URL ثابت و HTTPS در دسترس عموم می‌ذاریم:
```bash
sudo tailscale funnel --bg 8420   # سرویس رو در پس‌زمینه، پایدار، expose می‌کنه
tailscale funnel status           # آدرس نهایی رو اینجا می‌بینی، چیزی شبیه:
                                  # https://your-machine.your-tailnet.ts.net
```

> نکته: در نسخه‌های جدید Tailscale (۱.x به بعد) سینتکس عوض شده — دیگه `tailscale funnel 8420 on` کار نمی‌کنه. حالا `tailscale funnel --bg 8420` (پس‌زمینه) یا `tailscale funnel 8420` (فورگراند) می‌زنی، و برای خاموش کردن `tailscale funnel reset`.

این آدرس بین ری‌استارت‌ها عوض نمی‌شه (برخلاف نسخه‌ی رایگان ngrok)، پس می‌تونی همین الان بری و در Google Cloud Console یک **OAuth Client ID** (نوع: **Web application**) بسازی با:
```
Authorized redirect URI: https://your-machine.your-tailnet.ts.net/oauth/google/callback
```
Client ID و Client Secret رو یادداشت کن.

> اگه بعداً خواستی به‌جای Tailscale از دامنه‌ی خودت (وردست۲۴) و nginx استفاده کنی، فایل `nginx/seo-mcp.conf` همین‌جا در ریپو آماده‌ست — ولی برای استفاده‌ی شخصی فعلی لازم نیست.

---

## مرحله ۳: پیکربندی و اجرا

```bash
git clone <repo-url> seo-mcp
cd seo-mcp
cp .env.example .env
```

`.env` رو باز کن و پر کن:
- `MCP_ACCESS_TOKEN`: یک توکن تصادفی بساز: `openssl rand -hex 32`
- `GOOGLE_CLIENT_ID` و `GOOGLE_CLIENT_SECRET`: از مرحله‌ی ۲
- `GOOGLE_REDIRECT_URI`: همون آدرس Tailscale که در مرحله‌ی ۲ ثبت کردی

بالا بیار:
```bash
docker compose up -d --build
docker compose ps        # باید status "healthy" باشه بعد از چند ثانیه
sudo tailscale funnel --bg 8420   # اگه در مرحله‌ی ۲ هنوز این رو نزده بودی
```

---

## مرحله ۴: اتصال اکانت گوگل (یک‌بار)

با مرورگر برو به:
```
https://your-machine.your-tailnet.ts.net/oauth/google/start
```
با همون اکانت گوگلی که در GSC مالک سایت(هات)ه لاگین کن و دسترسی رو تأیید کن. بعد از تأیید، توکن به‌صورت خودکار ذخیره می‌شه (در volume پایدار، با هر `docker compose restart` از بین نمی‌ره).

چک کن که وصله:
```bash
curl -H "Authorization: Bearer <MCP_ACCESS_TOKEN>" https://your-machine.your-tailnet.ts.net/health
```

---

## مرحله ۵: اضافه کردن به Claude / ChatGPT

آدرس MCP همیشه به `/mcp` ختم می‌شه: `https://your-machine.your-tailnet.ts.net/mcp`

### Claude (Desktop یا claude.ai)
`MCP_AUTH_ENABLED=true` بذار. بعد Settings → Connectors → Add custom connector → آدرس `https://your-machine.your-tailnet.ts.net/mcp` رو وارد کن → در Advanced settings توکن رو به‌عنوان Bearer/Authorization header بذار.

### ChatGPT
ChatGPT در developer mode فقط **OAuth / No Auth / Mixed** رو پشتیبانی می‌کنه و راهی برای فرستادن Bearer token ثابت نداره. پس لایه B رو خاموش کن:

1. در `.env` مقدار `MCP_AUTH_ENABLED=false` بذار و `docker compose up -d --build` رو دوباره بزن.
2. **Developer Mode** رو فعال کن (Settings → Apps & Connectors → Advanced settings).
3. Create app → Connection: **Server URL** = `https://your-machine.your-tailnet.ts.net/mcp` → Authentication: **No Auth** → Create.

با خاموش بودن لایه B، تنها محافظ دسترسی، مخفی بودن آدرس Tailscale Funnel است (سرویس read-only است، ولی هر کسی که آدرس رو بدونه می‌تونه داده‌ی GSC تو رو بخونه — آدرس رو خصوصی نگه دار).

> توجه: چون این connector فقط read-only هست (هیچ ابزاری داده‌ای رو تغییر نمی‌ده)، حتی با پلن‌های Plus/Pro فردی هم روی ChatGPT کار می‌کنه.

---

## ابزارهای موجود

| ابزار | کاربرد |
|---|---|
| `list_sites` | لیست سایت‌های تأییدشده در GSC |
| `get_search_analytics` | آمار کلیک/ایمپرشن/CTR/پوزیشن با فیلتر دلخواه |
| `find_striking_distance_pages` | صفحاتی که پوزیشن ۵-۱۵ دارن و ایمپرشن‌شون بالاست — بهترین فرصت بهبود |
| `inspect_url` | وضعیت ایندکس و مشکلات کاوریج یک URL |
| `fetch_sitemap` | استخراج لیست URL از یک سایت‌مپ (شامل sitemap index) |
| `fetch_page_content` | خوندن تایتل/متادیسکریپشن/هدینگ/متن اصلی یک صفحه |

نمونه‌ی استفاده در چت: *"صفحاتی از سایتم که پوزیشن ۵ تا ۱۵ دارن رو پیدا کن، بعد محتوای سه‌تای اولشون رو بخون و بگو چی کم دارن که رنک بهتر بگیرن."*

---

## عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| `invalid_grant` بعد از چند روز | یعنی OAuth consent screen رو روی "Testing" گذاشتی. برو مرحله‌ی ۱ و به "In Production" تغییرش بده، بعد دوباره از `/oauth/google/start` وصل شو. |
| ۴۰۱ از سمت MCP | مطمئن شو هدر `Authorization: Bearer <token>` دقیقاً با `MCP_ACCESS_TOKEN` در `.env` یکیه (فقط وقتی `MCP_AUTH_ENABLED=true`). |
| `Error creating connector` در ChatGPT / لاگ `Invalid Host header` و کد ۴۲۱ | محافظت DNS-rebinding ترنسپورت MCP، هدر Host آدرس عمومی رو رد می‌کنه. اپ این host رو خودکار از `GOOGLE_REDIRECT_URI` مجاز می‌کنه؛ مطمئن شو `GOOGLE_REDIRECT_URI` دقیقاً همون آدرس Tailscale/دامنه‌ی عمومیته و بعد از تغییرش `docker compose up -d --build` بزنی. |
| کانتینر مدام restart می‌شه | `docker compose logs seo-mcp` رو چک کن؛ اگه به خاطر `mem_limit: 512m` کشته می‌شه (OOM)، در `docker-compose.yml` بیشترش کن. |
| بعد از deploy جدید باید دوباره Google رو وصل کنم | یعنی volume پایدار نبود. مطمئن شو `seo-mcp-data` در `docker-compose.yml` واقعاً persist می‌شه و پاک نمی‌کنیش. |
| صفحه در گوگل ایندکس شده | چک کن هدر `X-Robots-Tag` واقعاً برمی‌گرده: `curl -I https://your-machine.your-tailnet.ts.net`. یادت باشه Tailscale Funnel این هدر رو خودش اضافه نمی‌کنه، این وظیفه‌ی خود اپ (Prompt 5) هست. |
| `tailscale funnel status` چیزی نشون نمی‌ده | مطمئن شو `tailscale funnel --bg 8420` رو زدی (سینتکس قدیمی `... 8420 on` دیگه کار نمی‌کنه) و کانتینر واقعاً روی `127.0.0.1:8420` گوش می‌ده (`docker compose ps`). |

---

## محدودیت‌های شناخته‌شده

- این deployment فقط به یک اکانت گوگل (و سایت‌های زیرش) وصل می‌شه. برای چند مشتری/چند اکانت جدا روی یک سرور، معماری فعلی کافی نیست (نیاز به چندمستأجری واقعی داره).
- `fetch_page_content` صفحات JavaScript-heavy (SPA بدون SSR) رو ممکنه ناقص بخونه.