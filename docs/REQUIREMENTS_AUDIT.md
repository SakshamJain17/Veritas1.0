# VERITAS brief audit

The three original briefs were checked against the implementation on 20 October 2026.

| Requirement | Implemented behavior | Verification / limit |
| --- | --- | --- |
| Distinct landing design | Navy editorial hero, burgundy accents, local Geist, asymmetric sections and integrated product scenes | Production build passes; browser visual inspection was unavailable in this session |
| Coordinated motion | One-pass introduction, scroll-linked document, source scan, connector, delayed evidence phase, claim ledger, summary, replay and section reveals | Compiles; reduced-motion and responsive styles implemented; visual timing still needs browser review |
| Upload and OCR | PDF/PNG/JPG, multi-file selection, drag/drop, real upload progress, processing state, MIME/size checks, embedded text and OCR | Unit tests and running local HTTP smoke pass |
| Structured extraction | Eight labeled claim types, original/normalized values, regional numeral normalization and source regions | Deterministic extraction tested; no general-purpose LLM extraction provider is configured |
| Claim explorer | Connected document/claim/evidence panels, page navigation, zoom, search, filters, evidence checks and decision history | TypeScript/production build and backend flow checks pass |
| TinyFish Search | Real REST request, approved-host annotation, persisted result/error, no snippet-based verdict | Unit failure/retry paths tested; live test skipped without key |
| TinyFish Fetch | Real REST request, requested/final URL checks, excerpt/digest persistence and evidence evaluation | Authority/scope/value tests pass; live test skipped without key |
| TinyFish Browser | Actual managed CDP session, public lookup, navigation guard, steps, screenshot and cleanup | Timeout cleanup unit test passes; live run requires key and public issuer URL |
| TinyFish Agent | Actual async run, structured evidence output, duration bound, optional beta step limit, polling and trace persistence | Budget/timeout persistence tested; live run requires key |
| Adaptive routing | Plan endpoint and UI recommendation based on source, interaction and multi-step requirements | All four routing branches tested; execution requires user consent |
| Verification engine | Source authority per field, excerpt span, normalized value and record/jurisdiction scope; preserve conflicting eligible observations | Unit and local registry flow checks pass |
| Cross-document comparison | Server loads both documents and compares all shared fields under matching record, jurisdiction and exact applicable date | Altered owner yields one conflict in live local smoke |
| Human review | Source inspection, normalized correction, extraction decisions, evidence approval/rejection, mandatory reasons and history | Correction invalidation and evidence rejection tests pass |
| Persistence | SQLAlchemy models, SQLite default, PostgreSQL configuration, source registry, traces and decisions | SQLite tested; PostgreSQL live deployment has not been executed |
| QR/selective proof | Optional evidence references, public lookup, hash integrity, revocation, copy link and QR download | Local HTTP smoke verifies hash, QR and private-field exclusion |
| Audit and provenance | Upload/decision/review/investigation/attestation events, timestamps, digests and role-protected audit view | API flow tests pass |
| Synthetic issuer | Interactive lookup, labeled records, issuer information, JSON and restricted-access notice | Local registry HTTP checks pass; not publicly deployed |
| Access/privacy | Optional signed-cookie workspace/reviewer roles, backend-only key, explicit external consent, URL checks and limited public QR response | Role/privacy tests pass; open mode remains a local demonstration |

## Outstanding external and production work

Final local checks: both Next.js production builds passed. The Python suite ran 35 tests: 31 passed and four live TinyFish tests skipped. The running HTTP smoke passed upload, page preview, registry evidence, comparison, selective attestation privacy, public hash verification, QR and routing. Landing, workspace, public lookup, public attestation, issuer lookup, issuer information and issuer detail routes all returned HTTP 200. The served stylesheet bundle loaded successfully. These checks do not substitute for browser rendering or device interaction QA.

Hosted-demo update: a restricted Neon Free database and the three-service Vercel deployment have passed staging checks for PDF and scanned-image extraction, registry support/contradiction, comparison, source preview, two-visitor isolation, selective attestation hashes/QR, owner-only revocation, and reset. Real TinyFish Search returned eight results and Fetch returned one page. Browser and Agent were not run as part of this verification because they can consume wallet credits. See [Hosted demo](HOSTED_DEMO.md) for the new deployment model; earlier local-only evidence in the table is historical.

Production operations still require database migrations, backups, private durable storage, real user/account management if needed, durable job execution, retention policy, deployment validation and browser/device QA. The project uses server-rendered page images for document viewing rather than PDF.js, and native styled controls rather than replacing the existing frontend with a component framework. No blockchain transaction or legal certification is claimed.
