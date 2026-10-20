# Schema inventory (ORM + migration source audit)

**النطاق:** declarations في `backend/app/models/` ومخططات Alembic الموجودة محليًا فقط. لم يتم الاتصال بقاعدة البيانات، ولم تُقرأ `.env` أو production؛ لذلك لا توجد مزاعم عن جداول/صفوف live أو استخدام فعلي. الغرض مستنتج من أسماء models وعلاقاتها.

- ORM table mappings المرصودة: **41**.
- يوجد تسلسل Alembic متعدد الخطوات لإضافة tenancy/RLS وledger/outbox/cache identity/integrity؛ راجع `backend/alembic/versions/` وراجع حالة target DB قبل أي حذف.

| Table | Model | الغرض (استدلالي) | مخاطر الحذف | Source |
|---|---|---|---|---|
| `access_requests` | `AccessRequest` | طلبات الوصول/الانضمام | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/access_grant.py:17` |
| `organization_access_grants` | `OrganizationAccessGrant` | منح الوصول الممنوحة يدويًا للـorganization | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/access_grant.py:32` |
| `ai_insights` | `AIInsight` | نتائج/ملخصات AI مرتبطة بالـcreative | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/ai_insight.py:9` |
| `api_keys` | `ApiKey` | مفاتيح API للمستخدم/الـworkspace | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/api_key.py:8` |
| `external_api_usage` | `ExternalApiUsage` | تسجيل استهلاك المزودين الخارجيين | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/api_usage.py:9` |
| `app_updates` | `AppUpdate` | إعلانات وتحديثات التطبيق | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/app_update.py:7` |
| `creatives` | `Creative` | الإعلانات/creative records | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/creative.py:10` |
| `creative_scores` | `CreativeScore` | درجات تقييم creative | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/creative_score.py:8` |
| `operation_idempotency` | `OperationIdempotency` | منع تكرار العمليات المالية/الـjobs | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/credit_ledger.py:17` |
| `credit_reservations` | `CreditReservation` | حجز credits قبل التنفيذ | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/credit_ledger.py:39` |
| `credit_ledger` | `CreditLedgerEntry` | دفتر حركة credits | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/credit_ledger.py:58` |
| `leadgen_jobs` | `LeadGenJob` | مهام جمع الـleads | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/leadgen.py:21` |
| `leadgen_leads` | `LeadGenLead` | سجلات الـleads الناتجة | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/leadgen.py:68` |
| `leadgen_worker_heartbeat` | `LeadGenWorkerHeartbeat` | نبض worker lead-generation | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/leadgen.py:105` |
| `media_jobs` | `MediaGenerationJob` | مهام توليد الوسائط | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/media_job.py:12` |
| `monitors` | `Monitor` | اشتراكات مراقبة البحث المجدول | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/monitor.py:12` |
| `monitor_runs` | `MonitorRun` | تنفيذات monitor | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/monitor.py:49` |
| `monitor_creatives` | `MonitorCreative` | creative snapshots المرتبطة بالمراقبة | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/monitor.py:76` |
| `monitor_events` | `MonitorEvent` | أحداث/تنبيهات monitor | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/monitor.py:115` |
| `notifications` | `Notification` | إشعارات المستخدم | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/notification.py:8` |
| `organizations` | `Organization` | مساحات العمل/tenants | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/organization.py:9` |
| `organization_members` | `OrganizationMember` | عضوية المستخدمين في الـorganization | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/organization_member.py:8` |
| `organization_invites` | `OrganizationInvite` | دعوات الفريق | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/organization_member.py:17` |
| `patterns` | `Pattern` | أنماط/إشارات مستخرجة من creatives | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/pattern.py:8` |
| `pattern_quarantine` | `PatternQuarantine` | عزل/مراجعة patterns | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/pattern_quarantine.py:17` |
| `plans` | `Plan` | خطط الوصول/الميزات/الـcredits | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/plan.py:8` |
| `playbooks` | `Playbook` | مخرجات playbook | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/playbook.py:13` |
| `saved_creatives` | `SavedCreative` | العناصر المحفوظة/Swipe files | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/saved_creative.py:8` |
| `scout_jobs` | `ScoutJob` | مهام Scout الأساسية | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/scout.py:11` |
| `scout_leads` | `ScoutLead` | نتائج Scout leads | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/scout.py:43` |
| `scout_maps_jobs` | `ScoutMapsJob` | مهام Scout Maps | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/scout.py:69` |
| `scout_maps_leads` | `ScoutMapsLead` | نتائج خرائط Scout | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/scout.py:103` |
| `scrape_jobs` | `ScrapeJob` | سجلات scraping | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/scrape_job.py:11` |
| `simulation_reports` | `SimulationReport` | نتائج simulation | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/simulation_report.py:12` |
| `support_tickets` | `SupportTicket` | تذاكر الدعم | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/support_ticket.py:10` |
| `support_ticket_replies` | `SupportTicketReply` | ردود تذاكر الدعم | متوسط إلى عالٍ: feature data/relations؛ لا row counts أو اعتماد production متاح في هذا التدقيق | `backend/app/models/support_ticket.py:25` |
| `usage_logs` | `UsageLog` | سجل usage والعمليات | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/usage_log.py:8` |
| `users` | `User` | حسابات المستخدمين | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/user.py:8` |
| `webhook_events` | `WebhookEvent` | معرّفات/حالة معالجة webhooks | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/webhook_event.py:12` |
| `work_items` | `WorkItem` | outbox/مهام العمل ذات leases | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/work_item.py:15` |
| `workspace_provider_credentials` | `WorkspaceProviderCredential` | credentials مزودين مشفرة للـworkspace | عالٍ جدًا: auth/tenant/access/financial integrity; لا يُحذف بلا مراجعة FK/RLS والبيانات | `backend/app/models/workspace_credential.py:12` |

## Ranked data cut candidates (only if product scope is reduced)

1. **Scout/Maps/Leadgen family:** `scout_jobs`, `scout_leads`, `scout_maps_jobs`, `scout_maps_leads`, `leadgen_jobs`, `leadgen_leads`, `leadgen_worker_heartbeat`. Candidate only if Scout is explicitly cut; endpoints/jobs and foreign keys must be traced, export/retention obligations checked, data exported or deleted by policy, then reversible migration and rollback window.
2. **Monitors:** `monitors`, `monitor_runs`, `monitor_creatives`, `monitor_events`. Keep if recurring Discover is part of the core; otherwise stop scheduling first, preserve audit history, then cut in dependency order.
3. **Creative extensions:** `patterns`, `pattern_quarantine`, `ai_insights`, `creative_scores`, `simulation_reports`, `playbooks`, `media_jobs`. Hide/merge unfinished product surfaces before schema deletion; no runtime usage or row counts were measured.
4. **Billing/credit/access ledger:** `plans`, `operation_idempotency`, `credit_reservations`, `credit_ledger`, `usage_logs`, `external_api_usage`, `organization_access_grants`, `webhook_events`. **Not a safe cut list today:** even without a payment processor these records enforce manual entitlements, metering, idempotency, refunds, or webhook dedupe. Remove only after replacing those guarantees and reconciling historical records.
5. **Identity and tenant tables:** users/organizations/members/invites/access grants/API keys/provider credentials: foundational; do not cut as part of feature pruning.

No deletion is recommended solely from static code. Confirm table usage, FK graph, RLS policies, and data-retention obligations against a disposable DB at migration head and a production-safe inventory before changes.
