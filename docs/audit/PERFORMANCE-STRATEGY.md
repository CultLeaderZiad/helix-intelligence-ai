# الأداء والاستراتيجية — رأي audit مبدئي

التاريخ: 2026-10-20. ده تقييم source/build محلي؛ مش production load test ولا browser measurement. الأرقام الفعلية وطريقة القياس في evidence/build.log وevidence/dependencies.json وevidence/dependencies.md.

## الخلاصة التنفيذية

المنتج عنده فرصة يبقى workstation متخصص لاستخبارات إعلانات المنافسين، بس توسيع الأسطح قبل تثبيت حلقة Discover المدفوعة هيزود الدعم والتكلفة ومخاطر البيانات. رأيي هو open-core بحذر: خلي core صغير قابل للتشغيل الذاتي، وبيع hosted convenience والـ connectors ذات التكلفة، المراقبة المجدولة والتعاون والدعم. مايتوصفش المشروع بأنه open-source قبل حسم الترخيص؛ ما ظهرش ملف LICENSE/COPYING على مستوى الجذر في الفحص الحالي.

فيه تعارض محتاج حسم قبل قرار إزالة أو إطلاق: README.md:5-12 بيقول إن Intelligence/Create/Performance لسه planned والـ non-Discover routes placeholders؛ ARCHITECTURE.md:11-13 بيصنف Create على إنه Live وبيشرح Gemini flow في §8، بينما بيذكر Create ضمن placeholder في architecture tree عند السطر 58. بالتالي ما اعتبرتش Create مستخدم أو غير مستخدم بناءً على docs وحدها؛ اتأكد من التنفيذ/deployment والاستخدام الفعلي قبل إيقافه.

أصغر منتج أقدر أوصي ببيعه: بحث Discover واحد موثوق، صفحة creative/detail فيها المصدر والتاريخ، حفظ قوائم المنافسين، مشاركة/تصدير نتائج، وmonitor بسيط لنفس البحث بعد ما تتحمل queue والـ provider cost. ابدأ بـ provider واحد ومصادر موثقة، مع limits واضحة. أجّل Intelligence وPerformance كمنتجات كاملة، وخلي Scout/lead-gen وCreate surfaces مخفية بالـ feature flags لحد ما يبقى ليهم استخدام مدفوع مثبت. ده تقليص واجهة ومخاطر، مش قرار حذف بيانات أو API.

## الأداء المرصود محليًا

### Build وassets

- الأمر pnpm build نجح على Node v24.22.0 وpnpm 9.15.4؛ Vite حوّل 1,982 modules، وذكر build duration حوالي 15 ثانية. ده وقت build محلي فقط، مش زمن تحميل.
- ملفات dist مجتمعة: 1,958,073 bytes. main JS 481,532 bytes raw و147,494 gzip؛ CSS 135,665 raw و25,694 gzip؛ DocSearchModal chunk 182,288 raw و51,820 gzip. الأسماء/الأحجام الكاملة في evidence/build.log.
- DocSearchModal ظاهر كـ chunk منفصل؛ فمتوقع إن lazy loading موجود لجزء من الواجهة، لكن لم أقس route-level transfer أو زمن first paint. أكبر تحسين آمن: راجع graph لصفحة الدخول الأساسية، قسّم الـ heavy route code تدريجيًا، واختبر إن Discover الأساسي ما يحملش admin/docs/scout code من غير داعي.
- Fonts وbrand images كمان ضمن assets. خفّض font subsets والـ font weights المستخدمة بعد مراجعة اللغات EN/AR؛ ما تحذفش glyph coverage المطلوبة للـ Arabic.

### Dependencies

قياس workspace المثبت: node_modules 234,236,741 bytes و397 package directories، وPython /tmp/w4-venv بحجم 181,398,865 bytes و58 distributions. دي أوزان developer environment مش runtime image أو network payload. فحص literal references وجد استعمال لكل runtime dependency مباشرة في src؛ مفيش cut آمن من package.json حاليًا. راجع evidence/dependencies.md للتفاصيل وأكبر الحزم. قياس production Python image وcold start مش متاح/ما اتعملش.

### Polling والطلبات المتكررة

- Discover job status يبدأ بـ JOB_POLL_INTERVAL_MS=400ms ويفوّض الجدولة لـ pollDelay حسب عدد المحاولات؛ انتهاء دورة الطلب محكوم بـ JOB_POLL_TIMEOUT_MS=240000ms. المصدر: src/services/config.js:38,48 وsrc/hooks/useDiscoverySearch.js:83,92 وsrc/hooks/useJobLifecycle.js:40. الـ 400ms قيمة بداية للـ client poll، مش معدل ثابت مضمون بسبب pollDelay ومدة الشبكة.
- Lead-gen polls كل 1,500ms ويبطّأ لـ3,000ms في حالة pause؛ src/hooks/useLeadGenJob.js:25-26,96,107. Notifications تسأل كل 20 ثانية من src/components/NotificationBell.jsx:80. Monitors تعمل quiet refresh كل 20 ثانية حسب src/hooks/useMonitors.js:50. الـ app كمان يبدأ keep-alive ping كل دقيقتين من src/services/http.js:77.
- دي دورات لكل hook/صفحة نشطة؛ ما اتقاسش عدد العملاء المتزامنين أو إجمالي RPS. قلّل الطلبات باستخدام visibility-aware pause، منع duplicate poll لنفس job، exponential backoff bounded مع jitter للحالات الهادئة، وRetry-After/ETag لو الـ API يقدر يدعمهم. خلّي تحديثات queue-active أقصر لكن خفّفها بعد انتهاء المهمة. راجع إذا كان keep-alive مطلوبًا حسب سياسة hosting بدل ما يعمل ping دائم بلا حاجة.
- لا تستبدل polling بـ WebSocket/SSE قبل قياس عدد jobs النشطة وكلفة الاتصالات؛ تحسين polling أبسط وأقل مخاطر في المرحلة الأولى.

### قواعد البيانات — مؤشرات مصدرية فقط

فيه limits واضحة في أجزاء: discover list تستخدم offset/page_size في backend/app/services/discover_service.py:416؛ dashboard creative queries محدودة لـ60 وmonitor snippets لـ20 في backend/app/services/dashboard_service.py:194,223,347,366؛ notifications محدودة لـ30 في backend/app/services/notification_service.py:38؛ وmonitor event limit مقيد بحد أقصى 200 في backend/app/services/monitor_service.py:290.

في المقابل، lead lists عند backend/app/api/routers/leadgen.py:429,526 مبنية على job_id؛ الـ select في السطور دي ما يبينش limit/pagination محليًا. اعتبرها query candidates للمراجعة، مش دليل إنها بطيئة: ما قستش حجم الجداول، زمن SQL، EXPLAIN ANALYZE، أو indexes الفعلية. الخطوة الصحيحة: خُد representative query plans على بيانات staging مصرح بها، راجع index على tenant/job/status/time وأي sort key، ثم أضف pagination/covering index حسب الدليل. ما نضيفش index عشوائي يبطّأ الكتابة.

### حدود التحقق

ما اتعملش browser timing أو profiler، ولا DB seed/query plan، ولا production/provider call. مفيش أرقام uptime أو latency أو conversion متاحة في القياس ده؛ أي ادعاء أداء حقيقي غير متحقق.

## رأي المنتج: open-core SaaS

**Open core مناسب بشرطين:** ترخيص واضح ومراجع قبل نشر المصدر، وفصل تكاليف البيانات/المزودين عن القيمة المفتوحة. خلي schema/client/local mode وإمكانية تشغيل Discover الأساسي مفتوحة؛ خلّي الاستضافة المُدارة، connectors المدفوعة، scheduling/reliability، team administration، retention، audit/support ضمن hosted tiers. ما تفتحش secrets أو مفاتيح مزودين؛ onboarding يشرح BYOK مقابل managed provider بشكل صريح.

قيمة Helix مش AI عام؛ هي تقليل وقت متابعة المنافسين مع مصدر وتاريخ واضحين. كل result لازم يجاوب: الإعلان منين؟ اتشاف إمتى؟ إيه confidence؟ وتصديره ومراجعته. إثبات الدقة، جودة التغطية، وحقوق إعادة استخدام بيانات المزود أهم من إضافة صفحة تحليل جديدة.

التسعير كتوجه لا كأرقام: usage-based metering للـ provider-heavy searches مع spend caps وcredits واضحة، ثم team/workspace tier للتعاون والmonitoring، وenterprise controls للدعم/الامتثال وretention. افصل تكلفة مزود البحث عن هامش الاستضافة؛ ماتعلنش unlimited قبل وجود cost telemetry وعقود مزود تسمح بالاستخدام. راجع التناقضات بين trial/credits والـ image entitlements في docs قبل توحيد العرض التجاري.

## Roadmap مرتبة وتقدير جهد

التقديرات engineer-weeks تقريبية من مراجعة المصدر، مش commitment؛ تشمل implementation ومراجعة QA، وتتغير بعد discovery.

1. **قفل wedge وقياس القيمة — 1–2 أسبوع.** عرّف persona واحدة (فريق growth/agency)، نجاح Discover، مصدر التغطية، retention، وlimits. اعمل dogfood ببيانات مصرح بها، واجمع search success ووقت الوصول لأول نتيجة وتكلفة كل result. اخفِ surfaces التجريبية بfeature flags بدل حذفها.
2. **اعتمادية jobs والتكلفة — 3–5 أسابيع.** انتقل من in-process jobs إلى durable queue/worker مع idempotency وbackpressure وretry policy؛ وثّق recovery بعد restart. أضف provider/job metrics وalerts وhealth/SLO، cache لنتائج البحث المتوافقة مع freshness/tenant keys، وحماية budget. اختبر DB query plans قبل indexes. لا توعد uptime قبل مراقبة فعلية.
3. **تشغيل hosted بأمان — 2–4 أسابيع.** أضف backup/restore runbook واختبار restore دوري، retention/deletion، upload/media CDN عبر R2 signed access، rate limits، admin access محكوم بـRBAC/MFA/audit trail، وإدارة secrets/rotation. عرّف target uptime داخليًا بعد availability history. حدّد incident contact وstatus page.
4. **Onboarding وجودة النشر — 3–5 أسابيع.** مسار onboarding يختبر مصدر البيانات ويشرح freshness والتكلفة؛ EN/AR كاملين مع RTL واختبارات اتجاه النص؛ keyboard/screen-reader contrast؛ SEO للعناوين العامة المسموح بها وcanonical/sitemap، مع عدم فهرسة workspace/private results. انشر docs محدثة وAPI reference/versioning وquickstart وsample app. راجع security/privacy/retention ومتطلبات العقود حسب الأسواق المقصودة قبل ادعاء compliance.
5. **توزيع وGTM — 2–4 أسابيع لبداية pilot، ثم مستمر.** ابدأ design partners محدودين، onboarding يدوي، وقناة محتوى/قوالب حول competitor-ad research؛ قسّ activation والاحتفاظ وتكلفة search قبل self-serve واسع. بعدها افتح core بتراخيص وcontribution policy واضحين، وقدم hosted beta بمراقبة support وتكاليف المزود. public API يبدأ read-only/search + export محدود مع quotas، وبعدها writes/webhooks لما تبقى auth/versioning/rate limits جاهزة.

## قائمة Cut/Hide مرتبة حسب قيمة تخفيف الضوضاء

الأولوية إخفاء الواجهة/البيع أولًا، مع إبقاء routes/data متوافقة. ما فيش دليل نشاط عملاء ضمن هذا الفحص.

| الترتيب | السطح المقترح | الأثر المتوقع | مخاطر الإزالة | خطوة آمنة |
|---|---|---|---|---|
| 1 | Intelligence وPerformance كمنتجات مستقلة قبل ما تكمل | يقلل توقعات features غير متحققة ويوجه الـ onboarding لـDiscover | روابط مباشرة أو roadmap promises | خليهم "planned" بوضوح أو اخفِ nav بالـ flag؛ حافظ على deep links برسالة/redirect، من غير حذف schemas |
| 2 | Scout/lead-generation كـ default navigation | يقلل اتساع المنتج وتكلفة scraping/enrichment ومخاطر شروط المصادر | users/jobs/exports أو workflows حقيقية | feature flag على الحسابات الجديدة؛ احتفظ بـread/export وراقب الاستخدام/cost قبل deprecation؛ migration لاحقة بعد موافقة |
| 3 | Create/media generation كجزء من core pitch | يفصل AI/media costs والـ credentials عن ad-intelligence value | assets/jobs/entitlements ومشتركين حاليين | أوقف acquisition/upsell أولًا، أبقِ jobs والملفات قابلة للوصول، وخطة export/deprecation معلنة قبل أي حذف |
| 4 | trial/credit entitlements المتعددة | يقلل confusion في onboarding والفوترة والدعم | كل quota ممكن تمثل entitlement منفصل أو التزام قائم | لا تحذفها الآن؛ وضّح الفرق بين credits العامة وحدود image-specific، وحّد source of truth، اختبر staging، ثم migrate مع audit/communication |

لا أوصي بحذف runtime dependencies من الفحص الحالي؛ كل dependency مباشرة لها literal source reference. ولا أوصي بإزالة billing/media tables أو provider integrations قبل بيانات usage والعقود.

## توزيع وتشغيل: معايير إطلاق

- **Uptime/jobs:** durable queue وdead-letter/retry، idempotent workers، health/queue-lag alerts، وrunbook للحوادث. استخرج uptime من telemetry بدل تقدير غير موثق.
- **Cache/CDN:** cache keyed by org + normalized query + source/freshness؛ احترام provider TTL/terms. static assets على CDN وmedia على R2 مع signed URLs، CORS وretention.
- **Backup:** قاعدة البيانات وmetadata والـ media؛ جداول RPO/RTO واختبار restore موثق، مش مجرد وجود cron snapshot.
- **Access/admin:** owner/admin/member roles، MFA/SSO حسب السوق، audit logs وleast privilege؛ فصل platform admin عن org scope.
- **Localization/accessibility/SEO:** EN وAR/RTL end-to-end، تاريخ/أرقام/ترتيب columns صح، keyboard and screen reader، وSEO للصفحات العامة فقط.
- **Security/compliance:** threat model للمصادر المستخرجة وSSRF، secret handling، deletion/export، vendor/data rights، privacy notice وDPA لما يلزم. ما تدّعيش معيار امتثال من غير audit مستقل.
- **Docs/API:** quickstart، provider/freshness/cost transparency، limits، changelog، versioned OpenAPI وAPI key lifecycle وexamples. لا تفتح endpoint يعرّض tenant data قبل authorization/rate-limit tests.
- **GTM:** ابدأ agencies وفرق growth اللي عندها weekly competitor review؛ قِس وقت البحث الموفر وجودة التغطية. التسعير المنطقي usage + team + enterprise support، من غير أسعار لحد ما provider cost وretention يبقوا measured.

## الأدلة المصدرية الأساسية

- Build: evidence/build.log؛ footprint وقائمة runtime imports: evidence/dependencies.json وevidence/dependencies.md.
- Polling: src/services/config.js، src/hooks/useDiscoverySearch.js، src/hooks/useJobLifecycle.js، src/hooks/useLeadGenJob.js، src/components/NotificationBell.jsx، src/hooks/useMonitors.js، src/services/http.js.
- Query shapes: backend/app/services/discover_service.py، backend/app/services/dashboard_service.py، backend/app/services/notification_service.py، backend/app/services/monitor_service.py، backend/app/api/routers/leadgen.py.
- Product/provider/trial/job constraints: README.md، ARCHITECTURE.md، DEVELOPMENT.md، API_CONTRACTS.md. راجعها كحزمة واحدة؛ اتساق وصف المنتج والـ trial/quota محتاج تثبيت قبل public launch.
