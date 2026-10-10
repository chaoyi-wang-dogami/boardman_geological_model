(() => {
  const data=JSON.parse(document.getElementById('database-data').textContent);
  const byId=new Map(data.wells.map(w=>[w.well_id,w]));
  const el=id=>document.getElementById(id),scope=el('scope'),view=el('view'),category=el('category'),search=el('search');
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const val=v=>v===null||v===undefined||v===''?'Unavailable':esc(v);
  const categories={numeric:{numeric_complete:['Numeric fields complete','#2d9364'],missing_depth:['Missing completion depth','#cf4c49'],missing_elevation:['Missing elevation','#d68b24'],inconsistent:['Discrepancy to review','#9264b2'],not_audited:['Outside the current audit','#8494a2']},ground:{recorded_linked_site:['Recorded at linked site','#3286b5'],calculated_only:['Calculated candidate only','#d68b24'],missing:['Ground height missing','#cf4c49'],not_audited:['Outside the current audit','#8494a2']}};
  const key=w=>(view.value==='numeric'?w.numeric_category:w.ground_height_category)||'not_audited';
  const inScope=w=>scope.value==='all'||(scope.value==='working'?w.state==='working':w.state!=='working');
  const position=w=>[Number(w.metadata.latitude),Number(w.metadata.longitude)];
  let visible=[],markers=new Map(),selected=null,map=null,points=null,topo=null;
  const rawTable=r=>`<div class="raw"><table><tbody>${Object.entries(r||{}).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${val(v)}</td></tr>`).join('')}</tbody></table></div>`;
  const safeLink=url=>/^https?:\/\//.test(url||'')?`<a href="${esc(url)}" target="_blank" rel="noopener">Open source website</a>`:'';
  function configure(){
    const candidates=data.wells.filter(inScope),counts={};for(const w of candidates)counts[key(w)]=(counts[key(w)]||0)+1;
    category.innerHTML='<option value="all">All categories</option>';
    el('legend').innerHTML='';
    for(const [id,[label,color]] of Object.entries(categories[view.value]))if(counts[id]){
      const option=document.createElement('option');option.value=id;option.textContent=`${label} — ${counts[id]}`;category.appendChild(option);
      el('legend').insertAdjacentHTML('beforeend',`<div><span class="dot" style="background:${color}"></span>${esc(label)}: <strong>${counts[id]}</strong></div>`);
    }
  }
  function intervalTable(w,kind){
    const rows=w[kind];if(!rows.length)return '<p class="muted">No records for this well.</p>';
    return `<table class="interval-table"><thead><tr><th>Top ft</th><th>Bottom ft</th><th>${kind==='stratigraphy'?'Layer':'Rock description'}</th></tr></thead><tbody>${rows.map(r=>{
      const v=r.values,top=kind==='stratigraphy'?v.start_depth:v.from_ft,bottom=kind==='stratigraphy'?v.end_depth:v.to_ft;
      return `<tr><td>${val(top)}</td><td>${val(bottom)}</td><td><details><summary>${esc(kind==='stratigraphy'?v.strat_unit:v.material_raw)}</summary>${rawTable(v)}<p class="source">Interval ID: ${esc(r.interval_id)}<br>Source fingerprint: ${esc(r.source_id)}<br>CSV record: ${r.csv_record}</p></details></td></tr>`;
    }).join('')}</tbody></table>`;
  }
  function show(w){
    selected=w.well_id;const m=w.metadata,a=w.audit||{};
    const status=w.state==='working'?'Current working well':w.state==='deduplicated'?'Archived duplicate':'Archived: no stratigraphy';
    el('details').innerHTML=`<h2>${esc(w.well_id)}</h2><span class="badge">${status}</span><span class="badge">${esc(categories.numeric[w.numeric_category||'not_audited'][0])}</span>
      <p>Site ${val(m.gw_site_id)} · ${val(m.tr_key)}<br>Latitude ${val(m.latitude)} · Longitude ${val(m.longitude)}<br>Reported completion depth: <strong>${val(m.completed_depth_ft)} ft</strong></p>
      ${w.representative?`<p>Surviving representative: <button class="well-link" data-well="${esc(w.representative)}">${esc(w.representative)}</button></p>`:''}
      <h3>Findings (${w.findings.length})</h3>${w.findings.length?w.findings.map(f=>`<div class="issue"><strong>${esc(f.issue_code.replaceAll('_',' '))}</strong><p>${esc(f.description)}</p><details><summary>Finding and source details</summary>${rawTable(f.values)}<p class="source">Finding ID: ${esc(f.finding_id)}<br>Affected database record: ${esc(f.affected_record_id)}<br>Status: ${esc(f.review_status)}</p></details></div>`).join(''):`<p class="muted">${w.audit?'No numeric or interval-sequence discrepancy was flagged.':'This well was outside iteration 3’s audit.'}</p>`}
      <h3>Stratigraphy (${w.stratigraphy.length} intervals)</h3>${intervalTable(w,'stratigraphy')}
      <h3>Lithology (${w.lithology.length} intervals)</h3>${intervalTable(w,'lithology')}
      <h3>Ground-height evidence</h3><p>Calculated candidate: ${val(a.implied_ground_height_min_ft)} ft<br>Saved linked-site height: ${val(a.cached_site_ground_height_ft)} ft<br>Saved site reference: ${val(a.cached_site_vertical_reference)}</p>
      <p class="notice">Calculated candidates and linked-site heights have not been adopted. The interval elevation reference remains unverified. The map uses the existing longitude/latitude display assumption.</p>
      ${w.heights.map(h=>`<details><summary>Saved site evidence · ${val(h.height_ft)} ft</summary>${rawTable(h.values)}<p>Coordinates match this well: ${h.coordinate_match?'Yes':'No'}</p><p>Adoption: ${esc(h.adoption_status)}</p></details>`).join('')}
      ${w.candidates.length?`<details><summary>All candidate calculations (${w.candidates.length})</summary><table><thead><tr><th>Endpoint</th><th>Depth ft</th><th>Elevation ft</th><th>Candidate ft</th></tr></thead><tbody>${w.candidates.map(c=>`<tr><td>${esc(c.endpoint)}</td><td>${val(c.values.depth_raw)}</td><td>${val(c.values.elevation_raw)}</td><td>${val(c.values.implied_ground_height_ft)}</td></tr>`).join('')}</tbody></table></details>`:''}
      <h3>Iteration history</h3><table><thead><tr><th>Iteration</th><th>Membership</th></tr></thead><tbody>${w.history.map(h=>`<tr><td>${h.iteration_number}${h.iteration_number===3?' (audit)':''}</td><td>${esc(h.state.replaceAll('_',' '))}</td></tr>`).join('')}</tbody></table>
      ${w.removed_wells.length?`<h3>Archived under this representative (${w.removed_wells.length})</h3><p class="muted">Each original well retains its own lithology and metadata.</p>${w.removed_wells.map(d=>`<p><button class="well-link" data-well="${esc(d.removed_well_id)}">${esc(d.removed_well_id)}</button> · ${Number(d.distance_m).toFixed(1)} m</p>`).join('')}`:''}
      <details><summary>Full recorded well metadata</summary>${rawTable(m)}<p class="source">Database record: ${esc(w.record_id)}<br>Source fingerprint: ${esc(w.source_id)}<br>CSV record: ${w.csv_record}</p>${safeLink(m.detail_url)}</details>
      ${w.audit?`<details><summary>Full completeness audit</summary>${rawTable(a)}</details>`:''}`;
    el('details').scrollTop=0;
    el('details').querySelectorAll('[data-well]').forEach(b=>b.addEventListener('click',()=>{
      const target=byId.get(b.dataset.well);scope.value=target.state==='working'?'working':'archive';search.value=target.well_id;configure();render();show(target);fit();
    }));
    if(map&&markers.has(w.well_id)){map.setView(position(w),Math.max(map.getZoom(),12),{animate:false});markers.get(w.well_id).openTooltip();}
  }
  function fit(){if(map&&visible.length)map.fitBounds(L.latLngBounds(visible.map(position)),{padding:[25,25],maxZoom:16,animate:false});}
  function render(){
    const q=search.value.trim().toLowerCase();visible=data.wells.filter(w=>inScope(w)&&(category.value==='all'||key(w)===category.value)&&(!q||[w.well_id,w.metadata.gw_site_id,w.metadata.tr_key].some(v=>String(v||'').toLowerCase().includes(q))));
    if(points)points.clearLayers();markers=new Map();
    for(const w of visible)if(map&&w.metadata.latitude!==''&&w.metadata.longitude!==''){
      const marker=L.circleMarker(position(w),{radius:scope.value==='working'?6:4,color:'#fff',weight:1,fillColor:categories[view.value][key(w)][1],fillOpacity:.9}).bindTooltip(w.well_id).on('click',()=>show(w)).addTo(points);markers.set(w.well_id,marker);
    }
    el('visible-count').textContent=`${visible.length} of ${data.wells.filter(inScope).length} well IDs shown`;
    el('well-list').replaceChildren();for(const w of visible.slice(0,80)){
      const b=document.createElement('button');b.innerHTML=`${esc(w.well_id)}<small>${esc(categories[view.value][key(w)][0])}</small>`;b.addEventListener('click',()=>show(w));el('well-list').appendChild(b);
    }
    el('list-note').textContent=visible.length>80?'The list shows the first 80 matches; all matching wells are plotted.':visible.length?'':'No wells match.';
  }
  if(window.L){
    map=L.map('map',{preferCanvas:true,minZoom:0,maxZoom:19});points=L.layerGroup().addTo(map);L.control.scale({imperial:false,maxWidth:150}).addTo(map);
    topo=L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',{maxNativeZoom:16,maxZoom:19,attribution:'USGS The National Map'});
    topo.on('tileerror',()=>el('tile-status').textContent='Background unavailable; well points and details still work.');
    el('background').addEventListener('change',()=>{if(el('background').value==='none'){map.removeLayer(topo);el('tile-status').textContent='Wells only; no internet connection needed.';}else{topo.addTo(map);el('tile-status').textContent='USGS background requires internet access.';}});
  }else el('library-error').style.display='block';
  scope.addEventListener('change',()=>{configure();render();fit();});view.addEventListener('change',()=>{configure();render();});category.addEventListener('change',()=>{render();fit();});search.addEventListener('input',render);
  el('fit').addEventListener('click',fit);el('reset').addEventListener('click',()=>{scope.value='working';view.value='numeric';search.value='';configure();render();fit();});
  configure();render();fit();
  // Small read-only inspection surface for reproducible browser checks.
  window.boardmanMap={get visibleCount(){return visible.length},get selectedWell(){return selected},selectWell:id=>show(byId.get(id))};
})();
