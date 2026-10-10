"""Docker transport, source identities, and PostgreSQL access. No external Python packages."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import uuid
from functools import lru_cache

VERSION = Path(__file__).resolve().parents[1]
DATABASE = VERSION.parents[1]
ANALYSIS = DATABASE.parent
REPO = ANALYSIS.parents[1]
ITERATION = ANALYSIS / 'iter4_10092026_build_postgres_well_database'
CONTAINER = 'boardman-stratigraphy-db'
PROJECT = 'boardman_stratigraphy'
NAMESPACE = uuid.UUID('178ec8e1-645b-48aa-b03e-6de2942041dd')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def record_id(source_hash, ordinal):
    return str(uuid.uuid5(NAMESPACE, f'{source_hash}:{ordinal}'))

def csv_rows(path):
    with Path(path).open(newline='',encoding='utf-8') as stream:
        return list(csv.DictReader(stream))

def write_json(path, data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')

def config():
    path = DATABASE / 'runtime' / 'connection.json'
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        os.chmod(path.parent,0o700)
        data={'container':CONTAINER,'database':'boardman','username':'boardman_admin',
              'host':'127.0.0.1','port':55432,'password':secrets.token_urlsafe(32)}
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:json.dump(data,stream,indent=2)
    return json.loads(path.read_text())

@lru_cache(maxsize=1)
def docker_binary():
    # Windows interop bypasses Linux socket group permissions in Docker Desktop WSL.
    for candidate in ['docker.exe','docker']:
        binary=shutil.which(candidate)
        if binary:
            result=subprocess.run([binary,'info','--format','{{.ServerVersion}}'],capture_output=True)
            if result.returncode==0:return binary
    raise RuntimeError('Docker Desktop is unreachable. Enable WSL integration or Windows interop.')

def docker(args, data=None, binary=False):
    result=subprocess.run([docker_binary(),*args],input=data,capture_output=True)
    if result.returncode:
        message=result.stderr.decode(errors='replace')
        secret_path=DATABASE/'runtime'/'connection.json'
        if secret_path.exists():message=message.replace(json.loads(secret_path.read_text())['password'],'[redacted]')
        raise RuntimeError(message[:4000])
    return result.stdout if binary else result.stdout.decode()

def sql(statement, db='boardman'):
    command=['exec','-i',CONTAINER,'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-U','boardman_admin','-d',db]
    return docker(command,('SET search_path TO boardman,public;\n'+statement).encode())

def query(statement, db='boardman'):
    return json.loads(sql('SELECT COALESCE(json_agg(q),\'[]\'::json) FROM ('+statement+') q;',db))

def copy_block(table, columns, rows):
    stream=io.StringIO(newline='')
    writer=csv.writer(stream,lineterminator='\n')
    for row in rows:writer.writerow(['\\N' if value is None else value for value in row])
    return f"COPY boardman.{table} ({','.join(columns)}) FROM STDIN WITH (FORMAT csv, NULL '\\N');\n"+stream.getvalue()+"\\.\n"
