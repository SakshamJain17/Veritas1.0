from __future__ import annotations
import json, mimetypes, os, io, subprocess, shutil, hmac, hashlib, base64, time, re, ipaddress, asyncio
from pathlib import Path
from typing import Optional, List
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .core import canonical_hash, compare_claims, decide_evidence, extract_claims, sha256_bytes, normalize_unicode, normalize_field, validate_public_url
from .store import UPLOADS, all_rows, get, init_db, insert, now, uid, connect, public_demo, document_bytes, charge_budget, workspace_id, clear_workspace
from .tinyfish import TinyFishAdapter
from .verification import save_observation, save_decision

app=FastAPI(title="VERITAS API",version="1.0.0",description="Evidence-first claim verification. Not a legal authority.")
def session_role(request:Request)->str|None:
    token=request.cookies.get("veritas_session","")
    if not token or "." not in token:return None
    payload,signature=token.rsplit(".",1)
    secret=os.getenv("VERITAS_SESSION_SECRET","").encode()
    if not secret:return None
    expected=hmac.new(secret,payload.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature,expected):return None
    try:
        role,expiry=base64.urlsafe_b64decode(payload.encode()).decode().split(":")
        return role if float(expiry)>time.time() else None
    except (ValueError,UnicodeDecodeError):return None
@app.middleware("http")
async def private_access(request:Request,call_next):
    if public_demo():
        from .demo import anonymous_workspace
        return await anonymous_workspace(request,call_next)
    if not os.getenv("VERITAS_ACCESS_KEY") or request.method=="OPTIONS":return await call_next(request)
    path=request.url.path
    if path in {"/health","/tinyfish/health","/auth/session","/openapi.json","/docs","/redoc"} or path.startswith("/verify/"):return await call_next(request)
    role=session_role(request)
    if not role:return Response('{"detail":"Authentication required"}',status_code=401,media_type="application/json")
    if (path.startswith("/reviews") or path=="/audit" or (path.startswith('/evidence/') and path.endswith('/review')) or (path=="/sources" and request.method!="GET") or (path.startswith("/attestations/") and path.endswith("/revoke"))) and role!="reviewer":return Response('{"detail":"Reviewer access required"}',status_code=403,media_type="application/json")
    return await call_next(request)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("VERITAS_WEB_ORIGIN","http://localhost:3000").split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
class Login(BaseModel):passphrase:str
@app.post("/auth/session")
def login(req:Login,response:Response):
    access=os.getenv("VERITAS_ACCESS_KEY","");reviewer=os.getenv("VERITAS_REVIEWER_KEY","")
    if not access:raise HTTPException(503,"Authentication is not configured")
    role="reviewer" if reviewer and hmac.compare_digest(req.passphrase,reviewer) else "user" if hmac.compare_digest(req.passphrase,access) else None
    if not role:raise HTTPException(401,"Invalid access key")
    secret=os.getenv("VERITAS_SESSION_SECRET","")
    if not secret:raise HTTPException(503,"Session secret is not configured")
    payload=base64.urlsafe_b64encode(f"{role}:{time.time()+28800}".encode()).decode()
    signature=hmac.new(secret.encode(),payload.encode(),hashlib.sha256).hexdigest()
    response.set_cookie("veritas_session",f"{payload}.{signature}",httponly=True,secure=os.getenv("VERITAS_COOKIE_SECURE","false").lower()=="true",samesite="lax",max_age=28800)
    return {"role":role}
@app.get("/auth/session")
def current_session(request:Request):return {"configured":True,"role":"reviewer","demo":True,"upload_max_mb":3} if public_demo() else {"configured":bool(os.getenv("VERITAS_ACCESS_KEY")),"role":session_role(request)}
@app.delete('/auth/session')
def logout(response:Response):response.delete_cookie('veritas_session');return {'signed_out':True}
@app.on_event("startup")
def start():
    if not public_demo():init_db();UPLOADS.mkdir(parents=True,exist_ok=True)
@app.get('/')
def api_index():return {'service':'VERITAS API','docs':'/api/docs' if public_demo() else '/docs','workspace':'https://veritas1-0.vercel.app/app'}
@app.get("/health")
def health():return {"status":"ok","service":"veritas-api"}
@app.delete('/workspace')
def reset_workspace():
    if not public_demo():raise HTTPException(404,'This endpoint is available only in the isolated hosted demo.')
    clear_workspace()
    return {'cleared':True,'notice':'Only this browser workspace was cleared, including its public attestations.'}
@app.get("/tinyfish/health")
def tf_health():
    state="not_checked" if os.getenv("TINYFISH_API_KEY") else "missing_credentials"
    return {"configured":bool(os.getenv("TINYFISH_API_KEY")),"capabilities":{name:state for name in ("search","fetch","browser","agent")}}

def ocr_available():return bool(shutil.which('tesseract') or (Path(__file__).parent/'tessdata'/'eng.traineddata').exists())

def document_pages(data:bytes,mime:str)->tuple[list[dict],str]:
    if mime=="application/pdf":
        try:
            import fitz
            with fitz.open(stream=data,filetype="pdf") as doc:
                pages=[{"text":p.get_text(),"boxes":{}} for p in doc]
                if any(p["text"].strip() for p in pages):
                    mixed=False
                    for index,page in enumerate(doc):
                        if not pages[index]['text'].strip() and ocr_available():
                            scale=min(2,2000/max(page.rect.width,page.rect.height))
                            pages[index]=ocr_page(page.get_pixmap(matrix=fitz.Matrix(scale,scale)).tobytes('png'));mixed=True;continue
                        for word in page.get_text("words"):
                            token=word[4].strip(" :#.,")
                            if token:pages[index]["boxes"].setdefault(token.lower(),[]).append([round(word[0]/page.rect.width,4),round(word[1]/page.rect.height,4),round(word[2]/page.rect.width,4),round(word[3]/page.rect.height,4)])
                    return pages,"mixed_text_ocr_extracted" if mixed else "embedded_text_extracted"
                if ocr_available():
                    pages=[]
                    for page in doc:
                        scale=min(2,2000/max(page.rect.width,page.rect.height))
                        image=page.get_pixmap(matrix=fitz.Matrix(scale,scale)).tobytes("png")
                        pages.append(ocr_page(image))
                    return pages,"ocr_extracted"
        except Exception:return [],"extraction_failure"
    elif mime in {"image/png","image/jpeg"} and ocr_available():
        try:return [ocr_page(data)],"ocr_extracted"
        except Exception:return [],"extraction_failure"
    return [],"review_required"

def ocr_page(data:bytes)->dict:
    if not shutil.which('tesseract'):
        import fitz
        pix=fitz.Pixmap(data)
        if pix.alpha:pix=fitz.Pixmap(pix,0)
        if pix.n!=3:pix=fitz.Pixmap(fitz.csRGB,pix)
        with fitz.open(stream=pix.pdfocr_tobytes(language='eng',tessdata=str(Path(__file__).parent/'tessdata')),filetype='pdf') as pdf:
            page=pdf[0];boxes={}
            for x0,y0,x1,y1,word,*_ in page.get_text('words'):
                boxes.setdefault(word.strip(' :#.,').lower(),[]).append([x0/page.rect.width,y0/page.rect.height,x1/page.rect.width,y1/page.rect.height])
            return {'text':page.get_text(),'boxes':boxes}
    import csv
    from PIL import Image
    width,height=Image.open(io.BytesIO(data)).size
    output=subprocess.run(["tesseract","stdin","stdout","tsv"],input=data,capture_output=True,timeout=30,check=True).stdout.decode(errors="replace")
    rows=list(csv.DictReader(io.StringIO(output),delimiter="\t"));lines={};boxes={}
    for row in rows:
        token=row.get("text","").strip()
        if not token:continue
        line_key=(row.get("block_num"),row.get("par_num"),row.get("line_num"))
        lines.setdefault(line_key,[]).append(token)
        try:x,y,w,h=(int(row[k]) for k in ("left","top","width","height"))
        except (ValueError,KeyError):continue
        boxes.setdefault(token.strip(" :#.,").lower(),[]).append([round(x/width,4),round(y/height,4),round((x+w)/width,4),round((y+h)/height,4)])
    return {"text":"\n".join(" ".join(words) for words in lines.values()),"boxes":boxes}

@app.post("/documents",status_code=201)
async def upload(file:UploadFile=File(...)):
    allowed={"application/pdf","image/png","image/jpeg"}; mime=file.content_type or mimetypes.guess_type(file.filename or "")[0]
    if mime not in allowed:raise HTTPException(415,"Only PDF, PNG and JPG files are supported")
    limit=(3 if public_demo() else int(os.getenv("UPLOAD_MAX_MB","15")))*1024*1024
    data=await file.read(limit+1)
    if not data or len(data)>limit:raise HTTPException(413,"File is empty or exceeds the configured upload limit")
    signatures={"application/pdf":data.startswith(b"%PDF-"),"image/png":data.startswith(b"\x89PNG\r\n\x1a\n"),"image/jpeg":data.startswith(b"\xff\xd8\xff")}
    if not signatures[mime]:raise HTTPException(415,"File content does not match its declared type")
    if public_demo():
        if len(all_rows('documents'))>=8:raise HTTPException(429,'The free demo supports 8 documents per browser workspace. Delete a document to upload another.')
    if mime=='application/pdf':
        import fitz
        try:
            with fitz.open(stream=data,filetype='pdf') as pdf:
                if len(pdf)>25:raise HTTPException(422,'Please upload a document with at most 25 pages.')
                if pdf.needs_pass:raise HTTPException(422,'Please unlock the PDF before uploading it.')
        except HTTPException:raise
        except Exception:raise HTTPException(422,'This PDF could not be opened.')
    else:
        from PIL import Image
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.width*image.height>20000000:raise HTTPException(422,'Please use an image under 20 megapixels.')
        except HTTPException:raise
        except Exception:raise HTTPException(422,'This image could not be opened.')
    did=uid();extension={"application/pdf":".pdf","image/png":".png","image/jpeg":".jpg"}[mime];path=UPLOADS/f"{did}{extension}"
    if not public_demo():path.write_bytes(data)
    pages,ocr_status=document_pages(data,mime)
    if public_demo():
        if sum(len(page['text']) for page in pages)>1000000:raise HTTPException(422,'This document contains too much extracted text for the free demo.')
        try:charge_budget('upload-bytes-total',len(data),75*1024*1024)
        except ValueError as exc:raise HTTPException(429,str(exc))
    insert("documents",{"id":did,"name":file.filename,"mime":mime,"size":len(data),"sha256":sha256_bytes(data),"path":str(path),"text":"\n".join(p["text"] for p in pages),"created_at":now()})
    if public_demo():insert('document_objects',{'id':did,'data':data})
    for page_number,page in enumerate(pages,1):
        for c in extract_claims(page["text"]):
            words=c["original_value"].split();boxes=[box for word in words for box in page["boxes"].get(word.lower(),[])]
            bbox=[min(x[0] for x in boxes),min(x[1] for x in boxes),max(x[2] for x in boxes),max(x[3] for x in boxes)] if boxes else None
            if mime=="application/pdf" and ocr_status=="embedded_text_extracted":
                import fitz
                with fitz.open(stream=data,filetype="pdf") as source:
                    rects=source[page_number-1].search_for(c["original_value"])
                    if rects:
                        rect=rects[0];page_rect=source[page_number-1].rect
                        bbox=[round(rect.x0/page_rect.width,4),round(rect.y0/page_rect.height,4),round(rect.x1/page_rect.width,4),round(rect.y1/page_rect.height,4)]
            cid=uid();stamp=now()
            insert("claims",{"id":cid,"document_id":did,"field":c["field"],"original_value":c["original_value"],"normalized_value":c["normalized_value"],"confidence":c["confidence"] if bbox else 0.55,"page":page_number,"bbox":json.dumps(bbox),"status":"pending_review","created_at":stamp})
            insert('ocr_spans',{'id':uid(),'document_id':did,'page':page_number,'text':c['original_value'],'bbox':json.dumps(bbox),'confidence':c['confidence'] if bbox else .55,'created_at':stamp})
            insert('normalized_claim_values',{'id':uid(),'claim_id':cid,'value':c['normalized_value'],'unit':'hectares' if c['field']=='area' else None,'rule':'deterministic_v2','created_at':stamp})
    insert("audit_events",{"id":uid(),"event":"document.uploaded","subject_id":did,"detail":json.dumps({"sha256":sha256_bytes(data)}),"created_at":now()})
    result=get("documents",did);result.pop("path",None);result.pop("text",None)
    return {**result,"claims":all_rows("claims","WHERE document_id=?",(did,)),"ocr_status":ocr_status}
@app.get("/documents")
def documents():
    rows=all_rows("documents","ORDER BY created_at DESC")
    for row in rows:
        row.pop("path",None);row.pop("text",None)
        items=all_rows('claims','WHERE document_id=?',(row['id'],));row['claim_count']=len(items)
        row['status_counts']={status:sum(item['status']==status for item in items) for status in {item['status'] for item in items}}
    return rows
@app.get("/documents/{id}")
def document(id:str):
    result=get("documents",id)
    if not result:raise HTTPException(404,"Document not found")
    if result['mime']=='application/pdf':
        import fitz
        with fitz.open(stream=document_bytes(result),filetype='pdf') as pdf:result['page_count']=len(pdf)
    else:result['page_count']=1
    result.pop("path",None);result.pop("text",None);return result
@app.get("/documents/{id}/claims")
def claims(id:str):return all_rows("claims","WHERE document_id=?",(id,))
@app.get("/documents/{id}/file")
def document_file(id:str):
    doc=get("documents",id)
    if not doc:raise HTTPException(404,"Document not found")
    return Response(document_bytes(doc),media_type=doc['mime'],headers={'Content-Disposition':'inline','Cache-Control':'private, no-store'})
@app.get("/documents/{id}/pages/{page_number}")
def document_page(id:str,page_number:int):
    doc=get("documents",id)
    if not doc:raise HTTPException(404,"Document not found")
    if doc["mime"]!="application/pdf":return Response(document_bytes(doc),media_type=doc['mime'])
    import fitz
    with fitz.open(stream=document_bytes(doc),filetype='pdf') as source:
        if page_number<1 or page_number>len(source):raise HTTPException(404,"Page not found")
        page=source[page_number-1];scale=min(1.6,1100/max(page.rect.width,page.rect.height))
        data=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).tobytes("png")
    return Response(data,media_type="image/png")

class Investigation(BaseModel):
    capability:str=Field(pattern="^(search|fetch|browser|agent)$"); query:Optional[str]=Field(default=None,max_length=600); urls:List[str]=Field(default_factory=list); url:Optional[str]=Field(default=None,max_length=2048); goal:Optional[str]=Field(default=None,max_length=4000); district:Optional[str]=None; survey_number:Optional[str]=None; claim_id:Optional[str]=None; consent:bool=False
    question:str=Field(default='VERIFY_FIELD_VALUE',pattern='^VERIFY_(ISSUER_EXISTS|RECORD_EXISTS|FIELD_VALUE|VALIDITY_WINDOW|REVOCATION_STATUS|CROSS_RECORD)$');routing_reason:Optional[str]=None
class InvestigationPlan(BaseModel):
    question:str=Field(default='VERIFY_FIELD_VALUE',pattern='^VERIFY_(ISSUER_EXISTS|RECORD_EXISTS|FIELD_VALUE|VALIDITY_WINDOW|REVOCATION_STATUS|CROSS_RECORD)$')
    url:Optional[str]=None;interaction_required:bool=False;multi_step:bool=False
@app.post('/investigations/plan')
def investigation_plan(req:InvestigationPlan):
    from .tinyfish.router import choose
    from urllib.parse import urlparse
    known=bool(req.url and urlparse(req.url).hostname in approved_hosts())
    decision=choose(source_known=known,publicly_readable=known,interaction_required=known and req.interaction_required,multi_step=known and req.multi_step)
    return {**decision,'question':req.question,'approved_source':known,'stop_conditions':['sufficient_evidence','access_gated','budget_exhausted'],'budget':{'max_attempts':2,'max_duration_seconds':180}}
class SourceInput(BaseModel):
    hostname:str;claim_types:List[str]=Field(default_factory=list);authority:str=Field(pattern="^(reference|issuer)$")
@app.get("/sources")
def sources():return all_rows("source_registry","ORDER BY hostname")
@app.post("/sources",status_code=201)
def add_source(source:SourceInput):
    host=source.hostname.lower().strip()
    labels=host.split(".")
    if len(host)>253 or len(labels)<2 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",label) for label in labels):raise HTTPException(422,"Enter an exact public hostname")
    if host.endswith(".localhost") or host.endswith(".local") or host.endswith(".internal"):raise HTTPException(422,"Local destinations are not allowed")
    try:ipaddress.ip_address(host)
    except ValueError:pass
    else:raise HTTPException(422,"Register a hostname, not an IP address")
    existing=next((row for row in all_rows("source_registry") if row["hostname"]==host),None)
    if existing:raise HTTPException(409,"Source already registered")
    supported={'record_id','owner_name','survey_number','area','issue_date','expiry_date','jurisdiction','issuer'}
    if not set(source.claim_types).issubset(supported):raise HTTPException(422,'Unknown claim type')
    if source.authority=='issuer' and not source.claim_types:raise HTTPException(422,'Issuer sources need at least one authorized claim type')
    entry={"id":uid(),"hostname":host,"claim_types":json.dumps(source.claim_types),"authority":source.authority,"created_at":now()}
    insert("source_registry",entry)
    insert("audit_events",{"id":uid(),"event":"source.registered","subject_id":entry["id"],"detail":json.dumps({"hostname":host,"authority":source.authority}),"created_at":now()})
    return entry
def approved_hosts():return {row["hostname"] for row in all_rows("source_registry")}|{host.strip().lower() for host in os.getenv("VERITAS_APPROVED_HOSTS","www.tinyfish.ai,docs.tinyfish.ai").split(",") if host.strip()}
def safe_trace(value):
    if isinstance(value,dict):return {key:safe_trace(item) for key,item in value.items() if key.lower() not in {"cdp_url","streaming_url","video_url","base_url","password","api_key","x-api-key","authorization","access_token"}}
    if isinstance(value,list):return [safe_trace(item) for item in value]
    if isinstance(value,str):
        value=re.sub(r'wss?://[^\s]+','[managed browser connection redacted]',value)
        key=os.getenv('TINYFISH_API_KEY')
        if key:value=value.replace(key,'[credential redacted]')
    return value
async def run_investigation(iid:str,req:Investigation):
    adapter=TinyFishAdapter()
    trace_id=uid()
    insert('tinyfish_runs',{'id':trace_id,'investigation_id':iid,'capability':req.capability,'external_run_id':None,'status':'running','trace':json.dumps({'question':req.question,'reason':req.routing_reason}),'started_at':now(),'finished_at':None})
    with connect() as c:c.execute("UPDATE investigations SET status='running' WHERE id=?",(iid,))
    try:
        if req.capability=="search":
            result=await adapter.search(req.query or "")
            from urllib.parse import urlparse
            for candidate in result.get('results',[]):
                if isinstance(candidate,dict):candidate['approved_source']=urlparse(candidate.get('url','')).hostname in approved_hosts()
        elif req.capability=="fetch":
            for url in req.urls:validate_public_url(url,approved_hosts())
            result=await adapter.fetch(req.urls)
            for item in result.get("results",[]):
                final_url=item.get("final_url") or item["url"]
                validate_public_url(final_url,approved_hosts())
                if req.claim_id:
                    claim=get("claims",req.claim_id);page_text=item.get("text") or ""
                    if isinstance(page_text,dict):page_text=json.dumps(page_text)
                    save_observation(claim,final_url,page_text,'tinyfish_fetch',iid)
            if not result.get('results') and result.get('errors'):raise ValueError(json.dumps(result['errors']))
        elif req.capability=="browser":
            validate_public_url(req.url or "",approved_hosts())
            if not req.district or not req.survey_number:raise ValueError("Browser lookup requires district and survey number")
            result=await asyncio.wait_for(adapter.browser_lookup(req.url or "",req.district,req.survey_number),timeout=150)
            validate_public_url(result['url'],approved_hosts())
            if req.claim_id:save_observation(get('claims',req.claim_id),result['url'],result['result_text'],'tinyfish_browser',iid)
        else:
            validate_public_url(req.url or "",approved_hosts())
            schema={'type':'object','properties':{'source_url':{'type':'string'},'excerpt':{'type':'string'}},'required':['source_url','excerpt']} if req.claim_id else None
            task=(req.goal or '')+(' Return an exact verbatim excerpt containing the record identifier, jurisdiction and relevant field, and the source URL.' if req.claim_id else '')
            result=await adapter.run_agent(req.url or "",task,schema)
        status="running" if req.capability=="agent" else "completed";error=None
    except Exception as exc:result=None;status="failed";error=safe_trace(str(exc) or type(exc).__name__)
    with connect() as c:
        c.execute("UPDATE investigations SET status=?,result=?,error=?,finished_at=? WHERE id=?",(status,json.dumps(safe_trace(result)),error,now() if status!="running" else None,iid))
        c.execute('UPDATE tinyfish_runs SET status=?,external_run_id=?,trace=?,finished_at=? WHERE id=?',(status,result.get('run_id') if isinstance(result,dict) else None,json.dumps(safe_trace(result) if result else {'error':error}),now() if status!='running' else None,trace_id))
    insert('audit_events',{'id':uid(),'event':'investigation.'+status,'subject_id':iid,'detail':json.dumps({'capability':req.capability,'error':error}),'created_at':now()})
@app.post("/investigations",status_code=202)
async def investigate(req:Investigation,tasks:BackgroundTasks):
    if not req.consent:raise HTTPException(400,"Explicit consent is required before transmitting record identifiers")
    if req.capability=="search" and not req.query:raise HTTPException(422,"Search query is required")
    if req.capability=="fetch" and not req.urls:raise HTTPException(422,"At least one URL is required")
    if req.capability in {"browser","agent"} and not req.url:raise HTTPException(422,"A public URL is required")
    if req.capability=="agent" and not req.goal:raise HTTPException(422,"A bounded goal is required")
    if req.claim_id and not get("claims",req.claim_id):raise HTTPException(404,"Claim not found")
    if len(req.urls)>10:raise HTTPException(422,'At most 10 source URLs may be fetched')
    if req.capability=='browser' and (not req.district or not req.survey_number):raise HTTPException(422,'Browser lookup requires district and survey number')
    if req.capability in {'fetch','browser','agent'}:
        try:
            for url in (req.urls if req.capability=='fetch' else [req.url]):validate_public_url(url,approved_hosts())
        except ValueError as exc:raise HTTPException(422,str(exc))
    if public_demo():
        day=time.strftime('%Y-%m-%d',time.gmtime())
        try:
            charge_budget('requests:'+workspace_id.get()+':'+day,1,10)
            charge_budget('provider:'+req.capability+':'+day,1,3 if req.capability in {'browser','agent'} else 100)
        except ValueError as exc:raise HTTPException(429,str(exc))
    iid=uid();insert("investigations",{"id":iid,"kind":req.capability,"status":"queued","request":req.model_dump_json(),"result":None,"error":None,"started_at":now(),"finished_at":None})
    if public_demo():await run_investigation(iid,req)
    else:tasks.add_task(run_investigation,iid,req)
    return get("investigations",iid)
async def refresh_investigation(id:str):
    r=get("investigations",id)
    if not r:raise HTTPException(404,"Investigation not found")
    if r["kind"]=="agent" and r["status"]=="running" and r["result"]:
        try:
            run_id=json.loads(r["result"]).get("run_id")
            if run_id:
                state=await TinyFishAdapter().get_agent_run(run_id)
                state.setdefault('run_id',run_id)
                if state.get("status") in {"COMPLETED","FAILED","CANCELLED"}:
                    with connect() as c:
                        updated=c.execute("UPDATE investigations SET status=?,result=?,error=?,finished_at=? WHERE id=? AND status='running'",(state["status"].lower(),json.dumps(safe_trace(state)),json.dumps(safe_trace(state.get("error"))) if state.get("error") else None,now(),id)).rowcount
                    if not updated:return get('investigations',id)
                    request_data=json.loads(r['request']);output=state.get('result') or {}
                    if state['status']=='COMPLETED' and request_data.get('claim_id') and isinstance(output,dict) and output.get('source_url') and output.get('excerpt'):
                        try:
                            validate_public_url(output['source_url'],approved_hosts())
                            save_observation(get('claims',request_data['claim_id']),output['source_url'],output['excerpt'],'tinyfish_agent',id)
                        except Exception as exc:
                            state['evidence_evaluation_error']=safe_trace(str(exc))
                            with connect() as c:c.execute('UPDATE investigations SET result=? WHERE id=?',(json.dumps(safe_trace(state)),id))
                    with connect() as c:c.execute('UPDATE tinyfish_runs SET status=?,trace=?,finished_at=? WHERE investigation_id=?',(state['status'].lower(),json.dumps(safe_trace(state)),now(),id))
                    insert('audit_events',{'id':uid(),'event':'investigation.'+state['status'].lower(),'subject_id':id,'detail':json.dumps({'capability':'agent'}),'created_at':now()})
                    r=get("investigations",id)
                else:
                    with connect() as c:
                        c.execute('UPDATE investigations SET result=? WHERE id=?',(json.dumps(safe_trace(state)),id))
                        c.execute('UPDATE tinyfish_runs SET trace=? WHERE investigation_id=?',(json.dumps(safe_trace(state)),id))
                    r=get('investigations',id)
        except Exception as exc:r["poll_error"]=safe_trace(str(exc))
    if r.get('error'):
        error=r['error'].lower()
        r['reason_code']='budget_exhausted' if any(word in error for word in ('402','credit','wallet','max_steps','timeout','time limit','billing')) else 'access_gated' if any(word in error for word in ('401','403','captcha','authentication','access denied')) else 'retrieval_failure'
    return r
@app.get("/investigations/{id}")
async def investigation(id:str):return await refresh_investigation(id)
@app.get("/claims/{id}/evidence")
def evidence(id:str):return {"claim_id":id,"items":all_rows("evidence","WHERE claim_id=? ORDER BY created_at DESC",(id,)),"reason_code":"insufficient_eligible_evidence" if not all_rows("evidence","WHERE claim_id=?",(id,)) else None}
@app.get('/claims/{id}/history')
def claim_history(id:str):
    if not get('claims',id):raise HTTPException(404,'Claim not found')
    return {'decisions':all_rows('verification_decisions','WHERE claim_id=? ORDER BY created_at DESC',(id,)),'reviews':all_rows('reviews','WHERE claim_id=? ORDER BY created_at DESC',(id,))}
@app.get('/investigations/{id}/traces')
def investigation_traces(id:str):return all_rows('tinyfish_runs','WHERE investigation_id=?',(id,))
@app.get("/investigations")
async def investigations():
    rows=all_rows("investigations","ORDER BY started_at DESC")
    semaphore=asyncio.Semaphore(4)
    async def bounded(row):
        async with semaphore:return await refresh_investigation(row['id'])
    async def refresh_active(row):return await bounded(row) if row['kind']=='agent' and row['status']=='running' else row
    return list(await asyncio.gather(*(refresh_active(row) for row in rows)))
@app.post("/claims/{id}/registry-check")
def registry_check(id:str):
    claim=get("claims",id)
    if not claim:raise HTTPException(404,"Claim not found")
    doc=get("documents",claim["document_id"]);record=next((c["original_value"] for c in all_rows("claims","WHERE document_id=? AND field='record_id'",(doc["id"],))),None)
    def unresolved(reason):
        outcome={'status':'unverified','reason_code':reason,'checks':{'source':True,'span':False,'value':None,'scope':False}}
        result=save_decision(id,outcome)
        return {**result,'record_id':record}
    if not record:return unresolved('insufficient_eligible_evidence')
    import httpx
    url=f"{os.getenv('ISSUER_PORTAL_URL','http://localhost:3001')}/api/records/{record}"
    fetch_url=f"{os.environ['REGISTRY_INTERNAL_URL'].rstrip('/')}/registry/api/records/{record}" if os.getenv('REGISTRY_INTERNAL_URL') else url
    try:
        response=httpx.get(fetch_url,timeout=20)
        if response.status_code==404:return unresolved('no_public_source')
        response.raise_for_status();item=response.json()
    except httpx.HTTPError as exc:raise HTTPException(503,f"Synthetic registry retrieval failed: {exc}")
    expected=item.get(claim["field"])
    if expected is None:return unresolved('insufficient_eligible_evidence')
    expected_normalized=normalize_field(claim['field'],str(expected))
    value=None if expected_normalized is None or claim['normalized_value'] is None else normalize_unicode(claim['normalized_value']).casefold()==normalize_unicode(expected_normalized).casefold()
    scope=normalize_field('record_id',str(item.get('record_id','')))==normalize_field('record_id',record)
    jurisdiction=next((c['normalized_value'] for c in all_rows('claims','WHERE document_id=? AND field=\'jurisdiction\'',(doc['id'],))),None)
    if jurisdiction:scope=scope and normalize_unicode(str(item.get('jurisdiction',''))).casefold()==normalize_unicode(jurisdiction).casefold()
    decision=decide_evidence(approved=True,span=True,value=value,scope=scope)
    eid=uid();insert("evidence",{"id":eid,"claim_id":id,"investigation_id":None,"url":url,"method":"local_synthetic_registry","excerpt":f"{claim['field']}: {expected}","content_sha256":sha256_bytes(response.content),"checks":json.dumps(decision["checks"]),"created_at":now()})
    with connect() as c:c.execute("UPDATE claims SET status=? WHERE id=?",(decision["status"],id))
    insert("audit_events",{"id":uid(),"event":"claim.registry_checked","subject_id":id,"detail":json.dumps(decision),"created_at":now()})
    decision=save_decision(id,decision)
    return {**decision,"evidence_id":eid,"source":"synthetic_registry","record_id":record}
class Comparison(BaseModel): a:dict;b:dict
@app.post("/comparisons")
def comparisons(req:Comparison):
    result={"id":uid(),**compare_claims(req.a,req.b)};insert("comparisons",{"id":result["id"],"claim_a":json.dumps(req.a),"claim_b":json.dumps(req.b),"result":json.dumps(result),"created_at":now()});return result
@app.get("/comparisons")
def comparison_list():return all_rows("comparisons","ORDER BY created_at DESC")
class DocumentComparison(BaseModel):document_a:str;document_b:str
@app.post('/comparisons/documents')
def compare_documents(req:DocumentComparison):
    left=get('documents',req.document_a);right=get('documents',req.document_b)
    if not left or not right:raise HTTPException(404,'Document not found')
    if req.document_a==req.document_b:raise HTTPException(422,'Choose two different documents')
    a={c['field']:c for c in all_rows('claims','WHERE document_id=?',(req.document_a,))};b={c['field']:c for c in all_rows('claims','WHERE document_id=?',(req.document_b,))}
    def scoped(rows,field):return {'field':field,'record_id':rows.get('record_id',{}).get('normalized_value'),'jurisdiction':rows.get('jurisdiction',{}).get('normalized_value'),'period':rows.get('issue_date',{}).get('normalized_value'),'normalized_value':rows[field]['normalized_value']}
    rows=[]
    for field in sorted(set(a)&set(b)):
        result=compare_claims(scoped(a,field),scoped(b,field));rows.append({'field':field,'left':a[field]['original_value'],'right':b[field]['original_value'],**result})
    payload={'id':uid(),'document_a':{'id':left['id'],'name':left['name']},'document_b':{'id':right['id'],'name':right['name']},'fields':rows,'conflicts':sum(x['conflict'] for x in rows),'notice':'Conflict found. Legal ownership not determined.' if any(x['conflict'] for x in rows) else None}
    insert('comparisons',{'id':payload['id'],'claim_a':req.document_a,'claim_b':req.document_b,'result':json.dumps(payload),'created_at':now()})
    return payload
@app.get("/comparisons/{id}")
def comparison(id:str):
    row=get("comparisons",id)
    if not row:raise HTTPException(404,"Comparison not found")
    return json.loads(row["result"])
@app.get("/reviews")
def reviews():return all_rows("claims","WHERE status IN ('pending_review','conflicting') OR (status='unverified' AND id NOT IN (SELECT claim_id FROM reviews WHERE decision='approved'))")
class Review(BaseModel):decision:str=Field(pattern="^(approved|rejected|corrected)$");reason:str=Field(min_length=3);corrected_value:Optional[str]=None
@app.post("/reviews/{id}/decision")
def review(id:str,req:Review):
    claim=get('claims',id)
    if not claim:raise HTTPException(404,"Claim not found")
    if req.decision=="corrected" and not req.corrected_value:raise HTTPException(422,"Corrected value is required")
    rid=uid();insert("reviews",{"id":rid,"claim_id":id,"decision":req.decision,"reason":req.reason,"corrected_value":req.corrected_value,"created_at":now()})
    if req.decision=="corrected" and req.corrected_value:
        with connect() as c:c.execute("UPDATE claims SET normalized_value=?,status='pending_review' WHERE id=?",(req.corrected_value,id))
        insert('normalized_claim_values',{'id':uid(),'claim_id':id,'value':req.corrected_value,'unit':'hectares' if claim['field']=='area' else None,'rule':'human_correction','created_at':now()})
        for item in all_rows('evidence','WHERE claim_id=?',(id,)):
            checks=json.loads(item['checks']);checks['value']=None
            with connect() as c:c.execute('UPDATE evidence SET checks=? WHERE id=?',(json.dumps(checks),item['id']))
    elif req.decision!="corrected":
        new_status=(claim['status'] if claim['status'] in {'supported','contradicted','conflicting'} else 'unverified') if req.decision=='approved' else 'not_applicable'
        with connect() as c:c.execute("UPDATE claims SET status=? WHERE id=?",(new_status,id))
    insert("audit_events",{"id":uid(),"event":f"review.{req.decision}","subject_id":id,"detail":req.model_dump_json(),"created_at":now()});return {"id":rid,"claim_id":id,**req.model_dump()}
class EvidenceReview(BaseModel):decision:str=Field(pattern='^(approved|rejected)$');reason:str=Field(min_length=3)
@app.post('/evidence/{id}/review')
def review_evidence(id:str,req:EvidenceReview):
    item=get('evidence',id)
    if not item:raise HTTPException(404,'Evidence not found')
    checks=json.loads(item['checks'])
    if req.decision=='approved' and not (checks.get('source') and checks.get('span') and checks.get('scope') and checks.get('value') is not None):raise HTTPException(409,'Evidence must pass source, span and scope and contain a comparable value before approval')
    checks['review_rejected']=req.decision=='rejected'
    with connect() as conn:conn.execute('UPDATE evidence SET checks=? WHERE id=?',(json.dumps(checks),id))
    result=save_decision(item['claim_id'],{'status':'unverified','reason_code':'insufficient_eligible_evidence','checks':checks})
    insert('audit_events',{'id':uid(),'event':'evidence.review_'+req.decision,'subject_id':item['claim_id'],'detail':json.dumps({'evidence_id':id,**req.model_dump()}),'created_at':now()})
    return {'evidence_id':id,'decision':req.decision,'claim_status':result['status']}
@app.get("/audit")
def audit():return all_rows("audit_events","ORDER BY created_at DESC")
class Attestation(BaseModel):claim_id:str;status:str;issuer:str="VERITAS";evidence_refs:List[str]=Field(default_factory=list)
@app.post("/attestations",status_code=201)
def attest(req:Attestation):
    claim=get("claims",req.claim_id)
    if not claim:raise HTTPException(404,"Claim not found")
    if req.status!=claim["status"]:raise HTTPException(409,"Attestation status must match the stored claim decision")
    owned={row["id"] for row in all_rows("evidence","WHERE claim_id=?",(req.claim_id,))}
    if not set(req.evidence_refs).issubset(owned):raise HTTPException(422,"Evidence reference does not belong to this claim")
    aid=uid();issuer="VERITAS Local Attestation Ledger";payload={"version":"1.0","attestation_id":aid,"claim_id":req.claim_id,"status":claim["status"],"evidence_refs":req.evidence_refs,"issuer":issuer,"timestamp":now(),"revoked":False};digest=canonical_hash(payload);insert("attestations",{"id":aid,"claim_id":req.claim_id,"status":claim["status"],"issuer":issuer,"payload":json.dumps(payload,sort_keys=True),"hash":digest,"revoked":0,"created_at":payload["timestamp"]})
    if public_demo():insert('public_attestations',get('attestations',aid))
    insert('audit_events',{'id':uid(),'event':'attestation.created','subject_id':aid,'detail':json.dumps({'claim_id':req.claim_id,'hash':digest}),'created_at':now()})
    return {**payload,"attestation_hash":digest,"ledger":"Local Attestation Ledger"}
@app.get('/attestations')
def attestation_list():return all_rows('attestations','ORDER BY created_at DESC')
@app.get('/demo-fixtures/{name}')
def demo_fixture(name:str):
    if name not in {'matching-record.pdf','altered-owner.pdf','altered-area.pdf','unavailable-record.pdf','scanned-record.png'}:raise HTTPException(404,'Sample not found')
    return FileResponse(Path(__file__).resolve().parents[2]/'fixtures'/name,filename=name)
@app.post("/attestations/{id}/revoke")
def revoke_attestation(id:str):
    if not get("attestations",id):raise HTTPException(404,"Attestation not found")
    with connect() as c:c.execute("UPDATE attestations SET revoked=1 WHERE id=?",(id,))
    if public_demo():
        with connect() as c:c.execute('UPDATE public_attestations SET revoked=1 WHERE id=?',(id,))
    insert("audit_events",{"id":uid(),"event":"attestation.revoked","subject_id":id,"detail":"{}","created_at":now()})
    return {"attestation_id":id,"revoked":True}
@app.get("/verify/{id}")
def verify(id:str):
    r=get("public_attestations" if public_demo() else "attestations",id)
    if not r:raise HTTPException(404,"Attestation not found")
    p=json.loads(r["payload"]);return {"attestation_id":id,"claim_id":r["claim_id"],"status":r["status"],"issuer":r["issuer"],"timestamp":r["created_at"],"hash":r["hash"],"hash_valid":canonical_hash(p)==r["hash"],"revoked":bool(r["revoked"]),"evidence_summary":p.get("evidence_refs",[])}
@app.get("/verify/{id}/qr")
def verify_qr(id:str):
    if not get("public_attestations" if public_demo() else "attestations",id):raise HTTPException(404,"Attestation not found")
    import qrcode
    image=qrcode.make(f"{os.getenv('PUBLIC_WEB_URL','http://localhost:3000')}/verify/{id}");buf=io.BytesIO();image.save(buf,format="PNG");return Response(buf.getvalue(),media_type="image/png")
