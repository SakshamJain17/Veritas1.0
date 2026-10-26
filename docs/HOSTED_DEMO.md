# Hosted public demo

The deployment remains at **https://veritas1-0.vercel.app**. Vercel Services (beta) builds three components together:

| Path | Component |
| --- | --- |
| `/`, `/app`, `/verify` | Next.js frontend |
| `/api/*` | FastAPI backend, with the public `/api` prefix stripped before application routing |
| `/registry/*` | Next.js synthetic issuer, built with `/registry` as its base path |

The API uses a private registry service binding for its own synthetic checks. Evidence references use the public registry URL, not the private binding URL.

## Anonymous workspace isolation

Visitors need no shared code or signup. The API issues a random, HMAC-signed, Secure, HttpOnly, SameSite=Lax cookie. It selects a separate workspace for that browser. The frontend's reviewer tools operate only inside that demo workspace; they do not grant access to other visitors' data.

The new `veritas-demo` database uses Neon's `free_v3` plan. Supabase is not used. Original document bytes and application records persist in PostgreSQL rather than a Vercel function's temporary disk.

`VERITAS_DATABASE_URL` uses a restricted `veritas_app` role without BYPASSRLS or superuser rights. Every private application table has forced row-level security using a transaction-local workspace identifier. Runtime startup rejects a role that bypasses RLS. The Neon owner connection is for the versioned bootstrap/migration script, not application queries.

The public attestation index contains only already-permitted snapshot metadata. Other visitors can check a known verification link but cannot list the creator's documents, fetch original files, or revoke the creator's attestation.

Cookies expire after 30 days. Expired workspace cleanup runs opportunistically in bounded batches when a new visitor arrives; it is not an exact-time deletion guarantee. Clearing browser cookies loses access to the workspace. **Reset my demo** immediately deletes that workspace's records and public attestations. Do not upload sensitive documents to this demonstration.

## Free-demo safeguards

- PDF, PNG, or JPEG; maximum 3 MB per upload, 25 PDF pages, and 20 megapixels per image.
- At most eight documents per browser workspace. Reset the demo to clear them.
- Maximum 75 MB of retained original document bytes across the public demonstration. Reset/expired cleanup releases this budget.
- At most 250 new guest sessions per UTC day.
- At most ten investigation submissions per workspace per UTC day.
- Global daily investigation submission ceilings: 100 Search, 100 Fetch, three Browser, and three Agent requests. These are request ceilings, not monetary spend caps.
- Browser and Agent can consume TinyFish wallet credits and still require the account's product access. No paid Browser or Agent run is part of the deployment smoke test.
- English OCR data is fetched from the pinned Tesseract `tessdata_fast` 4.1.0 tag during the backend build. PyMuPDF 1.26.5 uses its bundled OCR engine without a system Tesseract executable. Other OCR languages are not bundled in the hosted demo.

These are application-level protections, not unlimited capacity or production abuse prevention. Vercel Hobby and Neon Free also have provider quotas. No paid hosting plan was enabled.

## Configuration and deployment

- `vercel.json` owns the three services and their routing. The Vercel project root is the repository root, not `apps/web`.
- `scripts/hosted-config.json` contains non-secret production settings.
- `scripts/bootstrap_hosted.py` applies the idempotent v1 schema and creates the restricted role, then stores its URL and the session-signing key as production Secrets. It requires the ignored `.env.production.local` with the owner's unpooled connection and must not be run casually to rotate keys.
- The existing `TINYFISH_API_KEY` remains a server-only production Secret.
- Do not overwrite the ignored local environment files with production Secret placeholders. Vercel cannot pull those Secret values back.
- Build and test a staged production deployment before promoting it. Keep the existing public alias unchanged until the tests pass.

Search/Fetch run within the API request in hosted mode; Agent creation returns its persisted run ID and subsequent reads poll the provider. This avoids depending on detached FastAPI background tasks surviving after a serverless response. It is not a general durable job queue.

## Verification

```bash
# Protected staging deployment: authenticated CLI access, not disabled protection
.venv/bin/python scripts/smoke_hosted.py https://DEPLOYMENT.vercel.app --vercel --tinyfish

# Public URL: anonymous HTTP clients with two separate cookie jars
.venv/bin/python scripts/smoke_hosted.py https://veritas1-0.vercel.app
```

The script uploads only synthetic fixtures and tests OCR, source previews, supported and contradicted outcomes, comparison, public hash/QR checks, unauthorized access rejection, owner revocation, and reset. `--tinyfish` adds one real Search and Fetch call; it never starts Browser or Agent. The script clears its own synthetic workspaces at the end.

`apps/api/tests/test_hosted.py` separately verifies isolation against the real restricted database when the hosted environment variables are supplied. The ordinary offline suite skips that test and all live TinyFish tests.

This is a public demonstration, not a service for production legal records. Formal migrations beyond bootstrap v1, operational backups, richer account recovery, dedicated abuse protection, malware scanning, and issuer signatures remain production work.
