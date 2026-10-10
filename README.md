# Boardman geological model — OWRD downloader

This first project component downloads Oregon Water Resources Department
(OWRD) well-report data for the 19 configured Boardman-area townships.

It produces:

- all FeatureServer well metadata;
- one directory per well report;
- structured lithology intervals when OWRD provides them digitally;
- the original scanned well-report PDF;
- all-well and high-confidence CSV tables;
- an ArcGIS Pro-compatible GeoPackage with `wells_all` and
  `wells_high_confidence` layers; and
- an append-only download log so missing tables and failed PDFs are visible.

The raw driller description is retained as `material_raw`. The downloader does
not standardize lithology or assign formations.

## Project locations used

```text
00_config/owrd_download.yml
01_raw/owrd/wells_raw.csv
01_raw/owrd/download_log.csv
01_raw/wells/<WELL_REPORT>/metadata.json
01_raw/wells/<WELL_REPORT>/lithology.csv
01_raw/wells/<WELL_REPORT>/stratigraphy.csv  # optional GWIS site interpretation
01_raw/wells/<WELL_REPORT>/well_report.pdf
02_gis/wells_all.csv
02_gis/wells_high_confidence.csv
02_gis/wells.gpkg
03_processed/lithology/lithology_all_raw.csv
scripts/download_owrd.py
```

The supplied `.gitignore` excludes downloaded PDFs, generated CSVs, and GIS
outputs. Configuration, scripts, and later hand-curated interpretation files
remain trackable.

The [Git storage policy](GIT_STORAGE.md) also keeps database backups, generated
interactive maps, plotting datasets, runtime logs, and downloaded page caches
local. These files remain useful project data and require separate backup;
they are excluded from the source-code repository.

## Install with uv

From the repository root:

```bash
uv sync
```

Dependencies are defined in `pyproject.toml` (Python 3.11 or newer). This is a
script project, not an installable package. `uv sync` creates `.venv` and
generates `uv.lock`; commit that lockfile to Git for reproducible installs.
No environment activation is required when using `uv run`, on Windows or Linux.
The bundle does not include a pre-generated lockfile.

To add dependencies later:

```bash
uv add gempy
```

`requirements.txt` is optional and is not used by `uv sync`. If needed for
other tools, regenerate it after dependency changes:

```bash
uv export --format requirements-txt --no-emit-project --output-file requirements.txt
```

See the [official uv project guide](https://docs.astral.sh/uv/guides/projects/).

## Profile raw lithology wording and report identities

After downloading the configured 19-township data, run:

```bash
uv run python scripts/profile_raw_lithology.py
uv run python scripts/compare_bonded_descriptions.py
uv run python scripts/investigate_bonded_naming_spatial.py
```

The first script checks source joins, coordinates, repeated well tags, work
types, and raw wording. The second compares exact-description Dice similarity
within and between selected drillers for all geological well units and their
A/B subset. The third investigates phrase reuse, five-nearest-well spatial
concentration, and the relationship between spatial and wording scores. They
write derived tables and figures to
`04_analysis/raw_lithology_profile/artifacts/`. See the [findings](04_analysis/raw_lithology_profile/FINDINGS.md)
for denominators, definitions, and limitations. Driller figures use one
geological report per identified well unit and names with at least 10 A/B units.
The approved Zollman aliases are combined; Zachary Neigel's concentrated
project is excluded. Generated CSVs are ignored by Git. The
findings, selected figures allowed by `.gitignore`, named description example,
and JSON summaries are retained in Git. Other generated figures remain local.
Source data are not changed.

## Curate the saved 19-township reports

```bash
uv run python scripts/curate_boardman_19_townships.py
```

This writes three local, joinable tables under
`03_processed/boardman_19_townships/`:

- `boardman_wells_summary.csv`: one row per saved well report;
- `boardman_wells_lithology.csv`: one row per interval in that report's
  `01_raw/wells/<WELL_REPORT>/lithology.csv`;
- `boardman_wells_stratigraphy.csv`: one row per linked GWIS site
  interpretation in that report's `stratigraphy.csv`.

The Morrow County scrape provides the layout for the summary and stratigraphy
tables. The 19-township lithology table keeps the *well-report* fields
`material_raw`, `from_ft`, and `to_ft`, because those are the data already
downloaded. The scrape's GWIS fields `prim_lithology` and
`water_bearing_zone` are not inferred from free-text descriptions.

Join on `wl_id` for a report or `gw_site_id` for a GWIS site. `well_id` is
the existing zero-padded report folder name. More than one report can share
the same site interpretation, so stratigraphy rows can repeat across
different `wl_id` values. Summary counts are report-level row counts; empty
source tables yield zero. `received_date` is the saved OWRD date, not the
scrape's `received` yes/no field. Coordinates come from the saved OWRD
`longitude_dec` and `latitude_dec` fields; `location_class` shows their
quality category. The curation script reads only local files and validates
report IDs, GWIS links, and interval counts before writing the outputs.

To map all saved reports and the subsets with lithology or stratigraphy:

```bash
uv run python scripts/plot_boardman_19_townships.py
```

The three 300-dpi PNGs are saved beside the curated CSVs. They share the
same 19-township extent and county colors. Three anomalous coordinates fall
outside that common map view (one report has lithology); the CSVs retain all
reports, and each map states how many points are visible.

## Test on five wells first

This retrieves metadata and structured lithology for five wells, but skips the
larger PDF files:

```bash
uv run python scripts/download_owrd.py --limit 5 --skip-pdfs
```

Review the five well directories, `01_raw/owrd/download_log.csv`, and the two
layers in `02_gis/wells.gpkg`.

## Run the complete download

```bash
uv run python scripts/download_owrd.py
```

Existing per-well files are reused, so the same command can resume an
interrupted run. To replace them, add `--overwrite`.

## Add GWIS stratigraphy to the saved 19-township inventory

```bash
uv run python scripts/download_owrd.py --stratigraphy-only
```

This mode reads the existing `01_raw/owrd/wells_raw.csv`. It does not query
the 19-township well-report layer again or rewrite the existing lithology,
metadata, PDFs, combined lithology table, or GIS outputs. It uses OWRD's
groundwater-site layer to link reports to GWIS sites, reuses complete tables
from the separately scraped county files when available, and fetches GWIS
site pages only when no linked well folder already has the data. It checks
still-unmatched well-log pages for
secondary site links and caches those lookup results in
`01_raw/owrd/gwis_report_site_lookups.csv`. A second run resumes missing
lookups and well folders. `--overwrite`
refreshes only stratigraphy in this mode.

Linked report folders get `stratigraphy.csv`, including a header-only file
when GWIS has no rows for a linked site. The downloader resumes from these
per-well files. `01_raw/owrd/gwis_stratigraphy_links.csv` records each
report-to-site match and its source. `01_raw/owrd/gwis_stratigraphy_audit.csv`
records the outcome for every report. These are GWIS *site interpretations*,
which can be shared by several well reports. They are separate from the
driller's `lithology.csv` and should not be treated as an independent
interpretation for every linked report. Reports without a site link do not
receive a stratigraphy file; an absent link does not prove that the site has
no interpretation. Failed site or link requests remain visible in the audit
and are retried on the next run.

Useful options:

```text
--limit N          Process only the first N queried records
--skip-lithology   Skip OWRD detail pages and lithology parsing
--skip-pdfs        Skip original scanned well reports
--stratigraphy-only  Add missing GWIS site stratigraphy from saved inventory
--overwrite        Replace existing per-well files (stratigraphy only in that mode)
--config PATH      Use a different YAML configuration
--project-root DIR Write outputs under another project root
```

## Coordinate handling

OWRD's layer is a hybrid location dataset. Many records have only a point
derived from the Public Land Survey System (PLSS). The downloader therefore
keeps both:

- `latitude_dec` and `longitude_dec`: coordinates supplied by a location
  source, when available; and
- `map_latitude` and `map_longitude`: the FeatureServer display point, which
  can be a section or quarter-quarter centroid.

`display_latitude` and `display_longitude` are used for the `wells_all` GIS
layer. Source coordinates are preferred; the display point is the fallback.

Location classes are:

| Class | Rule | Default modeling use |
|---|---|---|
| A | Sourced coordinates; estimated error no more than 50 ft | Include |
| B | Sourced coordinates; estimated error over 50 ft and no more than 100 ft | Include |
| C | Sourced coordinates but error is missing or over 100 ft | Review |
| D | No sourced coordinates, or source appears PLSS/centroid-derived | Exclude from primary model |

The `wells_high_confidence` layer contains Classes A and B. The thresholds and
the inferred-source expression are configurable in
`00_config/owrd_download.yml`.

## Data cautions

- The digital lithology table is not available for every report. Always retain
  and check the scanned report where interpretation matters.
- `lithology.csv` preserves OWRD/driller wording; clean and standardize it only
  in downstream processed files.
- A well folder represents a report, not necessarily a unique physical borehole.
  Deepening, alteration, and abandonment reports can describe the same well.
- `download_log.csv` is append-only and may contain entries from multiple runs.

Official sources:

- OWRD Well Reports FeatureServer: <https://gis.wrd.state.or.us/server/rest/services/dynamic/Well_Reports_Query_WGS84/FeatureServer/0>
- OWRD Well Report Query: <https://apps.wrd.state.or.us/apps/gw/well_log/Default.aspx>
- OWRD Groundwater Information System: <https://apps.wrd.state.or.us/apps/gw/gw_info/gw_info_report/Default.aspx>
