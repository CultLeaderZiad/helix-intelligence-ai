# Render production config check for W8 (no Shell needed, prints no values)

The live API is Render service **`helix-intelligence-ai`**
(`srv-da3ocem7bikc73bfi4fg`, ohio), a **free** web service: no Shell, no SSH,
no pre-deploy command. There is no service named `helix-backend`. The check
runs on your own machine against a local env file.

The downloaded Render export is **plaintext secrets** (database URLs, `SECRET_KEY`,
provider keys).

1. Render → **helix-intelligence-ai** → Environment → **Export → Download .env**,
   or compose the same values in a local file before **Save, rebuild and deploy**.
   Keep that file only on your machine.
2. From `backend/`:

   ```bash
   python scripts/check_release_env.py --env-file "C:/path/to/render.env"
   ```

3. It prints only `OK`/`FAIL`, setting names, role names, the Neon branch and
   endpoint ids (read from the server: `neon.branch_id`) and the migration
   revision. The database part is read-only. Exit code 0 means everything passed.
4. **Delete the file** as soon as the check finishes, and empty the trash.
   Do not commit it, paste it into chat, or leave it in Downloads. A second
   export after the deploy, to confirm what Render stored, gets deleted too.

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
