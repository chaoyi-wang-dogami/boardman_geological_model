"""Preservation-first migration of frozen Boardman iterations into PostgreSQL."""
import csv
import argparse
from decimal import Decimal, InvalidOperation
import gzip
import json
from pathlib import Path
from common import ANALYSIS, ITERATION, REPO, VERSION, copy_block, csv_rows, digest, record_id, sql, write_json

CORE={'boardman_wells_summary.csv':'well','boardman_wells_stratigraphy.csv':'stratigraphy','boardman_wells_lithology.csv':'lithology'}

def number(value):
    if value in ('',None):return None
    try:
        value=Decimal(value)
        return str(value) if value.is_finite() else None
    except InvalidOperation:return None

def migrate(database='boardman'):
    if sql("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='boardman');",database).strip()=='t':
        raise RuntimeError('boardman schema already exists; refusing to overwrite an existing migration')
    ITERATION.mkdir(parents=True,exist_ok=True)
    for name in ['inputs','outputs','audit','evidence/maps','evidence/workflow']:(ITERATION/name).mkdir(parents=True,exist_ok=True)
    dirs={n:next(ANALYSIS.glob(f'iter{n}_*')) for n in range(4)}
    sources=set()
    for directory in dirs.values():
        sources.update(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    # Include earlier exploratory findings, maps, workflow documents and cached ground-height evidence.
    for name in ['artifacts','maps']:
        sources.update(p for p in (ANALYSIS/name).rglob('*') if p.is_file())
    sources.update(ANALYSIS.glob('*.md'))
    phase=dirs[3]/'audit/phase1_completeness'
    for row in csv_rows(phase/'cached_ground_height_sources.csv'):
        sources.add(REPO/row['metadata_path']);sources.add(REPO/row['page_path'])
    existing_inventory=ITERATION/'inputs/input_files.csv'
    if existing_inventory.exists():
        inventory=csv_rows(existing_inventory)
        sources={REPO/r['path'] for r in inventory}
        for row in inventory:
            if digest((REPO/row['path']).read_bytes())!=row['sha256']:
                raise RuntimeError('Frozen migration input changed: '+row['path'])
    else:
        # Living workflow files are frozen before source discovery and later index updates.
        for path in list(sources):
            if path.parent==ANALYSIS and path.suffix=='.md':
                target=ITERATION/'evidence/workflow'/path.name
                if not target.exists():target.write_bytes(path.read_bytes())
                sources.remove(path);sources.add(target)
    file_data={};locations=[];records={};rows_by_path={};input_rows=[]
    for path in sorted(sources):
        content=path.read_bytes();sha=digest(content);relative=str(path.relative_to(REPO))
        iteration=4 if path.is_relative_to(ITERATION) else next((n for n,d in dirs.items() if path.is_relative_to(d)),None)
        file_data.setdefault(sha,content)
        locations.append([relative,sha,iteration,'historical_input'])
        row_count=None
        if path.suffix=='.csv':
            rows=csv_rows(path);rows_by_path[path]=rows;row_count=len(rows)
            for ordinal,row in enumerate(rows,2):records[record_id(sha,ordinal)]=(sha,ordinal,row)
        input_rows.append({'path':relative,'sha256':sha,'size_bytes':len(content),'row_count':row_count,'parent_iteration':iteration})
    # Confirm the frozen core releases against their own manifests before copying anything.
    for n in range(3):
        manifest=json.loads((dirs[n]/'manifest.json').read_text())
        for entry in manifest.get('outputs',[]):
            if Path(entry['path']).name in CORE:
                base=REPO if entry.get('path_base')=='repository_root' else dirs[n]
                path=base/entry['path']
                if entry.get('sha256') and digest(path.read_bytes())!=entry['sha256']:
                    raise RuntimeError('Frozen source fingerprint changed: '+str(path))
    hashes={p:digest(p.read_bytes()) for p in rows_by_path}
    def rid(path,ordinal):return record_id(hashes[path],int(ordinal))
    def affected(row):
        path=REPO/row['source_file']
        if row['source_sha256']!=hashes[path]:raise RuntimeError('Audit source fingerprint mismatch')
        return rid(path,row['source_record'])
    well_ids=set(row['well_id'] for row in rows_by_path[dirs[0]/'outputs/boardman_wells_summary.csv'])
    well_versions={};intervals={};interval_versions={};lineages={}
    memberships={};interval_memberships={};canonical={}
    for n in range(3):
        if n:
            wm=dict(memberships[n-1]);im=dict(interval_memberships[n-1])
            side=csv_rows(dirs[n]/'audit/source_row_links.csv')
            links={(r['output_file'],int(r['output_record'])):r for r in side}
        else:wm={};im={};links={}
        for folder,state in [('outputs','working'),('outputs/removed_records','deduplicated' if n==1 else 'excluded_no_stratigraphy')]:
            if n==0 and state!='working':continue
            for filename,kind in CORE.items():
                path=dirs[n]/folder/filename
                if not path.exists():continue
                for ordinal,row in enumerate(rows_by_path[path],2):
                    rec=rid(path,ordinal)
                    if n:
                        link=links[(folder+'/'+filename,ordinal)]
                        parent=record_id(link['source_sha256'],int(link['source_record']))
                        baseline=parent if n==1 else record_id(link['baseline_source_sha256'],int(link['baseline_source_record']))
                        if rec!=parent:lineages[rec]=[rec,parent,baseline,'iteration_source_row_links']
                    else:baseline=rec
                    if kind=='well':
                        lat=number(row['latitude']);lon=number(row['longitude'])
                        well_versions[rec]=[rec,row['well_id'],lat,lon,number(row['completed_depth_ft'])]
                        wm[row['well_id']]=(rec,state)
                    else:
                        canonical[rec]=baseline
                        if n==0:intervals[baseline]=[baseline,row['well_id'],kind,baseline]
                        if kind=='stratigraphy':
                            values=[number(row[k]) for k in ['start_depth','end_depth','start_depth_elev','end_depth_elev','depth_thickness']]+[row['strat_unit'],None]
                        else:values=[number(row['from_ft']),number(row['to_ft']),None,None,number(row['thickness_ft']),None,row['material_raw']]
                        interval_versions[rec]=[rec,baseline,*values]
                        im[baseline]=(rec,state)
        memberships[n]=wm;interval_memberships[n]=im
    for n in [3,4]:
        memberships[n]=dict(memberships[2]);interval_memberships[n]=dict(interval_memberships[2])
    blocks=[]
    def add(table,cols,rows):blocks.append(copy_block(table,cols,rows))
    iterations=[]
    for n,directory in dirs.items():
        m=json.loads((directory/'manifest.json').read_text())
        iterations.append([n,directory.name,m['purpose'],m['status'],None if n==0 else (2 if n==3 else n-1),n!=3])
    iterations.append([4,ITERATION.name,'Migrate preserved well data and audit history into PostgreSQL/PostGIS','Complete',2,True])
    add('iterations',['iteration_number','directory_name','purpose','source_status','dataset_parent','is_data_release'],iterations)
    add('source_files',['source_id','size_bytes','content_gzip'],[[sha,len(content),'\\x'+gzip.compress(content,mtime=0).hex()] for sha,content in file_data.items()])
    add('source_locations',['path','source_id','iteration_number','role'],locations)
    add('source_records',['record_id','source_id','csv_record','raw_values'],[[rec,sha,ordinal,json.dumps(row,ensure_ascii=False)] for rec,(sha,ordinal,row) in records.items()])
    add('wells',['well_id'],[[w] for w in sorted(well_ids)])
    add('well_versions',['record_id','well_id','latitude','longitude','completed_depth_ft'],well_versions.values())
    add('intervals',['interval_id','well_id','kind','baseline_record_id'],intervals.values())
    add('interval_versions',['record_id','interval_id','top_depth_ft','bottom_depth_ft','top_elevation_ft','bottom_elevation_ft','thickness_ft','strat_unit','material_raw'],interval_versions.values())
    add('well_membership',['iteration_number','well_id','version_record_id','state'],[[n,w,*value] for n,wm in memberships.items() for w,value in wm.items()])
    add('interval_membership',['iteration_number','interval_id','version_record_id','state'],[[n,i,*value] for n,im in interval_memberships.items() for i,value in im.items()])
    add('record_lineage',['child_record_id','parent_record_id','baseline_record_id','method'],lineages.values())
    # All location geometry follows the existing display assumption, not verified source CRS.
    blocks.append("ALTER TABLE boardman.well_versions DISABLE TRIGGER preserve_history; UPDATE boardman.well_versions SET location=ST_SetSRID(ST_MakePoint(longitude::float8,latitude::float8),4326) WHERE longitude BETWEEN -180 AND 180 AND latitude BETWEEN -90 AND 90; ALTER TABLE boardman.well_versions ENABLE TRIGGER preserve_history;\n")
    audits=[];auditpath=phase/'well_completeness.csv'
    for ordinal,row in enumerate(rows_by_path[auditpath],2):audits.append([rid(auditpath,ordinal),3,row['well_id'],row['numeric_category'],row['ground_height_category']])
    add('well_audits',['audit_id','iteration_number','well_id','numeric_category','ground_height_category'],audits)
    path=phase/'interval_findings.csv';findings=[]
    for ordinal,row in enumerate(rows_by_path[path],2):
        target=affected(row)
        findings.append(['ITER3_'+row['finding_id'],rid(path,ordinal),3,row['well_id'],target,canonical.get(target),row['issue_code'],row['description']])
    add('findings',['finding_id','audit_record_id','iteration_number','well_id','affected_record_id','interval_id','issue_code','description'],findings)
    path=phase/'ground_height_candidates.csv'
    add('ground_height_candidates',['candidate_id','well_id','affected_record_id','interval_id','endpoint','candidate_height_ft'],[[rid(path,o),r['well_id'],affected(r),canonical[affected(r)],r['endpoint'],number(r['implied_ground_height_ft'])] for o,r in enumerate(rows_by_path[path],2)])
    path=phase/'cached_ground_height_sources.csv';heights=[];sites={}
    for ordinal,row in enumerate(rows_by_path[path],2):
        key=rid(path,ordinal);sites[row['gw_site_id']]=key
        heights.append([key,row['gw_site_id'],number(row['source_ground_elevation_ft']),row['source_vertical_datum'],digest((REPO/row['metadata_path']).read_bytes()),digest((REPO/row['page_path']).read_bytes())])
    add('ground_height_sources',['height_source_id','gw_site_id','height_ft','vertical_reference_raw','metadata_source_id','page_source_id'],heights)
    add('well_height_links',['well_id','height_source_id','coordinate_match'],[[r['well_id'],sites[r['gw_site_id']],r['cached_site_coordinates_match_well']=='True'] for r in rows_by_path[auditpath] if r['cached_source_metadata']])
    path=dirs[1]/'audit/deduped_well_links.csv'
    add('duplicate_wells',['removed_well_id','representative_well_id','distance_m','audit_record_id'],[[r['removed_well_id'],r['representative_well_id'],r['distance_to_representative_m'],rid(path,o)] for o,r in enumerate(rows_by_path[path],2)])
    path=dirs[1]/'audit/stratigraphy_duplicate_links.csv'
    add('duplicate_intervals',['removed_interval_id','representative_interval_id','audit_record_id'],[[record_id(r['source_sha256'],int(r['removed_source_record'])),record_id(r['source_sha256'],int(r['representative_source_record'])),rid(path,o)] for o,r in enumerate(rows_by_path[path],2)])
    decisions=[]
    for n,directory in dirs.items():
        for path in directory.rglob('decisions.json'):
            data=json.loads(path.read_text())
            if isinstance(data,list):
                for j,row in enumerate(data):decisions.append([f'ITER{n}_'+str(row.get('decision_id',j)),n,digest(path.read_bytes()),json.dumps(row)])
            else:decisions.append([f'ITER{n}_'+path.parent.name,n,digest(path.read_bytes()),json.dumps(data)])
    decisions.append(['ITER4_KEEP_WITH_FINDINGS',4,None,json.dumps({'decided_by':'User','status':'accepted','decision':'Retain all iteration 2 working wells and original values; import all iteration 3 findings without geological corrections.'})])
    add('decisions',['decision_id','iteration_number','source_id','details'],decisions)
    schema=(VERSION/'schema.sql').read_text()
    # Schema and migration data commit together; partial loads roll back.
    schema=schema.removesuffix('COMMIT;\n')
    sql(schema+'\n'+''.join(blocks)+'COMMIT;\n',database)
    path=ITERATION/'inputs/input_files.csv'
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(input_rows[0]));writer.writeheader();writer.writerows(input_rows)
    write_json(ITERATION/'audit/import_summary.json',{'source_files':len(file_data),'source_locations':len(locations),'source_records':len(records),'wells':len(well_ids),'intervals':len(intervals),'well_versions':len(well_versions),'interval_versions':len(interval_versions),'record_lineage':len(lineages),'geological_values_changed':0})
    print('Imported',len(well_ids),'well IDs and',len(intervals),'original interval occurrences')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--database',default='boardman')
    migrate(parser.parse_args().database)
