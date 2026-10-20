# VERITAS · Proof of Reality

VERITAS extracts claims from documents, links them to source regions, checks them against evidence, and creates selective QR attestations. It does not determine legal ownership or act as a government authority.

## Run locally

Requirements: Node 20+, Python 3.11+ recommended, Tesseract 5 for scanned documents. Python 3.9 also works with the pinned dependency ranges currently used here.

```bash
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
cp .env.example .env
python scripts/generate_fixtures.py
uvicorn apps.api.main:app --env-file .env --port 8002
```

In two more terminals, run:

```bash
npm run dev -w @veritas/issuer-portal
NEXT_PUBLIC_API_URL=http://localhost:8002 npm run dev -w @veritas/web
```

Open the main app at `http://localhost:3000/app`, the fictional issuer at `http://localhost:3001`, and API docs at `http://localhost:8002/docs`. The four generated PDFs and one scanned PNG are in `fixtures/`.

The local registry check works without TinyFish credentials. Upload `matching-record.pdf`, select a claim, and click “Check synthetic registry.” `altered-owner.pdf` and `altered-area.pdf` produce contradictions. `unavailable-record.pdf` produces an unverified result. Tesseract must be installed to extract claims from `scanned-record.png`.

## Application

The sun/moon button in each page’s header switches directly between light and dark mode. New visitors follow their device setting until they choose a mode. The preference persists across reloads and is applied before first paint. Logos and favicons follow the selected theme; original document previews retain their paper colours. The main app and local issuer portal share the preference through a same-host cookie.

- `/`: animated landing page with a scroll-linked, manually scrollable document, extraction stages, source connectors, replay, editorial reveals, and reduced-motion support.
- `/app`: document library, multiple-file upload with real upload progress, samples processed through the backend, claim search and status filters, page navigation and zoom, linked source regions, four evidence checks, decision history, and selective attestation controls.
- Workspace navigation also opens the four TinyFish capabilities, adaptive routing recommendations, run history and traces, comparisons across all shared claim fields, reviewer decisions, approved source registration, audit history, and the attestation ledger.
- `/verify`: public attestation lookup. `/verify/{id}` checks the canonical hash and revocation state, and offers a share link and QR download without exposing the original document.
- The issuer portal provides public lookup, record details, issuer information, restricted-access notice, and machine-readable records.

Extraction currently uses deterministic rules for labeled records and certificates. It supports issuer, record ID, owner name, survey number, area, issue/expiry dates, and jurisdiction. No OpenAI dependency or general-purpose AI extraction is claimed.

## TinyFish

Set `TINYFISH_API_KEY` in the ignored `.env` file and restart the API. No OpenAI key is needed. The TinyFish key stays on the backend. Search and Fetch use TinyFish REST endpoints. Browser creates a TinyFish CDP session and drives a public lookup with Playwright. Agent starts an async run and is polled from the console. Browser and Agent require account access and wallet balance. To run them against the fictional issuer, deploy that portal to a public HTTPS host and register its exact hostname through the reviewer-only `POST /sources` endpoint (or `VERITAS_APPROVED_HOSTS`). The local `localhost:3001` registry cannot be reached by TinyFish cloud sessions.

Never put complete private documents in TinyFish queries. The console requires explicit consent before each request. Search snippets are discovery only; they do not change claim status.

## Access

For a deployed instance, set `VERITAS_ACCESS_KEY`, `VERITAS_REVIEWER_KEY`, and a long random `VERITAS_SESSION_SECRET`. Set `VERITAS_COOKIE_SECURE=true` behind HTTPS and `VERITAS_WEB_ORIGIN` to the exact frontend origin. Users sign in with the workspace key. Review and audit routes require the reviewer key. Without `VERITAS_ACCESS_KEY`, the app runs as an open local demo and must not be exposed to the internet with real documents.

SQLAlchemy persists to SQLite at `VERITAS_DB_PATH` by default (`data/veritas.db`). Set `DATABASE_URL` to use PostgreSQL instead. Uploaded originals go to `VERITAS_UPLOAD_PATH`; use a durable private volume in deployment. Table creation is automatic, but schema migrations, backups, and storage retention still need production operations. The public `/verify/{id}` endpoint returns attestation metadata only, not the original document.

## Tests

```bash
.venv/bin/python -m unittest discover -s apps/api/tests -v
npm run build
```

The deterministic suite tests PDF and scanned image extraction, local evidence decisions, attestation and QR integrity, authentication, and missing TinyFish credentials. Live TinyFish smoke tests are skipped until a key is configured. Live failures are never replaced with fixtures.

With all three local services running, `.venv/bin/python scripts/smoke_local.py` checks uploads, page previews, registry evidence, cross-document comparison, attestation privacy, QR output, and routing against real local HTTP endpoints. It creates two fictional uploads and an attestation. It does not call TinyFish.

TinyFish Agent runs have a 180-second duration limit. `TINYFISH_BETA_STEP_LIMIT=true` adds the documented 30-step limit only for accounts enabled for that beta capability. A monetary per-run cap is not exposed by the integration. Safe read requests have one bounded retry; browser and agent creation are not retried automatically.

See [architecture](docs/ARCHITECTURE.md), [requirements audit](docs/REQUIREMENTS_AUDIT.md), [deployment](docs/DEPLOYMENT.md), [demo guide](docs/DEMO.md), and [access policy](docs/ACCESS_POLICY.md).
