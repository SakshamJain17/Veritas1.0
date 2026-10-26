"""Optional real-database isolation checks. Never call TinyFish or private sources."""
import os,unittest
from pathlib import Path
from fastapi.testclient import TestClient

@unittest.skipUnless(os.getenv('VERITAS_PUBLIC_DEMO')=='true' and os.getenv('VERITAS_DATABASE_URL'),'restricted hosted database not configured for this test')
class HostedIsolationTests(unittest.TestCase):
 def test_private_workspaces_and_public_attestation(self):
  from apps.api.main import app
  a,b=TestClient(app,base_url='https://testserver'),TestClient(app,base_url='https://testserver')
  try:
   self.assertTrue(a.get('/auth/session').json()['demo'])
   self.assertTrue(b.get('/auth/session').json()['demo'])
   source=Path(__file__).resolve().parents[3]/'fixtures/matching-record.pdf'
   result=a.post('/documents',files={'file':('matching-record.pdf',source.read_bytes(),'application/pdf')})
   self.assertEqual(result.status_code,201,result.text)
   doc=result.json();did=doc['id'];claim=doc['claims'][0]
   self.assertEqual(len(a.get('/documents').json()),1)
   self.assertEqual(b.get('/documents').json(),[])
   for path in [f'/documents/{did}',f'/documents/{did}/file',f'/documents/{did}/pages/1']:
    self.assertEqual(b.get(path).status_code,404)
   self.assertEqual(a.get(f'/documents/{did}/pages/1').status_code,200)
   att=a.post('/attestations',json={'claim_id':claim['id'],'status':claim['status']}).json()['attestation_id']
   public=b.get('/verify/'+att).json()
   self.assertTrue(public['hash_valid']);self.assertNotIn('original_value',public)
   self.assertEqual(b.get('/attestations').json(),[])
   self.assertEqual(b.get('/verify/'+att+'/qr').status_code,200)
   self.assertEqual(b.post('/attestations/'+att+'/revoke').status_code,404)
   self.assertEqual(a.post('/attestations/'+att+'/revoke').status_code,200)
   self.assertTrue(b.get('/verify/'+att).json()['revoked'])
   self.assertEqual(a.delete('/workspace').status_code,200)
   self.assertEqual(a.get('/documents').json(),[])
   self.assertEqual(b.get('/verify/'+att).status_code,404)
  finally:a.close();b.close()
