# Database map snapshot

Open [well_database_map.html](well_database_map.html). Generated entirely from PostgreSQL; no live CSV or database reads occur when opening the HTML. The embedded map library works offline. The optional USGS background uses internet tiles.

The default is the 332 working wells. Archived selection shows 7,070 original well IDs (91 deduplicated and 6,979 excluded for no stratigraphy). All selection shows 7,402. Colors reflect iteration 3's numeric/ground evidence categories; archived wells outside that audit are gray.

Selecting a well opens a details panel with full recorded intervals, expandable source metadata, findings, ground-height evidence and unadopted calculations, membership history, and archived-well links. Each original well retains its own lithology. Search accepts well IDs, site IDs and township strings. The list shows the first 80 matches; every matching location is plotted.

Source locations are displayed under the existing longitude/latitude assumption, not independently verified datum metadata. Depths/heights use the source/repository feet convention. Category completeness does not establish geological suitability. Map generation does not repair gaps or overlaps.

The map manifest records the PostgreSQL source, generation time and payload/HTML hashes. Regenerate to a NEW output path using the [shared tools](../../../database/versions/v001/README.md); preserve completed map snapshots.
