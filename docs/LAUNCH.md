# Draft introduction · experimental 0.1

Do not post this automatically. Select a license/copyright holder and complete
browser acceptance before declaring the downloadable open-source preview ready.
The local package is 0.1.0a1; no public release/tag/package upload has been made.

## Reproducible 60-second demo

Preparation: install the checkout and run `python scripts/preview.py`. Browser steps
below are the planned recording script, not a claim that browser QA has passed.

0–8s: Ask “اگر وابستگی احراز هویت را تغییر بدهم، چه endpointهایی تحت‌تأثیرند؟”
Show examples/preview/security.py and the natural request in the agent.

8–18s: Show the actual CLI command:
`change-radar impact examples/preview --seed security.py::read_token --depth 8`.
The standalone CLI receives an explicit seed; the agent chooses it from the request.

18–35s: Open .change-radar/preview/auth.html. Follow reverse impact from read_token
through current_user and the CurrentUser alias to listing and me. Point out that
UI arrows point consumer→dependency. Select the alias and show security.py:13 and
its keyword Depends witness, then routes.py:9 and :14 consumer annotations.

35–45s: Open models.html. Show Item→Page→listing impact with models.py:9. State that
this is a type-reference dependency, not proof of serialization failure.

45–53s: Show the existing HTTP test candidate, labeled heuristic, and the manual
coverage list. Export JSON/Markdown only after manually accepting browser behavior.

53–60s: Show the bounded public evaluation result: both scoped recalls improved,
but ORM composition adds one labeled false positive. Invite fixture-based feedback.
No “most accurate”, “production ready” or general 100% accuracy claim.

## پیشنویس لینکدین فارسی

نسخه آزمایشی ۰.۱ Change Radar: پیش از تغییر کد، مصرف‌کننده‌های احتمالی را با شاهد ببینیم.

تمرکز این ابزار روی Python و FastAPI است. در این مرحله دو الگوی رایج اضافه شده:
وابستگی‌های مشترک Annotated/Depends و مدل‌های تو‌در‌تو. گزارش محلی، مسیر رسیدن
از نماد شروع به endpoint و شماره خط شواهد را نشان می‌دهد.

تحلیل پایه آفلاین است و کد یا تست مخزن هدف را اجرا نمی‌کند. CLI و اسکیل از یک
هسته استفاده می‌کنند. رفتار Codex روی یک مثال جدا بررسی شده؛ آزمون واقعی Claude
Code هنوز انجام نشده است.

ارزیابی روی یک مخزن عمومی با commit و برچسب‌های ثابت، پوشش بهتری نشان داد؛ در عین
حال یک مثبت کاذب ناشی از رابطه‌های ORM باقی ماند. این نتایج ادعای دقت عمومی نیستند.
تحلیل ایستا محل بررسی را پیشنهاد می‌کند، نه خرابی قطعی یا تضمین ایمنی تغییر.

برای تکمیل معرفی، تأیید دستی مرورگر و تصمیم مالک درباره لایسنس هنوز لازم است.
بازخورد همراه با مثال کوچک و انتظار مشخص، برای مرحله بعد مفید است.
