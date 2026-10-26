# Deployment

The public demo uses the three-service configuration in `vercel.json` on the existing Vercel project. See [Hosted demo](HOSTED_DEMO.md) for its Neon Free persistence, anonymous isolation, limits, and smoke tests. The instructions below describe a separate private/production installation and its remaining operational requirements.

## Main web app

- Build: `npm ci && npm run build -w @veritas/web`.
- Start: `npm run start -w @veritas/web -- --port 3000`.
- Set `NEXT_PUBLIC_API_URL` to the public HTTPS API origin before building.
- Set `NEXT_PUBLIC_ISSUER_PORTAL_URL` to the public synthetic issuer origin for the workspace link.
- Set the API's `PUBLIC_WEB_URL` to this app's public HTTPS origin for QR links.

## API

- Use Python 3.11+ and install `apps/api/requirements.txt`.
- Install Tesseract 5 and the required OCR languages in the API image/host.
- Start: `uvicorn apps.api.main:app --host 0.0.0.0 --port 8002`.
- Set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE` for PostgreSQL. Without it, SQLite uses `VERITAS_DB_PATH`.
- Put `VERITAS_UPLOAD_PATH` on a private durable filesystem. Original documents must not be served as public static files.
- Set `VERITAS_WEB_ORIGIN` to the exact HTTPS frontend origin. For cookie authentication across distinct domains, use a reverse proxy/same-site deployment or configure and validate the cookie policy for that topology. The current default is `SameSite=Lax`.
- Set distinct `VERITAS_ACCESS_KEY` and `VERITAS_REVIEWER_KEY`, a strong `VERITAS_SESSION_SECRET`, and `VERITAS_COOKIE_SECURE=true`.
- Initial tables are created automatically. Use one API worker for this demo initialization flow; add migrations, durable jobs and operational controls before scaling.

## Synthetic issuer

- Build: `npm ci && npm run build -w @veritas/issuer-portal`.
- Start: `npm run start -w @veritas/issuer-portal -- --port 3001`.
- Deploy it at a public HTTPS URL. Keep the synthetic-data notice visible.
- Set the API's `ISSUER_PORTAL_URL` to its origin for synthetic registry checks.
- In the Source registry UI, register its exact public hostname as an issuer for `record_id`, `owner_name`, `area`, `issue_date`, `jurisdiction`, and `issuer`.

## TinyFish

Set backend-only `TINYFISH_API_KEY`. Keep the default documented product hosts from `.env.example` unless your account requires another supported endpoint. TinyFish Browser and Agent cannot reach localhost.

Set `TINYFISH_LIVE_REGISTRY_URL` to the deployed issuer homepage, then run:

```bash
.venv/bin/python scripts/smoke_tinyfish.py
```

This script loads `.env`, makes real provider requests, and reports failures. Browser and Agent tests explicitly skip when no public registry URL is configured. Agent has a 180-second duration limit; an optional beta step cap requires account enablement. No monetary cap is enforced by this API integration.

## Acceptance

Run the local smoke script against the configured API, validate both user and reviewer login, check upload previews and QR pages from the deployed browser, test revocation, then run all four real TinyFish capabilities. Add backups, retention rules, logging, rate limiting, durable workers and account-level user management before accepting sensitive production documents.
