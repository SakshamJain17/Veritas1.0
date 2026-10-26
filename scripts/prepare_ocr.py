"""Fetch pinned English OCR data for PyMuPDF's built-in Tesseract, not a daemon."""
from pathlib import Path
import urllib.request
target=Path(__file__).resolve().parents[1]/'apps/api/tessdata/eng.traineddata'
if not target.exists():
    target.parent.mkdir(parents=True,exist_ok=True)
    urllib.request.urlretrieve('https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/eng.traineddata',target)
print('English OCR language data is ready.')
