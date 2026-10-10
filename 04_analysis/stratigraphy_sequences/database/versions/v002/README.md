# Map tools v002: USGS basemap on startup

October 9, 2026. This is a map presentation revision. Database schema, Docker,
credentials, queries and Leaflet assets continue to use immutable v001 tools.
The map now selects and loads the USGS topographic background automatically.
The Wells only option, points, scale, search and details work offline.

Generate a new map from PostgreSQL, from the repository root:

```bash
python3 04_analysis/stratigraphy_sequences/database/versions/v002/scripts/build_database_map.py --output /tmp/boardman_new_map.html
```

For a display repair with the existing data snapshot unchanged, add
`--snapshot <existing_map.html>`. Outputs must use a new path. The map manifest
records its data timestamp, map version, embedded payload hash and HTML hash.
This revision does not modify the database or original observations.

`browser_check.cjs` verifies offline controls and failure handling, then opens
an online browser to verify that real USGS images load on startup and after
switching the background off and on. It requires Playwright and Chromium.

Keep `v001` available: v002 deliberately reuses its helpers and vendor assets
instead of duplicating database infrastructure.
