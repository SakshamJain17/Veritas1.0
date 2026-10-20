import io, os, tempfile, unittest
from unittest.mock import patch
import fitz
from pathlib import Path
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api import store

class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        store.DB=__import__('pathlib').Path(self.tmp.name)/'test.db'
        store.UPLOADS=__import__('pathlib').Path(self.tmp.name)/'uploads'
        store.init_db();store.UPLOADS.mkdir()
        self.client=TestClient(app)
    def tearDown(self):self.tmp.cleanup()
    def upload(self,owner='Ramesh Kumar'):
        pdf=fitz.open();page=pdf.new_page();page.insert_text((72,72),f'Record ID: VR-1042\nOwner: {owner}\nArea: 2 Acres\nDate: 14 Aug 2024')
        return self.client.post('/documents',files={'file':('record.pdf',pdf.tobytes(),'application/pdf')})
    def test_upload_and_selective_attestation(self):
        response=self.upload();self.assertEqual(response.status_code,201)
        data=response.json();self.assertEqual(len(data['claims']),4)
        page=self.client.get('/documents/'+data['id']+'/pages/1')
        self.assertEqual(page.status_code,200)
        self.assertEqual(page.headers['content-type'],'image/png')
        self.assertTrue(any(x['bbox']!='null' for x in data['claims']))
        self.assertEqual(self.client.get('/documents').status_code,200)
        claim=data['claims'][0]
        a=self.client.post('/attestations',json={'claim_id':claim['id'],'status':'pending_review'})
        self.assertEqual(a.status_code,201)
        aid=a.json()['attestation_id'];verified=self.client.get('/verify/'+aid).json()
        self.assertTrue(verified['hash_valid']);self.assertNotIn('text',verified)
        qr=self.client.get('/verify/'+aid+'/qr');self.assertEqual(qr.status_code,200);self.assertEqual(qr.headers['content-type'],'image/png')
        self.assertEqual(self.client.post('/attestations',json={'claim_id':claim['id'],'status':'supported'}).status_code,409)
    def test_registry_support_and_conflict(self):
        import httpx
        def lookup(url,**kwargs):return httpx.Response(200,json={'record_id':'VR-1042','owner_name':'Ramesh Kumar','area':'2 acres','issue_date':'2024-08-14','jurisdiction':'Pune'},request=httpx.Request('GET',url))
        with patch('httpx.get',side_effect=lookup):
            good=self.upload().json();owner=next(x for x in good['claims'] if x['field']=='owner_name')
            self.assertEqual(self.client.post('/claims/'+owner['id']+'/registry-check').json()['status'],'supported')
            bad=self.upload('Suresh Kumar').json();owner2=next(x for x in bad['claims'] if x['field']=='owner_name')
            self.assertEqual(self.client.post('/claims/'+owner2['id']+'/registry-check').json()['status'],'contradicted')
    def test_scanned_image_ocr(self):
        if not __import__('shutil').which('tesseract'):self.skipTest('Tesseract not installed')
        image=(Path(__file__).resolve().parents[3]/'fixtures'/'scanned-record.png').read_bytes()
        result=self.client.post('/documents',files={'file':('scan.png',image,'image/png')})
        self.assertEqual(result.status_code,201)
        values={x['field']:x['original_value'] for x in result.json()['claims']}
        self.assertEqual(values['owner_name'],'Ramesh Kumar')
        self.assertEqual(values['record_id'],'VR-1042')
        self.assertTrue(any(x['bbox']!='null' for x in result.json()['claims']))
    def test_missing_credentials_recorded(self):
        with patch.dict(os.environ,{'TINYFISH_API_KEY':''}):
            response=self.client.post('/investigations',json={'capability':'search','query':'public registry','consent':True})
            self.assertEqual(response.status_code,202)
            result=self.client.get('/investigations/'+response.json()['id']).json()
            self.assertEqual(result['status'],'failed')
            self.assertIn('TINYFISH_API_KEY',result['error'])
    def test_private_session_and_reviewer_role(self):
        settings={'VERITAS_ACCESS_KEY':'local-user-key','VERITAS_REVIEWER_KEY':'local-reviewer-key','VERITAS_SESSION_SECRET':'test-secret-only'}
        with patch.dict(os.environ,settings):
            guest=TestClient(app)
            self.assertEqual(guest.get('/documents').status_code,401)
            cors=guest.get('/documents',headers={'Origin':'http://localhost:3000'})
            self.assertEqual(cors.headers.get('access-control-allow-origin'),'http://localhost:3000')
            self.assertEqual(guest.get('/verify/not-found').status_code,404)
            self.assertEqual(guest.post('/auth/session',json={'passphrase':'wrong'}).status_code,401)
            self.assertEqual(guest.post('/auth/session',json={'passphrase':'local-user-key'}).status_code,200)
            self.assertEqual(guest.get('/documents').status_code,200)
            self.assertEqual(guest.get('/reviews').status_code,403)
            self.assertEqual(guest.post('/sources',json={'hostname':'registry.example.org','authority':'issuer','claim_types':['owner_name']}).status_code,403)
            reviewer=TestClient(app)
            self.assertEqual(reviewer.post('/auth/session',json={'passphrase':'local-reviewer-key'}).status_code,200)
            self.assertEqual(reviewer.get('/reviews').status_code,200)
            added=reviewer.post('/sources',json={'hostname':'registry.example.org','authority':'issuer','claim_types':['owner_name']})
            self.assertEqual(added.status_code,201)
            self.assertIn('registry.example.org',[item['hostname'] for item in reviewer.get('/sources').json()])
            self.assertEqual(reviewer.post('/sources',json={'hostname':'registry.example.org','authority':'issuer'}).status_code,409)
            self.assertEqual(reviewer.post('/sources',json={'hostname':'127.0.0.1','authority':'issuer'}).status_code,422)
    def test_review_updates_extraction_state_without_claiming_support(self):
        data=self.upload().json();claim=data['claims'][0]
        response=self.client.post('/reviews/'+claim['id']+'/decision',json={'decision':'approved','reason':'Text and source region inspected'})
        self.assertEqual(response.status_code,200)
        after=self.client.get('/documents/'+data['id']+'/claims').json()
        self.assertEqual(next(x for x in after if x['id']==claim['id'])['status'],'unverified')
        self.assertNotIn(claim['id'],[x['id'] for x in self.client.get('/reviews').json()])

if __name__=='__main__':unittest.main()
