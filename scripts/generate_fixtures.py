"""Generate fictional PDFs for the local VERITAS demonstration."""
from pathlib import Path
import fitz

ROOT=Path(__file__).resolve().parents[1]/"fixtures"
ROOT.mkdir(exist_ok=True)
RECORDS={
    "matching-record.pdf":("VR-1042","Ramesh Kumar","2 Acres"),
    "altered-owner.pdf":("VR-1042","Suresh Kumar","2 Acres"),
    "altered-area.pdf":("VR-1042","Ramesh Kumar","3 Acres"),
    "unavailable-record.pdf":("VR-1045","Unknown Person","2 Acres"),
}
for filename,(record,owner,area) in RECORDS.items():
    pdf=fitz.open();page=pdf.new_page(width=595,height=842)
    page.insert_text((65,65),"VERITAS DEMO REGISTRY",fontsize=15,fontname="helv")
    page.insert_text((65,100),"SYNTHETIC DATA - NOT A GOVERNMENT DOCUMENT",fontsize=9,color=(.5,.15,.2))
    page.draw_line((65,116),(530,116),color=(.5,.15,.2))
    for index,line in enumerate((f"Record ID: {record}",f"Owner: {owner}",f"Area: {area}","Date: 14 Aug 2024","District: Pune")):
        page.insert_text((65,160+index*38),line,fontsize=12)
    page.insert_text((65,760),"For software demonstration only. No legal standing.",fontsize=9)
    pdf.save(ROOT/filename)
    if filename=="matching-record.pdf":
        (ROOT/"scanned-record.png").write_bytes(page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes("png"))
    pdf.close()
print(f"Generated {len(RECORDS)} synthetic PDF fixtures in {ROOT}")
