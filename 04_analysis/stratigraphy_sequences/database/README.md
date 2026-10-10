# Shared Boardman database tools

Database and Docker tools use [versions/v001](versions/v001/README.md). The current map generator uses [map tools v002](versions/v002/README.md), which loads the USGS basemap on startup and reuses v001 helpers and vendor assets. Shared versions remain immutable; later iterations reference them instead of copying their infrastructure.

The live PostgreSQL/PostGIS database is in Docker's named volume `boardman_stratigraphy_pgdata`. Iteration directories contain frozen backups, maps, checks, and decisions. A map is a generated snapshot; it does not write to or refresh itself from the database.

Private connection settings are generated locally in `runtime/connection.json` (file permissions 0600, directory 0700). This directory is excluded from Git and iteration backups. Database backups contain records and evidence, not the runtime password. Keep these connection settings separately when moving machines.
