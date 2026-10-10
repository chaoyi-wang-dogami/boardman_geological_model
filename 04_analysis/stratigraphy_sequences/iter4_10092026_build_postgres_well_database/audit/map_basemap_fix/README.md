# Iteration 4 basemap repair

October 9, 2026. The user reported no basemap in the iteration 4 HTML and
requested folding this repair into the Git cleanup commit.

The previous map selected Wells only and never attached a background layer on
startup. The USGS service returned HTTP 200 with a valid image for a regional
tile. Map tools v002 select USGS by default and attach the background after the
initial well extent is established. Successful and failed tile requests update
the status message. Wells only removes the background for offline viewing.

The corrected map preserves the original embedded PostgreSQL data byte-for-byte.
It does not query or modify the database during this display repair. The v001
database tools, backup, geological values and original completion date remain
unchanged. Reusable map code lives in `database/versions/v002`, reusing v001
helpers and Leaflet assets.

Previous HTML, preview, manifests and documentation are retained here. Their
hashes, corrected output hashes, and the repair record are in
[change_record.json](change_record.json). The large historical HTML and PNG
remain local under Git ignore rules; audit records and repair code stay tracked.

[Browser checks](browser_checks.json) verify live USGS images on initial load,
background switching, offline error handling, all category counts, well details,
archived-survivor navigation, scale, and search/reset without JavaScript errors.
The iteration manifest records updated display artifacts and both shared tool
versions; the pre-repair manifest is retained unchanged here.
