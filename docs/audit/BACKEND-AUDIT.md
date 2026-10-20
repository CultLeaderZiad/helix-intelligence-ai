# تدقيق الـBackend — Helix Intelligence

**النطاق والنسخة:** مراجعة source-only على `eab70cc` بفرع `audit/helix-full`، مقارنةً بـ`5b45806` عند الحاجة. لم يتغير كود التطبيق. قرأت `README.md`, `ARCHITECTURE.md`, `DEVELOPMENT.md`, `API_CONTRACTS.md` و`DESIGN_SYSTEM.md` إن وُجد؛ وحصرت endpoints بتحليل Python AST لتسجيلات FastAPI و`include_router`، ثم قارنتها بمراجع `request()`/`fetch()` في الواجهة. لم أستورد التطبيق، ولم أتصل بقاعدة البيانات أو production أو أي provider، ولم أقرأ `.env` أو أي قيمة سرية.

## الخلاصة

الـBackend أكبر وأكمل من صورة المنتج المعلنة: فيه auth وmulti-tenancy وRLS وcredit ledger وoutbox وDiscover وScout/leadgen/monitors/media وغيرها. هذا يعطي أساسًا حقيقيًا، لكن النطاق الحالي واسع على منتج README يصفه بأن Discover هو الـloop الوحيد المكتمل. التوصية العملية: ثبّتوا Discover + وصول يديره admin كـcore مؤقتًا، أخفوا الأسطح غير المؤكدة، ولا تحذفوا الـledger أو جداولها قبل استبدال entitlement/idempotency/refund guarantees.

المقارنة `5b45806..eab70cc` تُظهر 219 ملفًا متغيرًا، مع توسع واضح في RLS/tenancy وcredit ledger وoutbox وdiscovery-cache identity؛ هذا تقدم أمني وتشغيلي في الكود، وليس إثباتًا على إعداد production أو نجاح migrations عليه. مصدر الحصر الكامل للطرق والاستخدام الظاهر بالواجهة: [`evidence/api-inventory.md`](evidence/api-inventory.md) و[JSON](evidence/api-inventory.json). جرد جداول ORM ومخاطر حذفها: [`evidence/schema-inventory.md`](evidence/schema-inventory.md).

## API: الحصر والاستهلاك

- الـAST عثر على **168 سجل route**: **166 مسجلًا عند التطبيق** و2 handler declarations في `analysis.creatives_insights_router` غير mounted. الـ166 تشمل alias إضافي لـScout على `/api/v1/scout`، health/root، وdecorators المتقاربة مع/بدون trailing slash؛ لذلك الرقم ليس عددًا من deduplicated URL strings.
- مسح الواجهة وجد **130 مرجع request/fetch** بعد تتبع خمس استدعاءات مركبة عبر `uploadFile`/`exportUrl`؛ طابق 136 سجل method/path (تتضمن mounts aliases). لا توجد وجهة frontend literal بلا route مطابق. بقي **30 سجلًا mounted** غير مطابق لاستدعاء واجهة ثابت؛ هذا يعني “غير ظاهر في scan الواجهة”، وليس “ميت”: فيها cron/provider/worker callbacks وhealth aliases وScout v1، بالإضافة لسطوح تستحق التحقق اليدوي.
- أهم عدم اتساق API: Scout router نفسه mounted على `/api/scout` و`/api/v1/scout` (`backend/app/main.py:113-114`)؛ الـfrontend يستخدم `/api/scout/*` عبر خدماته (`src/services/api/scoutService.api.js:7-67`). لا تحذفوا alias قبل فحص مستهلكي CLI/خارج المستودع. `POST /api/auth/logout` اسم بديل لمسار sign-out (`backend/app/api/routers/auth.py:200`)، و`updates` يقبل PATCH/PUT/POST على مورد التحديث (`backend/app/api/routers/updates.py:140`).
- handlerان في `backend/app/api/routers/analysis.py:14-35` على `creatives_insights_router` غير مسجلين في `main.py`; توجد مسارات insights مماثلة من `creatives.router`. إما إزالة التعريفات اليتيمة بعد التحقق أو mount واحد صريح.
- أمثلة endpoints غير مطابقة لاستدعاء browser literal: `POST /api/account/access-grants`، `GET /api/account/trial-status`، و`POST /api/account/billing/provider-events` (`account.py:194,285,335`)، و`POST /api/monitors/tick` (`monitors.py:112`)، heartbeat للـworker (`leadgen.py:683`). الأولين يحتاجان قرار منتج/مراجعة security؛ tick وheartbeat متوقع أن يكونا تكاملين داخليين. Billing provider-events لا يثبت وجود billing provider.
- الإحالات بين عقود الخدمات والـAPI الفعلي موجودة في [`evidence/api-inventory.json`](evidence/api-inventory.json) مع method/path وsource line. الحصر static وقد يفوّت URLs ديناميكية أو مستهلكين خارج الواجهة؛ لا توجد claims عن traffic فعلي.

## Providers والإعداد

المصادر الأساسية للإعداد `backend/app/core/config.py:12-252`، والـwiring في `backend/app/services/` و`backend/app/services/scraping/`. أسماء المتغيرات أدناه مأخوذة من الكود/config schema، والقيم لم تُقرأ. **لم أتحقق من الأسعار أو اشتراكات الحسابات**؛ التكلفة/الـpaid status لكل مزود **غير متحقق منها**، ولم تُجرَ provider requests.

| Provider/تكامل | أين يظهر / وضع wiring | env/config ذات الصلة | ملاحظة تدقيق |
|---|---|---|---|
| Metapi | أول fallback في Discover؛ `scraping/metapi_provider.py`, `scraping/ad_library_provider.py:...` | `METAPI_API_KEY` (تقبل config aliases أخرى) | موصول في الكود؛ صحة المفتاح والخطة غير متحققتين. |
| Adyntel | fallback للبحث الملائم بصيغة domain | `ADYNTEL_API_KEY`, `ADYNTEL_EMAIL` | موصول شرطيًا؛ غير مضمون لكل keyword. |
| Meta Graph API / ad library | fallback في سلسلة Discover | `META_ACCESS_TOKEN` | موصول بالكود؛ صلاحية التطبيق/الموافقة/الحدود غير متحققة. |
| Apify | fallback اختياري في Discover | `APIFY_API_TOKEN`, `APIFY_ENABLED` | تشغيله مرتبط بالإعداد/الـtoken؛ لا إثبات على actor أو usage في production. |
| ScrapeGraphAI | إثراء landing pages / Scout extraction | `SCRAPEGRAPH_API_KEY` | تكامل مستقل عن جلب ads؛ التكلفة والـquota غير متحققتين. |
| Scrapling worker/engine | scraping workers، robots/URL safeguards وlead generation | مجموعة `SCRAPLING_*`، ومنها `SCRAPLING_WORKER_ENABLED`, `SCRAPLING_WORKER_URL`, `SCRAPLING_DEFAULT_ENGINE`, concurrency/proxy/heartbeat settings | مكتبة/worker وليست ad-library provider بذاتها؛ availability الفعلية غير متحققة. |
| Bright Data | مفتاح في config وhealth/diagnostics؛ ليس ظاهرًا كعنصر في سلسلة `DISCOVERY_PROVIDER_CHAIN` الحالية | `BRIGHTDATA_API_KEY` | مرشح إزالة بعد فحص health/worker وكل deployments، لا تحذفوه اعتمادًا على scan واحد. |
| Groq / OpenRouter / Gemini text | AI router وخدمات query/entity/creative | `GROQ_API_KEY`, `GROQ_MODEL`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `GEMINI_TEXT_MODEL` | تكاملات في الكود؛ model selection/runtime والـcost غير متحققة. |
| Gemini BYOK | credentials مشفرة للـworkspace واختبار اتصال | `CREDENTIAL_ENCRYPTION_KEY`, `CREDENTIAL_ENCRYPTION_KEY_PREVIOUS`, `CREDENTIAL_ENCRYPTION_KEY_VERSION`; بيانات key داخل credential store | لا تُرجع plaintext حسب التصميم؛ تحقق production من key rotation وrestricted DB role ضروري. |
| Gemini / AIHubMix / Pollinations image | media providers | `GEMINI_IMAGE_MODEL`, `AIHUBMIX_API_KEY`, `POLLINATIONS_API_KEY`, `MEDIA_MANAGED_FALLBACK` | Modules موجودة؛ الاختيار والفallback live غير متحققين. |
| TokenHarbor | إعداد/AI routing | `TOKENHARBOR_API_KEY` | wiring في AI router لكن ليس جزءًا من core Discover حسب source search؛ راجع هل مطلوب قبل حذف المفتاح. |
| Resend | password reset/notification email | `RESEND_API_KEY`, `RESEND_FROM`, `PUBLIC_APP_BASE_URL` | موصول؛ الكود يفرض إعدادات عند validation للإنتاج (`core/config.py`)، التسليم الفعلي غير متحقق. |
| Cloudflare R2 | تخزين avatars/media durable مع local fallback | `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE_URL`, `R2_ENDPOINT_URL` | تكامل storage ظاهر؛ bucket/CORS/permissions الفعلية غير متحققة. |
| Billing processor | لا يوجد SDK/connector دفع ظاهر في `backend/requirements.txt` أو provider route wiring المفحوص | لا processor-specific key ظهر في config | توجد billing/trial/credit APIs و`provider-events`، لكن هذا لا يساوي اشتراكًا أو قبض أموال. المنتج يقول access يدوي؛ اجعلوا الواجهة تعكس ذلك. |

**Discover chain drift:** الكود يذكر Metapi → Adyntel (بحسب query) → Meta Graph → Apify (`backend/app/services/scraping/ad_library_provider.py`)، بينما `DEVELOPMENT.md:380-398` يوثق ترتيبًا مختلفًا ويذكر Bright Data deep fallback. المرجع النهائي يجب أن يكون implementation أو عقدًا مولدًا منه، لا نسختين متعارضتين.

## البيانات، migrations، tenancy

يوجد **41 ORM table mapping** في `backend/app/models/`، تغطي identity/organizations، access وprovider credentials، usage/credit ledger، creatives/patterns/insights، work items/jobs، Scout/leadgen/maps، monitors، support/notifications، media/playbooks. أسماء الجداول والـmodel/source line ومخاطر القطع في [`evidence/schema-inventory.md`](evidence/schema-inventory.md). هذه inventory للـORM فقط: لا row counts ولا إثبات إن كل جدول موجود أو مستخدم في DB المنشورة.

سلسلة Alembic تضم 20 revision file، من initial schema إلى credit/access, RLS deny-by-default, outbox/provenance, cache identity وW4 integrity؛ أمثلة: `backend/alembic/versions/e7c1a9b4d2f0_w1_tenancy_ledger_rls.py`, `f3d9a7c2b1e4_rls_deny_by_default.py`, `c2a4e8b1d907_w2_outbox_and_provenance.py`, `a9d4e6f8c2b0_w3_discovery_cache_identity.py`, `b7e4c9a1d2f0_w4_alignment_integrity.py`. CI يعرّف `alembic upgrade head`, `alembic check` وrollback على disposable DB (`.github/workflows/ci.yml:70-88`)، لكن هذه المراجعة لم تشغّل migrations ولم تتحقق من target DB.

في الكود فيه JWT/session/auth dependencies، feature gates، organization scoping، PostgreSQL RLS وموديلات access grants. اختبارات مخصصة موجودة مثل `backend/tests/test_rls_deny_by_default.py`, `test_intelligence_w1_tenancy.py`, `test_intelligence_w4_migrations.py`, `test_phase5_durable_jobs_suite.py`. التقييم لا يثبت أن production يستخدم login role غير superuser/BYPASSRLS، أو أن كل tenant query يضبط السياق في runtime؛ افحصوا ذلك من إعداد آمن منفصل، لا من credentials داخل audit.

## Jobs، الأداء، وقابلية التوسع

- Discover يستقبل `POST /api/discovery/jobs` ثم `trigger_search` ويشغّل pipeline (`backend/app/api/routers/discover.py:13-44`, `backend/app/services/discover_service.py:...`). يوجد DB-backed `work_items`/outbox وleasing/reconciliation (`backend/app/services/work_outbox.py`, `backend/app/services/job_reconciliation.py`)، لكن التنفيذ يستدعي pipeline في process التطبيق في مسارات inline/background (`discover_service.py:338-340`, `work_outbox.py:295-296`). هذا أفضل من task بلا سجل دائم، لكنه ليس دليلًا على worker fleet مستقل أو capacity/back-pressure كافية.
- الفallback الشبكي المتسلسل يضيف latency متغيرًا؛ لا توجد أرقام p50/p95 أو request/provider timing من production هنا. حالة “Resolving sources” معروضة في الواجهة (`src/data/jobs.js:12`)، والـjob lifecycle يpoll status (`src/hooks/useDiscoverySearch.js:83-92`). **السبب الجذري للتعليق لم يُثبت** في هذه المهمة: لم أشغّل API أو provider ولا managed preview، لذلك يلزم correlation لjob ID وstage timestamps وprovider timeout/error في preview. لا تُنسب المشكلة لمزود بعينه بلا هذا الدليل.
- Polling موجود في أكثر من feature: leadgen كل 1.5s (3s عند pause) (`src/hooks/useLeadGenJob.js:25-26,96-107`)، monitors كل 20s (`src/hooks/useMonitors.js:7,50`)، Scout/Maps (`useScoutSearch.js`, `useMapsScoutSearch.js`) وhealth ping كل دقيقتين (`src/services/http.js:77`). هذه أرقام source defaults، ليست قياس حمل. اجعلوا polling visibility-aware ومحدودًا، مع backoff مشترك/terminal-state stop؛ لا تغيّروا interval قبل مراجعة freshness requirement.
- `Vite/React` dependencies تشمل React 19/Router 7 و`gsap`, `driver.js`, Vitest/Playwright؛ Python runtime pins FastAPI/SQLAlchemy/asyncpg/httpx/Pillow/boto3 وغيرها (`package.json`, `backend/requirements.txt`). لم أشغّل build حسب حدود المهمة، لذلك **bundle/chunk sizes وأثقل modules/unused dependencies غير مقاسة**؛ لا أصف dependency بأنها dead بلا import/bundle evidence.

## درجات الـBackend

| المجال | الدرجة | الدليل/المخاطرة | التصليح المقترح |
|---|---|---|---|
| Structure | **مقبول** | Routers/services/models منفصلة، لكن 150 route declarations و41 table mappings على scope أوسع من Discover (`main.py:95-122`). | قسّموا API إلى core/optional domains، وحددوا owner وfeature flag لكل surface قبل توسع جديد. |
| API design/consistency | **مقبول** | duplicate Scout mounts، alias verbs وunmounted declarations؛ جرد AST في `evidence/api-inventory.json`. | عرّفوا OpenAPI contract واحدًا، اختبروا generated schema مقابل clients، واعملوا deprecation window للمسارات القديمة. |
| Error handling | **مقبول** | Discover يحتوي failure/refund paths وclient lifecycle tests؛ لا تم التحقق من provider failures live. | وحّدوا envelope/correlation IDs وطبّقوا حدود زمنية/تصنيف retry per provider؛ اختبروا timeout وrefund idempotency. |
| Auth & tenancy | **مقبول** | JWT/dependencies، feature gates، RLS migrations واختبارات مخصصة؛ إعداد DB role الإنتاجي غير متحقق. | CI إلزامي بدور غير privileged على Postgres disposable، واختبار tenant matrix لكل route ذات بيانات. |
| DB & migrations | **مقبول** | Alembic يحوي RLS/ledger/outbox وعمليات alignment متعاقبة؛ لا migration run في هذا التدقيق. | Migration rehearsal على نسخة disposable، مراجعة FK/RLS/index locks وrollback للـrevisions الحساسة. |
| Tests & CI | **جيد من حيث البنية** | `.github/workflows/ci.yml:16-130` يغطي frontend gates، compile/pyflakes، upgrade/drift/rollback، pytest، secret scan وsecurity smoke. | اربطوا كل endpoint/provider critical بـcontract test؛ نتيجة CI الحالية غير متحققة من هذا الفرع. |
| Observability | **مقبول** | request IDs/security headers وhealth routes، job heartbeat/reconciliation موجودة (`main.py`, `core`, `work_outbox.py`). | أضيفوا stage/provider timings وqueue age/retries وerror reporting مع redacted secrets وalerts/SLO. |
| Security | **مقبول** | RLS deny-by-default، SSRF/safe URL code/tests، BYOK encryption وsecret scan في CI. إعداد production/secrets/network غير مفحوص. | أثبتوا RLS role/config، تدوير encryption keys، retention/deletion، admin audit trail وrate limits لكل expensive provider endpoint. |
| Performance | **ضعيف حتى القياس** | polling متعدد، sequential external chain وin-process execution؛ لم تُقَس build أو queries أو latency. | أضيفوا tracing وquery budgets، cap متزامن للمزودين وcache hits/latency، ثم load test بعد تعريف SLO. |
| Scalability | **ضعيف كضمان قائم** | outbox/leasing يساعد recoverability لكن التنفيذ ما زال مرتبطًا بعمر process في المسارات المذكورة؛ لا throughput/worker evidence. | افصلوا dispatch عن API إلى worker replicas بlease semantics، admission control، per-provider quotas وdead-letter alerts قبل فتح onboarding واسع. |

## قائمة تقليص مرتبة ومخاطر الحذف

1. **P0 — حل تعارض access/trial/billing في المنتج:** لا تُعرض “select a plan” كأن الدفع متاح إذا access يديره admin ولا provider دفع مثبت. أخفوا Billing & Meter/trial copy لحين القرار، واحتفظوا مؤقتًا بـcredit ledger وgrants لأنها تغذي entitlement/quota. الخطر: كسر الوصول/الفوترة الداخلية؛ أزيلوا UI أولًا ثم نظفوا API بعد معرفة consumers.
2. **P1 — تقليل public API aliases/handlers:** `/api/v1/scout` duplicate، `/auth/logout` alias، methods الإضافية لتحديثات admin، و`analysis.creatives_insights_router` غير mounted. الخطر: عملاء CLI أو تكاملات غير مرئية؛ سجّلوا usage/اعلنوا deprecation قبل الحذف. تحقّقوا أيضًا من `trial-status`, self `access-grants`, `/media/models` و`/media/providers`؛ غياب frontend literal ليس وحده سببًا للحذف.
3. **P1 — إخفاء product breadth غير مثبتة:** Scout/leadgen/maps، monitors، simulation، playbooks، media generation. واجهاتها وAPIs والجداول موجودة؛ قرروا feature flag/keep/merge قبل قطعها. خطر إزالة data/history أعلى من إخفاء nav؛ export/retention وforeign keys أولًا.
4. **P2 — provider/config trimming:** راجعوا `BRIGHTDATA_API_KEY` (موجود config/diagnostics وليس في chain الحالي) و`TOKENHARBOR_API_KEY` وغيرهما مع deploy/health call sites. لا تحذفوا متغيرًا أو secret من منصة النشر قبل inventory آمن لكل بيئة.
5. **P2 — schema cleanup فقط بعد الاستخدام الفعلي:** مرشحو Scout, monitors, simulation/playbooks مذكورون في `schema-inventory.md`. الخطر مرتفع لوجود علاقات أو سجلات؛ لا drop table مباشرة، بل إيقاف الكتابة، export/retention، reversible migration، ثم تحقق بعد نافذة استرجاع. لا تقطعوا identity/RLS/ledger/idempotency كـcleanup عادي.

## ما لم يُتحقق

لم يُشغّل managed browser أو API محليًا، ولم تُلتقط screenshots، ولم تُشغّل pytest/CI/build، ولم تُختبر migrations على Postgres، ولم تُرسل requests لمزودي AI/scraping/email أو production. لا يوجد قياس للـbundle size أو SQL latency/query plans أو deployment env presence أو الأسعار أو billing collection. نتائج tests/CI الموجودة في تعريف workflow هي **coverage/configuration** وليست نجاحًا على هذا الـcommit. متابعة UI/build وreproduction لمشكلة Discover متروكة للـparent حسب نطاق التفويض.
