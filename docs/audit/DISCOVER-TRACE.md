# Discover — تتبّع تعليق «Resolving sources»

## النتيجة المختصرة

من مراجعة الكود أقدر أؤكد إن السطر `Resolving sources` في Discover مش دليل لوحده إن الـjob واقف: الواجهة بتعرض مرحلة ثابتة محسوبة من `stage_index`، والـbackend بيفضل على نفس المرحلة طول تنفيذ سلسلة مصادر الإعلانات. لكن فيه عيبين مؤكدين بيخلّوا التعليق حقيقيًا من منظور المستخدم: الواجهة ما بتعرضش `stage_label` اللي بيتحدّث من الـworker، ومهلة الأربع دقايق بتوقف polling من المتصفح فقط، مش شغل الـjob على السيرفر. كمان زر الإلغاء محلي؛ مفيش endpoint في Discover يطلب إلغاء الـjob من الـbackend.

ده تفسير مدعوم بالكود، مش تأكيد لسبب حالة إنتاج بعينها. ما اتصلتش بالإنتاج وما شفتش سجل job أو لوجاته، فمش ممكن أحسم إذا الحالة المُبلّغ عنها بطء مزوّد، worker مش شغال، lease منتهي، أو عطل/مشكلة DB.

## النطاق والنسخ

- نسخة W4 المطلوبة: `eab70cc75bbc2aa8fe841a2c792f72bfd8e7e957` (`docs(w4): record exact checks and out-of-scope blockers`).
- نسخة المقارنة المسماة production main: `5b458061c04ee772a49b123568fd008c14e9d646`.
- الـworkspace الحالي على `af5cdf9f4c0a785f9eb169e1d14b46dc9876d7dc`، و`git diff eab70cc..HEAD` أكد عدم وجود تغييرات في ملفات مسار Discover اللي اتراجعت؛ بالتالي الملاحظات دي على كود W4 المحدد.
- قريت `README.md`, `ARCHITECTURE.md`, `DEVELOPMENT.md`, `API_CONTRACTS.md` وتعليمات المستودع المتاحة. ما لقيتش `AGENTS.md` أو `CLAUDE.md`.

## المسار الفعلي: من الصفحة للمزوّد والـDB

```text
DiscoverPage
  → useDiscoverySearch
  → discoverService API adapter
  → POST /discovery/jobs
  → discover_service.trigger_search
  → ScrapeJob + credit ledger + PostgreSQL work_outbox
  → worker claims lease, calls run_discovery_pipeline
  → preflight → analyze_entity_intent → AdLibraryProvider.search
  → Metapi → Adyntel (domain queries فقط) → Meta Graph → Apify
  → normalize/filter/dedupe/save creatives → score → succeeded
  → GET /discovery/jobs/{id} polling → GET /results
```

1. **الصفحة والـhook:** `src/pages/DiscoverPage.jsx` بيستخدم `useDiscoverySearch` (`src/hooks/useDiscoverySearch.js:51-99`). الـhook بيبعت البحث، وبعدها بيعمل polling تسلسليًا لحالة الـjob، وبعدين يطلب النتائج عند النجاح. خدمة API بتستعمل `POST /discovery/jobs`, `GET /discovery/jobs/{id}` و`GET /results` (`src/services/api/discoverService.api.js:16-35`).
2. **إنشاء الـjob والـcache:** `backend/app/api/routers/discover.py:12-21` بيرفض query فاضي ويفوض الإنشاء للخدمة. `discover_service.py:194-245` بيجهز المؤسسة ويتحقق من entitlement، ويكوّن هوية بحث؛ `discovery_cache.py:35-...` بيعمل hash لنسخة الـcache والمؤسسة والمزوّد والـquery المنظّف والـfilters. الطلب المطابق النشط بيتعاد استخدامه، والنجاح بيتعاد استخدامه لمدة 12 ساعة فقط لو فيه سجلات (`discover_service.py:246-258`). فيه partial unique index يمنع jobs نشطة مكررة لنفس المؤسسة والهوية (`models/scrape_job.py` ومهاجرة `a9d4e6f8c2b0_w3_discovery_cache_identity.py`).
3. **الـqueue والـworker:** بعد إنشاء `ScrapeJob` وشحن الرصيد، `trigger_search` بيضيف work item من نوع `discover` للـoutbox (`discover_service.py:260-340`). في production الـinline dispatch مرفوض حسب إعدادات التشغيل؛ المسار المعتمد هو PostgreSQL outbox (`services/work_outbox.py:110-136`) ثم worker. الـworker بيعمل lease مدته الافتراضية 120 ثانية، ويزيد `attempt_count` قبل التنفيذ؛ الـoutbox بيعيد work المنتهي أو الفاشل حسب حد المحاولات (`work_outbox.py:51, 178-204`). heartbeat للـjob كل 15 ثانية والـreconciliation بيعتبره stale بعد 120 ثانية (`core/config.py:180-185`, `services/job_heartbeat.py:...`, `services/job_reconciliation.py:74-132`).
4. **المراحل قبل المصادر:** `run_discovery_pipeline` بيبدأ heartbeat (`discover_service.py:441-448`)، يقرأ الـjob والمؤسسة والمالك، ويثبت `running`/`init` (`451-477`). بعدها يسجل preflight usage (`488-497`) ويعمل `analyze_entity_intent` قبل استدعاء المزوّد (`499-500`). من غير `GROQ_API_KEY` التصنيف heuristic؛ ولو المفتاح موجود فنداء Groq عليه timeout أربع ثوانٍ (`entity_intelligence.py:446-452` وما يليها). بعد كده بيتسجل stage=`scraping`, `stage_index=1`، ثم يبدأ `AdLibraryProvider.search` (`discover_service.py:502-523`).
5. **سلسلة المصادر:** الترتيب مكتوب `Metapi → Adyntel → Meta Official Graph API → Apify` (`scraping/ad_library_provider.py:56-100`). Adyntel بيتخطى query اللي مش domain-shaped (`145-...`). كل request له timeout منفصل؛ Metapi بيستخدم 45 ثانية للطلب، ويستنى 1.5 ثانية قبل كل واحدة من 25 محاولة polling (`metapi_provider.py:75-121`). بالتالي سقف polling النظري لو كل طلب status استهلك timeout كامل يقارب 19 دقيقة، زائد طلب إنشاء المهمة وجلب النتائج (قد يصل المجموع النظري إلى نحو 21 دقيقة). ده حد محسوب من timeouts وعدد المحاولات في الكود، مش قياس إنتاج. مفيش deadline موحد للسلسلة كلها.
6. **الحفظ والإنهاء:** صفر نتائج من غير outage بتنجّح الـjob كـ`zero_results`؛ نتائج المزوّد بتدخل إثراء محدود، normalization/filter/dedupe ثم تخزين؛ scoring best-effort، وبعده status=`succeeded` (`discover_service.py:525-590, 592-697`).
7. **القراءة والعزل:** status والنتائج بيتجابوا من endpoints منفصلة (`routers/discover.py:23-41`). الاتنين بيحسبوا org IDs للمستخدم قبل القراءة؛ job خارج نطاق المؤسسة بيرجع 404 (`discover.py:23-41`, `discover_service.py:355-382`). إنشاء الهوية scoped بـorg id، فـcache والـactive uniqueness مش مشتركين بين المؤسسات.

## عيوب مؤكدة مرتبطة بالعرض والتوقف

### 1) النص الظاهر للمرحلة لا يعكس تسمية الـbackend أو تحديثاته

- الواجهة بتختار label من قائمة ثابتة حسب index فقط (`src/features/discover/JobProgress.jsx:126-145`؛ النص جاي من `src/data/jobs.js:10-17`). و`JobProgress` ما بيقرأش `job.stage` أو `job.stage_label`.
- الـbackend بيعيّن `stage="scraping"`, label=`"Scraping Platforms"`, index=`1` قبل سلسلة المصادر (`discover_service.py:502-523`). index `1` في قائمة الواجهة اسمه `Resolving sources`، فده هو النص اللي يفضل active خلال السلسلة.
- في Metapi، progress callback بيحدّث `ScrapeJob.stage_label` وهو بيعمل polling (`metapi_provider.py:93-...`; `discover_service.py:506-513`) لكن الواجهة ما بتعرضش القيمة دي. النتيجة المؤكدة: المستخدم يفضل شايف `Resolving sources` حتى لو الـworker بينفذ ويحدّث label. ما يثبتش ده إن الـjob المبلغ عنه كان بيحقق تقدمًا فعليًا.

### 2) مهلة المتصفح مش مهلة للـjob على السيرفر

- `JOB_POLL_TIMEOUT_MS=240000` (`src/services/config.js:48`). عند انتهائها، `useJobLifecycle` بيبطل الـcontroller ويمسح timers ثم يغيّر phase للواجهة (`src/hooks/useJobLifecycle.js:30-40`). ده ما بيبعتش إلغاء للـbackend.
- `cancel()` في `useDiscoverySearch` بيبطل الجيل الحالي ويمسح الحالة المحلية فقط (`src/hooks/useDiscoverySearch.js:113-120`). الـAPI adapter ما عندوش cancel method (`discoverService.api.js:16-41`)، والـrouter ما عندوش cancel route (`routers/discover.py:10-50`).
- فيه `request_cancel(job_id)` داخلي في `work_outbox.py:151-169`، لكن مش موصول بواجهة Discover أو router، وحتى التنفيذ leased/provider-started موصوف صراحةً بأنه **مش بيتوقف**. إذن الضغط على Cancel أو انتهاء 4 دقائق مش دليل إن provider request أو الـjob وقف.

### 3) مدة سلسلة المصدر أطول من lease الـwork item

- lease الافتراضي 120 ثانية (`work_outbox.py:51, 130-135`) وMetapi ممكن يقضي وقتًا أطول بكثير في polling وحده (حتى 25 طلب status، كل واحد 45 ثانية، بالإضافة للانتظار؛ `metapi_provider.py:94-121`).
- ما لقيتش في outbox أو worker مسارًا لتجديد `lease_until` أثناء تشغيل provider call؛ المنفذ يعيد leases المنتهية (`work_outbox.py:178-204`). **المؤكد** عدم وجود تجديد lease في مسار التنفيذ المفحوص؛ **غير المؤكد** هل ده تسبب بتشغيل متكرر أو تداخل في production. يعتمد الأثر على worker count والتوقيت وحالة الـDB.

## المقارنة مع main `5b45806`

- في baseline main، إنشاء Discover كان يشغّل `run_discovery_pipeline` عبر `BackgroundTasks` أو `asyncio.create_task` من الخدمة؛ ما كانش مسار الـoutbox الدائم في W4 (`git show 5b45806:backend/app/services/discover_service.py`). ده فرق جوهري في الاسترداد بعد restart، مش ضمان إن W4 منع التعليق.
- W4 أضاف work outbox/reconciliation، cache identity canonical، عزل tenant أوضح، وألغى `USE_MOCKS` المبكر من مسار البحث، وأضاف lifecycle generation وAbortController وdeadline في الواجهة. ملفات Discover المحددة في هذه المراجعة متطابقة بين `eab70cc` وHEAD الحالي (`git diff --exit-code eab70cc..HEAD -- <المسارات>`).
- لا أستنتج من المقارنة وحدها أن حالة main الإنتاجية اتحلت في W4؛ العيوب الثلاثة أعلاه موجودة في الكود اللي اتراجع في W4.

## أصغر الإصلاحات المقترحة

1. خلي الـAPI يرجّع stage key/label واحد موحد، وخلي `JobProgress` يعرض label الحالي وprogress timestamp/provider substage بدل ما يستنتج النص من `stage_index` قديم. أظهر تنبيه «لسه بنستنى المزوّد» إذا ما وصلش تحديث خلال حد واضح.
2. أضف deadline monotonic على السيرفر للـjob كله، ومرّر الوقت المتبقي لكل provider؛ قلّل Metapi polling/timeout بحيث يكون عنده سقف إجمالي صريح. ميّز timeout عن zero-results وعن provider outage وسجّل provider/attempt/duration.
3. وصّل زر Cancel بendpoint مصادق ومقيد بالمؤسسة يطلب إلغاء الـjob/outbox؛ worker يفحص الطلب بين المراحل والمحاولات، ويوقف polling لو أمكن. وضّح للواجهة إن provider call الجاري ممكن ما يتوقفش فورًا.
4. جدّد lease للـoutbox طول التشغيل أو اضبطه على deadline السيرفر مع منع claim متزامن لنفس job. خلي reconciliation/retry يتفقوا مع timeout والإلغاء حتى ما يعيدوش تشغيل job حي.

## التحقق وحدوده

**اتحقق من الكود/الـdiff:** `git show -s` للنسختين؛ `git diff 5b45806..eab70cc` لملفات Discover/outbox/provider؛ `git diff --exit-code eab70cc..HEAD` لنفس مسار الملفات؛ و`rg`/`nl -ba` لتثبيت مواقع الواجهة والـAPI والخدمة والـprovider والـcache والـoutbox والـreconciliation.

**اتحقق محليًا فقط:** شغّلت اختبارات hook lifecycle والإلغاء الموجودة (`src/hooks/__tests__/request-lifecycle.w3.test.jsx`, `src/hooks/__tests__/adapter-cancellation.w3.test.jsx`) من غير تشغيل backend أو dispatch لمزوّد. نتيجة الاختبارات مذكورة مع تنفيذ الأمر في سجل المهمة؛ دي بتثبت سلوك hook المعزول فقط، مش تكامل Discover مع worker/DB.

**ما اتعملش:** لا production access ولا قراءة `.env`/أسرار، لا مزوّد خارجي، لا mock provider لإعادة إنتاج الحالة، لا server أو browser مشترك، ولا تعديل على التطبيق. `DATABASE_URL` ومفاتيح Meta/Apify/Metapi مش مضبوطة في بيئة المهمة، ومفيش قاعدة PostgreSQL محلية disposable جاهزة؛ لذلك ما شغلتش probe للـDB أو provider. كمان ما ثبتش إن worker الإنتاجي حي، ولا راجعت job IDs أو DB rows/logs/metrics أو lease state. السبب الجذري للحالة الإنتاجية يفضل **غير متحقق**.
