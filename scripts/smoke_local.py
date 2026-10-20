"""Exercise the running local stack using only fictional fixtures.

Creates two demo uploads and one selective attestation in the configured local database.
No external TinyFish request is made.
"""
from pathlib import Path
import argparse,json
import httpx

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--api',default='http://localhost:8002');args=parser.parse_args()
 root=Path(__file__).resolve().parents[1]
 with httpx.Client(base_url=args.api,timeout=90) as client:
  assert client.get('/health').json()['status']=='ok'
  documents=[]
  for filename in ['matching-record.pdf','altered-owner.pdf']:
   response=client.post('/documents',files={'file':(filename,(root/'fixtures'/filename).read_bytes(),'application/pdf')});response.raise_for_status();documents.append(response.json())
  doc=documents[0];area=next(c for c in doc['claims'] if c['field']=='area')
  checked=client.post(f"/claims/{area['id']}/registry-check");checked.raise_for_status();assert checked.json()['status']=='supported',checked.text
  page=client.get(f"/documents/{doc['id']}/pages/1");assert page.status_code==200 and page.headers['content-type']=='image/png'
  comparison=client.post('/comparisons/documents',json={'document_a':doc['id'],'document_b':documents[1]['id']});comparison.raise_for_status();assert comparison.json()['conflicts']==1,comparison.text
  attested=client.post('/attestations',json={'claim_id':area['id'],'status':'supported','evidence_refs':[]});attested.raise_for_status();aid=attested.json()['attestation_id']
  public=client.get(f'/verify/{aid}');public.raise_for_status();assert public.json()['hash_valid'];assert not {'path','text','original_value','normalized_value'}&set(public.json())
  qr=client.get(f'/verify/{aid}/qr');assert qr.status_code==200 and qr.headers['content-type']=='image/png'
  plan=client.post('/investigations/plan',json={'url':'https://docs.tinyfish.ai/'});plan.raise_for_status();assert plan.json()['capability']=='fetch'
  print(json.dumps({'upload':'passed','preview':'passed','registry_evidence':'supported','comparison_conflicts':comparison.json()['conflicts'],'selective_attestation':'passed','public_privacy':'passed','qr':'passed','routing':'passed','public_verification_path':f'/verify/{aid}'},indent=2))

if __name__=='__main__':main()
