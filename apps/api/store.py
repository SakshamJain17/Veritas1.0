"""SQLAlchemy backed persistence for SQLite development and PostgreSQL deployment."""
from __future__ import annotations
import os, uuid
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

def now():return datetime.now(timezone.utc).isoformat()
def database_url():
    configured=os.getenv("DATABASE_URL","")
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
        _engine=create_engine(url,pool_pre_ping=True)
        _engine_url=url
    return _engine

class Connection:
    def __enter__(self):
        self.conn=engine().connect()
        self.transaction=self.conn.begin()
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
    Base.metadata.create_all(engine())
    with connect() as conn:
        for hostname in ("www.tinyfish.ai","docs.tinyfish.ai"):
            present=conn.execute("SELECT id FROM source_registry WHERE hostname=?",(hostname,)).fetchone()
            if not present:conn.execute("INSERT INTO source_registry (id,hostname,claim_types,authority,created_at) VALUES (?,?,?,?,?)",(uid(),hostname,"[]","reference",now()))
def insert(table:str,values:dict):
    keys=list(values)
    columns=",".join(keys);parameters=",".join("?" for _ in keys)
    with connect() as conn:conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({parameters})",[values[key] for key in keys])
def get(table:str,id:str):
    with connect() as conn:
        row=conn.execute(f"SELECT * FROM {table} WHERE id=?",(id,)).fetchone()
        return dict(row._mapping) if row else None
def all_rows(table:str,where:str="",args:tuple=()):
    with connect() as conn:return [dict(row._mapping) for row in conn.execute(f"SELECT * FROM {table} {where}",args).fetchall()]
def uid():return str(uuid.uuid4())
