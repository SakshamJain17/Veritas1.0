# VERITAS
## Know what the record proves.

**Evidence-first, claim-level document verification.**

VERITAS turns documents into structured claims that can be traced to their original source, checked against evidence, reviewed for contradictions, and shared through selective verification links.

**Documents → Claims → Evidence → Verification → Trust**

[Website](https://veritas1-0.vercel.app) · [GitHub](https://github.com/SakshamJain17/Veritas1.0) · [Deployment guide](docs/DEPLOYMENT.md)

> The frontend is deployed on Vercel. A public API and persistent storage still need to be configured for hosted document and investigation workflows. Local setup runs the complete synthetic demonstration. VERITAS is not a government authority, legal certification service, or proof of ownership.

## Why VERITAS?

Ordinary extraction tells you what a document says. VERITAS also records where a claim came from, what evidence was retrieved, whether it applies to the same record, and why a verification decision was made.

For example, an uploaded record may state an owner's name and an area. VERITAS extracts these as separate claims, highlights their source regions, normalizes comparable values, and checks them independently. One field can be supported while another is contradicted or remains unverified.

## Features

### Documents and claims

- Upload PDFs, PNGs, and JPEGs with multiple-file selection and upload progress. The default limit is 15 MB per file.
- Read embedded PDF text with PyMuPDF; process scanned PDFs and images with Tesseract OCR, including mixed text/scanned PDFs.
- Extract supported labeled fields: issuer, record ID, owner name, survey number, area, issue/expiry dates, and jurisdiction.
- Inspect original values, normalized values, extraction confidence, page numbers, and source regions in a zoomable viewer.
- Search and filter claims, compare shared fields across documents, and inspect decision history.

### Evidence and investigation

- Check claims against a fictional local issuer registry.
- Discover public sources and retrieve evidence through TinyFish Search, Fetch, Browser, and Agent.
- Evaluate source authority, supporting excerpt, normalized value, and record/jurisdiction scope.
- Preserve supporting and contradictory observations instead of treating a document as wholly true or false.
- Inspect capability-routing recommendations, run history, results, errors, and persisted traces.
- Register approved sources and authorized claim fields through reviewer controls.

### Review and sharing

- Approve or reject extraction/evidence and correct extracted values.
- Inspect review decisions and audit events.
- Create selective attestation snapshots containing a chosen claim and evidence references.
- Share verification URLs and QR codes without returning the original upload through the public verification endpoint.
- Check canonical SHA-256 attestation integrity and current revocation state.

### Interface

- Responsive landing page and structured application workspace.
- Scroll-linked document motion, staged extraction, source connectors, replay, and reduced-motion support.
- Persistent sun/moon theme switch with matching light/dark logos and favicons.
- First-time visitors follow their device setting; original document previews retain their paper colours.

### Understanding claim status

| Status | Meaning |
| --- | --- |
| `pending_review` | An extracted claim awaits evaluation; extraction alone proves nothing. |
| `supported` | Eligible evidence supports the normalized value within the checked scope. |
| `contradicted` | Eligible evidence disagrees with the claim value. |
| `conflicting` | Eligible observations conflict and require review. |
| `unverified` | Insufficient eligible evidence for a supported or contradicted result. |

OCR confidence is not verification confidence. Missing public evidence does not prove a claim false. Approving extraction is not the same as approving external evidence.

## Architecture and technology

| Component | Responsibility | Technology |
| --- | --- | --- |
| Web app | Landing page, workspace, viewer, investigations, public verification UI | Next.js 16, React 19, TypeScript, Motion, Geist |
| API | Uploads, extraction, checks, investigations, reviews, comparisons, attestations | Python, FastAPI, Pydantic, HTTPX |
| Database | Documents, claims, sources, evidence, runs, reviews, audit events, attestations | SQLAlchemy; SQLite locally or PostgreSQL through configuration |
| Document processing | PDF parsing/rendering and scanned-document OCR | PyMuPDF, Pillow, Tesseract |
| External retrieval | Discovery, page retrieval, interactive lookup, bounded investigation | TinyFish; Playwright for managed CDP browser interactions |
| Synthetic issuer | Fictional public record lookup and machine-readable evidence | Separate Next.js application |

The web app calls FastAPI. The API stores metadata in the database and uploaded originals on its private filesystem. Claims retain page coordinates so source highlighting remains aligned when zooming. Evidence evaluation creates recorded decisions; selective attestations capture snapshots for public checking.

A document fingerprint identifies uploaded bytes. An attestation hash checks its canonical payload. Neither implies a blockchain transaction or an issuer's digital signature.

### Repository structure

```text
apps/
  web/                 Main Next.js application
  api/                 FastAPI service, extraction, persistence, and tests
    tinyfish/          Capability adapters and routing
  issuer-portal/       Fictional public registry and record API
packages/shared/       Shared logos, brand styles, and theme implementation
fixtures/              Synthetic PDFs and a scanned demonstration image
scripts/               Fixture generation and smoke checks
docs/                  Architecture, deployment, demo, and access documentation
.env.example           Configuration template without credentials
```

## Local setup

### 1. Prerequisites

- Node.js 22+ recommended, with npm.
- Python 3.11+ recommended, with virtual environment support.
- Tesseract 5 for scanned-document extraction; install the OCR languages your documents require.

Install Tesseract on macOS with `brew install tesseract`, or on Debian/Ubuntu with `sudo apt-get install tesseract-ocr`. Embedded-text PDFs are the appropriate demo input when OCR is unavailable.

### 2. Clone and install

```bash
git clone https://github.com/SakshamJain17/Veritas1.0.git
cd Veritas1.0
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

### 3. Configure

On a fresh checkout:

```bash
cp .env.example .env
python scripts/generate_fixtures.py
```

If `.env` already exists, edit it rather than overwriting its settings. TinyFish credentials are optional for the local registry demonstration. Never commit credentials or place them in `NEXT_PUBLIC_` variables.

### 4. Start three services

Run each command in a separate terminal from the repository root.

**API**

```bash
.venv/bin/uvicorn apps.api.main:app --env-file .env --port 8002
```

**Synthetic issuer**

```bash
npm run dev -w @veritas/issuer-portal
```

**Web application**

```bash
NEXT_PUBLIC_API_URL=http://localhost:8002 npm run dev -w @veritas/web
```

For PowerShell, set `$env:NEXT_PUBLIC_API_URL="http://localhost:8002"` before the npm command. Use `.venv\Scripts\python.exe -m uvicorn ...` instead of the Unix API executable path.

| Local URL | Purpose |
| --- | --- |
| `http://localhost:3000` | Landing page |
| `http://localhost:3000/app` | Workspace |
| `http://localhost:3000/verify` | Attestation lookup |
| `http://localhost:3001` | Fictional issuer |
| `http://localhost:8002/docs` | Interactive API documentation |
| `http://localhost:8002/health` | API health |
| `http://localhost:8002/tinyfish/health` | Credential configuration, not a live provider test |

### 5. Walk through the demo

1. Upload `fixtures/matching-record.pdf` in the workspace.
2. Select a claim and inspect its source highlight and normalized value.
3. Choose **Check synthetic registry** to compare it with the local fictional issuer.
4. Try `altered-owner.pdf` or `altered-area.pdf` to inspect contradictions.
5. Try `unavailable-record.pdf` for an unverified result. Unavailability is not proof of falsehood.
6. Upload `scanned-record.png` to exercise OCR when Tesseract is installed.
7. Compare documents, review a claim, then create and open an attestation and its QR code.

All supplied records are synthetic and have no legal standing.

## TinyFish integration

| Capability | Role |
| --- | --- |
| Search | Discover candidate public sources. Snippets never establish claim support. |
| Fetch | Retrieve approved pages and retain evidence excerpts and content digests. |
| Browser | Perform the synthetic district/survey lookup in a managed cloud browser; record steps and a screenshot. |
| Agent | Run a bounded asynchronous investigation and persist its polled result or failure. |

### Enable live requests

1. Add `TINYFISH_API_KEY=your_key_here` to the root `.env`.
2. Restart the API with `--env-file .env`.
3. Check `/tinyfish/health` for `configured: true`. This confirms a key was loaded, not accepted by the provider.
4. Open **Investigations**, select a capability, enter a public task, approve external-request consent, and execute.
5. Inspect the actual result and trace to confirm success or diagnose failure.

The key stays on the backend. No OpenAI key or dependency is required. Keep the product endpoint defaults in [.env.example](.env.example) unless your integration requires an alternative.

Fetch, Browser, and Agent destinations require approval through the source registry or `VERITAS_APPROVED_HOSTS`. Host approval alone does not establish issuer authority for every field: supporting evidence must also pass excerpt, normalized-value, and scope checks.

TinyFish cloud sessions cannot reach `localhost:3001`. To use this project's issuer, deploy it to public HTTPS, register its exact hostname and authorized fields, and set `TINYFISH_LIVE_REGISTRY_URL` for live tests. Browser and Agent depend on account access and available balance.

Agent runs have a 180-second duration limit. `TINYFISH_BETA_STEP_LIMIT=true` adds a 30-step limit only for accounts enabled for that beta feature. No monetary per-run cap is enforced. Safe reads have one bounded retry; browser and agent creation are not automatically retried.

Never send complete private documents in external search queries. Share only the minimum information needed for an authorized investigation.

## Configuration

See [.env.example](.env.example) for all defaults and product endpoint settings.

| Variable | Purpose |
| --- | --- |
| `TINYFISH_API_KEY` | Backend-only external-investigation credential |
| `TINYFISH_LIVE_REGISTRY_URL` | Public issuer homepage for live tests |
| `DATABASE_URL` | Optional PostgreSQL connection, overriding local SQLite |
| `VERITAS_DB_PATH` | SQLite path; default `./data/veritas.db` |
| `VERITAS_UPLOAD_PATH` | Private document directory; default `./uploads` |
| `UPLOAD_MAX_MB` | File-size limit; default 15 MB |
| `ISSUER_PORTAL_URL` | Issuer origin used by backend synthetic checks |
| `VERITAS_APPROVED_HOSTS` | Comma-separated exact retrieval hostnames |
| `NEXT_PUBLIC_API_URL` | Frontend API origin; set before building |
| `NEXT_PUBLIC_ISSUER_PORTAL_URL` | Frontend issuer link |
| `PUBLIC_WEB_URL` | Web origin embedded in verification/QR URLs |
| `VERITAS_WEB_ORIGIN` | Frontend origin allowed by API CORS |
| `VERITAS_ACCESS_KEY` | Workspace key; unset means open local demonstration |
| `VERITAS_REVIEWER_KEY` | Separate reviewer key |
| `VERITAS_SESSION_SECRET` | Session-signing secret |
| `VERITAS_COOKIE_SECURE` | Set to `true` behind HTTPS |

The API loads the root file through its explicit `--env-file` option. Configure non-default frontend values through the web app's environment or shell/build settings; do not assume Next.js loads the repository-root API file.

## API overview

Interactive schemas are available at `/docs` on the API service.

| Route group | Examples |
| --- | --- |
| Sessions and health | `/auth/session`, `/health`, `/tinyfish/health` |
| Documents | `/documents`, `/documents/{id}/claims`, `/documents/{id}/pages/{page_number}` |
| Evidence | `/claims/{id}/evidence`, `/claims/{id}/history`, `/claims/{id}/registry-check` |
| Sources and investigations | `/sources`, `/investigations/plan`, `/investigations`, `/investigations/{id}/traces` |
| Comparison and review | `/comparisons/documents`, `/reviews/{id}/decision`, `/evidence/{id}/review`, `/audit` |
| Attestation and public lookup | `/attestations`, `/attestations/{id}/revoke`, `/verify/{id}`, `/verify/{id}/qr` |

Methods, payloads, and permissions vary by endpoint. Source registration, review, and audit access require reviewer permissions when authentication is enabled.

## Privacy and trust boundaries

- Originals stay on the API host's private filesystem. Public lookup returns attestation metadata, not the original upload.
- Attestations intentionally disclose selected claim/evidence metadata. Review those selections before sharing.
- Attestations are snapshots, not live queries of the claim's latest status. Revocation is checked separately on lookup.
- Correcting a value invalidates prior evidence value checks until re-evaluation.
- Trace handling redacts credentials and connection URLs; retrieved content may still be sensitive.
- Restricted sources must not be bypassed. The synthetic issuer includes an explicit access notice.
- Set distinct access/reviewer keys, a strong session secret, HTTPS-only cookies, and the exact frontend origin before exposing private workflows.
- Sessions use `SameSite=Lax`. Validate a same-site/reverse-proxy topology before deploying authenticated services on unrelated domains.

Without `VERITAS_ACCESS_KEY`, this is an open local demo. Do not expose that configuration publicly with real documents.

## Tests

```bash
# Backend suite
.venv/bin/python -m unittest discover -s apps/api/tests -v

# Production builds for both Next.js applications
npm run build

# Real local HTTP workflow: start all three services first
.venv/bin/python scripts/smoke_local.py

# External provider requests: configure TinyFish and public issuer first
.venv/bin/python scripts/smoke_tinyfish.py
```

The local smoke script creates fictional uploads and an attestation, checking previews, registry evidence, comparison, privacy, QR output, and routing without TinyFish calls. The live smoke script makes external requests and may consume account credits.

The latest recorded backend run during setup had 35 tests: 31 passed, with four live TinyFish tests skipped because credentials were unavailable. Skipped live tests do not establish provider readiness. Re-run tests after changes; live failures are never replaced with fixtures.

## Deployment and limitations

The frontend is hosted at [veritas1-0.vercel.app](https://veritas1-0.vercel.app). Its Vercel project uses `apps/web` as the root and includes shared source outside that directory. GitHub is connected for future deployments. The requested `veritas.vercel.app` alias was unavailable; the older Veritas deployment was left unchanged.

To enable the full hosted application:

1. Deploy FastAPI with its Python dependencies, Tesseract, a durable database, and private persistent document storage.
2. Deploy the synthetic issuer separately, retaining fictional-data notices.
3. Configure access keys, session signing, HTTPS, CORS, cookie topology, issuer URLs, and approved sources.
4. Set the frontend's public API/issuer origins in Vercel and rebuild. A remote user's browser must not depend on `localhost`.
5. Configure backend TinyFish credentials and test all four capabilities with your account.
6. Validate uploads, user/reviewer access, evidence decisions, attestations, QR links, and revocation end to end.

Current boundaries:

- Extraction uses deterministic rules for supported labeled records/certificates, not arbitrary general-purpose AI document understanding.
- FastAPI background tasks are not a durable distributed worker queue.
- Automatic table creation is not a production migration strategy.
- Formal migrations, backups, retention/deletion policies, malware scanning, rate limiting, durable jobs, and account-level user management remain hardening work.
- A serverless host's local upload filesystem must not be assumed durable.
- Canonical hashes are not issuer signatures, legal authenticity guarantees, or blockchain anchoring.
- Live TinyFish access must be verified with the configured account before claiming readiness.

## Further documentation

- [Architecture and evidence rules](docs/ARCHITECTURE.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Demo walkthrough](docs/DEMO.md)
- [Access policy](docs/ACCESS_POLICY.md)
- [Requirements and implementation audit](docs/REQUIREMENTS_AUDIT.md)

**Every claim. Traceable to its source.**
