# شروع سریع Change Radar

این ابزار پیش از تغییر کد Python و FastAPI، مصرف‌کننده‌های احتمالی و زنجیره شواهد را نشان می‌دهد. تحلیل ایستا است؛ نتیجه خالی به معنی امن بودن تغییر نیست.

در ریشه پروژه اجرا کنید:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python scripts/demo.py
```

فایل `.change-radar/demo/shared.html` را در مرورگر باز کنید. گزارش آفلاین و مستقل است. روی یک نماد کلیک کنید تا مسیر اثر و شماره خط شاهد را ببینید. فلش از مصرف‌کننده به وابستگی اشاره می‌کند. جست‌وجو، فیلتر نوع رابطه و عمق، جابه‌جایی گراف و تمرکز روی یک گره در دسترس است.

سه دمو: `otp.html` برای تغییر ورود، `response.html` برای تغییر مدل پاسخ و `shared.html` برای تابع مشترک. خروجی JSON و Markdown هم در همان پوشه تولید می‌شود.

برای پروژه خودتان:

```bash
.venv/bin/change-radar scan '/path/to/project'
.venv/bin/change-radar impact '/path/to/project' \
  --seed 'app/services.py::authenticate' --depth 6 \
  --request 'تغییر ورود از پسورد به OTP' \
  --format html --output /tmp/my-change-radar.html
```

گزینه request فقط عنوان گزارش است؛ CLI متن طبیعی را تفسیر معنایی نمی‌کند. مسیر و نام دقیق seed را از scan پیدا کنید یا با اسکیل از ایجنت بخواهید آن را با شاهد انتخاب کند. فایل خروجی نباید از قبل موجود باشد. اجرای تحلیل، کد و تست‌های مخزن هدف را اجرا نمی‌کند.

برای نصب اسکیل ابتدا dry-run بگیرید؛ سپس همان دستور را بدون آن اجرا کنید:

```bash
.venv/bin/change-radar install-skill --agent codex --scope project --root /path/to/project --dry-run
.venv/bin/change-radar install-skill --agent claude --scope project --root /path/to/project --dry-run
```

محدودیت‌های تحلیل در گزارش و [راهنمای فنی](ANALYSIS.md) آمده‌اند. فراخوانی پویا، تغییر دقیق فیلد مدل و dispatch نمونه‌ها کامل حل نمی‌شوند. گزارش‌ها شامل نام فایل، نماد و مسیر API هستند؛ پیش از اشتراک‌گذاری بررسی کنید. برای اسکن اینترنت و API key لازم نیست؛ نصب ابزار ساخت ممکن است اینترنت بخواهد.

## نسخه آزمایشی ۰.۱

برای دموی alias احراز هویت و مدل تو‌در‌تو، `.venv/bin/python scripts/preview.py` را اجرا و `.change-radar/preview/auth.html` یا `models.html` را باز کنید. نسخه بسته 0.1.0a1 است. رفتار واقعی Codex روی یک مثال جدا بررسی شد؛ بررسی مرورگر و Claude Code انجام نشده است. انتخاب لایسنس و تأیید دستی مرورگر هنوز مانع اعلام آمادگی کامل معرفی عمومی‌اند. [وضعیت دقیق](PREVIEW.md) و [چک‌لیست مرورگر](BROWSER_ACCEPTANCE.md).
