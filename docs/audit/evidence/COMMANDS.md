# أوامر التحقق ونتايجها

Snapshot: `eab70cc75bbc2aa8fe841a2c792f72bfd8e7e957`؛ audit docs فقط. Node 24.22.0، pnpm 9.15.4، Python 3.12 محليًا؛ PostgreSQL 16.15. log files تحت المجلد ده. الاختبارات اللي محتاجة mock تستخدم الموجود في tests بس؛ مفيش mock اتعرض كمنتج أو provider success في الـbrowser.

| Command | Exit | النتيجة / الدليل |
|---|---:|---|
| `git rev-parse fix/intelligence-W4` | 0 | `eab70cc75bbc2aa8fe841a2c792f72bfd8e7e957` وقت إنشاء audit branch |
| `git diff --stat 5b45806..eab70cc` | 0 | 218 files، 20,630 insertions و5,995 deletions؛ حجم التغيير مش دليل جودة |
| `pnpm typecheck` | 2 | 483 diagnostics؛ [typecheck.log](typecheck.log) |
| `pnpm lint` | 1 | 159 errors، zero warnings؛ [lint.log](lint.log) |
| `pnpm test` | 0 | 5 Node + 110 Vitest tests، 14 Vitest files؛ [frontend-tests.log](frontend-tests.log) |
| `pnpm build` | 0 | 1,982 modules، 14.99s؛ raw/gzip sizes في [build.log](build.log)؛ tracked generated files اتردّت بعد القياس |
| `python -m compileall -q app` من backend | 0 | [compileall.log](compileall.log)؛ empty log هنا معناه مفيش compile error |
| `python -m pyflakes app` من backend | 1 | 127 diagnostics، من غير filtering/suppression؛ [pyflakes.log](pyflakes.log) |
| `python -m pytest -q tests` من backend | 1 | 224 passed، 2 failed، 18 warnings؛ [backend-tests.log](backend-tests.log) |
| `python -m alembic upgrade head` | 0 | fresh disposable `helix_audit_w4` إلى `b7e4c9a1d2f0`؛ [migration-upgrade.log](migration-upgrade.log) |
| `python -m alembic check` | 0 | No new upgrade operations؛ [migration-check.log](migration-check.log) |
| actual local `GET /api/openapi.json` | 0 / HTTP 200 | 165 unique method/path، مطابقين mounted static set؛ [runtime-routes.json](runtime-routes.json) |
| `agent-browser` route/tab capture scripts | 0 | [browser-summary.json](browser-summary.json) و[raw attempts](browser-captures.jsonl)؛ failed selectors القديمة مش محسوبة كنجاح |
| `git diff --check` | 0 | آخر فحص قبل الـcommit من غير whitespace errors |

## تفسير failures

- `tests/test_intelligence_w2_boundaries.py:106`: بيطلب ظهور raw provider error (`provider down`) بينما W4 بيرجع sanitized 503؛ مش هنسرّب رسالة vendor عشان test يعدّي.
- `scripts/prove_prod_schema_reconcile.py:23,394-395` اللي بتناديه `tests/test_migration_failure.py:27`: يقارن head الحالي بـ`f3d9a7c2b1e4` القديم. Retry upgrade نفسه نجح، بس revision الجديدة مش نفس الثابت. ده fragility في proof، مش دليل فشل fresh migration.
- باقي type/lint/pyflakes diagnostics متسجلة بالكامل. المراجعة read-only، فمفيش إصلاحات أو blanket ignores اتعملت.

## فصل قواعد البيانات

- الـbrowser والـAPI: `helix_audit_w4` fresh schema؛ حساب admin وحساب pending فقط، من غير creatives/leads/jobs مصطنعة.
- full regression tests: `helix_test_db` disposable منفصلة، مش قاعدة screenshots. بعض اختبارات migrations بتنشئ/drop قواعد عشوائية loopback، وفيها injected failure وrollback/retry كجزء من tests.
- migrations/test-operator privileges مستقلة عن API role. الـAPI runtime `NOSUPERUSER NOBYPASSRLS`، وما اتغيّرش startup guard أو RLS أو grant policy.
- مافيش production DB أو real accounts أو provider API credentials أو إرسال email/generation/scraping خارجي.
