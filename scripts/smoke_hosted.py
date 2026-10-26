"""Verify the real hosted demo using disposable synthetic workspaces.

Use --vercel for a protected staging deployment; otherwise requests are anonymous.
--tinyfish opts into one Search and one Fetch request (no paid Browser/Agent runs).
"""
import argparse,json,subprocess,tempfile
from pathlib import Path
import httpx

p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('--vercel',action='store_true');p.add_argument('--tinyfish',action='store_true');args=p.parse_args()
ROOT=Path(__file__).resolve().parents[1]
clients={name:httpx.Client(base_url=args.url,timeout=180,follow_redirects=False) for name in ['a','b']}

with tempfile.TemporaryDirectory(prefix='veritas-smoke-') as temporary:
 def request(path,method='GET',body=None,file=None,who='a',expected=200):
  if args.vercel:
   output=Path(temporary)/'response';cookies=Path(temporary)/('cookies-'+who)
   command=['npx','--yes','vercel@64.7.0','--scope','team_VCakRFqWhi6YWS9pvQlx7SeD','curl',path,'--deployment',args.url,'--','--silent','--show-error','--max-time','180','--request',method,'--cookie',str(cookies),'--cookie-jar',str(cookies),'--output',str(output),'--write-out','%{http_code}']
   if body is not None:command+=['--header','Content-Type: application/json','--data',json.dumps(body)]
   if file:command+=['--form',f'file=@{file}']
   result=subprocess.run(command,capture_output=True,text=True)
   if result.returncode or not result.stdout.strip().isdigit():raise RuntimeError('Vercel request could not complete: '+path)
   status=int(result.stdout.strip());data=output.read_bytes()
  else:
   response=clients[who].request(method,path,json=body,files={'file':(file.name,file.read_bytes(),'image/png' if file.suffix=='.png' else 'application/pdf')} if file else None)
   status=response.status_code;data=response.content
  if status!=expected:raise AssertionError(f'{method} {path}: HTTP {status}, expected {expected}; '+data[:180].decode(errors='replace'))
  try:return json.loads(data)
  except (ValueError,UnicodeDecodeError):return data

 print('Health:',request('/api/health')['status'],flush=True)
 assert request('/api/auth/session')['demo']
 assert request('/api/auth/session',who='b')['demo']
 registry=request('/registry/api/records/VR-1042');assert registry['owner_name']=='Ramesh Kumar'
 print('Anonymous sessions and public registry: PASS',flush=True)
 documents=[]
 for filename in ['matching-record.pdf','altered-owner.pdf','scanned-record.png']:
  document=request('/api/documents','POST',file=ROOT/'fixtures'/filename,expected=201)
  assert document['claims'];documents.append(document)
  print('Extraction:',filename,document['ocr_status'],len(document['claims']),'claims',flush=True)
 good,altered,scan=documents
 owner=next(c for c in good['claims'] if c['field']=='owner_name')
 changed=next(c for c in altered['claims'] if c['field']=='owner_name')
 proof=request('/api/claims/'+owner['id']+'/registry-check','POST');assert proof['status']=='supported'
 assert request('/api/claims/'+changed['id']+'/registry-check','POST')['status']=='contradicted'
 comparison=request('/api/comparisons/documents','POST',{'document_a':good['id'],'document_b':altered['id']});assert comparison['conflicts']>=1
 assert request('/api/documents/'+scan['id']+'/pages/1').startswith(b'\x89PNG')
 print('Evidence, contradictions, comparison and source preview: PASS',flush=True)
 att=request('/api/attestations','POST',{'claim_id':owner['id'],'status':'supported','evidence_refs':[proof['evidence_id']]},expected=201)['attestation_id']
 assert request('/api/verify/'+att,who='b')['hash_valid']
 assert request('/api/verify/'+att+'/qr',who='b').startswith(b'\x89PNG')
 assert request('/api/documents',who='b')==[]
 request('/api/documents/'+good['id']+'/file',who='b',expected=404)
 request('/api/attestations/'+att+'/revoke','POST',who='b',expected=404)
 request('/api/attestations/'+att+'/revoke','POST')
 assert request('/api/verify/'+att,who='b')['revoked']
 print('Guest isolation, selective verification, QR and revocation: PASS',flush=True)
 if args.tinyfish:
  assert request('/api/tinyfish/health')['configured']
  for task in [{'capability':'search','query':'TinyFish official documentation','consent':True},{'capability':'fetch','urls':['https://www.tinyfish.ai/'],'consent':True}]:
   run=request('/api/investigations','POST',task,expected=202)
   if run['status']!='completed':raise AssertionError(task['capability']+' failed: '+str(run.get('error')))
   result=json.loads(run['result']);assert result.get('results')
   print('Live TinyFish',task['capability']+': PASS ('+str(len(result['results']))+' results)',flush=True)
 request('/api/workspace','DELETE');request('/api/workspace','DELETE',who='b')
 print('Synthetic test workspaces cleared. All hosted checks passed.',flush=True)

for client in clients.values():client.close()
