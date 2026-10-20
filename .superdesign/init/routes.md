# Routes
- `/`: apps/web/app/page.tsx, marketing landing, interactive document hero and editorial sections.
- `/app`: apps/web/app/app/page.tsx, private workspace, claim explorer, investigations, review, comparison.
- `/verify/[id]`: apps/web/app/verify/[id]/page.tsx, public selective attestation.
All use apps/web/app/layout.tsx.
Separate issuer app on port 3001 has /, /records/[id], /api/records/[id], /restricted.
