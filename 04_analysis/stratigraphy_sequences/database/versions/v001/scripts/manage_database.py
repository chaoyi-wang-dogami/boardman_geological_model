"""Start/stop the project service, take a backup, or restore to a NEW database."""
import argparse
import json
import time
from pathlib import Path
from common import CONTAINER, PROJECT, VERSION, config, docker, sql, write_json

def start():
    cfg=config()
    image='postgis/postgis:17-3.5'
    lock=VERSION/'image.lock.json'
    if lock.exists():image=json.loads(lock.read_text())['image_digest']
    else:
        docker(['pull',image])
        image=docker(['image','inspect',image,'--format','{{index .RepoDigests 0}}']).strip()
        write_json(lock,{'image_tag':'postgis/postgis:17-3.5','image_digest':image})
    existing=docker(['ps','-a','--filter','name=^/'+CONTAINER+'$','--format','{{.Names}}|{{.Label "com.docker.compose.project"}}']).strip()
    if existing and existing!=CONTAINER+'|'+PROJECT:raise RuntimeError('Container name belongs to another project; refusing to replace it')
    compose=(VERSION/'compose.yaml').read_text().replace('${BOARDMAN_IMAGE:-postgis/postgis:17-3.5}',image)
    compose=compose.replace('${BOARDMAN_DB_PASSWORD:?Set the project database password}',json.dumps(cfg['password']))
    # The password substitution needs a quoted YAML value; the original is unquoted.
    docker(['compose','-p',PROJECT,'-f','-','up','-d'],compose.encode())
    for _ in range(30):
        try:
            sql('SELECT 1;')
            print('Project database ready on localhost:55432');return
        except RuntimeError:time.sleep(1)
    raise RuntimeError('Database did not become ready')

def backup(path, db):
    path=Path(path)
    if path.exists():raise RuntimeError('Backup already exists; refusing overwrite')
    data=docker(['exec',CONTAINER,'pg_dump','-U','boardman_admin','-d',db,'-Fc','--no-owner','--no-acl'],binary=True)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print('Backup written:',path)

def restore(path,db):
    if not db.replace('_','').isalnum() or db=='boardman':raise RuntimeError('Use a new test database name, not the working database')
    sql('CREATE DATABASE "'+db+'";',db='postgres')
    docker(['exec','-i',CONTAINER,'pg_restore','-U','boardman_admin','-d',db,'--no-owner','--no-acl','--exit-on-error'],Path(path).read_bytes())
    print('Restored to:',db)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','stop','backup','restore'])
    parser.add_argument('--file');parser.add_argument('--database',default='boardman')
    args=parser.parse_args()
    if args.action=='start':start()
    elif args.action=='stop':docker(['stop',CONTAINER]);print('Database stopped; persistent volume retained')
    elif args.action=='backup':
        if not args.file:parser.error('--file is required')
        backup(args.file,args.database)
    else:
        if not args.file:parser.error('--file is required')
        restore(args.file,args.database)
