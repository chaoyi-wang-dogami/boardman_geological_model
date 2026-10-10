/* Source well IDs remain separate; shared coordinates are grouped only for display. */
(() => {
  const data = JSON.parse(document.getElementById('well-data').textContent);
  const view = document.getElementById('view');
  const lithology = document.getElementById('lithology');
  const search = document.getElementById('search');
  const background = document.getElementById('background');
  const status = document.getElementById('background-status');
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  if (!window.L) {
    document.getElementById('fallback-note').textContent = 'The interactive library could not load. Use the static comparison below, or reopen with internet access.';
    status.textContent = 'The interactive library could not load.';
    for (const element of [view, lithology, search, background, ...document.querySelectorAll('button')]) element.disabled = true;
    return;
  }
  document.getElementById('fallback').style.display = 'none';
  document.getElementById('map').style.display = 'block';
  const map = L.map('map', {preferCanvas:true, minZoom:0, maxZoom:19});
  const topo = L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}', {
    maxNativeZoom:16, maxZoom:19,
    attribution:'<a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">USGS The National Map</a>',
    errorTileUrl:'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="256" height="256"/%3E'
  });
  let failed = false;
  topo.on('loading', () => {
    if (!map.hasLayer(topo)) return;
    failed = false; status.textContent = 'Loading the USGS topographic background…';
  });
  topo.on('tileerror', () => {
    if (!map.hasLayer(topo)) return;
    failed = true; status.textContent = 'Some background tiles could not load. The well points still work; choose “Wells only” to hide the background.';
  });
  topo.on('load', () => {if (map.hasLayer(topo) && !failed) status.textContent = 'USGS topographic background loaded.';});
  background.addEventListener('change', () => {
    if (background.value === 'none') {
      map.removeLayer(topo);status.textContent = 'Showing wells without a background map.';
    } else {
      failed = false;status.textContent = 'Loading the USGS topographic background…';topo.addTo(map);
    }
  });
  topo.addTo(map);
  L.control.scale({imperial:false, maxWidth:180, position:'bottomleft'}).addTo(map);
  const points = L.layerGroup().addTo(map);
  const retained = data.wells.filter(w => w.status === 'retained');
  let visible = [], markers = new Map();
  const position = w => [Number(w.latitude), Number(w.longitude)];
  const fit = wells => {if (wells.length) map.fitBounds(L.latLngBounds(wells.map(position)), {padding:[35,35],maxZoom:16});};
  const sourceLink = w => /^https:\/\//.test(w.detail_url) ? `<a href="${esc(w.detail_url)}" target="_blank" rel="noopener noreferrer">Original well report</a>` : '';
  const popup = wells => `<div class="popup"><strong>${wells.length} visible well ID(s) at this location</strong><br>Latitude ${esc(wells[0].latitude)}<br>Longitude ${esc(wells[0].longitude)}<ul>${wells.map(w => `<li><strong>${esc(w.well_id)}</strong><small>${w.status === 'retained' ? 'Retained: stratigraphy present' : 'Excluded: no stratigraphy'}<br>Lithology: ${w.has_lithology === 'TRUE' ? 'present' : 'absent'}<br>Site ID: ${esc(w.gw_site_id || 'unknown')}<br>Township: ${esc(w.tr_key)}<br>Completed depth: ${esc(w.completed_depth_ft || 'unknown')} ft<br>Completion date: ${esc(w.complete_date || 'unknown')}<br>Source location class: ${esc(w.location_class || 'unknown')}<br>${sourceLink(w)}</small></li>`).join('')}</ul></div>`;
  function render() {
    const query = search.value.trim().toLowerCase();
    visible = data.wells.filter(w =>
      (view.value !== 'after' || w.status === 'retained') &&
      (view.value !== 'excluded' || w.status === 'excluded') &&
      (lithology.value === 'all' || (w.has_lithology === 'TRUE') === (lithology.value === 'yes')) &&
      (!query || [w.well_id,w.gw_site_id,w.tr_key].some(value => value.toLowerCase().includes(query))));
    points.clearLayers(); markers = new Map();
    const locations = new Map();
    for (const well of visible) {
      const key = position(well).join(',');
      if (!locations.has(key)) locations.set(key, []);
      locations.get(key).push(well);
    }
    // Draw retained-only locations last so the blue subset remains visible.
    const ordered = [...locations.values()].sort((a,b) => Number(a.some(w=>w.status==='retained')) - Number(b.some(w=>w.status==='retained')));
    for (const wells of ordered) {
      const kept = wells.filter(w => w.status === 'retained').length;
      const color = kept ? '#2463a6' : view.value === 'excluded' ? '#ba701d' : '#88949b';
      const marker = L.circleMarker(position(wells[0]), {radius:kept ? 5 : 3.5, color:kept ? '#fff' : color,weight:kept ? 1 : .5,fillColor:color,fillOpacity:kept ? .95 : .55});
      marker.bindTooltip(`${wells.length} well ID(s) · ${kept} retained · ${wells.length-kept} excluded`).bindPopup(popup(wells)).addTo(points);
      for (const well of wells) markers.set(well.well_id,marker);
    }
    const keptCount = visible.filter(w=>w.status==='retained').length;
    document.getElementById('visible-count').textContent = `${visible.length.toLocaleString('en-US')} well IDs · ${locations.size.toLocaleString('en-US')} locations · ${keptCount} retained · ${(visible.length-keptCount).toLocaleString('en-US')} excluded`;
    const list = document.getElementById('well-list');list.replaceChildren();
    for (const well of visible.slice(0,80)) {
      const button = document.createElement('button');
      button.innerHTML = `${esc(well.well_id)}<small>${well.status === 'retained' ? 'Retained' : 'Excluded'} · ${esc(well.tr_key)}</small>`;
      button.addEventListener('click',()=>{map.setView(position(well),16);markers.get(well.well_id).openPopup();});
      list.appendChild(button);
    }
    document.getElementById('list-note').textContent = visible.length > 80 ? 'The list shows the first 80 matches. All matching points are on the map; search to find another well.' : visible.length ? '' : 'No wells match these choices.';
  }
  for (const select of [view,lithology]) select.addEventListener('change',()=>{render();fit(visible);});
  search.addEventListener('input',render);
  document.getElementById('fit').addEventListener('click',()=>fit(visible));
  document.getElementById('region').addEventListener('click',()=>fit(retained));
  document.getElementById('reset').addEventListener('click',()=>{view.value='after';lithology.value='all';search.value='';render();fit(visible);});
  render();fit(visible);
})();
