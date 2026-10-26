"""No-code demo sessions. The signed HttpOnly cookie selects an RLS workspace."""
from __future__ import annotations
import hashlib,hmac,os,re,secrets,time
from datetime import datetime,timezone
from .store import workspace_id,seed_sources,charge_budget,insert,all_rows,clear_workspace,connect,now

def session_cookie(value:str)->str|None:
    try:
        identifier,expires,signature=value.split('.')
        if not re.fullmatch(r'[a-f0-9]{32}',identifier) or int(expires)<time.time():return None
        secret=os.environ['VERITAS_SESSION_SECRET']
        expected=hmac.new(secret.encode(),f'{identifier}.{expires}'.encode(),hashlib.sha256).hexdigest()
        return identifier if hmac.compare_digest(signature,expected) else None
    except (ValueError,KeyError):return None

def new_session()->tuple[str,str]:
    identifier=secrets.token_hex(16);expires=int(time.time())+30*86400
    payload=f'{identifier}.{expires}'
    signature=hmac.new(os.environ['VERITAS_SESSION_SECRET'].encode(),payload.encode(),hashlib.sha256).hexdigest()
    return identifier,f'{payload}.{signature}'

def cleanup_expired():
    """Bounded, opportunistic expiry; no paid scheduler or always-on worker."""
    for row in all_rows('demo_workspaces','WHERE expires_at<? LIMIT 2',(now(),)):
        if not re.fullmatch(r'[a-f0-9]{32}',row['id']):continue
        token=workspace_id.set(row['id'])
        try:
            clear_workspace()
            with connect() as conn:conn.execute('DELETE FROM demo_workspaces WHERE id=?',(row['id'],))
        finally:workspace_id.reset(token)

async def anonymous_workspace(request,call_next):
    # Public attestations contain only permitted snapshot metadata, never an upload.
    if request.url.path in {'/','/health','/tinyfish/health','/docs','/openapi.json','/redoc'} or request.url.path.startswith('/verify/'):
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        return response
    from fastapi.responses import JSONResponse
    identifier=session_cookie(request.cookies.get('veritas_demo',''));cookie=None
    try:
        if not identifier:
            cleanup_expired()
            charge_budget('guests:'+time.strftime('%Y-%m-%d',time.gmtime()),1,250)
            identifier,cookie=new_session()
            insert('demo_workspaces',{'id':identifier,'created_at':now(),'expires_at':datetime.fromtimestamp(int(cookie.split('.')[1]),timezone.utc).isoformat()})
        token=workspace_id.set(identifier)
        try:
            seed_sources()
            response=await call_next(request)
        finally:workspace_id.reset(token)
        if cookie:response.set_cookie('veritas_demo',cookie,httponly=True,secure=os.getenv('VERITAS_COOKIE_SECURE')=='true',samesite='lax',max_age=30*86400,path='/')
        response.headers['Cache-Control']='private, no-store'
        return response
    except ValueError as exc:return JSONResponse({'detail':str(exc)},status_code=429)
