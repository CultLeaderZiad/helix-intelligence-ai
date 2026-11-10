# Render production config check for W8 (no Shell needed, prints no values)

The live API (`srv-da3ocem7bikc73bfi4fg`, ohio) is a **free** Render web service:
no Shell, no SSH, no pre-deploy command. So the check runs on your own machine
against Render's environment export.

1. Render → helix-backend → Environment → **Export → Download .env**. Keep the
   file local: never commit it, never paste it into chat.
2. From `backend/`:

   ```bash
   python scripts/check_release_env.py --env-file "C:/path/to/render.env"
   ```

3. It prints only `OK`/`FAIL`, setting names, role names, the Neon branch and
   endpoint ids (read from the server: `neon.branch_id`) and the migration
   revision. The database part is read-only. Exit code 0 means everything passed.

What must pass before the W8 deploy:

- `DATABASE_URL` is `helix_api_login` on the live branch:
  - branch `br-gentle-star-axcrbk22` (the Neon branch **named `dev`**);
  - endpoint `ep-cold-rice-axydlqmv`;
  - role doesn't bypass RLS;
  - member of `helix_app`, and of `helix_worker` for the embedded worker.
- `ENVIRONMENT=production`.
- `PUBLIC_APP_BASE_URL` and `APP_BASE_URL` are public https URLs.
- `BACKEND_CORS_ORIGINS` has no `localhost`.
- `CREDENTIAL_ENCRYPTION_KEY` differs from `SECRET_KEY`.
- `RESEND_API_KEY` and `RESEND_FROM` are set.
- `EMBEDDED_WORKER_ENABLED=true`.
- `METAPI_API_KEY` is set.

Before the cutover, the current export reports the owner role, revision
`b1c2d3e4f5a6` and several missing settings. That list is the to-do list in
`docs/w8/release-plan.md`.
