"""Evaluate retrieved observations without treating retrieval itself as proof."""
from __future__ import annotations
import json
from urllib.parse import urlparse
from .core import extract_claims, normalize_field, normalize_unicode, decide_evidence, sha256_bytes
from .store import all_rows, get, insert, connect, uid, now

def evaluate_observation(claim:dict,url:str,text:str)->dict:
    fields={item['field']:item['original_value'] for item in extract_claims(text)}
    try:
        structured=json.loads(text)
        if isinstance(structured,dict):
            for field in ('record_id','owner_name','area','issue_date','expiry_date','jurisdiction','issuer','survey_number'):
                if structured.get(field) is not None:fields[field]=str(structured[field])
    except (ValueError,TypeError):pass
    source=next((row for row in all_rows('source_registry') if row['hostname']==urlparse(url).hostname),None)
    approved=bool(source and source['authority']=='issuer' and claim['field'] in json.loads(source['claim_types']))
    siblings=all_rows('claims','WHERE document_id=?',(claim['document_id'],))
    scope_fields={item['field']:item['normalized_value'] for item in siblings}
    record=scope_fields.get('record_id')
    scope=bool(record and fields.get('record_id') and normalize_field('record_id',fields['record_id'])==record)
    if scope_fields.get('jurisdiction'):
        scope=scope and normalize_unicode(fields.get('jurisdiction','')).casefold()==normalize_unicode(scope_fields['jurisdiction']).casefold()
    observed=fields.get(claim['field'])
    normalized=normalize_field(claim['field'],observed) if observed else None
    match=None if normalized is None else normalized.casefold()==(claim['normalized_value'] or '').casefold()
    span=bool(observed and normalize_unicode(observed).casefold() in normalize_unicode(text).casefold())
    return {**decide_evidence(approved=approved,span=span,value=match,scope=scope),'observed_value':observed,'normalized_observed':normalized}

def save_observation(claim:dict,url:str,text:str,method:str,investigation_id:str)->dict:
    result=evaluate_observation(claim,url,text)
    eid=uid()
    insert('evidence',{'id':eid,'claim_id':claim['id'],'investigation_id':investigation_id,'url':url,'method':method,'excerpt':text[:2400],'content_sha256':sha256_bytes(text.encode()),'checks':json.dumps(result['checks']),'created_at':now()})
    result=save_decision(claim['id'],result)
    return {**result,'evidence_id':eid}

def save_decision(claim_id:str,result:dict):
    checks=result['checks']
    prior=all_rows('evidence','WHERE claim_id=?',(claim_id,))
    values={c['value'] for item in prior if (c:=json.loads(item['checks'])).get('source') and c.get('span') and c.get('scope') and c.get('value') is not None and not c.get('review_rejected')}
    if len(values)>1:result={**result,'status':'conflicting','reason_code':None}
    elif values:result={**result,'status':'supported' if True in values else 'contradicted','reason_code':None}
    with connect() as conn:conn.execute('UPDATE claims SET status=? WHERE id=?',(result['status'],claim_id))
    insert('verification_decisions',{'id':uid(),'claim_id':claim_id,'status':result['status'],'reason_code':result.get('reason_code'),'checks':json.dumps(checks),'created_at':now()})
    insert('audit_events',{'id':uid(),'event':'evidence.evaluated','subject_id':claim_id,'detail':json.dumps(result),'created_at':now()})
    return result
