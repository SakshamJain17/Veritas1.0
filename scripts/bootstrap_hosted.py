"""Versioned hosted-demo schema and restricted application role. Never print secrets.

Run from the repository root after Vercel's Neon Free integration is connected.
The admin connection is used for migrations only. Runtime uses a non-BYPASSRLS role.
"""
import os,secrets,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values,set_key
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
from psycopg import sql
from apps.api.models import Base

ENV=Path('.env.production.local')
values=dotenv_values(ENV)
admin=values['DATABASE_URL_UNPOOLED'].replace('postgresql://','postgresql+psycopg://',1)
engine=create_engine(admin,connect_args={'connect_timeout':20})
GLOBAL={'demo_usage','demo_workspaces'}
ROLE='veritas_app'

with engine.begin() as conn:
    # All migration DDL is transactional and idempotent. This resource is new.
    conn.execute(text('SELECT pg_advisory_xact_lock(68429271)'))
    Base.metadata.create_all(conn)
    existing=values.get('VERITAS_DATABASE_URL')
    password=make_url(existing).password if existing and existing!='[SENSITIVE]' else secrets.token_urlsafe(40)
    raw=conn.connection.driver_connection
    with raw.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s",(ROLE,))
        if not cursor.fetchone():cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOBYPASSRLS NOCREATEDB NOCREATEROLE').format(sql.Identifier(ROLE),sql.Literal(password)))
        elif not existing or existing=='[SENSITIVE]':raise SystemExit('Runtime role already exists. Reuse its saved configuration rather than rotating credentials silently.')
    conn.execute(text('GRANT USAGE ON SCHEMA public TO veritas_app'))
    for table in Base.metadata.sorted_tables:
        name=table.name
        if name not in GLOBAL:
            conn.execute(text(f"ALTER TABLE {name} ADD COLUMN IF NOT EXISTS workspace_id text NOT NULL DEFAULT current_setting('veritas.workspace',true)"))
            conn.execute(text(f'ALTER TABLE {name} ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'ALTER TABLE {name} FORCE ROW LEVEL SECURITY'))
            exists=conn.execute(text('SELECT 1 FROM pg_policies WHERE schemaname=\'public\' AND tablename=:name AND policyname=\'workspace_owner\''),{'name':name}).first()
            if not exists:conn.execute(text(f"CREATE POLICY workspace_owner ON {name} USING (workspace_id=current_setting('veritas.workspace',true)) WITH CHECK (workspace_id=current_setting('veritas.workspace',true))"))
            conn.execute(text(f'CREATE INDEX IF NOT EXISTS {name}_workspace_idx ON {name}(workspace_id)'))
        conn.execute(text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON {name} TO veritas_app'))
    conn.execute(text('ALTER TABLE source_registry DROP CONSTRAINT IF EXISTS source_registry_hostname_key'))
    conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS source_registry_workspace_hostname ON source_registry(workspace_id,hostname)'))
    if not conn.execute(text("SELECT 1 FROM pg_policies WHERE tablename='public_attestations' AND policyname='public_read'")).first():
        conn.execute(text('CREATE POLICY public_read ON public_attestations FOR SELECT USING (true)'))
    conn.execute(text('CREATE TABLE IF NOT EXISTS veritas_schema_versions (version integer PRIMARY KEY, applied_at timestamptz DEFAULT now())'))
    conn.execute(text('INSERT INTO veritas_schema_versions(version) VALUES(1) ON CONFLICT DO NOTHING'))

runtime=make_url(values['DATABASE_URL']).set(drivername='postgresql+psycopg',username=ROLE,password=password).render_as_string(hide_password=False)
secret=values.get('VERITAS_SESSION_SECRET')
if not secret or secret=='[SENSITIVE]':secret=secrets.token_urlsafe(48)
for key,value in {'VERITAS_DATABASE_URL':runtime,'VERITAS_SESSION_SECRET':secret}.items():
    set_key(str(ENV),key,value)
    result=subprocess.run(['npx','--yes','vercel@64.7.0','--scope','team_VCakRFqWhi6YWS9pvQlx7SeD','env','add',key,'--environment','production','--project','veritas1-0','--type','secret','--force','--yes'],input=value,text=True,capture_output=True)
    if result.returncode:raise SystemExit(f'Could not store {key}; configuration remains in the ignored local environment file. No secret value was printed.')
    print(f'{key}: saved as production Secret')
os.chmod(ENV,0o600)
print('Schema v1 ready; runtime role cannot bypass row security.')
