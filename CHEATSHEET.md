# SEO MCP — چیت‌شیت

## وضعیت سرویس

| چک | دستور |
|---|---|
| وضعیت کانتینر | `docker compose ps` |
| لاگ‌ها | `docker compose logs seo-mcp --tail 50` |
| Health | `curl http://127.0.0.1:8420/health` |
| توکن گوگل | `docker exec seo-mcp test -f /app/data/google_token.json && echo OK` |
| تست‌ها | `python3 -m pytest tests/ -q` |

**Endpoint اصلی:** `http://127.0.0.1:8420/mcp` (عمومی: `https://<host>/mcp`)

---

## ۶ ابزار MCP

### 1. `list_sites`
لیست propertyهای GSC — **همیشه اول این رو بزن.**

| پارامتر | الزامی |
|---|---|
| — | — |

**خروجی:** `{"sites": [{"site_url", "permission_level"}, ...]}`

**پرامپت نمونه:**
```
چه سایت‌هایی توی Search Console من ثبت شده؟
```

---

### 2. `get_search_analytics`
آمار کلیک / ایمپرشن / CTR / پوزیشن با dimension دلخواه.

| پارامتر | نوع | پیش‌فرض | توضیح |
|---|---|---|---|
| `site_url` | string | — | دقیقاً مثل `list_sites` (مثلاً `sc-domain:bitpin.ir`) |
| `start_date` | string | — | `YYYY-MM-DD` |
| `end_date` | string | — | `YYYY-MM-DD` |
| `dimensions` | list | — | `query`, `page`, `date`, `device`, `country` |
| `filters` | list | null | فیلتر dimension (AND) |
| `row_limit` | int | 100 | ۱ تا ۲۵۰۰۰ |

**فیلتر نمونه:**
```json
{"dimension": "query", "operator": "excludingRegex", "expression": "bitpin|بیت.?پین"}
```

**اپراتورها:** `equals`, `notEquals`, `contains`, `notContains`, `includingRegex`, `excludingRegex`

**پرامپت‌های نمونه:**
```
پربازدیدترین ۲۰ کوئری sc-domain:bitpin.ir در ۲۸ روز گذشته
```
```
عملکرد sc-domain:bitpin.ir به تفکیک device و country در ۹۰ روز اخیر
```
```
کوئری‌های sc-domain:bitpin.ir با ایمپرشن بالا ولی CTR پایین
```

---

### 3. `find_striking_distance_pages`
صفحات نزدیک صفحه اول — بهترین فرصت بهبود سریع.

| پارامتر | نوع | پیش‌فرض |
|---|---|---|
| `site_url` | string | — |
| `start_date` | string | — |
| `end_date` | string | — |
| `position_min` | float | 5.0 |
| `position_max` | float | 15.0 |
| `min_impressions` | float | 50.0 |

**پرامپت‌های نمونه:**
```
صفحه‌های striking distance سایت sc-domain:bitpin.ir در ماه اخیر
```
```
صفحه‌های sc-domain:bitpin.ir با پوزیشن ۵–۱۵ و حداقل ۱۰۰ ایمپرشن
```

---

### 4. `inspect_url`
وضعیت ایندکس و coverage یک URL.

| پارامتر | نوع |
|---|---|
| `site_url` | string |
| `inspection_url` | string (URL کامل) |

**خروجی:** `verdict`, `coverageState`, `mobileUsability`

**پرامپت نمونه:**
```
وضعیت ایندکس https://bitpin.ir/blog/post رو در GSC بررسی کن
```

---

### 5. `fetch_sitemap`
خواندن sitemap (شامل sitemap index).

| پارامتر | نوع |
|---|---|
| `sitemap_url` | string |

**خروجی:** `{"pages": [...], "count": N}`

**پرامپت نمونه:**
```
سایت‌مپ https://bitpin.ir/sitemap.xml رو بخون و تعداد URLها رو بگو
```

---

### 6. `fetch_page_content`
استخراج title، meta، headings، متن اصلی.

| پارامتر | نوع |
|---|---|
| `url` | string |

**خروجی موفق:** `title`, `meta_description`, `headings`, `main_text`, `word_count`

**پرامپت نمونه:**
```
تایتل و متادیسکریپشن https://bitpin.ir/page رو بیار و از نظر سئو ارزیابی کن
```

---

## سناریوهای ترکیبی (پیشنهادی)

```
صفحه‌های striking distance sc-domain:bitpin.ir رو پیدا کن،
محتوای ۳ تای اول رو بخون و بگو چی کم دارن.
```

```
سایت‌مپ https://bitpin.ir/sitemap.xml رو بخون،
وضعیت ایندکس ۵ URL اول رو چک کن.
```

```
۱۰ کوئری برتر sc-domain:bitpin.ir در ۷ روز اخیر (بدون برند)،
به‌همراه صفحه‌ی هر کوئری.
```

---

## مدیریت و اتصال

```bash
# بالا آوردن
docker compose up -d --build

# اتصال اکانت گوگل (یک‌بار)
# https://<host>/oauth/google/start

# Tailscale Funnel
sudo tailscale funnel --bg 8420
tailscale funnel status
```

**Claude:** `MCP_AUTH_ENABLED=true` + Bearer token در connector  
**ChatGPT:** `MCP_AUTH_ENABLED=false` + Authentication: No Auth

---

## عیب‌یابی سریع

| مشکل | راه‌حل |
|---|---|
| ۴۰۱ | `MCP_ACCESS_TOKEN` و هدر `Authorization: Bearer` |
| ۴۲۱ Invalid Host | `GOOGLE_REDIRECT_URI` = آدرس عمومی واقعی |
| `invalid_grant` | OAuth consent → In Production، دوباره `/oauth/google/start` |
| داده GSC خالی | ۲–۳ روز تأخیر GSC؛ تاریخ‌ها رو عقب‌تر ببر |
| SPA ناقص | `fetch_page_content` JS اجرا نمی‌کنه |

---

## پرامپت‌های بیشتر

فایل [`PROMPTS.md`](PROMPTS.md) مجموعه‌ی کامل‌تری از جمله‌های آماده دارد.
