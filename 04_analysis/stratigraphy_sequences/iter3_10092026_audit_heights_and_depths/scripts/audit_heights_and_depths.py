"""Read-only completeness audit; writes evidence, never a corrected well release."""
import csv
import gzip
import hashlib
import html
import json
import math
import platform
import re
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

ITER = Path(__file__).resolve().parent.parent
BASE = ITER.parent
REPO = BASE.parents[1]
PARENT = BASE / "iter2_10092026_keep_stratigraphy_wells"
PHASE = ITER / "audit/phase1_completeness"
CACHE = REPO / "07_commercial_eval/rockworks/input/35_paired_spread/evidence"
TOL = Decimal("0.01")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    with p.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def csv_write(p, rows, fields=None):
    with p.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def num(value):
    try:
        n = Decimal(value.strip())
        return n if n.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def span(text, id_suffix):
    match = re.search(r'<span[^>]*id="[^"]*'+re.escape(id_suffix)+r'"[^>]*>(.*?)</span>', text, re.S)
    return html.unescape(re.sub(r"<[^>]*>", "", match[1])).strip() if match else ""


def main():
    if PHASE.exists() or (ITER/"manifest.json").exists():
        raise SystemExit("Existing audit detected. Refusing to overwrite evidence.")
    started = datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds")
    parent = json.loads((PARENT/"manifest.json").read_text())
    assert parent["status"] == "Complete"
    inputs = []
    tables = {}
    for kind in ("summary", "stratigraphy", "lithology"):
        p = PARENT/"outputs"/f"boardman_wells_{kind}.csv"
        expected = next(e for e in parent["outputs"] if e["path"] == str(p.relative_to(REPO)))
        assert sha(p) == expected["sha256"]
        tables[kind] = read(p)
        inputs.append({**expected, "file_id":"input_"+kind, "role":"source", "parent_iteration":PARENT.name})
    parent_sha = sha(PARENT/"manifest.json")
    summary = tables["summary"][1]
    wells = {r["well_id"]:r for r in summary}
    assert len(wells)==len(summary)==332
    by = {k:defaultdict(list) for k in ("stratigraphy", "lithology")}
    for kind in by:
        for ordinal, row in enumerate(tables[kind][1], 2):
            assert row["well_id"] in wells
            by[kind][row["well_id"]].append((ordinal,row))
    assert set(by["stratigraphy"])==set(wells)
    metadata = {}
    evidence_inputs = []
    for p in sorted(CACHE.glob("gwis_*.json")):
        d = json.loads(p.read_text())
        if d["gw_site_id"] not in {w["gw_site_id"] for w in summary}:
            continue
        page = p.with_suffix(".html.gz")
        raw = gzip.decompress(page.read_bytes())
        assert hashlib.sha256(raw).hexdigest()==d["page_sha256"]
        text = raw.decode("utf-8")
        assert span(text,"lb_lsd_elevation")==d["source_ground_elevation_ft"]
        assert span(text,"lb_elevation_datum")==d["source_vertical_datum"]
        metadata[d["gw_site_id"]] = {**d,"site_latitude":span(text,"lb_latitude_dec"),
            "site_longitude":span(text,"lb_longitude_dec"),"metadata_path":str(p.relative_to(REPO)),"metadata_sha256":sha(p),
            "page_path":str(page.relative_to(REPO)),"page_compressed_sha256":sha(page)}
        for source in (p,page):
            evidence_inputs.append({"file_id":"evidence_"+source.name,"path_base":"repository_root","path":str(source.relative_to(REPO)),
                                   "sha256":sha(source),"size_bytes":source.stat().st_size,"role":"existing_source_evidence"})
    for folder in (PHASE,ITER/"inputs",ITER/"evidence/workflow"):
        folder.mkdir(parents=True,exist_ok=True)
    (ITER/"inputs/parent_manifest_snapshot.json").write_bytes((PARENT/"manifest.json").read_bytes())
    inputs += evidence_inputs
    csv_write(ITER/"inputs/input_files.csv",[{k:e.get(k,"") for k in ("file_id","path_base","path","role","sha256","size_bytes","row_count","parent_iteration")} for e in inputs])
    findings, candidates, completeness = [], [], []
    issues = defaultdict(set)
    depth_bad, elev_bad, mismatch = set(),set(),set()
    totals = Counter()

    def flag(well,kind,record,code,field,value,detail,level="review"):
        index = {"summary":0,"stratigraphy":1,"lithology":2}[kind]
        findings.append({"finding_id":f"F{len(findings)+1:05d}","well_id":well,"issue_code":code,"field":field,"raw_value":value,
                         "description":detail,"level":level,"source_file":inputs[index]["path"],"source_sha256":inputs[index]["sha256"],"source_record":record})
        issues[well].add(code)

    for ordinal,w in enumerate(summary,2):
        well=w["well_id"];rows=by["stratigraphy"][well];lith=by["lithology"][well]
        completed=num(w["completed_depth_ft"])
        if completed is None:
            depth_bad.add(well)
            flag(well,"summary",ordinal,"missing_completion_depth" if not w["completed_depth_ft"].strip() else "invalid_completion_depth",
                 "completed_depth_ft",w["completed_depth_ft"],"The well's recorded completion depth is unavailable.","missing")
        elif completed<0:
            depth_bad.add(well);flag(well,"summary",ordinal,"negative_completion_depth","completed_depth_ft",w["completed_depth_ft"],"Negative under the repository positive-down depth convention.")
        missing_d=missing_z=0
        implied=[]
        for kind,records,fields in (("stratigraphy",rows,("start_depth","end_depth","depth_thickness")),("lithology",lith,("from_ft","to_ft","thickness_ft"))):
            for record,r in records:
                a,b,t=[num(r[f]) for f in fields]
                for f,v in zip(fields[:2],(a,b)):
                    if v is None or v<0:
                        depth_bad.add(well);missing_d+=1
                        flag(well,kind,record,"missing_or_invalid_interval_depth",f,r[f],"Missing, nonfinite, nonnumeric, or negative interval depth.","missing")
                if a is not None and b is not None:
                    if b<=a:
                        mismatch.add(well);flag(well,kind,record,"nonpositive_interval_thickness",fields[1],r[fields[1]],"Bottom is not deeper than top.")
                    if t is None or abs((b-a)-t)>TOL:
                        mismatch.add(well);flag(well,kind,record,"thickness_mismatch",fields[2],r[fields[2]],"Recorded thickness differs from bottom minus top by more than 0.01 ft, or is unavailable.")
                    if completed is not None and b>completed+TOL:
                        mismatch.add(well);flag(well,kind,record,"interval_below_recorded_completion",fields[1],r[fields[1]],f"Interval bottom exceeds summary completion depth {w['completed_depth_ft']} ft. Linked site interpretation and drilling report may describe different histories.")
                if r.get("completed_depth_ft","")!=w["completed_depth_ft"]:
                    mismatch.add(well);flag(well,kind,record,"repeated_completion_depth_disagrees","completed_depth_ft",r.get("completed_depth_ft",""),"Repeated completion depth differs from the well summary.")
                if kind=="stratigraphy":
                    za,zb=num(r["start_depth_elev"]),num(r["end_depth_elev"])
                    for d,z,df,zf in ((a,za,"start_depth","start_depth_elev"),(b,zb,"end_depth","end_depth_elev")):
                        if z is None:
                            elev_bad.add(well);missing_z+=1
                            flag(well,kind,record,"missing_or_invalid_interval_elevation",zf,r[zf],"Endpoint elevation is unavailable; no value was inferred.","missing")
                        elif d is not None:
                            implied.append(d+z)
                            candidates.append({"well_id":well,"endpoint":zf,"depth_raw":r[df],"elevation_raw":r[zf],"implied_ground_height_ft":str(d+z),
                                "status":"calculated_candidate_not_adopted","assumption":"depth zero is ground surface; values use the repository feet convention",
                                "source_file":inputs[1]["path"],"source_sha256":inputs[1]["sha256"],"source_record":record})
                    if None not in (a,b,za,zb) and abs((za-zb)-(b-a))>TOL:
                        mismatch.add(well);flag(well,kind,record,"depth_elevation_thickness_disagrees","start_depth_elev/end_depth_elev",r["start_depth_elev"]+" / "+r["end_depth_elev"],"Elevation drop and depth thickness disagree by more than 0.01 ft.")
        if implied and max(implied)-min(implied)>TOL:
            mismatch.add(well);flag(well,"summary",ordinal,"implied_ground_height_inconsistent","computed_offsets",str(max(implied)-min(implied)),"Different endpoints imply ground heights differing by more than 0.01 ft; no height adopted.")
        # Sequence holes/overlaps are factual depth findings, not geological corrections.
        ordered=sorted([(rec,r) for rec,r in rows if num(r['start_depth']) is not None and num(r['end_depth']) is not None],key=lambda item:num(item[1]['start_depth']))
        deepest=None
        for rec,r in ordered:
            a,b=num(r['start_depth']),num(r['end_depth'])
            if deepest is not None and abs(a-deepest)>TOL:
                code='stratigraphy_depth_gap' if a>deepest else 'stratigraphy_depth_overlap'
                mismatch.add(well);flag(well,'stratigraphy',rec,code,'start_depth',r['start_depth'],f"Top differs from the deepest previous interval bottom {deepest} ft; separation {a-deepest} ft. No boundary changed.")
            deepest=b if deepest is None else max(deepest,b)
        meta=metadata.get(w['gw_site_id'])
        ground='recorded_linked_site' if meta else 'calculated_only' if implied else 'missing'
        klass='missing_depth' if well in depth_bad else 'missing_elevation' if well in elev_bad else 'inconsistent' if well in mismatch else 'numeric_complete'
        min_g,max_g=(str(min(implied)),str(max(implied))) if implied else ('','')
        source_delta= str(num(meta['source_ground_elevation_ft'])-min(implied)) if meta and implied else ''
        completeness.append({"well_id":well,"gw_site_id":w['gw_site_id'],"tr_key":w['tr_key'],"latitude":w['latitude'],"longitude":w['longitude'],
            "numeric_category":klass,"all_issue_codes_json":json.dumps(sorted(issues[well])),"completed_depth_ft_raw":w['completed_depth_ft'],
            "completion_depth_present":completed is not None,"stratigraphy_intervals":len(rows),"lithology_intervals":len(lith),
            "missing_or_invalid_interval_depth_fields":missing_d,"missing_or_invalid_elevation_fields":missing_z,
            "implied_ground_height_min_ft":min_g,"implied_ground_height_max_ft":max_g,"implied_ground_height_spread_ft":str(max(implied)-min(implied)) if implied else '',
            "ground_height_category":ground,"core_ground_height_field_present":False,"cached_site_ground_height_ft":meta['source_ground_elevation_ft'] if meta else '',
            "cached_site_vertical_reference":meta['source_vertical_datum'] if meta else '',"cached_site_latitude":meta['site_latitude'] if meta else '',
            "cached_site_longitude":meta['site_longitude'] if meta else '',"cached_site_coordinates_match_well":bool(meta and num(meta['site_latitude'])==num(w['latitude']) and num(meta['site_longitude'])==num(w['longitude'])),
            "cached_minus_implied_ground_height_ft":source_delta,"cached_source_metadata":meta['metadata_path'] if meta else '',
            "cached_source_metadata_sha256":meta['metadata_sha256'] if meta else '',"cached_source_url":meta['source_url'] if meta else '',
            "interval_vertical_reference":"not_recorded_in_core_csv","depth_units_status":"feet_repository_convention","depth_zero_status":"ground_surface_assumed_not_independently_verified",
            "summary_source_file":inputs[0]['path'],"summary_source_sha256":inputs[0]['sha256'],"summary_source_record":ordinal})
    csv_write(PHASE/'well_completeness.csv',completeness)
    csv_write(PHASE/'interval_findings.csv',findings)
    csv_write(PHASE/'ground_height_candidates.csv',candidates)
    cached_rows=[{k:d[k] for k in ('gw_site_id','source_ground_elevation_ft','source_vertical_datum','source_elevation_method','site_latitude','site_longitude','metadata_path','metadata_sha256','page_path','page_compressed_sha256','source_url','retrieved_at_utc')} for d in metadata.values()]
    csv_write(PHASE/'cached_ground_height_sources.csv',cached_rows)
    counts={"wells":len(summary),"stratigraphy_intervals":len(tables['stratigraphy'][1]),"lithology_intervals":len(tables['lithology'][1]),
        "numeric_categories":dict(Counter(r['numeric_category'] for r in completeness)),"ground_height_categories":dict(Counter(r['ground_height_category'] for r in completeness)),
        "missing_completion_depth_wells":sum(num(w['completed_depth_ft']) is None for w in summary),
        "missing_elevation_wells":len(elev_bad),"wells_with_flagged_mismatches":len(mismatch),
        "issue_counts":dict(Counter(f['issue_code'] for f in findings)),"issue_well_counts":{code:len({f['well_id'] for f in findings if f['issue_code']==code}) for code in sorted({f['issue_code'] for f in findings})},
        "implied_ground_height_available_wells":sum(bool(r['implied_ground_height_min_ft']) for r in completeness),
        "cached_ground_height_sites":len(metadata),"cached_ground_height_wells":sum(bool(r['cached_source_metadata']) for r in completeness),
        "cached_source_coordinates_match_wells":sum(r['cached_site_coordinates_match_well'] for r in completeness),
        "interval_vertical_reference_not_recorded_wells":332,"core_explicit_ground_height_fields":0,
        "ground_height_candidate_occurrences":len(candidates),"finding_occurrences":len(findings)}
    assert len(completeness)==332 and len({r['well_id'] for r in completeness})==332
    assert sum(counts['numeric_categories'].values())==sum(counts['ground_height_categories'].values())==332
    assert all(sha(REPO/e['path'])==e['sha256'] for e in inputs)
    assert sha(PARENT/'manifest.json')==parent_sha
    for filename,expected in (('well_completeness.csv',completeness),('interval_findings.csv',findings),('ground_height_candidates.csv',candidates)):
        actual=read(PHASE/filename)[1]
        assert actual==[{k:str(v) for k,v in row.items()} for row in expected]
    checks={'result':'pass','counts':counts,'arithmetic_tolerance_ft':str(TOL),'checks':{k:'pass' for k in ('parent_output_hashes','well_ids_unique','interval_ids_join_summary','one_audit_row_per_well','exclusive_map_category_totals','csv_read_back','cached_pages_match_saved_hashes_and_ground_fields','all_source_hashes_unchanged','parent_manifest_unchanged')}}
    dump(PHASE/'checks.json',checks)
    dump(PHASE/'classification_rules.json',{'numeric_priority':['missing_depth','missing_elevation','inconsistent','numeric_complete'],
        'numeric_complete':'Required completion and interval depths/elevations present, with no flagged numeric/sequence discrepancy. Does not establish a verified height reference.',
        'ground_height_priority':['recorded_linked_site','calculated_only','missing'],
        'recorded_linked_site':'Existing cached ground height linked through gw_site_id; not automatically a verified height for this well or its interval elevations.',
        'calculated_only':'Depth plus elevation yields an implied height, assuming ground-based depths and the repository feet convention; not adopted.',
        'arithmetic_tolerance_ft':str(TOL),'zero_is_missing':False,'negative_elevation_is_invalid':False,
        'sentinel_policy':'No undocumented finite number is silently treated as a missing-value code.','reference_policy':'Core CSVs lack interval height-reference fields. Cached site reference strings remain separate and are not assigned to interval elevations.'})
    for name in ('SOP.md','ACTION_PLAN.md','DATA_FORMAT.md'):
        (ITER/'evidence/workflow'/name).write_bytes((BASE/name).read_bytes())
    manifest=json.loads((BASE/'templates/manifest.example.json').read_text());manifest.pop('template_only')
    manifest.update(iteration_number=3,directory_name=ITER.name,purpose='Audit elevation, ground height, and depth completeness before deciding on any modifications.',
        status='In progress',started_local=started,parent_iterations=[PARENT.name],inputs=inputs,outputs=[],
        software=[{'name':'Python','version':platform.python_version(),'libraries':'Standard library; plots use Matplotlib'}],
        method_files=[{'path_base':'iteration_directory','path':'scripts/audit_heights_and_depths.py','sha256':sha(Path(__file__))}],
        workflow_documents=[{'path_base':'iteration_directory','path':'evidence/workflow/'+n,'sha256':sha(ITER/'evidence/workflow'/n)} for n in ('SOP.md','ACTION_PLAN.md','DATA_FORMAT.md')],
        decision_ids=['ITER3_READ_ONLY_AUDIT'],open_issue_ids=['ITER3_ACTIONS_NOT_SELECTED'],verification_summary=checks,
        notes='Audit phase only. No working CSV release or data modifications. Candidate ground heights are audit evidence, not adopted values. Iteration 2 remains the current working data. Keep iteration 3 open pending action decisions.')
    dump(ITER/'manifest.json',manifest)
    dump(PHASE/'manifest.json',{'phase':'Read-only audit','status':'Complete','completed_local':datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(timespec='seconds'),
        'inputs':inputs,'parent_manifest_sha256':parent_sha,'outputs':[{'path':p.name,'sha256':sha(p)} for p in sorted(PHASE.iterdir()) if p.name!='manifest.json'],'counts':counts,'data_modified':False})
    print(json.dumps(counts,indent=2))


if __name__=='__main__':
    main()
