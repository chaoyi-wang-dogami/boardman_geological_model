"""Round-trip values, evidence bytes, release membership, and known deficiencies."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from common import ANALYSIS, ITERATION, REPO, csv_rows, digest, query, sql, write_json

def verify(database='boardman',output=None):
    checks=[]
    def check(name,actual,expected):
        ok=actual==expected
        checks.append({'check':name,'passed':ok,'actual':actual,'expected':expected})
        if not ok:raise AssertionError(f'{name}: {actual!r} != {expected!r}')
    check('original well IDs',query('SELECT count(*) n FROM wells',database)[0]['n'],7402)
    check('original interval occurrences',query('SELECT kind,count(*) n FROM intervals GROUP BY kind ORDER BY kind',database),[{'kind':'lithology','n':15586},{'kind':'stratigraphy','n':1854}])
    for iteration in [0,1,2]:
        directory=next(ANALYSIS.glob(f'iter{iteration}_*'))
        for filename,kind in [('boardman_wells_summary.csv','well'),('boardman_wells_stratigraphy.csv','stratigraphy'),('boardman_wells_lithology.csv','lithology')]:
            original=csv_rows(directory/'outputs'/filename)
            if kind=='well':statement=f"SELECT r.raw_values FROM well_membership m JOIN source_records r ON r.record_id=m.version_record_id WHERE m.iteration_number={iteration} AND m.state='working'"
            else:statement=f"SELECT r.raw_values FROM interval_membership m JOIN intervals i USING(interval_id) JOIN source_records r ON r.record_id=m.version_record_id WHERE m.iteration_number={iteration} AND m.state='working' AND i.kind='{kind}'"
            retrieved=[r['raw_values'] for r in query(statement,database)]
            canonical=lambda rows:Counter(json.dumps(r,sort_keys=True) for r in rows)
            check(f'iteration {iteration} {kind} values and occurrence counts',canonical(retrieved)==canonical(original),True)
    check('working well count',query('SELECT count(*) n FROM working_wells',database)[0]['n'],332)
    check('working interval counts',query('SELECT kind,count(*) n FROM working_intervals GROUP BY kind ORDER BY kind',database),[{'kind':'lithology','n':1215},{'kind':'stratigraphy','n':1427}])
    # Exact original strings and repeated occurrences survive every CSV import.
    locations=query("SELECT path,source_id FROM source_locations WHERE path LIKE '%.csv' ORDER BY path",database)
    checked=set();total=0
    for location in locations:
        sha=location['source_id']
        if sha in checked:continue
        checked.add(sha)
        retrieved=query(f"SELECT raw_values FROM source_records WHERE source_id='{sha}' ORDER BY csv_record",database)
        source=csv_rows(REPO/location['path'])
        if [r['raw_values'] for r in retrieved]!=source:raise AssertionError('CSV value round trip failed: '+location['path'])
        total+=len(source)
    check('all unique CSV files round trip',len(checked),len(checked))
    check('CSV records verified',query('SELECT count(*) n FROM source_records',database)[0]['n'],total)
    objects=query("SELECT source_id,size_bytes,encode(content_gzip,'hex') content FROM source_files",database)
    for obj in objects:
        raw=gzip.decompress(bytes.fromhex(obj['content']))
        if digest(raw)!=obj['source_id'] or len(raw)!=obj['size_bytes']:raise AssertionError('Stored source bytes differ')
    check('stored source files reconstruct exactly',len(objects),len(objects))
    files=csv_rows(ITERATION/'inputs/input_files.csv')
    check('input paths and hashes unchanged',all(digest((REPO/r['path']).read_bytes())==r['sha256'] for r in files),True)
    check('all foreign keys validated',query("SELECT count(*) n FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='boardman' AND c.contype='f' AND NOT c.convalidated",database)[0]['n'],0)
    check('well membership identity matches',query('SELECT count(*) n FROM well_membership m JOIN well_versions v ON v.record_id=m.version_record_id WHERE m.well_id<>v.well_id',database)[0]['n'],0)
    check('interval membership identity matches',query('SELECT count(*) n FROM interval_membership m JOIN interval_versions v ON v.record_id=m.version_record_id WHERE m.interval_id<>v.interval_id',database)[0]['n'],0)
    check('duplicate survivor links',query('SELECT count(*) n FROM duplicate_wells',database)[0]['n'],91)
    check('duplicate interval links',query('SELECT count(*) n FROM duplicate_intervals',database)[0]['n'],427)
    check('current archived well states',query('SELECT state,count(*) n FROM well_membership WHERE iteration_number=4 GROUP BY state ORDER BY state',database),[{'state':'deduplicated','n':91},{'state':'excluded_no_stratigraphy','n':6979},{'state':'working','n':332}])
    check('findings retained',query('SELECT count(*) n FROM findings',database)[0]['n'],163)
    check('no findings silently resolved',query("SELECT count(*) n FROM findings WHERE review_status<>'open'",database)[0]['n'],0)
    check('ground candidates not adopted',query("SELECT count(*) n FROM ground_height_candidates WHERE adoption_status='candidate_not_adopted'",database)[0]['n'],2844)
    check('recorded height sources',query('SELECT count(*) n FROM ground_height_sources',database)[0]['n'],35)
    check('recorded height well associations',query('SELECT count(*) n FROM well_height_links',database)[0]['n'],36)
    check('numeric categories',query('SELECT numeric_category,count(*) n FROM working_wells GROUP BY numeric_category ORDER BY numeric_category',database),[{'numeric_category':'inconsistent','n':66},{'numeric_category':'missing_depth','n':19},{'numeric_category':'missing_elevation','n':1},{'numeric_category':'numeric_complete','n':246}])
    check('working geometries',query('SELECT count(*) n FROM working_wells WHERE location IS NOT NULL AND ST_X(location)=longitude::float8 AND ST_Y(location)=latitude::float8',database)[0]['n'],332)
    check('five affected wells retained',query("SELECT count(*) n FROM working_wells WHERE well_id IN ('UMAT_0005342','UMAT_0005858','UMAT_0005859','MORR_0001751','MORR_0052638')",database)[0]['n'],5)
    check('zero-thickness lithology remains',query("SELECT count(*) n FROM working_intervals WHERE well_id='MORR_0052638' AND kind='lithology' AND top_depth_ft=1076 AND bottom_depth_ft=1076",database)[0]['n'],1)
    check('no geological value changes',query('SELECT count(*) n FROM changes',database)[0]['n'],0)
    # This expected failure verifies the preservation trigger without changing data.
    try:sql("BEGIN; UPDATE wells SET well_id=well_id WHERE well_id='MORR_0001751'; ROLLBACK;",database)
    except RuntimeError as error:check('historical update blocked','Historical records are append-only' in str(error),True)
    else:raise AssertionError('History protection did not reject update')
    result={'database':database,'passed':True,'checks':checks,'source_files_verified':len(objects),'source_records_verified':total}
    write_json(output or ITERATION/'audit/checks.json',result)
    print(f'{len(checks)} checks passed for {database}; {total} original CSV records verified')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--database',default='boardman');parser.add_argument('--output')
    args=parser.parse_args();verify(args.database,args.output)
