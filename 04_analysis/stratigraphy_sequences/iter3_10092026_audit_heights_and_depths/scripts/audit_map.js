(() => {
  const data=JSON.parse(document.getElementById('audit-data').textContent);
  const view=document.getElementById('view'),category=document.getElementById('category'),search=document.getElementById('search'),background=document.getElementById('background'),status=document.getElementById('background-status');
  const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const value=(w,key)=>w[key]===''?'Unavailable':esc(w[key]);
  const key=w=>view.value==='numeric'?w.numeric_category:view.value==='ground'?w.ground_height_category:w.cached_site_vertical_reference?'site_reference_available':'not_found';
  function configure(){
    category.replaceChildren();const all=document.createElement('option');all.value='all';all.textContent='All 332 wells';category.appendChild(all);
    const legend=document.getElementById('legend');legend.replaceChildren();
    for(const [id,item] of Object.entries(data.categories[view.value])){
      const n=data.wells.filter(w=>key(w)===id).length;
      const option=document.createElement('option');option.value=id;option.textContent=`${item.label} — ${n}`;category.appendChild(option);
      const row=document.createElement('div');row.innerHTML=`<span class="dot" style="background:${item.color}"></span>${esc(item.label)}: <strong>${n}</strong>`;legend.appendChild(row);
    }
  }
  configure();
  if(!window.L){document.getElementById('fallback-note').textContent='The interactive library could not load. Use the local static map below.';status.textContent='Interactive library unavailable.';for(const element of [view,category,search,background,...document.querySelectorAll('button')])element.disabled=true;return;}
  document.getElementById('fallback').style.display='none';document.getElementById('map').style.display='block';
  const map=L.map('map',{preferCanvas:true,minZoom:0,maxZoom:19});
  const topo=L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',{maxNativeZoom:16,maxZoom:19,attribution:'<a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">USGS The National Map</a>',errorTileUrl:'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="256" height="256"/%3E'});
  let failed=false;
  topo.on('loading',()=>{if(map.hasLayer(topo)){failed=false;status.textContent='Loading the USGS background…';}});
  topo.on('tileerror',()=>{if(map.hasLayer(topo)){failed=true;status.textContent='Some background tiles could not load. The wells still work; choose “Wells only” to hide the background.';}});
  topo.on('load',()=>{if(map.hasLayer(topo)&&!failed)status.textContent='USGS background loaded.';});
  background.addEventListener('change',()=>{if(background.value==='none'){map.removeLayer(topo);status.textContent='Showing wells without a background map.';}else{failed=false;status.textContent='Loading the USGS background…';topo.addTo(map);}});topo.addTo(map);
  L.control.scale({imperial:false,maxWidth:180,position:'bottomleft'}).addTo(map);
  const points=L.layerGroup().addTo(map);let visible=[],markers=new Map();
  const pos=w=>[Number(w.latitude),Number(w.longitude)];
  const fit=()=>{if(visible.length)map.fitBounds(L.latLngBounds(visible.map(pos)),{padding:[35,35],maxZoom:16});};
  const popup=w=>`<div class="popup"><strong>${esc(w.well_id)}</strong><br>Site ${esc(w.gw_site_id)} · ${esc(w.tr_key)}<hr>
    <strong>${esc(data.categories.numeric[w.numeric_category].label)}</strong><br>Completion depth: ${value(w,'completed_depth_ft_raw')} ft<br>
    Missing interval depth fields: ${w.missing_or_invalid_interval_depth_fields}<br>Missing elevation fields: ${w.missing_or_invalid_elevation_fields}<br>
    Stratigraphy intervals: ${w.stratigraphy_intervals} · Lithology intervals: ${w.lithology_intervals}<hr>
    <strong>Ground-height information</strong><br>Implied height: ${value(w,'implied_ground_height_min_ft')} ft<br>Implied-height spread: ${value(w,'implied_ground_height_spread_ft')} ft<br>
    Saved linked-site height: ${value(w,'cached_site_ground_height_ft')} ft<br>Saved site reference: ${value(w,'cached_site_vertical_reference')}<br>
    Saved site coordinates match well: ${w.cached_source_metadata?(w.cached_site_coordinates_match_well==='True'?'Yes':'No'):'No saved site evidence'}<br>
    Saved minus implied height: ${value(w,'cached_minus_implied_ground_height_ft')} ft (references not confirmed equivalent)<br>
    <small>Interval height reference: unrecorded. Calculated/site heights have not been adopted.</small><hr>
    <strong>All findings (${w.findings.length})</strong>${w.findings.length?`<ul>${w.findings.map(f=>`<li>${esc(f.description)}<br><small>${esc(f.field)}: ${esc(f.raw_value||'(blank)')} · ${esc(f.source_file.split('/').pop())}, CSV record ${esc(f.source_record)}</small></li>`).join('')}</ul>`:'<br>No numeric/sequence discrepancy flagged.'}</div>`;
  function render(){
    const query=search.value.trim().toLowerCase();visible=data.wells.filter(w=>(category.value==='all'||key(w)===category.value)&&(!query||[w.well_id,w.gw_site_id,w.tr_key].some(v=>v.toLowerCase().includes(query))));
    points.clearLayers();markers=new Map();
    for(const w of visible){const item=data.categories[view.value][key(w)];const marker=L.circleMarker(pos(w),{radius:6,color:'#fff',weight:1,fillColor:item.color,fillOpacity:.95});marker.bindTooltip(`${w.well_id} · ${item.label}`).bindPopup(popup(w)).addTo(points);markers.set(w.well_id,marker);}
    document.getElementById('visible-count').textContent=`${visible.length} of 332 well IDs shown`;
    const list=document.getElementById('well-list');list.replaceChildren();for(const w of visible.slice(0,80)){const button=document.createElement('button');button.innerHTML=`${esc(w.well_id)}<small>${esc(data.categories[view.value][key(w)].label)}</small>`;button.addEventListener('click',()=>{map.setView(pos(w),16);markers.get(w.well_id).openPopup();});list.appendChild(button);}
    document.getElementById('list-note').textContent=visible.length>80?'The list shows the first 80 matches; all matching wells are plotted.':visible.length?'':'No wells match these choices.';
  }
  view.addEventListener('change',()=>{configure();render();fit();});category.addEventListener('change',()=>{render();fit();});search.addEventListener('input',render);
  document.getElementById('fit').addEventListener('click',fit);document.getElementById('reset').addEventListener('click',()=>{view.value='numeric';search.value='';configure();render();fit();});render();fit();
})();
