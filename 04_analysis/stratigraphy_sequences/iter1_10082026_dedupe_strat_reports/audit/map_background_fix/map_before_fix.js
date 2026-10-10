/* Group data are embedded, so opening the HTML locally needs no data server. */
(() => {
  const data = JSON.parse(document.getElementById('group-data').textContent);
  const filter = document.getElementById('filter');
  const search = document.getElementById('search');
  const radius = document.getElementById('radius');
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  if (!window.L) {
    document.getElementById('fallback-note').textContent = 'The interactive map library could not load. Use the static overview below, or reopen with an internet connection.';
    for (const element of [filter, search, radius, document.getElementById('fit'), document.getElementById('reset')]) element.disabled = true;
    return;
  }
  document.getElementById('fallback').style.display = 'none';
  document.getElementById('map').style.display = 'block';
  const map = L.map('map', {preferCanvas:true});
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom:19, attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  L.control.scale({imperial:false, maxWidth:180, position:'bottomleft'}).addTo(map);
  const points = L.layerGroup().addTo(map), circles = L.layerGroup().addTo(map), lines = L.layerGroup().addTo(map);
  let visible = [], markers = new Map();
  const coords = group => group.locations.map(p => [p.latitude, p.longitude]);
  const fit = groups => {
    const locations = groups.flatMap(coords);
    if (locations.length) map.fitBounds(L.latLngBounds(locations), {padding:[40,40], maxZoom:16});
  };
  const popup = (g, p) => `<div class="popup"><strong>Site ${esc(g.site_id)}</strong><br>${g.well_count} records in this group · ${g.interval_count} intervals per interpretation<br>Largest within-group separation: ${g.spread_m.toFixed(1)} m<hr>Latitude ${p.latitude.toFixed(8)}<br>Longitude ${p.longitude.toFixed(8)}<ul>${p.wells.map(w => `<li><strong>${esc(w.well_id)}</strong><small>Location class: ${esc(w.location_class || 'unknown')}<br>Completion date: ${esc(w.complete_date || 'unknown')}<br>Completed depth: ${esc(w.completed_depth_ft || 'unknown')} ft</small></li>`).join('')}</ul></div>`;
  function render() {
    const query = search.value.trim().toLowerCase();
    visible = data.groups.filter(g => (filter.value === 'all' || (filter.value === 'same' ? g.same_coordinates : !g.same_coordinates)) &&
      (!query || g.site_id.includes(query) || g.locations.some(p => p.wells.some(w => w.well_id.toLowerCase().includes(query)))));
    points.clearLayers(); circles.clearLayers(); lines.clearLayers(); markers = new Map();
    const list = document.getElementById('group-list'); list.replaceChildren();
    const visibleIds = new Set(visible.map(g => g.site_id));
    for (const g of visible) {
      const color = g.same_coordinates ? '#2463a6' : '#c77716';
      const groupMarkers = [];
      if (!g.same_coordinates) L.polyline(coords(g), {color, weight:2, dashArray:'5 5', opacity:.6}).addTo(lines);
      for (const p of g.locations) {
        const marker = L.circleMarker([p.latitude,p.longitude], {radius:6 + Math.min(p.wells.length, 4), color:'#fff', weight:1.3, fillColor:color, fillOpacity:.9});
        marker.bindTooltip(`Site ${g.site_id} · ${p.wells.length} well record(s)`).bindPopup(popup(g,p)).addTo(points);
        groupMarkers.push(marker);
        if (radius.checked) L.circle([p.latitude,p.longitude], {radius:100, color, weight:1, fillOpacity:.06}).addTo(circles);
      }
      markers.set(g.site_id, groupMarkers);
      const button = document.createElement('button');
      button.innerHTML = `Site ${esc(g.site_id)} · ${g.well_count} well records<small>${g.same_coordinates ? 'One shared location' : `${g.locations.length} locations · ${g.spread_m.toFixed(0)} m spread`}</small>`;
      button.addEventListener('click', () => {fit([g]); groupMarkers[0].openPopup();});
      list.appendChild(button);
    }
    for (const pair of data.nearby_pairs) {
      if (visibleIds.has(pair.site_a) && visibleIds.has(pair.site_b)) {
        L.polyline([pair.point_a,pair.point_b], {color:'#bb3046',weight:4}).bindTooltip(`Sites ${pair.site_a} / ${pair.site_b}: ${pair.distance_m.toFixed(1)} m`).addTo(lines);
        for (const position of [pair.point_a,pair.point_b]) L.circleMarker(position, {radius:13,color:'#bb3046',weight:2,fill:false,interactive:false}).addTo(lines);
      }
    }
    document.getElementById('visible-count').textContent = `${visible.length} groups visible · ${visible.reduce((total,g) => total+g.well_count,0)} well records`;
  }
  for (const pair of data.nearby_pairs) {
    const button = document.createElement('button'); button.className = 'pair';
    button.textContent = `Sites ${pair.site_a} ↔ ${pair.site_b} · ${pair.distance_m.toFixed(0)} m`;
    button.addEventListener('click', () => {
      filter.value = 'all'; search.value = ''; render();
      map.fitBounds(L.latLngBounds([pair.point_a,pair.point_b]), {padding:[80,80], maxZoom:18});
    });
    document.getElementById('pair-list').appendChild(button);
  }
  filter.addEventListener('change', render); search.addEventListener('input', render); radius.addEventListener('change', render);
  document.getElementById('fit').addEventListener('click', () => fit(visible));
  document.getElementById('reset').addEventListener('click', () => {filter.value='all';search.value='';radius.checked=false;render();fit(visible);});
  render(); fit(visible);
})();
