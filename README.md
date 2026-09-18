# Boardman geological model — OWRD downloader

This first project component downloads Oregon Water Resources Department
(OWRD) well-report data for the nine configured Boardman-area townships.

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

Useful options:

```text
--limit N          Process only the first N queried records
--skip-lithology   Skip OWRD detail pages and lithology parsing
--skip-pdfs        Skip original scanned well reports
--overwrite        Replace existing metadata, lithology, and PDFs
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
