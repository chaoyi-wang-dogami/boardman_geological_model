"""Generate a portable HTML snapshot exclusively from PostgreSQL queries."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
VERSION=Path(__file__).resolve().parents[1]
BASE_VERSION=VERSION.parent/'v001'
sys.path.insert(0,str(BASE_VERSION/'scripts'))
from common import ITERATION, digest, query, write_json

def build(output,database='boardman',snapshot=None):
    output=Path(output)
    if output.exists():raise RuntimeError('Map output already exists; use a new path')
    if snapshot:
        original=Path(snapshot).read_text()
        match=re.search(r'<script type="application/json" id="database-data">(.*?)</script>',original,re.S)
        if not match:raise RuntimeError('Snapshot has no embedded database data')
        data=json.loads(match.group(1))
        return render(data,output,'Preserved embedded PostgreSQL snapshot; display repair only')
    wells=query("""SELECT m.well_id,m.state,r.raw_values AS metadata,
      r.record_id,r.csv_record,r.source_id,a.numeric_category,a.ground_height_category,
      ar.raw_values AS audit FROM well_membership m
      JOIN source_records r ON r.record_id=m.version_record_id
      LEFT JOIN well_audits a ON a.well_id=m.well_id AND a.iteration_number=3
      LEFT JOIN source_records ar ON ar.record_id=a.audit_id
      WHERE m.iteration_number=(SELECT max(iteration_number) FROM iterations WHERE is_data_release)
      ORDER BY m.well_id""",database)
    by_id={w['well_id']:w for w in wells}
    for w in wells:
        for name in ['stratigraphy','lithology','findings','candidates','heights','history','removed_wells']:w[name]=[]
    for row in query("""SELECT i.well_id,i.kind,i.interval_id,v.record_id,r.source_id,r.csv_record,r.raw_values AS values
      FROM interval_membership m JOIN intervals i USING(interval_id)
      JOIN interval_versions v ON v.record_id=m.version_record_id JOIN source_records r ON r.record_id=v.record_id
      WHERE m.iteration_number=(SELECT max(iteration_number) FROM iterations WHERE is_data_release)
      ORDER BY i.well_id,v.top_depth_ft,v.bottom_depth_ft,r.csv_record""",database):
        by_id[row['well_id']][row['kind']].append(row)
    for row in query("SELECT f.*,r.raw_values AS values FROM findings f JOIN source_records r ON r.record_id=f.audit_record_id ORDER BY finding_id",database):by_id[row['well_id']]['findings'].append(row)
    for row in query("SELECT c.*,r.raw_values AS values FROM ground_height_candidates c JOIN source_records r ON r.record_id=c.candidate_id ORDER BY c.well_id,c.candidate_id",database):by_id[row['well_id']]['candidates'].append(row)
    for row in query("SELECT l.*,h.gw_site_id,h.height_ft,h.vertical_reference_raw,r.raw_values AS values FROM well_height_links l JOIN ground_height_sources h USING(height_source_id) JOIN source_records r ON r.record_id=h.height_source_id",database):by_id[row['well_id']]['heights'].append(row)
    for row in query("SELECT m.well_id,m.iteration_number,m.state,m.version_record_id,r.source_id,r.csv_record FROM well_membership m JOIN source_records r ON r.record_id=m.version_record_id ORDER BY m.well_id,m.iteration_number",database):by_id[row['well_id']]['history'].append(row)
    for row in query('SELECT * FROM duplicate_wells ORDER BY removed_well_id',database):
        by_id[row['representative_well_id']]['removed_wells'].append(row)
        by_id[row['removed_well_id']]['representative']=row['representative_well_id']
    data={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'database':database,
          'wells':wells,'working_count':sum(w['state']=='working' for w in wells),'total_count':len(wells)}
    return render(data,output,'PostgreSQL queries; no CSV reads')

def render(data,output,source):
    serialized=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    template=(VERSION/'scripts/map_template.html').read_text()
    template=template.replace('__LEAFLET_CSS__',(BASE_VERSION/'vendor/leaflet.css').read_text())
    template=template.replace('__LEAFLET_JS__',(BASE_VERSION/'vendor/leaflet.js').read_text())
    template=template.replace('__MAP_JS__',(VERSION/'scripts/map.js').read_text()).replace('__DATA__',serialized)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(template)
    write_json(output.with_suffix('.manifest.json'),{'generated_at_utc':datetime.now(timezone.utc).isoformat(),'data_generated_at_utc':data['generated_at_utc'],'source':source,'database':data['database'],'working_wells':data['working_count'],'all_well_ids':len(data['wells']),'html_sha256':digest(output.read_bytes()),'embedded_payload_sha256':digest(serialized.encode()),'snapshot':True,'map_tool_version':'v002','database_tool_version':'v001','external_services':'USGS background tiles load by default; Wells only option works offline; map library embedded locally'})
    print('Map written:',output,'with',len(data['wells']),'well IDs and',data['working_count'],'working wells')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ITERATION/'evidence/maps/well_database_map.html'));parser.add_argument('--database',default='boardman');parser.add_argument('--snapshot',help='Preserve the embedded data of an existing map while updating its presentation')
    args=parser.parse_args();build(args.output,args.database,args.snapshot)
