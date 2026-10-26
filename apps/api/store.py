"""SQLAlchemy backed persistence for SQLite development and PostgreSQL deployment."""
from __future__ import annotations
import os, uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from .models import Base

ROOT=Path(__file__).resolve().parents[2]
DB=Path(os.getenv("VERITAS_DB_PATH",ROOT/"data"/"veritas.db"))
UPLOADS=Path(os.getenv("VERITAS_UPLOAD_PATH",ROOT/"uploads"))
_engine:Engine|None=None
_engine_url:str|None=None
workspace_id:ContextVar[str]=ContextVar('veritas_workspace',default='local')

def public_demo():return os.getenv('VERITAS_PUBLIC_DEMO','false').lower()=='true'

def now():return datetime.now(timezone.utc).isoformat()
def database_url():
    if public_demo() and not os.getenv('VERITAS_DATABASE_URL'):raise RuntimeError('The public demo requires its restricted database connection.')
    configured=os.getenv("VERITAS_DATABASE_URL") or os.getenv("DATABASE_URL","")
    if configured:
        if configured.startswith('postgres://'):return configured.replace('postgres://','postgresql+psycopg://',1)
        if configured.startswith('postgresql://'):return configured.replace('postgresql://','postgresql+psycopg://',1)
        return configured
    DB.parent.mkdir(parents=True,exist_ok=True)
    return f"sqlite:///{DB}"
def engine():
    global _engine,_engine_url
    url=database_url()
    if _engine is None or _engine_url!=url:
        if _engine is not None:_engine.dispose()
        _engine=create_engine(url,pool_pre_ping=True,**({'pool_size':2,'max_overflow':3,'connect_args':{'connect_timeout':15}} if url.startswith('postgresql') else {}))
        if public_demo():
            if _engine.dialect.name!='postgresql':raise RuntimeError('Anonymous hosted workspaces require PostgreSQL row security.')
            with _engine.connect() as connection:
                if connection.execute(text('SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user')).scalar():raise RuntimeError('The public API must not run with a database owner or BYPASSRLS role.')
        _engine_url=url
    return _engine

class Connection:
    def __enter__(self):
        self.conn=engine().connect()
        self.transaction=self.conn.begin()
        if public_demo() and self.conn.dialect.name=='postgresql':
            self.conn.execute(text("SELECT set_config('veritas.workspace',:workspace,true)"),{'workspace':workspace_id.get()})
        return self
    def __exit__(self,exception_type,exception,_traceback):
        if exception_type:self.transaction.rollback()
        else:self.transaction.commit()
        self.conn.close()
    def execute(self,statement:str,values:tuple|list=()):
        parts=statement.split("?")
        if len(parts)-1!=len(values):raise ValueError("SQL placeholder count does not match parameters")
        sql="".join(part+(f":p{index}" if index<len(values) else "") for index,part in enumerate(parts))
        return self.conn.execute(text(sql),{f"p{index}":value for index,value in enumerate(values)})

def connect():return Connection()
def init_db():
    if not public_demo():Base.metadata.create_all(engine())
    seed_sources()

def seed_sources():
    import json
    from urllib.parse import urlparse
    with connect() as conn:
        for hostname in ("www.tinyfish.ai","docs.tinyfish.ai"):
            present=conn.execute("SELECT id FROM source_registry WHERE hostname=?",(hostname,)).fetchone()
            if not present:conn.execute("INSERT INTO source_registry (id,hostname,claim_types,authority,created_at) VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",(uid(),hostname,"[]","reference",now()))
        if public_demo():
            host=urlparse(os.getenv('PUBLIC_WEB_URL','https://veritas1-0.vercel.app')).hostname
            fields=['record_id','owner_name','area','issue_date','jurisdiction','issuer']
            conn.execute('INSERT INTO source_registry (id,hostname,claim_types,authority,created_at) VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING',(uid(),host,json.dumps(fields),'issuer',now()))
def insert(table:str,values:dict):
    keys=list(values)
    columns=",".join(keys);parameters=",".join("?" for _ in keys)
    with connect() as conn:conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({parameters})",[values[key] for key in keys])
def get(table:str,id:str):
    with connect() as conn:
        row=conn.execute(f"SELECT * FROM {table} WHERE id=?",(id,)).fetchone()
        result=dict(row._mapping) if row else None
        if result:result.pop('workspace_id',None)
        return result
def all_rows(table:str,where:str="",args:tuple=()):
    with connect() as conn:
        rows=[dict(row._mapping) for row in conn.execute(f"SELECT * FROM {table} {where}",args).fetchall()]
        for row in rows:row.pop('workspace_id',None)
        return rows
def uid():return str(uuid.uuid4())

def document_bytes(document:dict)->bytes:
    stored=get('document_objects',document['id'])
    return bytes(stored['data']) if stored else Path(document['path']).read_bytes()

def charge_budget(key:str,amount:int,limit:int):
    """Atomic global quotas, shared by all function instances; never a memory counter."""
    with connect() as conn:
        row=conn.execute('INSERT INTO demo_usage (id,amount) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET amount=demo_usage.amount+excluded.amount WHERE demo_usage.amount+excluded.amount<=? RETURNING amount',(key,amount,limit)).fetchone()
        if not row:raise ValueError('The free public demo usage limit has been reached. Please try again later.')

def clear_workspace():
    """Delete only the current guest's rows; FORCE RLS also applies to these deletes."""
    if not public_demo():raise ValueError('Workspace reset is available only in the isolated public demo.')
    with connect() as conn:
        used=conn.execute('SELECT COALESCE(SUM(size),0) FROM documents').scalar() or 0
        for table in reversed(Base.metadata.sorted_tables):
            if table.name not in {'demo_usage','demo_workspaces'}:conn.execute(f'DELETE FROM {table.name}')
        conn.execute('UPDATE demo_usage SET amount=CASE WHEN amount>=? THEN amount-? ELSE 0 END WHERE id=?',(used,used,'upload-bytes-total'))
