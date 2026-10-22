# Public introduction draft

Value: local, explainable change impact exploration for Python/FastAPI developers using Codex or Claude Code. It connects likely consumers, API contracts and tests to inspectable static evidence before editing code.

## 60-second video

0–8s: “Before replacing password login with OTP, what else should we inspect?” Show examples/shop and run the OTP demo.

8–20s: Open otp.html. Point to the seed and the DEMO badge. Select the login endpoint and its call evidence.

20–35s: Open shared.html. Follow normalization → authentication → login, then normalization → current_user → profile/session. Explain that the UI arrows point in the opposite direction, from consumer to dependency.

35–45s: Filter relations and inspect Depends, the response model and a suggested test. Distinguish literal-URL heuristic candidates from observed call references.

45–53s: Show coverage and unresolved items. “Static references show where to investigate; they do not prove breakage.”

53–60s: Export JSON/Markdown; show the skill's seed-selection workflow. Invite contributors to add tested resolver patterns. Avoid claiming runtime behavior has been verified.

## LinkedIn draft (Persian)

قبل از تغییر یک تابع مشترک، چطور می‌فهمیم کدام endpointها و تست‌ها به بررسی نیاز دارند؟

Change Radar را برای همین مرحله ساخته‌ام: تحلیل محلی Python و FastAPI، انتخاب فایل یا نماد شروع، و دیدن مصرف‌کننده‌های احتمالی همراه با مسیر شواهد و شماره خط.

دمو سه تغییر را بررسی می‌کند: ورود با OTP، تغییر مدل پاسخ و اصلاح تابع مشترک. گزارش HTML آفلاین است و CLI و اسکیل Codex/Claude Code از یک هسته استفاده می‌کنند.

تحلیل ایستا محدودیت دارد؛ import با call یکی نیست و نتیجه خالی تضمین امنیت تغییر نیست. موارد حل‌نشده در گزارش دیده می‌شوند. بازخورد درباره الگوهای واقعی FastAPI و fixtureهای ارزیابی برای مرحله بعد ارزشمند است.

Publication gate: choose a license/owner, validate real agent workflows and perform browser visual QA before describing those as verified. No screenshots were fabricated; none are included because no connected browser was available. This is a draft, not a published post.
