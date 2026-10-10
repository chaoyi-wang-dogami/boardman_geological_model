# Shared Boardman database tools

The accepted first implementation is [versions/v001](versions/v001/README.md). It is shared by data iterations; do not copy or edit it for each new iteration. Create `v002` for a changed shared implementation and record its hashes in the new iteration manifest.

The live PostgreSQL/PostGIS database is in Docker's named volume `boardman_stratigraphy_pgdata`. Iteration directories contain frozen backups, maps, checks, and decisions. A map is a generated snapshot; it does not write to or refresh itself from the database.

Private connection settings are generated locally in `runtime/connection.json` (file permissions 0600, directory 0700). This directory is excluded from Git and iteration backups. Database backups contain records and evidence, not the runtime password. Keep these connection settings separately when moving machines.
