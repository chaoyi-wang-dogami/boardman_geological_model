# Boardman 19-township processed well data

This directory contains joinable well-report, lithology, and GWIS stratigraphy tables for the 19-township Boardman study area, plus maps of their locations. The summary contains 7,402 reports selected by the 19 configured township keys; it is not a complete inventory of Morrow and Umatilla counties. The CSV files are derived from the saved OWRD data under `01_raw/`; they are not the original source records.

## Data files

| File | Rows | One row represents | Contents |
|---|---:|---|---|
| [`boardman_wells_summary.csv`](boardman_wells_summary.csv) | 7,402 | One well report | Report identifiers, township key, dates, depth, coordinates, location class, and flags/counts for lithology and stratigraphy |
| [`boardman_wells_lithology.csv`](boardman_wells_lithology.csv) | 15,586 | One reported lithology interval | Raw material description and interval depths for 3,067 well reports |
| [`boardman_wells_stratigraphy.csv`](boardman_wells_stratigraphy.csv) | 1,854 | One interpreted stratigraphic interval linked to a well report | GWIS stratigraphic unit, top and bottom depths/elevations, interpreter, age fields, and provenance for 423 reports |

The tables join on `well_id` or `wl_id`:

- `well_id` is the repository well-report identifier, such as `MORR_0000350`.
- `wl_id` is the OWRD numeric identifier for the same well-report record.
- In these files, `well_id` and `wl_id` have a one-to-one relationship.
- `gw_site_id` identifies the GWIS site interpretation. Several well reports can link to the same GWIS site, so it has a many-to-one relationship with report identifiers.

### Stratigraphy and lithology coverage

The 423 figure refers only to the subset of the 7,402 summarized reports that have GWIS stratigraphy. These 423 reports represent 328 distinct GWIS sites:

| GWIS linkage | Well reports | GWIS sites |
|---|---:|---:|
| Site linked to more than one report | 166 | 71 |
| Site linked to one report | 257 | 257 |
| **Total** | **423** | **328** |

Of these 423 reports, 121 have processed lithology and stratigraphy; they represent 112 GWIS sites. The other 302 have stratigraphy but no processed lithology rows.

For sequence cleaning, treat `gw_site_id` as the interpretation key and retain `well_id` and `wl_id` as links back to the reports. Otherwise, a shared site interpretation can be counted more than once. Preserve the original top and bottom values when creating corrected or standardized sequences.

## Location plots

All maps use the same 19-township extent and WGS 84 / UTM zone 11N coordinates (EPSG:32611). The beige polygons show the configured township area. Point colors identify the report county.

| Plot | What it shows |
|---|---|
| [`boardman_19_townships_locs.png`](boardman_19_townships_locs.png) | All saved reports: 7,399 of 7,402 are visible; 3 fall outside the common map extent |
| [`boardman_19_townships_lithology_locs.png`](boardman_19_townships_lithology_locs.png) | Reports with structured lithology: 3,066 of 3,067 are visible; 1 falls outside the common extent |
| [`boardman_19_townships_stratigraphy_locs.png`](boardman_19_townships_stratigraphy_locs.png) | All 423 reports linked to GWIS stratigraphy |

OWRD report coordinates can be approximate, and reports at the same or nearby coordinates can plot on top of one another. The number of visible markers may therefore appear smaller than the report count.
