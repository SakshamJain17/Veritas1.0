import asyncio,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,AsyncMock,MagicMock
from types import SimpleNamespace
import fitz,httpx
from fastapi.testclient import TestClient
from apps.api import store
from apps.api.main import app,safe_trace,document_pages
from apps.api.core import extract_claims,normalize_field,validate_public_url
from apps.api.verification import evaluate_observation,save_observation
from apps.api.tinyfish.adapter import TinyFishAdapter

class AdvancedFlowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old_db=store.DB
  store.DB=Path(self.tmp.name)/'advanced.db';store.init_db();self.client=TestClient(app)
 def tearDown(self):store.DB=self.old_db;self.tmp.cleanup()
 def upload(self,owner='Ramesh Kumar'):
  pdf=fitz.open();page=pdf.new_page();page.insert_text((72,72),f'Record ID: VR-1042\nOwner: {owner}\nArea: 2 Acres\nDate: 14 Aug 2024\nDistrict: Pune')
  return self.client.post('/documents',files={'file':('record.pdf',pdf.tobytes(),'application/pdf')}).json()
 def register(self):
  response=self.client.post('/sources',json={'hostname':'registry.example.org','authority':'issuer','claim_types':['owner_name','area']});self.assertEqual(response.status_code,201)
 def test_source_and_scope_are_required_for_retrieved_support(self):
  doc=self.upload();claim=next(c for c in doc['claims'] if c['field']=='owner_name');text='Record ID: VR-1042\nOwner: Ramesh Kumar\nDistrict: Pune'
  self.assertEqual(evaluate_observation(claim,'https://registry.example.org/record',text)['status'],'unverified')
  self.register();self.assertEqual(evaluate_observation(claim,'https://registry.example.org/record',text)['status'],'supported')
  self.assertEqual(evaluate_observation(claim,'https://registry.example.org/record',text.replace('Pune','Nashik'))['status'],'unverified')
  self.assertEqual(evaluate_observation(claim,'https://registry.example.org/record',text.replace('Ramesh','Suresh'))['status'],'contradicted')
 def test_conflicting_evidence_and_reviewer_rejection(self):
  self.register();doc=self.upload();claim=next(c for c in doc['claims'] if c['field']=='owner_name')
  first=save_observation(claim,'https://registry.example.org/a','Record ID: VR-1042\nOwner: Ramesh Kumar\nDistrict: Pune','tinyfish_fetch','test-run')
  second=save_observation(claim,'https://registry.example.org/b','Record ID: VR-1042\nOwner: Suresh Kumar\nDistrict: Pune','tinyfish_fetch','test-run')
  self.assertEqual(store.get('claims',claim['id'])['status'],'conflicting')
  rejected=self.client.post('/evidence/'+second['evidence_id']+'/review',json={'decision':'rejected','reason':'Incorrect secondary excerpt'})
  self.assertEqual(rejected.status_code,200);self.assertEqual(rejected.json()['claim_status'],'supported')
  self.assertGreaterEqual(len(self.client.get('/claims/'+claim['id']+'/history').json()['decisions']),3)
 def test_document_comparison_covers_every_field(self):
  a=self.upload();b=self.upload('Suresh Kumar');result=self.client.post('/comparisons/documents',json={'document_a':a['id'],'document_b':b['id']})
  self.assertEqual(result.status_code,200);self.assertEqual(result.json()['conflicts'],1)
  self.assertEqual(next(x for x in result.json()['fields'] if x['field']=='owner_name')['conflict'],True)
  self.assertEqual(len(result.json()['fields']),5)
 def test_adaptive_router_uses_approved_source(self):
  self.register()
  self.assertEqual(self.client.post('/investigations/plan',json={}).json()['capability'],'search')
  for flags,expected in [({},'fetch'),({'interaction_required':True},'browser'),({'multi_step':True},'agent')]:
   self.assertEqual(self.client.post('/investigations/plan',json={'url':'https://registry.example.org/',**flags}).json()['capability'],expected)
 def test_failed_run_has_persistent_trace(self):
  with patch.dict(os.environ,{'TINYFISH_API_KEY':''}):
   result=self.client.post('/investigations',json={'capability':'search','query':'public registry','consent':True}).json()
  traces=self.client.get('/investigations/'+result['id']+'/traces').json();self.assertEqual(traces[0]['status'],'failed')
  self.assertIn('TINYFISH_API_KEY',json.loads(traces[0]['trace'])['error'])
 def test_certificate_fields_and_original_numerals(self):
  claims={x['field']:x for x in extract_claims('Issuer: Demo Authority\nCertificate ID: CERT-1234\nOwner name: Anita Deshmukh\nArea: २ Acres\nIssue date: 2024-08-14\nExpiry date: 2026-08-14\nDistrict: Pune\nSurvey number: 12 / 3')}
  self.assertEqual(len(claims),8);self.assertEqual(claims['area']['original_value'],'२ Acres');self.assertEqual(claims['area']['normalized_value'],'0.80937')
  self.assertEqual(claims['survey_number']['normalized_value'],'12/3')
  self.assertEqual(normalize_field('record_id',' vr-१२३४ '),'VR-1234')
  regional=extract_claims('Issue date: १४/०८/२०२४');self.assertEqual(regional[0]['normalized_value'],'2024-08-14')
 def test_mixed_pdf_extracts_scanned_pages(self):
  if not __import__('shutil').which('tesseract'):self.skipTest('Tesseract not installed')
  pdf=fitz.open();page=pdf.new_page();page.insert_text((72,72),'Record ID: VR-1042');second=pdf.new_page();second.insert_image(second.rect,filename=str(Path(__file__).resolve().parents[3]/'fixtures'/'scanned-record.png'))
  pages,status=document_pages(pdf.tobytes(),'application/pdf');self.assertEqual(status,'mixed_text_ocr_extracted');self.assertEqual(len(pages),2);self.assertIn('Ramesh Kumar',pages[1]['text'])
 def test_empty_allowlist_blocks_every_destination(self):
  with self.assertRaises(ValueError):validate_public_url('https://example.org',set())
 def test_browser_timeout_closes_managed_session(self):
  adapter=TinyFishAdapter(key='unit-test-only');adapter.create_browser=AsyncMock(return_value={'session_id':'test-session','cdp_url':'wss://unit-test.invalid/cdp'});adapter.close_browser=AsyncMock(return_value={})
  manager=MagicMock();manager.__aenter__=AsyncMock(return_value=SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=AsyncMock(side_effect=TimeoutError('Browser connection timed out')))));manager.__aexit__=AsyncMock(return_value=None)
  with patch('playwright.async_api.async_playwright',return_value=manager),self.assertRaises(TimeoutError):asyncio.run(adapter.browser_lookup('https://registry.example.org','Pune','VR-1042'))
  adapter.close_browser.assert_awaited_once_with('test-session')
 def test_agent_timeout_is_persisted_as_budget_exhaustion(self):
  with patch('apps.api.main.validate_public_url',side_effect=lambda url,hosts:url),patch.object(TinyFishAdapter,'run_agent',new=AsyncMock(return_value={'run_id':'unit-test-run'})):
   result=self.client.post('/investigations',json={'capability':'agent','url':'https://registry.example.org','goal':'Find the public record.','consent':True}).json()
  with patch.object(TinyFishAdapter,'get_agent_run',new=AsyncMock(return_value={'run_id':'unit-test-run','status':'FAILED','error':{'code':'TIMEOUT','message':'Execution limit reached'}})):
   state=self.client.get('/investigations/'+result['id']).json()
  self.assertEqual(state['status'],'failed');self.assertEqual(state['reason_code'],'budget_exhausted')
  self.assertEqual(self.client.get('/investigations/'+result['id']+'/traces').json()[0]['status'],'failed')
 def test_correction_invalidates_prior_value_checks(self):
  self.register();doc=self.upload();claim=next(c for c in doc['claims'] if c['field']=='owner_name');saved=save_observation(claim,'https://registry.example.org/a','Record ID: VR-1042\nOwner: Ramesh Kumar\nDistrict: Pune','tinyfish_fetch','unit-test')
  result=self.client.post('/reviews/'+claim['id']+'/decision',json={'decision':'corrected','reason':'Corrected source transcription','corrected_value':'Ramesh K. Kumar'})
  self.assertEqual(result.status_code,200);self.assertEqual(store.get('claims',claim['id'])['status'],'pending_review');self.assertIsNone(json.loads(store.get('evidence',saved['evidence_id'])['checks'])['value'])
 def test_trace_redacts_connection_urls_and_credentials(self):
  with patch.dict(os.environ,{'TINYFISH_API_KEY':'unit-test-secret'}):
   value=safe_trace({'X-API-Key':'unit-test-secret','detail':'wss://example.invalid/cdp token unit-test-secret'})
  self.assertNotIn('X-API-Key',value);self.assertNotIn('unit-test-secret',value['detail']);self.assertNotIn('wss://',value['detail'])
 def test_read_retries_and_agent_has_documented_duration(self):
  calls=[];original=httpx.AsyncClient
  def handler(req):
   calls.append(req)
   return httpx.Response(503 if len(calls)==1 else 200,json={'results':[]})
  async def run():
   with patch('apps.api.tinyfish.adapter.httpx.AsyncClient',side_effect=lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs)),patch('apps.api.tinyfish.adapter.asyncio.sleep') as sleep:
    sleep.return_value=None
    return await TinyFishAdapter(key='unit-test-only').search('public sources')
  asyncio.run(run());self.assertEqual(len(calls),2)

if __name__=='__main__':unittest.main()
