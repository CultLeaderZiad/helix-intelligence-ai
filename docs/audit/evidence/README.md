# بيئة الأدلة

- Source snapshot: `eab70cc75bbc2aa8fe841a2c792f72bfd8e7e957`.
- Database: disposable PostgreSQL 16.15، loopback port 55432، `helix_audit_w4`.
- Backend runtime role: `w4_preview`، `NOSUPERUSER NOBYPASSRLS`، عضو `helix_app`؛ migration operator منفصل.
- Backend اتشغّل ببيئة محلية معزولة `env -i` و`USE_MOCKS=false`، من غير provider keys ولا credentials إنتاج. مفيش `.env` أو `.env.local` محلية موجودة في وقت التشغيل؛ `.env.production` ما اتقراش.
- Local test identities اتعملت بس عشان الدخول والـtenant/access checks. مفيش lead/creative/score/testimonial أو AI output اتزرع.
- Screenshots تشمل local empty/error/blocked states، مش دليل إن provider integration شغّال. أي provider execution: **not verified**.
- Fresh `alembic upgrade head` exit 0؛ `alembic check` exit 0؛ compileall exit 0؛ pyflakes exit 1 (127 diagnostics، المصدر من غير fixes).
- HTTP timings دي local preview timings فقط، مش production latency ولا load test.

- Evidence log trailing whitespace واتشالت blank lines في آخر الملفات للتوافق مع diff-check؛ مفيش diagnostic/test result اتفلتر أو اتغير.
