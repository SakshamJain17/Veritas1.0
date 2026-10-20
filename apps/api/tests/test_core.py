import unittest
from apps.api.core import canonical_hash,compare_claims,decide_evidence,extract_claims,normalize_area,normalize_date,normalize_unicode,sha256_bytes
class CoreTests(unittest.TestCase):
 def test_devanagari(self):self.assertEqual(normalize_unicode(" १२३  "),"123")
 def test_area(self):self.assertEqual(normalize_area("2 Acres")["normalized"],"0.80937")
 def test_square_metres(self):self.assertEqual(normalize_area("10000 square metres")["normalized"],"1.00000")
 def test_ambiguous_and_malformed_area_require_review(self):
  self.assertIsNone(normalize_area('1..2 Acres')['normalized'])
  self.assertIsNone(normalize_area('2 bigha')['normalized'])
 def test_date(self):self.assertEqual(normalize_date("14 Aug 2024"),"2024-08-14")
 def test_hash(self):self.assertEqual(sha256_bytes(b"a"),"ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb")
 def test_canonical(self):self.assertEqual(canonical_hash({"b":2,"a":1}),canonical_hash({"a":1,"b":2}))
 def test_claim_extraction(self):self.assertEqual(len(extract_claims("Record ID: VR-1042\nOwner: Ramesh Kumar\nArea: 2 Acres\nDate: 14 Aug 2024")),4)
 def test_supported(self):self.assertEqual(decide_evidence(approved=True,span=True,value=True,scope=True)["status"],"supported")
 def test_contradicted(self):self.assertEqual(decide_evidence(approved=True,span=True,value=False,scope=True)["status"],"contradicted")
 def test_missing(self):self.assertEqual(decide_evidence(approved=True,span=False,value=None,scope=True)["status"],"unverified")
 def test_comparison(self):
  a={"record_id":"VR-1042","jurisdiction":"Pune","field":"owner","period":"2024","normalized_value":"Ramesh Kumar"};b={**a,"normalized_value":"Suresh Kumar"};self.assertTrue(compare_claims(a,b)["conflict"])
  self.assertFalse(compare_claims({**a,"jurisdiction":"unconfirmed"},{**b,"jurisdiction":"unconfirmed"})["comparable"])
if __name__=="__main__":unittest.main()
