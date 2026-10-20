# API inventory (static source audit)

Generated from FastAPI decorators and app router mounts, cross-checked against literal `request()` / `fetch()` calls under `src/`. `Used` means a matching frontend literal and method was found; `Not statically matched` can still be used by cron, provider callbacks, CLI clients, or dynamic code. The local Preview health endpoints were separately checked; `GET /openapi.json` returned 404, so this is not an OpenAPI runtime capture.

- Commit audited: `eab70cc`; route records: **168**, mounted records: **166**, frontend request references: **130** (125 request call literals + 5 helper-built URLs), unmatched frontend targets: **0**.
- Prefix: `API_V1_STR=/api` (`backend/app/core/config.py:9`); router mounts are `backend/app/main.py:95-122`.
- Static inventory intentionally records duplicate paths and aliases; methods and file:line are kept in the JSON artifact.
- Preview verification: `GET /health`, `/api/health`, `/api/health/ready` returned HTTP 200 on `127.0.0.1:8000`; `/api/health/ready` reported database connected. Runtime had a restricted preview role, no provider keys, and no real result records (context from parent).

## Routes

| Method | Path (or declared but unmounted) | Frontend status | Source |
|---|---|---|---|
| `GET` | `/` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/main.py:128` |
| `GET` | `/api` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/main.py:128` |
| `GET` | `/api/account/access` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:255` |
| `POST` | `/api/account/access-grants` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/account.py:285` |
| `POST` | `/api/account/access-requests` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:267` |
| `GET` | `/api/account/api-keys` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:345` |
| `POST` | `/api/account/api-keys` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:352` |
| `DELETE` | `/api/account/api-keys/{key_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:360` |
| `POST` | `/api/account/avatar` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:113` |
| `GET` | `/api/account/billing` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:327` |
| `POST` | `/api/account/billing/provider-events` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/account.py:335` |
| `POST` | `/api/account/onboarding-complete` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:246` |
| `GET` | `/api/account/profile` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:56` |
| `PATCH` | `/api/account/profile` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:69` |
| `GET` | `/api/account/team` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:369` |
| `POST` | `/api/account/team/invites` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:376` |
| `POST` | `/api/account/team/invites/accept` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:392` |
| `DELETE` | `/api/account/team/invites/{invite_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:384` |
| `DELETE` | `/api/account/team/members/{member_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:400` |
| `GET` | `/api/account/trial-status` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/account.py:194` |
| `GET` | `/api/account/usage/today` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:140` |
| `POST` | `/api/account/workspace` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/account.py:298` |
| `GET` | `/api/admin/access-requests` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:245` |
| `POST` | `/api/admin/access-requests/{request_id}/approve` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:255` |
| `POST` | `/api/admin/access-requests/{request_id}/reject` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:267` |
| `POST` | `/api/admin/broadcast` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:185` |
| `GET` | `/api/admin/jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:28` |
| `GET` | `/api/admin/organizations` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:67` |
| `POST` | `/api/admin/organizations/{org_id}/access-grant` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:277` |
| `POST` | `/api/admin/organizations/{org_id}/access-revoke` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:289` |
| `POST` | `/api/admin/organizations/{org_id}/feature-flags` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:89` |
| `POST` | `/api/admin/organizations/{org_id}/grant-credits` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:71` |
| `POST` | `/api/admin/organizations/{org_id}/switch-plan` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:80` |
| `GET` | `/api/admin/overview/stats` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:24` |
| `GET` | `/api/admin/plans` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:37` |
| `POST` | `/api/admin/plans` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:41` |
| `DELETE` | `/api/admin/plans/{plan_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:58` |
| `PUT` | `/api/admin/plans/{plan_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:49` |
| `GET` | `/api/admin/support/tickets` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:200` |
| `POST` | `/api/admin/support/tickets/{ticket_id}/reply` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:212` |
| `PATCH` | `/api/admin/support/tickets/{ticket_id}/status` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:224` |
| `GET` | `/api/admin/system/health` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:32` |
| `GET` | `/api/admin/usage` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:99` |
| `GET` | `/api/admin/usage/logs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:103` |
| `GET` | `/api/admin/users` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:125` |
| `POST` | `/api/admin/users/{user_id}/ban` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:138` |
| `POST` | `/api/admin/users/{user_id}/impersonate` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:165` |
| `POST` | `/api/admin/users/{user_id}/plan` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:156` |
| `POST` | `/api/admin/users/{user_id}/role` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:147` |
| `POST` | `/api/admin/users/{user_id}/status` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/admin.py:129` |
| `POST` | `/api/auth/forgot-password` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/auth.py:226` |
| `POST` | `/api/auth/logout` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/auth.py:200` |
| `POST` | `/api/auth/reset-password` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/auth.py:267` |
| `GET` | `/api/auth/session` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/auth.py:286` |
| `POST` | `/api/auth/session/onboarding/complete` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/auth.py:290` |
| `POST` | `/api/auth/sign-in` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/auth.py:179` |
| `POST` | `/api/auth/sign-out` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/auth.py:200` |
| `POST` | `/api/auth/sign-up` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/auth.py:149` |
| `POST` | `/api/auth/webhook` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/auth.py:300` |
| `GET` | `/api/brands/` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:107` |
| `GET` | `/api/creatives` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:17` |
| `GET` | `/api/creatives/` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:17` |
| `POST` | `/api/creatives/custom` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:40` |
| `GET` | `/api/creatives/saved` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:30` |
| `POST` | `/api/creatives/translate-copy` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:152` |
| `GET` | `/api/creatives/{creative_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:97` |
| `POST` | `/api/creatives/{creative_id}/generate-insights` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:82` |
| `GET` | `/api/creatives/{creative_id}/insights` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:65` |
| `DELETE` | `/api/creatives/{creative_id}/save` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:57` |
| `POST` | `/api/creatives/{creative_id}/save` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:48` |
| `GET` | `/api/dashboard/metrics` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/dashboard.py:12` |
| `GET` | `/api/discovery/jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/discover.py:44` |
| `POST` | `/api/discovery/jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/discover.py:13` |
| `GET` | `/api/discovery/jobs/{job_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/discover.py:24` |
| `GET` | `/api/discovery/jobs/{job_id}/results` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/discover.py:30` |
| `GET` | `/api/health` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/health.py:46` |
| `GET` | `/api/health` | used by frontend (source path/method match; see refs) | `backend/app/main.py:128` |
| `GET` | `/api/health/` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/health.py:46` |
| `GET` | `/api/health/live` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/health.py:19` |
| `GET` | `/api/health/ready` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/health.py:25` |
| `GET` | `/api/insights/` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/analysis.py:37` |
| `POST` | `/api/media/jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/media.py:31` |
| `GET` | `/api/media/jobs/{job_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/media.py:64` |
| `POST` | `/api/media/jobs/{job_id}/cancel` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/media.py:75` |
| `GET` | `/api/media/models` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/media.py:40` |
| `GET` | `/api/media/providers` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/media.py:46` |
| `POST` | `/api/media/upload` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/media.py:91` |
| `GET` | `/api/monitors` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/monitors.py:42` |
| `POST` | `/api/monitors` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/monitors.py:51` |
| `GET` | `/api/monitors/` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/monitors.py:42` |
| `POST` | `/api/monitors/` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/monitors.py:51` |
| `GET` | `/api/monitors/events` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/monitors.py:70` |
| `POST` | `/api/monitors/tick` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/monitors.py:112` |
| `DELETE` | `/api/monitors/{monitor_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/monitors.py:94` |
| `PATCH` | `/api/monitors/{monitor_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/monitors.py:82` |
| `POST` | `/api/monitors/{monitor_id}/run` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/monitors.py:103` |
| `GET` | `/api/notifications` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/notifications.py:12` |
| `GET` | `/api/notifications/` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/notifications.py:12` |
| `POST` | `/api/notifications/read-all` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/notifications.py:27` |
| `POST` | `/api/notifications/{notification_id}/read` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/notifications.py:19` |
| `GET` | `/api/patterns/` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:118` |
| `POST` | `/api/patterns/generate` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/creatives.py:129` |
| `GET` | `/api/playbooks` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/playbooks.py:50` |
| `POST` | `/api/playbooks` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/playbooks.py:23` |
| `GET` | `/api/playbooks/public/{public_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/playbooks.py:57` |
| `GET` | `/api/scout/export` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:354` |
| `POST` | `/api/scout/jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:70` |
| `GET` | `/api/scout/jobs/{job_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:188` |
| `GET` | `/api/scout/jobs/{job_id}/leads` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:220` |
| `GET` | `/api/scout/latest-job` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:296` |
| `POST` | `/api/scout/leadgen/jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:270` |
| `GET` | `/api/scout/leadgen/jobs/{job_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:412` |
| `GET` | `/api/scout/leadgen/jobs/{job_id}/export.csv` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:543` |
| `GET` | `/api/scout/leadgen/jobs/{job_id}/export.jsonl` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:568` |
| `GET` | `/api/scout/leadgen/jobs/{job_id}/leads` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:422` |
| `GET` | `/api/scout/leadgen/jobs/{job_id}/leads/{lead_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:438` |
| `POST` | `/api/scout/leadgen/jobs/{job_id}/pause` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:452` |
| `POST` | `/api/scout/leadgen/jobs/{job_id}/resume` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:468` |
| `GET` | `/api/scout/leadgen/recipes` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:600` |
| `GET` | `/api/scout/leadgen/worker/health` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/leadgen.py:604` |
| `POST` | `/api/scout/leadgen/worker/heartbeat` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/leadgen.py:683` |
| `GET` | `/api/scout/maps/export` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:704` |
| `POST` | `/api/scout/maps/jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:419` |
| `GET` | `/api/scout/maps/jobs/{job_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:530` |
| `GET` | `/api/scout/maps/jobs/{job_id}/leads` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:567` |
| `GET` | `/api/scout/maps/latest-job` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:644` |
| `GET` | `/api/scout/maps/org-jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:615` |
| `GET` | `/api/scout/org-jobs` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:268` |
| `GET` | `/api/scout/settings` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:760` |
| `POST` | `/api/scout/settings` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/scout.py:786` |
| `POST` | `/api/simulation/creatives/{creative_id}/simulate` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/simulation.py:24` |
| `GET` | `/api/simulation/segments` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/simulation.py:14` |
| `GET` | `/api/support/tickets` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/support.py:46` |
| `POST` | `/api/support/tickets` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/support.py:23` |
| `GET` | `/api/support/tickets/{ticket_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/support.py:53` |
| `POST` | `/api/support/tickets/{ticket_id}/reply` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/support.py:61` |
| `GET` | `/api/updates` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/updates.py:31` |
| `POST` | `/api/updates/admin` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/updates.py:97` |
| `GET` | `/api/updates/admin/all` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/updates.py:84` |
| `DELETE` | `/api/updates/admin/{update_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/updates.py:171` |
| `GET` | `/api/updates/admin/{update_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/updates.py:122` |
| `PATCH` | `/api/updates/admin/{update_id}` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/updates.py:140` |
| `POST` | `/api/updates/admin/{update_id}` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/updates.py:140` |
| `PUT` | `/api/updates/admin/{update_id}` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/updates.py:140` |
| `GET` | `/api/updates/banner` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/updates.py:54` |
| `GET` | `/api/v1/scout/export` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:354` |
| `POST` | `/api/v1/scout/jobs` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:70` |
| `GET` | `/api/v1/scout/jobs/{job_id}` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:188` |
| `GET` | `/api/v1/scout/jobs/{job_id}/leads` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:220` |
| `GET` | `/api/v1/scout/latest-job` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:296` |
| `GET` | `/api/v1/scout/maps/export` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:704` |
| `POST` | `/api/v1/scout/maps/jobs` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:419` |
| `GET` | `/api/v1/scout/maps/jobs/{job_id}` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:530` |
| `GET` | `/api/v1/scout/maps/jobs/{job_id}/leads` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:567` |
| `GET` | `/api/v1/scout/maps/latest-job` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:644` |
| `GET` | `/api/v1/scout/maps/org-jobs` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:615` |
| `GET` | `/api/v1/scout/org-jobs` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:268` |
| `GET` | `/api/v1/scout/settings` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:760` |
| `POST` | `/api/v1/scout/settings` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/scout.py:786` |
| `DELETE` | `/api/workspaces/provider-credentials/google-gemini` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/providers.py:199` |
| `POST` | `/api/workspaces/provider-credentials/google-gemini` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/providers.py:75` |
| `POST` | `/api/workspaces/provider-credentials/google-gemini/test` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/providers.py:151` |
| `POST` | `/api/workspaces/provider-mode` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/providers.py:223` |
| `GET` | `/api/workspaces/providers` | used by frontend (source path/method match; see refs) | `backend/app/api/routers/providers.py:39` |
| `GET` | `/health` | used by frontend (source path/method match; see refs) | `backend/app/main.py:128` |
| `GET` | `/uploads/{filename}` | not matched by scanned frontend (possible unused or non-browser consumer) | `backend/app/api/routers/uploads.py:89` |
| `GET` | ``/{creative_id}/insights` (no mounted prefix)` | UNMOUNTED router declaration | `backend/app/api/routers/analysis.py:14` |
| `POST` | ``/{creative_id}/generate-insights` (no mounted prefix)` | UNMOUNTED router declaration | `backend/app/api/routers/analysis.py:24` |

## Frontend paths without a matching backend method/path


No unmatched static API request paths were found in the scanned frontend request/fetch literals. Dynamic URLs were not resolved.

## Interpretation

- Endpoint enumeration is source-only because local `GET /openapi.json` returned 404; it did not query production logs.
- `/api/v1/scout` and `/api/scout` are both mounted from the same router. The browser service uses `/scout/*` under the shared `/api` base; the `/api/v1/scout` alias was not matched by those references.
- A route absent from browser call literals is classified as not statically matched, not globally unused. Review cron/provider/webhook/CLI call sites before deletion.
- `analysis.creatives_insights_router` is declared but not included in `main.py`; equivalent creative-insight routes are served by the creatives router. It is an orphan declaration, not a mounted endpoint.
