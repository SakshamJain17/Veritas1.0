from __future__ import annotations
import hashlib, json, os, re, socket, unicodedata
from datetime import datetime
from decimal import Decimal,InvalidOperation
from ipaddress import ip_address
from urllib.parse import urlparse

DEVANAGARI = str.maketrans("०१२३४५६७८९", "0123456789")

def normalize_unicode(value: str) -> str:
    text=unicodedata.normalize("NFKC",value)
    text="".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    return " ".join(text.split())

def normalize_field(field:str,value:str)->str|None:
    if field=="area":return normalize_area(value)["normalized"]
    if field in {"issue_date","expiry_date"}:return normalize_date(value)
    if field in {"record_id","survey_number"}:return re.sub(r"\s*([/-])\s*",r"\1",normalize_unicode(value)).upper()
    return normalize_unicode(value)

def normalize_area(value: str, jurisdiction: str | None = None) -> dict:
    text = normalize_unicode(value).lower().replace(",", "")
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(acres?|hectares?|ha|square metres?|sq\.?\s*m)", text)
    if not match: return {"original": value, "normalized": None, "unit": None, "reason": "unrecognized_area"}
    amount, unit = Decimal(match.group(1)), match.group(2)
    if unit.startswith("acre"): hectares = amount * Decimal("0.40468564224")
    elif unit in ("ha", "hectare", "hectares"): hectares = amount
    else: hectares = amount / Decimal("10000")
    try:normalized=f"{hectares.quantize(Decimal('0.00001'))}"
    except InvalidOperation:return {"original":value,"normalized":None,"unit":None,"reason":"unrecognized_area"}
    return {"original": value, "normalized": normalized, "unit": "hectares"}

def normalize_date(value: str) -> str | None:
    text = normalize_unicode(value)
    for fmt in ("%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(text, fmt).date().isoformat()
        except ValueError: pass
    return None

def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def canonical_hash(payload: dict) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())

def validate_public_url(url: str, approved_hosts: set[str] | None = None) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname: raise ValueError("Only public HTTP(S) URLs are allowed")
    if approved_hosts is not None and parsed.hostname not in approved_hosts: raise ValueError("Destination is not in the approved source registry")
    if parsed.username or parsed.password: raise ValueError("Credentials in source URLs are not allowed")
    try:
        for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443):
            addr = ip_address(info[4][0])
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast or addr.is_unspecified: raise ValueError("Private network destinations are blocked")
    except socket.gaierror as exc: raise ValueError("Destination host could not be resolved") from exc
    return url

def extract_claims(text: str) -> list[dict]:
    date=r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})"
    patterns = [("record_id", r"(?:Record|Certificate)(?: ID| number| no\.?)\s*[:#-]?\s*([A-Z\d][A-Z\d/-]{2,40})"),("owner_name", r"(?:Owner(?: name)?|Person(?: name)?|Name)\s*[:#-]?\s*([^\n\r:]{3,80})"),("area", r"(?:Area|Property area)\s*[:#-]?\s*([\d.,]+\s*(?:acres?|hectares?|ha|square metres?|sq\.?\s*m))"),("issue_date",r"(?<!Expiry )(?<!expiry )(?<!Registration )(?<!registration )(?:Registration date|Issue date|Issued?|Date)\s*[:#-]?\s*"+date),("jurisdiction",r"(?:District|Jurisdiction)\s*[:#-]?\s*([^\n\r:]{2,80})"),("issuer",r"(?:Issuer|Issuing authority)\s*[:#-]?\s*([^\n\r:]{3,100})"),("survey_number",r"(?:Survey|Khasra|Property)(?: number| no\.?| ID)\s*[:#-]?\s*([A-Z\d][A-Z\d /-]{1,40})"),("expiry_date",r"(?:Expiry date|Expires|Valid until)\s*[:#-]?\s*"+date)]
    claims=[]
    for field, pattern in patterns:
        m=re.search(pattern,text,re.I)
        if m:
            value=m.group(1).strip(); normalized=normalize_field(field,value)
            claims.append({"field":field,"original_value":value,"normalized_value":normalized,"confidence":0.92,"page":1,"bbox":None})
    return claims

def decide_evidence(*, approved: bool, span: bool, value: bool | None, scope: bool, conflicting: bool=False) -> dict:
    checks={"source":approved,"span":span,"value":value,"scope":scope}
    if conflicting:return {"status":"conflicting","checks":checks,"reason_code":None}
    if not approved or not span or value is None or not scope:return {"status":"unverified","checks":checks,"reason_code":"insufficient_eligible_evidence"}
    return {"status":"supported" if value else "contradicted","checks":checks,"reason_code":None}

def compare_claims(a: dict,b: dict) -> dict:
    comparable=all(a.get(k) and b.get(k) and a.get(k)!="unconfirmed" and a.get(k)==b.get(k) for k in ("record_id","jurisdiction","field","period"))
    conflict=comparable and a.get("normalized_value")!=b.get("normalized_value")
    return {"comparable":comparable,"conflict":conflict,"explanation":"Compared because record, jurisdiction, field and applicable period match." if comparable else "Claims are outside a comparable scope.","notice":"Conflict found. Legal ownership not determined." if conflict else None}
