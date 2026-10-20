"""Run real TinyFish smoke tests with the ignored local environment file."""
from pathlib import Path
import os,unittest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1]/'.env')
if not os.getenv('TINYFISH_API_KEY'):
 raise SystemExit('TINYFISH_API_KEY is not configured. No live TinyFish request was made.')

suite=unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parents[1]/'apps'/'api'/'tests'),pattern='test_tinyfish_live.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
