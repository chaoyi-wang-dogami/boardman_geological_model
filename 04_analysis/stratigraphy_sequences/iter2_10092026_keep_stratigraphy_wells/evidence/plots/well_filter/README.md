# Iteration 2 well-filter maps

Open the [interactive map](well_filter_map.html), [static PNG](before_after_filter.png), or [PDF](before_after_filter.pdf).

Before means iteration 1's 7,311 well IDs. After means iteration 2's 332 retained well IDs. The 6,979 excluded IDs lack stratigraphy. Lithology is optional: 100 retained IDs have lithology and 232 do not. Counts are well IDs, not distinct locations.

The static comparison includes full-extent panels and closer panels based on retained-well bounds. Each before/after pair uses identical axes. The closer view shows 7,308 pre-filter IDs and omits 3; all source IDs appear in the full-extent view. Both rows have distance scales (20 km full extent; 5 km closer view). Grey means excluded and blue means retained. Coincident points may overlap.

The interactive map starts with the retained wells. Switch to **Before**, **Excluded**, or **Before + after overlay**. Filter by lithology and search well ID, site ID, or township. Click a marker or listed well for details. The list shows up to 80 matches; all matching wells are plotted. Recorded coordinate pairs are grouped only for popups, without merging well IDs. **Fit visible wells** includes all matches; **Zoom to retained area** changes the viewport without filtering the data.

The background uses [USGS The National Map](https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer), with a **Wells only** option and clear tile-error messages. Leaflet 1.9.4 loads from a CDN, so an internet connection is needed to initially load the interactive library. If it cannot load, the local static PNG remains available. The data and map JavaScript are embedded in the HTML; no local server is needed.

[well_locations.csv](well_locations.csv) preserves parent summary values, status, and source occurrence identity. [well_locations.geojson](well_locations.geojson) contains one feature per parent well ID. [manifest.json](manifest.json) records the checked input versions, generation methods, output hashes, and plot settings. Source latitude/longitude are displayed as geographic degrees; their geodetic datum has not been independently established. Scale bars use the same mean-Earth-radius distance convention as earlier maps. Distant coordinates have not been removed or corrected.

The generator is `scripts/build_filter_maps.py` inside iteration 2. Reproduce into a **new** external directory, for example from the repository root:

```bash
python3 04_analysis/stratigraphy_sequences/iter2_10092026_keep_stratigraphy_wells/scripts/build_filter_maps.py --output-dir /tmp/boardman_iter2_map_preview
```

The output directory must not already exist. Working CSVs, archives, filter decisions, and the original completion date remain unchanged. The generation-time iteration manifest was saved before adding map evidence, so hash references do not form a cycle.
