# PostgreSQL/PostGIS tools v001

Created for iteration 4, October 9, 2026. Uses a digest-pinned PostgreSQL 17 / PostGIS 3.5 image; `image.lock.json` records the exact downloaded image. Requires Python 3.10+ and Docker Desktop or Docker Engine. Python scripts use the standard library and the PostgreSQL tools inside the container.

From the repository root:

```bash
python3 04_analysis/stratigraphy_sequences/database/versions/v001/scripts/manage_database.py start
python3 04_analysis/stratigraphy_sequences/database/versions/v001/scripts/verify_database.py
```

The helper tries Windows `docker.exe` first when running in WSL and falls back to the Linux CLI. This avoids dependence on Linux Docker socket group membership. No separate Docker Engine installation in WSL is needed. Compose is submitted on standard input, so Windows Docker does not need Linux bind-mount paths. Only the dedicated named volume stores PostgreSQL files.

## Initial migration

```bash
python3 04_analysis/stratigraphy_sequences/database/versions/v001/scripts/build_database.py
```

The migration refuses to replace an existing `boardman` schema. Schema creation and data import run in one transaction. It checks the frozen release hashes and uses the recorded input inventory when rebuilding. It is the bootstrap importer for iterations 0–3, not a general editor for future geology. Later transformations should add new version and membership records and record decisions/changes in the affected iteration.

## Map snapshots

```bash
python3 04_analysis/stratigraphy_sequences/database/versions/v001/scripts/build_database_map.py --output /tmp/boardman_map_preview.html
```

The map reads only PostgreSQL. It embeds original well metadata, intervals, findings, height evidence, membership history, and duplicate links for all 7,402 well IDs. The default selection is the 332 working wells. Archived originals retain their own records. Leaflet 1.9.4 and CSS are embedded, so points, scales, search, and details work offline. USGS tiles are optional. Existing map paths are never overwritten.

## Backup and restore

```bash
python3 04_analysis/stratigraphy_sequences/database/versions/v001/scripts/manage_database.py backup --file /tmp/boardman_new_release.dump
python3 04_analysis/stratigraphy_sequences/database/versions/v001/scripts/manage_database.py restore --file /tmp/boardman_new_release.dump --database boardman_review_copy
python3 04_analysis/stratigraphy_sequences/database/versions/v001/scripts/verify_database.py --database boardman_review_copy --output /tmp/boardman_restore_checks.json
```

Restore creates a NEW database and refuses to target the working database. Backups use the container's matching `pg_dump` version. They preserve the complete database, including compressed source-file contents and PostGIS extension definitions. A backup is usable with a compatible PostgreSQL/PostGIS installation; it is not an ArcGIS geodatabase file.

Stop the service without removing its volume:

```bash
python3 04_analysis/stratigraphy_sequences/database/versions/v001/scripts/manage_database.py stop
```

## Connect from Windows

Use a PostgreSQL client with host `127.0.0.1`, port `55432`, database `boardman`, user `boardman_admin`, and the generated password in the local runtime connection file. The port is bound to Windows localhost. Docker Desktop must run for database queries; generated maps do not need it. WSL scripts use `docker exec` transport and do not depend on Windows-to-WSL TCP forwarding.

`compose.yaml` is reusable directly with Docker Compose when `BOARDMAN_DB_PASSWORD` and the digest-pinned `BOARDMAN_IMAGE` are supplied locally. The management helper supplies them without printing the password.

## Later ArcGIS export

`boardman.arcgis_wells` exposes stable well IDs, scalar coordinates and audit categories. Export working interval tables and recreate relationship classes using stable well/interval IDs in an ArcGIS environment. PostgreSQL foreign keys do not automatically become Esri relationship classes. No ArcGIS license is needed for this implementation.

References: [PostgreSQL backups](https://www.postgresql.org/docs/17/app-pgdump.html), [PostGIS Docker image](https://github.com/postgis/docker-postgis), [Docker volumes](https://docs.docker.com/engine/storage/volumes/). Leaflet's license is retained in `vendor/LEAFLET_LICENSE.txt`.
