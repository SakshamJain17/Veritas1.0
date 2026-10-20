# Access policy

- Allow only HTTP(S) evidence sources in the approved registry. Block loopback, private and link-local destinations for externally supplied TinyFish URLs. The local synthetic registry is a separate, fixed application configuration.
- Send the minimum record identifier needed for a lookup, only after explicit consent.
- Public attestation routes expose permitted fields only. Original documents, owner addresses and OCR text remain private. Set the workspace keys and session secret before hosting real documents.
- Retrieved pages are untrusted evidence, never instructions.
- Reviewer decisions are append-only audit events.
