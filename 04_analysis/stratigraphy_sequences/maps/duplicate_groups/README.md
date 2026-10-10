# Duplicate interpretation groups: exploratory map

Open [the interactive map](duplicate_groups_map.html), or [the static overview](duplicate_groups_overview.png). This visualization shows frozen iteration 0 before deduplication. [Iteration 1](../../iter1_10082026_dedupe_strat_reports/README.md) now contains the current working release; this map retains the original 166 records for comparison.

The [before-and-after plot](../../iter1_10082026_dedupe_strat_reports/evidence/plots/before_after/README.md) lives inside iteration 1 and compares the 166 original group records with the 75 surviving records, using identical axes and distance scales. PNG and PDF versions are available. Earlier copies remain here for existing links.

The map includes 71 groups, 166 well records, and 84 distinct coordinate pairs within their groups. Each group shares a `gw_site_id` and an identical complete stratigraphy interpretation, including repeated interval occurrence counts. Of these groups, 58 have one shared recorded location and 13 have differing locations.

- Blue points: groups whose records share one location.
- Orange points and dashed links: differing recorded locations within a group. No anchor or replacement location has been selected.
- Red links: the two different-group pairs within 100 metres: 1077/13353 and 135/680. Both pairs have different complete interpretations.

Click points for site IDs, well IDs, recorded coordinates, location classes, completion dates, and completed depths. Use the group filter, site/well search, group list, close-pair buttons, and optional 100 m circles. Coincident records are combined into one clickable point listing their original IDs. The interactive map has a metre/kilometre scale at the bottom left that adjusts as you zoom.

The HTML embeds its data and can be opened directly in a browser. Interactive mapping uses [Leaflet 1.9.4](https://leafletjs.com/download.html) from a CDN and the [USGS topographic background](https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer), requiring internet access. Select **Wells only** to hide background tiles while retaining search, filters, popups, and the distance scale. A message reports background loading failures; a static fallback appears if the library cannot load. The PNG always works without a basemap connection. The static overview uses latitude/longitude axes with a latitude-adjusted aspect ratio and a labelled 5 km (5,000 m) scale bar at the lower right. Its length is calculated at the bar's latitude and checked against the same distance formula. Inset panels use local metre offsets and 100 m reference circles.

On October 9, 2026, the interactive background changed from OpenStreetMap to USGS after blocked tile images appeared in a local preview. Local previews can omit the page address required by [OpenStreetMap's tile policy](https://operations.osmfoundation.org/policies/tiles/); the exact reason for the user's blocked requests was not independently established. Both HTML copies and the generator were updated. The previous HTML and manifests are retained in iteration 1 under `audit/map_background_fix/`. Group data, static plots, and deduplication results did not change.

Distances use the same approximate great-circle calculation as the earlier comparison: a mean Earth radius of 6,371,008.8 metres, with the nearest recorded coordinate pair used between groups. Source positions are preserved and have not been independently verified. Plotting precision is not a statement of location accuracy.

## Files and reproduction

| File | Purpose |
|---|---|
| `duplicate_groups_map.html` | Interactive map with embedded group data and JavaScript |
| `duplicate_groups_overview.png` | Static overview and two close-pair detail panels |
| `groups.json` | Groups, original well metadata, location spreads, nearby pairs, and counts |
| `group_locations.csv` | One row per original well record, retaining source coordinate strings |
| `group_locations.geojson` | One point per coordinate pair within a group, with associated well IDs |
| `map_manifest.json` | Input/source/output hashes, calculation method, software, and factual checks |
| `build_map.py`, `map_template.html`, `map.js` | Reproducible generator and map source files |

From the repository root:

```bash
python3 04_analysis/stratigraphy_sequences/maps/duplicate_groups/build_map.py
```

The generator requires Matplotlib and uses the standard library for CSV/group/distance calculations. It checks snapshot hashes, all expected counts, the two nearby pairs, and their differing interpretations. It regenerates only these exploratory map outputs. The completed iteration 0 files and authoritative inputs remain unchanged.
