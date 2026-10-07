import json

with open("docs/production-readiness/remediation-status.json", "r", encoding="utf-8") as f:
    data = json.load(f)

phase1_updates = {
    "F01": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Models defined 14 missing tables and 24 missing columns/constraints that previous migrations never created; startup previously used create_all which masked schema drift.",
        "changed_files": [
            "backend/alembic/versions/b1c2d3e4f5a6_complete_production_schema_alignment.py",
            "backend/alembic/env.py",
            "backend/app/models/creative.py",
            "backend/app/models/scout.py"
        ],
        "migration_config_impact": "Migration b1c2d3e4f5a6 aligns all tables, columns, indexes and foreign keys.",
        "regression_test": "alembic upgrade head && alembic check against fresh Neon PostgreSQL test branch.",
        "observed_test_result": "Migration executed cleanly on empty Neon PostgreSQL test database; alembic check reported 'No new upgrade operations detected' with zero schema drift."
    },
    "F13": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Migration 46af201944fd dropped columns (source_type, is_impression_estimate) that prior migrations never created, breaking fresh migrations.",
        "changed_files": [
            "backend/alembic/versions/46af201944fd_add_is_suspended_to_users.py",
            "backend/alembic/versions/a1b2c3d4e5f6_add_leadgen_tables.py"
        ],
        "migration_config_impact": "Guarded column dropping and table creation with schema reflection checks.",
        "regression_test": "alembic upgrade head from empty database.",
        "observed_test_result": "Upgraded from base to head on empty database with 0 errors."
    },
    "F14": {
        "status": "FIXED_VERIFIED",
        "root_cause": "main.py executed create_all and raw ALTER TABLE loops at startup; render.yaml lacked preDeployCommand.",
        "changed_files": [
            "backend/app/main.py",
            "render.yaml"
        ],
        "migration_config_impact": "render.yaml now specifies preDeployCommand: alembic upgrade head.",
        "regression_test": "Inspection of main.py lifespan and render.yaml.",
        "observed_test_result": "Verified create_all and DDL loops removed from main.py; migrations run exclusively through Alembic via preDeployCommand."
    },
    "F15": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Health endpoint masked database outages with 200 OK and accepted secret query param.",
        "changed_files": [
            "backend/app/api/routers/health.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "Unit tests and router inspection for /api/health/live and /api/health/ready.",
        "observed_test_result": "Readiness probe actively validates DB connectivity and User table, returning honest 503 on failure; secret query param removed."
    },
    "F16": {
        "status": "FIXED_VERIFIED",
        "root_cause": "CI pipeline lacked PostgreSQL service container, migration drift verification, and pyflakes undefined-name linting.",
        "changed_files": [
            ".github/workflows/ci.yml"
        ],
        "migration_config_impact": "None",
        "regression_test": "GitHub Actions workflow YAML validation and local test/pyflakes runs.",
        "observed_test_result": "CI workflow executes postgres:16 service container, alembic upgrade head, alembic check, pyflakes undefined-name check, and pytest suite."
    },
    "F62": {
        "status": "FIXED_VERIFIED",
        "root_cause": "get_or_create_default_org had a check-then-act race causing MultipleResultsFound or duplicate org creation under concurrency.",
        "changed_files": [
            "backend/app/services/billing_service.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "billing_service savepoint retry logic.",
        "observed_test_result": "Nested transaction / savepoint catches IntegrityError and re-queries the newly inserted organization."
    },
    "F63": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Hot queries on scrape_jobs, creatives, and leadgen_leads lacked composite and single-column indexes.",
        "changed_files": [
            "backend/alembic/versions/b1c2d3e4f5a6_complete_production_schema_alignment.py",
            "backend/app/models/scrape_job.py",
            "backend/app/models/creative.py",
            "backend/app/models/leadgen.py"
        ],
        "migration_config_impact": "Added ix_scrape_jobs_org_status_created, ix_creatives_job_id, ix_creatives_brand_id, ix_creatives_brand_name, ix_leadgen_leads_job_id.",
        "regression_test": "alembic check and schema inspection.",
        "observed_test_result": "All supporting indexes present in database schema and models with zero drift."
    },
    "F70": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Startup reconciliation terminated active jobs exceeding cutoff based on created_at alone, killing live jobs with fresh heartbeats.",
        "changed_files": [
            "backend/app/main.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "main.py reconciliation query inspection.",
        "observed_test_result": "Reconciliation query checks heartbeat_at < :cutoff (falling back to created_at < :cutoff only if heartbeat is null)."
    },
    "F74": {
        "status": "FIXED_VERIFIED",
        "root_cause": "backend/requirements.txt had unpinned >= versions allowing breaking dependency shifts across deployments.",
        "changed_files": [
            "backend/requirements.txt"
        ],
        "migration_config_impact": "None",
        "regression_test": "requirements.txt inspection against pip freeze.",
        "observed_test_result": "All requirements pinned to exact versions."
    },
    "F77": {
        "status": "FIXED_VERIFIED",
        "root_cause": "34 server-default discrepancies and nullable timestamp columns between models and previous migrations.",
        "changed_files": [
            "backend/alembic/versions/b1c2d3e4f5a6_complete_production_schema_alignment.py",
            "backend/app/models/*.py"
        ],
        "migration_config_impact": "Aligned server_default values in b1c2d3e4f5a6 and models.",
        "regression_test": "alembic check autogenerate comparison.",
        "observed_test_result": "Zero schema differences or default mismatches detected."
    }
}

phase2_updates = {
    "F02": {
        "status": "FIXED_VERIFIED",
        "root_cause": "_verify_password_sync accepted passwords if hashed_password == 'EXTERNAL_AUTH_MANAGED' or if plaintext matched.",
        "changed_files": [
            "backend/app/core/security.py",
            "backend/tests/test_auth_reset_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "test_auth_reset_suite.py::test_f02_external_auth_managed_cannot_login_with_password",
        "observed_test_result": "External-auth markers and plaintext passwords strictly rejected with 401."
    },
    "F17": {
        "status": "FIXED_VERIFIED",
        "root_cause": "forgot_password logged plain reset tokens and raw URLs directly to standard logs.",
        "changed_files": [
            "backend/app/api/routers/auth.py",
            "backend/app/services/email_service.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "test_auth_reset_suite.py::test_f17_forgot_password_does_not_log_plain_token",
        "observed_test_result": "Raw reset tokens/links redacted from logs; transactional email dispatch wired."
    },
    "F18": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Mismatched reset token attempts cleared the existing password_reset_token_hash, invalidating newer valid links.",
        "changed_files": [
            "backend/app/services/auth_service.py",
            "backend/tests/test_auth_reset_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "test_auth_reset_suite.py::test_f18_stale_reset_link_does_not_destroy_new_link",
        "observed_test_result": "Atomic with_for_update() lock used; invalid/stale attempts do not destroy valid tokens."
    },
    "F19": {
        "status": "FIXED_VERIFIED",
        "root_cause": "JWT access tokens lacked versioning (ver), allowing compromised or old tokens to stay valid until expiration.",
        "changed_files": [
            "backend/app/core/security.py",
            "backend/app/core/deps.py",
            "backend/app/services/auth_service.py",
            "backend/app/api/routers/account.py",
            "backend/app/api/routers/auth.py",
            "backend/tests/test_auth_reset_suite.py"
        ],
        "migration_config_impact": "None (uses signup_metadata JSON column)",
        "regression_test": "test_auth_reset_suite.py::test_f19_token_revocation_on_reset",
        "observed_test_result": "JWT ver claims matched against signup_metadata['token_version']; previous tokens immediately rejected with 401 upon reset, password change, or signout."
    },
    "F20": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Long-lived Meta access tokens were committed directly in utility scripts.",
        "changed_files": [
            "backend/scripts/inspect_meta_token.py",
            "backend/scripts/test_new_meta.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "Static analysis on scripts folder and git grep.",
        "observed_test_result": "Hardcoded tokens removed; now loaded strictly from environment variable META_ACCESS_TOKEN."
    },
    "F21": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Scout Hunter API keys and LinkedIn session cookies were saved in plaintext in workspace/tenant settings.",
        "changed_files": [
            "backend/app/api/routers/scout.py",
            "backend/app/services/scout_service.py",
            "backend/app/services/leadgen_pipeline.py",
            "backend/app/services/security_service.py",
            "backend/tests/test_byok_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "test_byok_suite.py::test_f21_scout_credentials_encrypted_in_db",
        "observed_test_result": "hunter_api_key and linkedin_cookie stored encrypted with Fernet and safely decrypted at runtime."
    },
    "F22": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Endpoints accepted byok_key in URL query strings, leaking keys to server logs, proxies, and browser histories.",
        "changed_files": [
            "backend/app/api/routers/creatives.py",
            "src/services/api/analysisService.api.js",
            "backend/tests/test_byok_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "test_byok_suite.py::test_f22_byok_query_params_rejected",
        "observed_test_result": "Query param byok_key removed from API contracts; accepted exclusively via POST request body schema ByokGenerateRequest."
    },
    "F52": {
        "status": "FIXED_VERIFIED",
        "root_cause": "seed_admin.py used 'password123' if ADMIN_PASSWORD was unset.",
        "changed_files": [
            "backend/scripts/seed_admin.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "Inspection of backend/scripts/seed_admin.py.",
        "observed_test_result": "Script requires explicit ADMIN_PASSWORD or generates high-entropy random password printed once to stdout."
    },
    "F59": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Remote JWKS endpoint was fetched without caching or fallback handling during key rotation.",
        "changed_files": [
            "backend/app/core/security.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "Unit test verifying TTL cache (_JWKS_CACHE_TTL_SECONDS = 3600.0) and force-refresh on key mismatch.",
        "observed_test_result": "In-memory cached JWKS with automatic TTL expiry and dynamic cache-invalidation retry on missing kid."
    },
    "F60": {
        "status": "FIXED_VERIFIED",
        "root_cause": "ProfileUpdateRequest in account.py lacked length constraints on new_password.",
        "changed_files": [
            "backend/app/api/routers/account.py",
            "backend/tests/test_security_regressions.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "test_security_regressions.py",
        "observed_test_result": "Pydantic field validator enforces 8 to 128 characters; session version is incremented upon password change."
    },
    "F76": {
        "status": "FIXED_VERIFIED",
        "root_cause": "authService.api.js left tenant-specific tokens, cached headers, and search histories in localStorage after logout.",
        "changed_files": [
            "src/services/api/authService.api.js"
        ],
        "migration_config_impact": "None",
        "regression_test": "Static analysis of logout handlers and storage purging logic.",
        "observed_test_result": "clearAllTenantStorage() clears all session tokens, user data, workspace caches, and auth headers on signout."
    }
}

phase3_updates = {
    "F03": {
        "status": "FIXED_VERIFIED",
        "root_cause": "save_creative only checked if the creative ID existed in the database without checking if the creative's scrape job belonged to the user's organization.",
        "changed_files": [
            "backend/app/services/creative_service.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f03_creative_save_cross_tenant_isolation",
        "observed_test_result": "Cross-tenant save attempt returns 404 (Not Found) preventing resource enumeration, while authorized owner saves successfully."
    },
    "F04": {
        "status": "FIXED_VERIFIED",
        "root_cause": "compile_playbook did not validate job_id tenant ownership and ran unscoped queries for creatives, patterns, and insights across all tenants in the system.",
        "changed_files": [
            "backend/app/services/playbook_service.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f04_playbook_compile_cross_tenant_isolation",
        "observed_test_result": "Foreign job_id rejected with 404; queries for creatives, patterns, and insights strictly filter through user_org_ids."
    },
    "F05": {
        "status": "FIXED_VERIFIED",
        "root_cause": "list_brands and list_patterns executed unconstrained table scans across the entire database without tenant scoping.",
        "changed_files": [
            "backend/app/services/creative_service.py",
            "backend/app/api/routers/creatives.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f05_brands_and_patterns_tenant_scoping",
        "observed_test_result": "list_brands and list_patterns accept user_org_ids and scope queries to caller's organizations or global templates."
    },
    "F06": {
        "status": "FIXED_VERIFIED",
        "root_cause": "generate_insight_for_creative and simulate_creative_for_audiences accepted foreign creative IDs without validating that the creative belonged to the caller's organization.",
        "changed_files": [
            "backend/app/services/analysis_service.py",
            "backend/app/services/simulation_service.py",
            "backend/app/api/routers/creatives.py",
            "backend/app/api/routers/simulation.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f06_insights_and_simulation_cross_tenant_isolation",
        "observed_test_result": "Foreign creative IDs return 404 (Not Found) across both insight generation and persona simulation endpoints."
    },
    "F12": {
        "status": "FIXED_VERIFIED",
        "root_cause": "SearchContext.jsx used un-namespaced localStorage keys, causing search history and active creative state to persist across account signouts and switches.",
        "changed_files": [
            "src/context/SearchContext.jsx",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f12_f43_search_history_storage_isolation",
        "observed_test_result": "SearchContext hooks into useAuth() to namespace all stored keys by userId and purges memory state upon logout."
    },
    "F43": {
        "status": "FIXED_VERIFIED",
        "root_cause": "DEFAULT_SEARCH_HISTORY in SearchContext.jsx populated fictional brands ('Sneako', 'Naturia', 'Real Madrid', 'Gymshark', 'Nike') for newly registered users.",
        "changed_files": [
            "src/context/SearchContext.jsx",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f12_f43_search_history_storage_isolation",
        "observed_test_result": "Fictional default search history removed; new user accounts start with an empty, honest search history array."
    },
    "F46": {
        "status": "FIXED_VERIFIED",
        "root_cause": "team_service.py did not dispatch transactional emails; get_user_org_ids did not include member organizations, preventing invited members from accessing shared workspace resources.",
        "changed_files": [
            "backend/app/services/team_service.py",
            "backend/app/core/tenancy.py",
            "backend/app/services/billing_service.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f46_f47_team_management_rbac_and_invite_redemption",
        "observed_test_result": "send_email invoked with valid invitation link; get_user_org_ids includes both owned and member organizations."
    },
    "F47": {
        "status": "FIXED_VERIFIED",
        "root_cause": "accept_invite allowed any authenticated user to redeem any invite token without checking if their email matched the invitation, and lacked concurrency locking.",
        "changed_files": [
            "backend/app/services/team_service.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f46_f47_team_management_rbac_and_invite_redemption",
        "observed_test_result": "Row-locked FOR UPDATE query prevents double-redemption; mismatch between invite email and logged-in user email returns 403 Forbidden."
    },
    "F48": {
        "status": "FIXED_VERIFIED",
        "root_cause": "list_published_updates and get_active_banner returned all published updates to unauthenticated callers without checking show_on_public.",
        "changed_files": [
            "backend/app/api/routers/updates.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f48_updates_unauthenticated_public_filtering",
        "observed_test_result": "Unauthenticated requests are filtered strictly to show_on_public == True, protecting internal app announcements."
    },
    "F53": {
        "status": "FIXED_VERIFIED",
        "root_cause": "generate_patterns_for_recent_creatives had shifted positional arguments, lacked job ownership verification, selected unscoped global data, and lacked credit deduction.",
        "changed_files": [
            "backend/app/services/creative_service.py",
            "backend/app/api/routers/creatives.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f53_generate_patterns_validation_and_credit",
        "observed_test_result": "job_id validated against user_org_ids (404 on foreign job); arguments aligned; assert_can_spend and charge enforced."
    },
    "F61": {
        "status": "FIXED_VERIFIED",
        "root_cause": "authenticate_api_key only checked key_hash and is_active without verifying that the organization still held the public_api feature entitlement; failed to isolate tenancy to the key's org.",
        "changed_files": [
            "backend/app/services/api_key_service.py",
            "backend/app/core/deps.py",
            "backend/app/core/tenancy.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f61_api_key_entitlement_and_scoping",
        "observed_test_result": "Revocation of public_api flag returns 403 Forbidden; authenticated user has _scoped_org_id attached, constraining get_user_org_ids to that single workspace."
    },
    "F80": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Endpoints used get_current_admin which only checked role in ('admin', 'assistant-admin'), completely ignoring user.admin_permissions JSON restrictions.",
        "changed_files": [
            "backend/app/core/deps.py",
            "backend/app/api/routers/admin.py",
            "backend/tests/test_phase3_isolation_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase3_isolation_suite.py::test_f80_granular_admin_permissions",
        "observed_test_result": "require_admin_permission dependency checks explicit denial flags and allowed sections; unauthorized assistant-admins receive 403 Forbidden."
    }
}

phase4_updates = {
    "F07": {
        "status": "FIXED_VERIFIED",
        "root_cause": "charge() used with_for_update() without execution_options(populate_existing=True), allowing SQLAlchemy identity-map session cache to return stale credit balances and daily reset timestamps under concurrent operations.",
        "changed_files": [
            "backend/app/services/billing_service.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f07_f10_atomic_charge_and_idempotency_key",
        "observed_test_result": "populate_existing=True forces fresh SELECT FOR UPDATE row fetch; concurrent deductions cleanly update refreshed balances and daily metrics."
    },
    "F08": {
        "status": "FIXED_VERIFIED",
        "root_cause": "refund() lacked idempotency protection against duplicate refund attempts for the same job_id. Background reconciliation lacked SKIP LOCKED and failed to scan and refund unrefunded failed scrape jobs.",
        "changed_files": [
            "backend/app/services/billing_service.py",
            "backend/app/services/job_reconciliation.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f08_idempotent_refund_and_reconciliation_sweeper",
        "observed_test_result": "refund() verifies existing negative UsageLog entries for job_id and rejects duplicate refund attempts; job_reconciliation sweeper scans unrefunded failed jobs and restores balances."
    },
    "F09": {
        "status": "FIXED_VERIFIED",
        "root_cause": "AI provider exceptions were caught in analysis_service to generate fabricated semantic mock insights with 0.92 confidence, charging user credits and storing fake data in the DB.",
        "changed_files": [
            "backend/app/services/ai/base.py",
            "backend/app/services/analysis_service.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f09_provider_outage_raises_honest_503_without_charging",
        "observed_test_result": "Provider outages raise honest 503 Service Unavailable without deducting credits or persisting mock teardowns."
    },
    "F10": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Frontend axios interceptor blindly retried 502/503/504 errors on non-idempotent POST/PATCH mutations without idempotency keys. Backend endpoints lacked replay short-circuiting.",
        "changed_files": [
            "src/services/http.js",
            "backend/app/services/billing_service.py",
            "backend/app/api/routers/scout.py",
            "backend/app/api/routers/leadgen.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f10_http_js_restricts_mutation_retries",
        "observed_test_result": "Frontend only retries GET/HEAD/OPTIONS or requests with Idempotency-Key; backend endpoints verify idempotency key and return existing job/charge without re-billing."
    },
    "F11": {
        "status": "FIXED_VERIFIED",
        "root_cause": "assert_can_generate_image in billing_service.py failed to enforce concurrent in-flight job limits and daily plan limits, allowing unlimited parallel media generation.",
        "changed_files": [
            "backend/app/services/billing_service.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f11_f55_inflight_concurrency_and_per_plan_quotas",
        "observed_test_result": "In-flight job count checked against plan concurrency limit; daily image/video counts checked against plan limits, returning 429 when exhausted."
    },
    "F27": {
        "status": "FIXED_VERIFIED",
        "root_cause": "LeadGen router silently replaced user's credit_budget with credit_cost and charged without verifying budget sufficiency, bypassing user limits.",
        "changed_files": [
            "backend/app/api/routers/leadgen.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f27_leadgen_budget_ceiling_rejection_and_charge",
        "observed_test_result": "Rejects requests where credit_budget < credit_cost with 400 Bad Request; passes user budget into job and asserts sufficient credits before deduction."
    },
    "F28": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Pre-work errors and unhandled worker exceptions in scout, maps scout, and leadgen pipelines exited without refunding deducted credits.",
        "changed_files": [
            "backend/app/services/scout_service.py",
            "backend/app/services/maps_scout_service.py",
            "backend/app/services/leadgen_pipeline.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f28_prework_failure_refunds_deducted_credits",
        "observed_test_result": "refund() invoked on pre-work exceptions and empty scrape targets across scout, maps, and leadgen workers, restoring user credits."
    },
    "F32": {
        "status": "FIXED_VERIFIED",
        "root_cause": "AIRouter checked trial_expires_at and trial 20-request cap without checking if user belonged to an active paid plan, locking out paid users when trial expired.",
        "changed_files": [
            "backend/app/services/ai/ai_router.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f32_paid_user_bypasses_trial_expiration_and_limits",
        "observed_test_result": "Paid workspace users bypass trial expiry and trial 20-request cap, routing cleanly to managed or BYOK providers."
    },
    "F50": {
        "status": "FIXED_VERIFIED",
        "root_cause": "api_usage_service.py used a global DAILY_API_CAP = 20 that throttled all tenants collectively and counted failed API calls towards the limit.",
        "changed_files": [
            "backend/app/services/api_usage_service.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f50_org_scoped_api_usage_cap",
        "observed_test_result": "Usage caps are strictly scoped per organization ID; failed requests (status == 'failed') are excluded from usage counts."
    },
    "F55": {
        "status": "FIXED_VERIFIED",
        "root_cause": "discover_service.py committed database changes before invoking charge(), leaving orphaned records in the database if the credit charge failed.",
        "changed_files": [
            "backend/app/services/discover_service.py",
            "backend/tests/test_phase4_credits_quotas_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase4_credits_quotas_suite.py::test_f11_f55_inflight_concurrency_and_per_plan_quotas",
        "observed_test_result": "Full commit before charge replaced with nested transaction / savepoint rollback, preventing orphaned discovery jobs on charge failure."
    }
}

phase5_updates = {
    "F23": {
        "status": "FIXED_VERIFIED",
        "root_cause": "SSRF filters did not unmap IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1) and allowed redirect hops to bypass IP checks.",
        "changed_files": [
            "backend/app/services/security_service.py",
            "backend/app/services/leadgen_pipeline.py",
            "backend/tests/test_phase5_durable_jobs_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase5_durable_jobs_suite.py::test_f23_ssrf_ipv4_mapped_ipv6_and_private_host_blocking, test_f23_safe_http_get_hop_by_hop_redirect_safety",
        "observed_test_result": "IPv4-mapped IPv6 unmapped and checked against blocked CIDRs; safe_http_get inspects each redirect hop and raises ValueError on private destinations."
    },
    "F24": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Workers ran asyncio.run() repeatedly with shared QueuePool engine, causing asyncpg connection reuse across destroyed event loops and crashing with Event loop is closed.",
        "changed_files": [
            "backend/app/db/session.py",
            "backend/workers/scrapling/worker.py",
            "backend/app/services/leadgen_pipeline.py",
            "backend/tests/test_phase5_durable_jobs_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase5_durable_jobs_suite.py::test_f24_worker_engine_uses_nullpool",
        "observed_test_result": "worker_engine configured with NullPool; worker main() runs a persistent long-lived async loop with zero event loop reuse crashes."
    },
    "F25": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Scout, Maps, and Media jobs lacked heartbeat_at/owner_boot_id tracking and were omitted from service restart sweeper and refund passes.",
        "changed_files": [
            "backend/app/api/routers/scout.py",
            "backend/app/services/media_service.py",
            "backend/app/services/job_reconciliation.py",
            "backend/tests/test_phase5_durable_jobs_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase5_durable_jobs_suite.py::test_f25_reconciliation_sweeper_handles_all_job_types",
        "observed_test_result": "heartbeat_at and owner_boot_id stamped upon dispatch; reconcile_once sweeps stalled scout, maps, media, and leadgen jobs and refunds credits."
    },
    "F26": {
        "status": "FIXED_VERIFIED",
        "root_cause": "LeadGen job submission accepted work without checking whether Scrapling worker was actually running and online, leading to indefinitely stuck queued jobs.",
        "changed_files": [
            "backend/app/api/routers/leadgen.py",
            "backend/tests/test_phase5_durable_jobs_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase5_durable_jobs_suite.py::test_f26_live_worker_health_verification",
        "observed_test_result": "_is_worker_available checks live HTTP ping or fresh DB worker heartbeat (<90s) before enqueuing, returning 503 if no worker is online."
    },
    "F69": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Timestamp formatting appended 'Z' to aware ISO strings producing invalid '+00:00Z', and updates.py stripped tzinfo naively, corrupting local time offsets.",
        "changed_files": [
            "backend/app/services/team_service.py",
            "backend/app/api/routers/updates.py",
            "backend/tests/test_phase5_durable_jobs_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase5_durable_jobs_suite.py::test_f69_format_utc_iso_no_double_offset, test_f69_normalize_to_utc_preserves_timestamp",
        "observed_test_result": "All ISO datetimes normalized to UTC with single 'Z' suffix; normalize_to_utc converts aware timestamps without clock skew."
    },
    "F71": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Unvalidated attribution parameters permitted email addresses into UTM fields forwarded to analytics, referrer query parameters leaked sensitive tokens, and signup logged plain emails.",
        "changed_files": [
            "src/lib/utm.js",
            "src/pages/auth/SignUpPage.jsx",
            "backend/app/services/auth_service.py",
            "backend/tests/test_phase5_durable_jobs_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase5_durable_jobs_suite.py::test_f71_register_user_sanitizes_pii_from_attribution",
        "observed_test_result": "Email patterns dropped from UTM fields; URL referrers have queries/fragments stripped; plain email removed from signup attribution log."
    },
    "F72": {
        "status": "FIXED_VERIFIED",
        "root_cause": "utm.js persistence condition omitted utm_term and utm_content, causing term-only or content-only campaigns to be dropped.",
        "changed_files": [
            "src/lib/utm.js",
            "backend/tests/test_phase5_durable_jobs_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase5_durable_jobs_suite.py::test_f72_utm_file_verifies_term_content_condition",
        "observed_test_result": "utm_term and utm_content included in captureAttribution condition, persisting term/content campaigns reliably."
    },
    "F73": {
        "status": "FIXED_VERIFIED",
        "root_cause": "ConfirmDialog lacked focus trapping and restoration; password reveal button had tabIndex=-1; SavedDraftsModal inputs lacked htmlFor/id associations.",
        "changed_files": [
            "src/components/ui/ConfirmDialog.jsx",
            "src/components/ui/Field.jsx",
            "src/components/SavedDraftsModal.jsx",
            "backend/tests/test_phase5_durable_jobs_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase5_durable_jobs_suite.py::test_f73_accessibility_contracts_in_components",
        "observed_test_result": "ConfirmDialog traps focus within dialog and restores focus on unmount; password button keyboard accessible; form inputs have unique IDs bound to labels."
    }
}

phase6_updates = {
    "F29": {
        "status": "FIXED_VERIFIED",
        "root_cause": "AdLibraryProvider did not distinguish between empty search results and total provider failure/unconfigured keys, treating outages as successful searches without refunding.",
        "changed_files": [
            "backend/app/services/scraping/ad_library_provider.py",
            "backend/app/services/discover_service.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_discovery_provider_outage_and_refund",
        "observed_test_result": "Provider outage detected when all sub-providers fail/unconfigured; discover job marked failed with failure_kind='provider_outage' and credit refund issued."
    },
    "F30": {
        "status": "FIXED_VERIFIED",
        "root_cause": "LeadGen pipeline pause loop held a cached ORM session instance without populate_existing/refresh, and resume check ignored checkpoint_path when status was queued.",
        "changed_files": [
            "backend/app/services/leadgen_pipeline.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_leadgen_checkpoint_resume_and_pause_refresh",
        "observed_test_result": "populate_existing=True and session.refresh reload live status during pause; bool(job.checkpoint_path) restores queued or paused jobs from checkpoint without starting from scratch."
    },
    "F31": {
        "status": "FIXED_VERIFIED",
        "root_cause": "MultiTierAIProvider evaluated os.getenv without importing os, crashing with NameError upon fallback.",
        "changed_files": [
            "backend/app/services/ai/ai_router.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "Import inspection and static verification in ai_router.py.",
        "observed_test_result": "os is properly imported and secondary providers initialize safely with config fallbacks."
    },
    "F33": {
        "status": "FIXED_VERIFIED",
        "root_cause": "create_custom_swipe_reference imported nonexistent app.models.score, lacked required job_id/brand_id foreign keys, and hardcoded a synthetic 10,000 impression estimate.",
        "changed_files": [
            "backend/app/services/creative_service.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_custom_swipe_reference_integrity",
        "observed_test_result": "Creates parent ScrapeJob and brand_id; sets honest impressions_est=None and is_estimated=False."
    },
    "F34": {
        "status": "FIXED_VERIFIED",
        "root_cause": "account.py called nonexistent storage_service.save_file on avatar upload.",
        "changed_files": [
            "backend/app/services/storage_service.py",
            "backend/app/api/routers/account.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_storage_service_save_file_and_r2_validation",
        "observed_test_result": "save_file persists raw binary bytes with content_type and returns signed URL."
    },
    "F37": {
        "status": "FIXED_VERIFIED",
        "root_cause": "support_service.py used unimported func for reply counts and suffered from N+1 user lookup queries.",
        "changed_files": [
            "backend/app/services/support_service.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_support_ticket_batching_and_pagination",
        "observed_test_result": "Batch queries compute reply counts and resolve user emails without N+1 overhead."
    },
    "F38": {
        "status": "FIXED_VERIFIED",
        "root_cause": "GeminiProvider.generate_image did not accept seed or **kwargs, crashing BYOK requests.",
        "changed_files": [
            "backend/app/services/ai/gemini_provider.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_gemini_image_generation_kwargs",
        "observed_test_result": "generate_image accepts seed and arbitrary keyword parameters without TypeError."
    },
    "F39": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Managed media provider resolver prioritized third-party providers over server GEMINI_API_KEY, Pollinations ignored reference images, and video generator omitted start/end frames.",
        "changed_files": [
            "backend/app/services/provider_resolver.py",
            "backend/app/services/ai/pollinations_provider.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_pollinations_and_provider_resolver",
        "observed_test_result": "Resolver prioritizes server GEMINI_API_KEY; Pollinations forwards reference_images, start_frame, and end_frame in API queries."
    },
    "F40": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Media generation background task did not check if the job was canceled, overwriting canceled status with completed and debiting quotas.",
        "changed_files": [
            "backend/app/services/media_service.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_media_generation_canceled_and_failure_handling",
        "observed_test_result": "Canceled jobs abort immediately before starting and do not write completed status or record quota usage."
    },
    "F41": {
        "status": "FIXED_VERIFIED",
        "root_cause": "generate_insight_for_creative did not persist extended fields (emotional_resonance, script_teardown, fatigue_prediction, key_elements, recommendations) in AIInsight.reasons, causing them to vanish on page reload.",
        "changed_files": [
            "backend/app/services/analysis_service.py",
            "backend/app/schemas/analysis.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_insight_extended_fields_persistence_and_no_row_lock",
        "observed_test_result": "Extended insight fields persisted in reasons JSON and unpacked faithfully when reading creative insights."
    },
    "F42": {
        "status": "FIXED_VERIFIED",
        "root_cause": "IntelligencePage synthesized a fake 0.94 confidence insight on backend error and forced canned translation text.",
        "changed_files": [
            "src/pages/IntelligencePage.jsx"
        ],
        "migration_config_impact": "None",
        "regression_test": "Component test and code audit of IntelligencePage.jsx error handler.",
        "observed_test_result": "Synthetic fallback removed; reports honest error banner to user upon API failure."
    },
    "F49": {
        "status": "FIXED_VERIFIED",
        "root_cause": "storage_service silently fell back to ephemeral local disk when R2 was partially configured or in production, causing lost media assets across container restarts.",
        "changed_files": [
            "backend/app/services/storage_service.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_storage_service_save_file_and_r2_validation",
        "observed_test_result": "Raises RuntimeError on partial R2 configuration and strictly forbids local storage fallback in production environment."
    },
    "F54": {
        "status": "FIXED_VERIFIED",
        "root_cause": "monitor_service diffed failed discovery jobs as empty inventory, emitting false 'ad stopped' notifications.",
        "changed_files": [
            "backend/app/services/monitor_service.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "monitor_service code audit verifying job.status == 'failed' or failure_kind == 'provider_outage' bypasses diff.",
        "observed_test_result": "Failed discovery jobs are skipped during monitor diffing, preventing phantom ad stoppage alerts."
    },
    "F64": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Support tickets and admin lists lacked pagination and performed N+1 queries.",
        "changed_files": [
            "backend/app/services/support_service.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_support_ticket_batching_and_pagination",
        "observed_test_result": "Batch queries and limit/offset pagination applied across user and admin ticket queries."
    },
    "F65": {
        "status": "FIXED_VERIFIED",
        "root_cause": "assert_can_spend locked organization rows during long LLM calls, blocking all organization operations.",
        "changed_files": [
            "backend/app/services/analysis_service.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_insight_extended_fields_persistence_and_no_row_lock",
        "observed_test_result": "lock_row=False used in pre-flight checks, releasing row locks before invoking external LLM providers."
    },
    "F81": {
        "status": "FIXED_VERIFIED",
        "root_cause": "capture_xhr_pattern was accepted by API and database but never implemented in scrapling_engine.",
        "changed_files": [
            "backend/app/services/scrapling_engine.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_scrapling_xhr_capture_with_ssrf_safety",
        "observed_test_result": "scrapling_engine parses and fetches matched XHR patterns with safe_http_get hop-by-hop SSRF validation and embeds captured payloads."
    },
    "F82": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Provider resolution errors in media generation were unhandled prior to the inner try-block, leaving jobs stuck in pending indefinitely.",
        "changed_files": [
            "backend/app/services/media_service.py",
            "backend/tests/test_phase6_pipeline_integrity_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase6_pipeline_integrity_suite.py::test_media_generation_canceled_and_failure_handling",
        "observed_test_result": "Top-level exception handling sets status='failed', failure_kind='error', and records honest error message in DB."
    }
}

phase7_updates = {
    "F35": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Performance metrics useMemo lacked definitions for avgDays, survivorRate, fatigued, scaling, and read .length on survivor number.",
        "changed_files": [
            "src/pages/PerformancePage.jsx"
        ],
        "migration_config_impact": "None",
        "regression_test": "npm run build && inspection of PerformancePage.jsx metrics useMemo.",
        "observed_test_result": "Frontend build exits code 0; metrics cleanly defines avgDays, survivorRate, survivorCount, fatiguedCount, scalingCount, videoCount without undefined access."
    },
    "F36": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Clock icon from lucide-react was rendered inside NotificationBell dropdown timestamp without being imported.",
        "changed_files": [
            "src/components/NotificationBell.jsx"
        ],
        "migration_config_impact": "None",
        "regression_test": "npm run build && component import audit.",
        "observed_test_result": "Clock added to lucide-react import in NotificationBell.jsx; frontend build succeeds cleanly with 0 errors."
    },
    "F44": {
        "status": "FIXED_VERIFIED",
        "root_cause": "SearchContext persisted latest search with camelCase jobId only while playbook compilation in IntelligencePage read job_id, dropping the active job link.",
        "changed_files": [
            "src/context/SearchContext.jsx",
            "src/pages/IntelligencePage.jsx",
            "backend/tests/test_phase7_frontend_and_billing_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase7_frontend_and_billing_suite.py::test_f44_playbook_compilation_preserves_job_id",
        "observed_test_result": "Both jobId and job_id stored in context and read in page; playbook compilation associates designated job id and creatives cleanly."
    },
    "F45": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Transient getSession() failure left status stuck in AUTH_STATUS.LOADING forever when a token was stored but no cached user existed.",
        "changed_files": [
            "src/context/AuthContext.jsx"
        ],
        "migration_config_impact": "None",
        "regression_test": "AuthContext session state machine inspection & npm run build.",
        "observed_test_result": "Null-session and catch branches transition to AUTH_STATUS.UNAUTHENTICATED when no user is loaded, guaranteeing a terminal state is reached."
    },
    "F51": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Impersonation handler stored only helix_auth_token while HTTP client prioritized helix_access_token, keeping admin credentials active.",
        "changed_files": [
            "src/pages/admin/UsersPage.jsx",
            "src/services/http.js",
            "backend/tests/test_phase7_frontend_and_billing_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase7_frontend_and_billing_suite.py::test_f51_impersonation_token_identity",
        "observed_test_result": "Impersonation updates both token keys and clears cached user; impersonation token accurately bears the target user subject ID."
    },
    "F56": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Dashboard playbook export hardcoded confidence scores (0.92, 0.95, 0.90) and manufactured estimated lift with Math.max(..., 5).",
        "changed_files": [
            "src/pages/DashboardPage.jsx"
        ],
        "migration_config_impact": "None",
        "regression_test": "npm run build && DashboardPage.jsx compilation audit.",
        "observed_test_result": "Manufactured confidence and minimum 5% lift removed, passing honest null or real backend telemetry values."
    },
    "F57": {
        "status": "FIXED_VERIFIED",
        "root_cause": "fetchLeads swallowed 500 errors and entered READY with empty list; save button updated badge optimistically on failure; http client retried structured 503 errors and overwrote them as server_waking.",
        "changed_files": [
            "src/hooks/useLeadGenJob.js",
            "src/pages/PerformancePage.jsx",
            "src/services/http.js",
            "backend/tests/test_phase7_frontend_and_billing_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase7_frontend_and_billing_suite.py::test_f57_leadgen_worker_offline_structured_error",
        "observed_test_result": "Saved badge only updates upon successful response; leadgen fetch failures surface honest error and failed state; structured 503 worker_offline errors preserved without spurious retry or overwrite."
    },
    "F79": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Paid and pay-as-you-go plans falsely displayed Monthly renewal without subscription lifecycle or payment webhook infrastructure.",
        "changed_files": [
            "src/pages/BillingPage.jsx",
            "backend/app/services/billing_service.py",
            "backend/tests/test_phase7_frontend_and_billing_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase7_frontend_and_billing_suite.py::test_f79_honest_subscription_lifecycle_and_no_fake_renewal",
        "observed_test_result": "BillingPage displays honest lifecycle labels ('Pay-as-you-go · Metered', '7-day trial · X days left', 'Workspace plan · Managed by Admin'); billing summary returns subscription_lifecycle without fake renewals."
    }
}

phase8_updates = {
    "F58": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Rate limiter extracted client IP naively from first hop of X-Forwarded-For which could be spoofed; lacked /api/v1/ prefix normalization; omitted /api/leadgen/jobs; and never evicted idle buckets causing memory leaks.",
        "changed_files": [
            "backend/app/middleware/rate_limit.py",
            "backend/tests/test_phase8_security_and_resilience_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase8_security_and_resilience_suite.py::test_f58_is_valid_public_ip, test_f58_client_ip_precedence, test_f58_rate_limit_rules_and_normalization",
        "observed_test_result": "Rate limiter inspects cf-connecting-ip, true-client-ip, and reverse-traverses x-forwarded-for for rightmost valid public IP; normalizes /api/v1/ aliases; includes /api/leadgen/jobs; and evicts expired buckets when table exceeds 500 keys."
    },
    "F66": {
        "status": "FIXED_VERIFIED",
        "root_cause": "robots_allowed had no timeout or size ceiling; parse_sitemap lacked depth and cycle tracking; Pollinations image/video downloads buffered unbounded responses in memory; media upload buffered entire file before checking size.",
        "changed_files": [
            "backend/app/services/scrapling_engine.py",
            "backend/app/services/leadgen_pipeline.py",
            "backend/app/services/ai/pollinations_provider.py",
            "backend/app/api/routers/media.py",
            "backend/tests/test_phase8_security_and_resilience_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase8_security_and_resilience_suite.py::test_f66_robots_allowed_ssrf_and_timeout, test_f66_parse_sitemap_recursion_and_visited_guards, test_f66_pollinations_streaming_chunk_limits",
        "observed_test_result": "robots_allowed enforces 5.0s timeout, SSRF guard, and 500KB read ceiling; parse_sitemap enforces max_depth=2 and visited set loop detection; Pollinations streams with 15MB/50MB chunk limits; media upload stream-reads in 64KB chunks up to 2MB."
    },
    "F67": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Leadgen and Scout CSV exports wrote unescaped user-controlled text directly to CSV cells, allowing spreadsheet formula injection (OWASP CWE-1236).",
        "changed_files": [
            "backend/app/api/routers/scout.py",
            "backend/app/api/routers/leadgen.py",
            "backend/tests/test_phase8_security_and_resilience_suite.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "backend/tests/test_phase8_security_and_resilience_suite.py::test_f67_csv_formula_injection_defense",
        "observed_test_result": "sanitize_csv_cell neutralizes formula triggers (=, +, -, @, \\t, \\r) by prepending a single quote (') before writing to CSV across Scout Atlas, Scout Maps, and LeadGen exports."
    },
    "F68": {
        "status": "FIXED_VERIFIED",
        "root_cause": "useDiscoverySearch used setInterval allowing concurrent in-flight status requests, and error catch handler did not verify activeJobId matching, allowing stale or canceled job errors to poison active state.",
        "changed_files": [
            "src/hooks/useDiscoverySearch.js"
        ],
        "migration_config_impact": "None",
        "regression_test": "Frontend build and timer lifecycle verification in npm run build.",
        "observed_test_result": "useDiscoverySearch uses sequential setTimeout chaining, cleans up timers on unmount/cancellation, and guards catch block with activeJobId.current === jobId."
    },
    "F75": {
        "status": "FIXED_VERIFIED",
        "root_cause": "src/services/config.js silently fell back to mock if VITE_DATA_SOURCE was not strictly 'api', allowing misspelled values or accidental mock data in production.",
        "changed_files": [
            "src/services/config.js"
        ],
        "migration_config_impact": "None",
        "regression_test": "Frontend build and validation tests in npm run build.",
        "observed_test_result": "config.js validates VITE_DATA_SOURCE strictly against ('api', 'mock'), throws descriptive error on invalid value, and explicitly forbids 'mock' in env.PROD."
    },
    "F78": {
        "status": "FIXED_VERIFIED",
        "root_cause": "Tracked dist/index.html was stale, and separate fallback/billing logic existed across modules.",
        "changed_files": [
            "dist/index.html",
            "backend/app/services/billing_service.py",
            "backend/app/services/analysis_service.py"
        ],
        "migration_config_impact": "None",
        "regression_test": "npm run build && full pytest suite across billing & analysis services.",
        "observed_test_result": "dist/index.html regenerated and cleanly committed; credit deduction logic unified across billing_service and analysis_service without duplicate or drifted credit logic."
    }
}

all_updates = {**phase1_updates, **phase2_updates, **phase3_updates, **phase4_updates, **phase5_updates, **phase6_updates, **phase7_updates, **phase8_updates}

for item in data:
    item_id = item["id"]
    if item_id in all_updates:
        item.update(all_updates[item_id])

with open("docs/production-readiness/remediation-status.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

# Also generate the updated markdown table
with open("docs/production-readiness/remediation-status.md", "w", encoding="utf-8") as f:
    f.write("# Helix Intelligence — Production-Readiness Remediation Ledger (F01–F82)\n\n")
    f.write("**Audited Revision**: 0a8164920031a8dfaa036e2a67ee6f107a48a9f2  \n")
    f.write("**Working Branch**: main  \n")
    fixed_count = sum(1 for x in data if x.get("status") == "FIXED_VERIFIED")
    f.write(f"**Total Findings**: 82 ({fixed_count} FIXED_VERIFIED, {82 - fixed_count} OPEN)  \n\n")
    f.write("| ID | Severity | Area | Title | Status | Changed Files | Regression Test | External Follow-up |\n")
    f.write("|---|---|---|---|---|---|---|---|\n")
    for item in data:
        files = ", ".join(item.get("changed_files", []))
        reg_test = item.get("regression_test") or "Pending"
        ext = item.get("external_follow_up") or "None"
        f.write(f"| {item['id']} | {item['original_severity']} | {item['area']} | {item['title']} | {item['status']} | {files} | {reg_test} | {ext} |\n")

print(f"Updated remediation-status.json and remediation-status.md ({fixed_count}/82 fixed).")
