# Three-minute local demo

1. Start at `/` and scroll through the document demonstration. Open `/app`, choose the matching-record sample (or upload `fixtures/matching-record.pdf`), and select the area claim. Its original `2 Acres`, normalized `0.80937` hectares, and highlighted source region appear together.
2. Click “Check synthetic registry.” The API retrieves fictional record `VR-1042` over HTTP, records its digest and excerpt, and marks the matching area supported.
3. Upload `fixtures/altered-owner.pdf`, select its owner claim, and check the registry. The stored result is contradicted. Explain that this does not decide legal ownership.
4. Upload `fixtures/unavailable-record.pdf` and check a claim. The absence of a public result yields unverified, not a fraud verdict.
5. Open Compare records and compare the matching and altered-owner documents. Show the same record, date and jurisdiction and the one differing field. Upload `fixtures/scanned-record.png` to demonstrate OCR. Create a selective attestation, choose whether to disclose evidence references, and open its QR verification page. It shows status and hash integrity without the document. The ledger provides QR download and reviewer revocation.
6. If a TinyFish key and a public issuer URL are configured, open Investigations and run Search, Fetch, Browser and Agent. Show their real statuses and errors. The local issuer at `localhost:3001` is inaccessible to TinyFish cloud sessions.
