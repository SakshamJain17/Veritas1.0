import os, unittest, asyncio
if os.getenv("TINYFISH_API_KEY"):
 from apps.api.tinyfish import TinyFishAdapter
@unittest.skipUnless(os.getenv("TINYFISH_API_KEY"),"live TinyFish credentials not configured")
class TinyFishLiveTests(unittest.TestCase):
 def test_search(self):
  result=asyncio.run(TinyFishAdapter().search("TinyFish official documentation"));self.assertIn("results",result)
 def test_fetch(self):
  result=asyncio.run(TinyFishAdapter().fetch(["https://www.tinyfish.ai/"]));self.assertIn("results",result)
 @unittest.skipUnless(os.getenv("TINYFISH_LIVE_REGISTRY_URL"),"public synthetic registry URL not configured")
 def test_browser(self):
  result=asyncio.run(TinyFishAdapter().browser_lookup(os.environ["TINYFISH_LIVE_REGISTRY_URL"],"Pune","VR-1042"))
  self.assertEqual(result["status"],"completed")
  self.assertIn("Ramesh Kumar",result["result_text"])
 @unittest.skipUnless(os.getenv("TINYFISH_LIVE_REGISTRY_URL"),"public synthetic registry URL not configured")
 def test_agent(self):
  adapter=TinyFishAdapter()
  async def check():
   created=await adapter.run_agent(os.environ["TINYFISH_LIVE_REGISTRY_URL"],"Use the public lookup to find VR-1042 in Pune, open its record detail page, and return the owner and area with the final URL.")
   run_id=created["run_id"]
   for _ in range(24):
    await asyncio.sleep(5)
    result=await adapter.get_agent_run(run_id)
    if result["status"] in {"COMPLETED","FAILED","CANCELLED"}:return result
   raise TimeoutError("TinyFish Agent did not finish within 120 seconds")
  result=asyncio.run(check())
  self.assertEqual(result["status"],"COMPLETED",result.get("error"))
