# Helix Intelligence — engineering disclosure draft

**Not approved. Ziad and qualified counsel must review before publication.**
This document describes source-visible behavior, not verified deployment settings,
contracts, processor certifications, or legal compliance. No production account,
provider, or data was used to prepare this W4 draft.

## Service and access

Helix provides AI solutions for advertising research and creative work. Access
requires manual administrator approval. An access tier is an administrator-granted
entitlement, not a purchasable subscription. Checkout and payment-provider routes
remain unavailable (503). No price, refund, renewal, or payment promise is made.
AI outputs and inferred signals are not independently verified business facts;
missing data must remain unknown, not become invented confidence or contacts.

## Data and processor inventory

The source can process account identity and password hashes; workspace queries,
public-source creative/lead records, prompts, generated media, saved drafts,
support messages, credit usage and security/audit identifiers. Publicly accessible
personal data still requires a lawful purpose, minimization and deletion handling.

| Source-visible integration | Potential data / purpose | Operator action before use |
|---|---|---|
| PostgreSQL (Neon configuration documented) | Identity, tenant records, job and audit state | Confirm actual host, region, retention, backups and DPA |
| Render and Vercel | API/application hosting and frontend distribution | Confirm deployment regions, request logging and retention |
| Cloudflare R2 / local upload fallback | Generated media and avatars | Confirm actual bucket access, lifecycle and deletion; local disk is not durable storage |
| Groq, OpenRouter, Google Gemini, AIHubMix, Token Harbor, Pollinations | Configured inference/media routes may transmit prompts and source content | Approve only enabled providers; verify contracts, regions, retention and training terms; no zero-retention claim is established |
| Adyntel, Apify, Meta, Bright Data, ScrapeGraphAI; active Scout scrapers | Configured public-source discovery and enrichment | Verify source terms, robots handling, purpose and personal-data minimization |
| Resend | Configured transactional email | Verify sender and DPA before sending; never log reset links or email payloads |

This is an integration inventory, not proof any provider is enabled or contracted.
Higgsfield is not an active processor in the current application. Error reporting
is **unwired** unless a real transport is configured and exercised; logging is not
an error-reporting service. No tracking/cookie exemption or compliance certification
is asserted by engineering inspection.

## Browser storage

The W0 session store still uses JavaScript-readable localStorage for the access
token and cached user. It guards unavailable storage and migrates old duplicate
sessionStorage keys; it is **not an HttpOnly cookie**. W4 does not duplicate or
silently replace that architecture. Cookie migration needs issuer, Secure,
SameSite, CORS and CSRF integration tests and changes outside the W4 allowlist.
Search history, active creative and draft caches are private operational data;
W4 scopes them by user and organization and purges them on session transitions.
Language preferences may persist separately. No secret should be stored in a draft.

## Deletion runbook — not verified end to end

The inspected account router exposes profile, credential, API-key and team
operations, but no account-erasure endpoint. A working end-to-end deletion path
is therefore **not established**. Do not promise automatic deletion, a 30-day
completion SLA, a 14-day log retention, or a self-service delete control.

Before enabling account erasure, the operator must:

1. Verify the requester through an authenticated support process and identify the
   account and all owned/shared organizations; preserve other tenants' records.
2. Revoke sessions, API keys, invitations and access grants; stop queued/running
   jobs and scheduled monitors, including work already dispatched to providers.
3. Delete or appropriately minimize tenant-scoped database rows in FK-safe order;
   decide whether audit/usage records must be retained and document the legal basis.
4. Remove owned R2 objects, local uploads and avatars; clear browser caches, email
   copies and configured processor-held inputs/outputs according to their contracts.
5. Record backup retention and restore-time deletion replay; do not claim deleted
   data is absent from backups without testing restoration and replay.
6. Prove the runbook on disposable fixtures: former sessions/keys cannot access
   data, objects no longer resolve, cross-tenant records survive, and repeat requests
   are idempotent. Then have Ziad/counsel approve the policy and completion notice.

**External owner: Ziad (operator), with counsel and infrastructure administrators.**
The account router, erasure service, storage deletion methods and related full-flow
changes are outside this W4 allowed-file list; implementation remains blocked.

## Contact, rights and approval

Privacy contact: **pending operator verification**. The repository's earlier email
addresses were not verified in this task and are not republished as working privacy
contacts. Ziad must approve a monitored contact, operator identity, jurisdiction,
rights-request workflow, retention periods, transfer safeguards, AI-output rights
and final EN/AR wording before approving or publishing legal policies. Engineering
has not sent mail, verified a mailbox or obtained legal approval.
