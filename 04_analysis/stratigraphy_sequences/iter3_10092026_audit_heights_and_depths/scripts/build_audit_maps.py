"""Generate audit maps from the frozen read-only findings, into a new directory."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from map_geometry import extent, position, scale_bar

ITER=Path(__file__).resolve().parent.parent
BASE=ITER.parent
REPO=BASE.parents[1]
PHASE=ITER/'audit/phase1_completeness'
CATEGORIES={
 'numeric':{
  'numeric_complete':{'label':'Numeric fields complete','color':'#238443'},
  'missing_elevation':{'label':'Missing interval elevations','color':'#e18a16'},
  'missing_depth':{'label':'Missing or invalid depths','color':'#c9343d'},
  'inconsistent':{'label':'Discrepancy to review','color':'#8451b5'}},
 'ground':{
  'recorded_linked_site':{'label':'Recorded at linked site','color':'#2463a6'},
  'calculated_only':{'label':'Calculated candidate only','color':'#e18a16'},
  'missing':{'label':'No ground height available','color':'#c9343d'}},
 'reference':{
  'site_reference_available':{'label':'Saved site reference available','color':'#2463a6'},
  'not_found':{'label':'No saved site reference found','color':'#88949b'}}}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def dump(p,value):p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args();out=args.output_dir.resolve()
 canonical=ITER/'evidence/plots/completeness'
 if out.exists():raise SystemExit('Output already exists. Refusing to overwrite audit maps.')
 if out.is_relative_to(BASE) and out!=canonical:raise SystemExit('Only the iteration 3 audit map directory is allowed inside the workflow.')
 source_paths=[PHASE/n for n in ('well_completeness.csv','interval_findings.csv','checks.json','classification_rules.json')]
 phase=json.loads((PHASE/'manifest.json').read_text())
 for p in source_paths:assert sha(p)==next(e['sha256'] for e in phase['outputs'] if e['path']==p.name)
 inputs={p:sha(p) for p in source_paths}
 wells=read(source_paths[0]);findings=read(source_paths[1]);checks=json.loads(source_paths[2].read_text())
 assert len(wells)==len({w['well_id'] for w in wells})==332
 by=defaultdict(list)
 for f in findings:by[f['well_id']].append(f)
 for w in wells:
  w['findings']=by[w['well_id']];position(w)
 assert dict(Counter(w['numeric_category'] for w in wells))==checks['counts']['numeric_categories']
 bounds=extent(wells,.12);out.mkdir(parents=True)
 fig,axes=plt.subplots(1,2,figsize=(16,8),facecolor='#fbfaf6')
 for ax,view,column,title in zip(axes,('numeric','ground'),('numeric_category','ground_height_category'),('Depth/elevation completeness','Ground-height information')):
  ax.set_facecolor('#f1f4f3');handles=[]
  for key,item in CATEGORIES[view].items():
   rows=[w for w in wells if w[column]==key]
   ax.scatter([position(w)[0] for w in rows],[position(w)[1] for w in rows],s=30,color=item['color'],edgecolors='white',linewidths=.4,zorder=3)
   handles.append(Line2D([],[],marker='o',linestyle='',color=item['color'],label=f"{item['label']}: {len(rows)}"))
  ax.set_xlim(bounds[:2]);ax.set_ylim(bounds[2:]);ax.set_aspect(1/__import__('math').cos(__import__('math').radians((bounds[2]+bounds[3])/2)))
  ax.set_xlabel('Longitude (degrees)');ax.set_ylabel('Latitude (degrees)');ax.grid(alpha=.2);ax.set_title(title,loc='left',fontsize=14)
  scale_bar(ax,bounds,5000);ax.text(.96,.94,'N ↑',transform=ax.transAxes,ha='right',fontsize=12)
  ax.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,-.16),frameon=False,ncol=2,fontsize=10)
  w=next(w for w in wells if w['numeric_category']=='missing_elevation');x,y=position(w)
  ax.annotate(w['well_id'],(x,y),xytext=(10,-18),textcoords='offset points',fontsize=8,color='#253345',arrowprops={'arrowstyle':'-','linewidth':.7})
 fig.suptitle('Boardman · iteration 3 depth and elevation audit',x=.06,ha='left',fontsize=20,y=.98)
 fig.text(.06,.93,'332 well IDs · Audit evidence only · All iteration 2 data preserved',fontsize=12,color='#536174')
 fig.text(.06,.025,'Green means numeric completeness; it does not confirm geological reliability or an elevation reference.\n'
  'Calculated heights are candidates only. Saved heights belong to linked sites. All 332 interval height references remain unrecorded in the core CSVs.',fontsize=10,color='#536174')
 fig.subplots_adjust(left=.06,right=.98,top=.86,bottom=.28,wspace=.20)
 fig.savefig(out/'audit_completeness.png',dpi=180,facecolor=fig.get_facecolor());fig.savefig(out/'audit_completeness.pdf',facecolor=fig.get_facecolor());plt.close(fig)
 data={'wells':wells,'categories':CATEGORIES,'counts':checks['counts']};dump(out/'audit_locations.json',data)
 dump(out/'audit_locations.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Point','coordinates':list(position(w))},'properties':{k:w[k] for k in ('well_id','gw_site_id','numeric_category','ground_height_category','cached_site_vertical_reference')}} for w in wells]})
 script=Path(__file__).resolve().parent
 page=(script/'audit_map_template.html').read_text().replace('__AUDIT_DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c')).replace('__MAP_JS__',(script/'audit_map.js').read_text())
 (out/'audit_map.html').write_text(page,encoding='utf-8')
 (out/'README.md').write_text('''# Iteration 3 completeness maps

Open the [interactive map](audit_map.html), [static PNG](audit_completeness.png), or [PDF](audit_completeness.pdf).

Both static panels use the same bounds and a 5 km scale. Green is numeric completeness, orange missing elevations, red missing/invalid depths, and purple a discrepancy to review. Numeric categories are exclusive, in priority order: depth deficiency, elevation deficiency, discrepancy, complete. Every well's full issue list remains available in the interactive popup and audit CSV.

The second panel shows ground-height information: recorded at a linked site, calculated candidate only, or missing. Recorded site heights are existing cached evidence, not automatically adopted well heights. Calculated candidates assume depth zero at ground and the repository feet convention. No ground height or interval height reference was assigned to the working data.

The interactive map additionally offers a saved site height-reference view, category filters, search, popups with all source-record findings, a distance scale, and USGS / Wells only background options. All 332 core interval height references remain unrecorded; the site-reference view shows available site evidence, not verified interval references. Six linked well coordinates differ from the saved site coordinates. Popup values show those associations separately.

The first 80 filtered matches appear in the well list; all matching points are plotted. Data are embedded in HTML. Leaflet 1.9.4 loads from a CDN; the background uses USGS The National Map. Internet is needed to load those services. Failed tiles leave the well controls usable, and failure to load Leaflet leaves the local static PNG available.

Files were generated by `scripts/build_audit_maps.py` from the phase 1 audit tables. Reproduce into a new external directory:

```bash
python3 04_analysis/stratigraphy_sequences/iter3_10092026_audit_heights_and_depths/scripts/build_audit_maps.py --output-dir /tmp/boardman_iter3_audit_preview
```

Existing output directories are refused. Source latitude/longitude are shown as recorded; the original coordinate reference is not independently verified. Scales use spherical distance at the bar latitude. [manifest.json](manifest.json) records inputs, generation sources, output hashes, colors, and settings. [audit_locations.geojson](audit_locations.geojson) contains one feature per well ID. No data modifications were performed.
''',encoding='utf-8')
 assert all(sha(p)==h for p,h in inputs.items())
 dump(out/'manifest.json',{'purpose':'Read-only audit maps','inputs':[{'path_base':'repository_root','path':str(p.relative_to(REPO)),'sha256':h} for p,h in inputs.items()],
  'sources':[{'path_base':'repository_root','path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in (Path(__file__).resolve(),script/'map_geometry.py',script/'audit_map.js',script/'audit_map_template.html')],
  'outputs':[{'path':p.name,'sha256':sha(p)} for p in sorted(out.iterdir())],'categories':CATEGORIES,'bounds_lon_lat':bounds,'scale_bar_metres':5000,
  'software':{'matplotlib':matplotlib.__version__,'leaflet':'1.9.4'},'data_modified':False,'checks':{'well_count':'pass','category_counts_match_audit':'pass','coordinates_valid':'pass','source_hashes_unchanged':'pass'}})
 print(json.dumps(checks['counts']['numeric_categories'],indent=2))


if __name__=='__main__':main()
