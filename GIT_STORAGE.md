# Git storage policy

Git stores the project's code, configuration, documentation, tests, dependency
lockfile, audit findings, decisions, manifests, and lightweight source metadata.
Downloaded data and generated products remain local and need separate backup.

## October 9, 2026 cleanup

The cleanup removes 141 existing files from Git tracking, totaling 170,388,451
bytes (170.4 MB). Every removed file remains at its original local path with
unchanged contents. The operation uses `git rm --cached`, not file deletion.

The user subsequently requested a basemap repair folded into this commit.
The iteration 4 map now loads USGS on startup; its previous HTML is preserved
locally in the repair audit, and its embedded well data remain unchanged.
The display repair does not add generated HTML or backups back to Git.

| Local-only content | Files | Approximate MB |
|---|---:|---:|
| PostgreSQL release backup | 1 | 57.7 |
| Downloaded GWIS page caches | 70 | 57.7 |
| Generated maps and plotting datasets | 15 | 44.9 |
| Generated PNG/PDF figures | 10 | 8.3 |
| Generated RockWorks workbook | 1 | 0.9 |
| Generated CSVs, model exports, extracted page tables, examples, and log | 44 | 0.8 |

The new ignore rules prevent ordinary `git add` from adding these products
again. Source map templates, JavaScript, SQL, Compose configuration, Leaflet
vendor files/license, and all iteration manifests and audit documentation remain
tracked. Lightweight saved height-source metadata remain tracked. Original
Morrow County query inputs and the small PLSS reference also remain tracked.

## Local data and reproducibility

Excluding a file from Git does not make it disposable. In particular, keep the
frozen iteration CSVs, database backups, downloaded source evidence, and their
manifests together in separate project storage. Historical evidence may not be
recoverable byte-for-byte by downloading it again. Existing manifests continue
to identify the exact local files and their hashes; they are not rewritten by
this cleanup.

A fresh clone contains the implementation and audit documentation, not the
complete dataset. Supply the local data package to reproduce CSV-based stages,
or restore iteration 4's `outputs/boardman.dump` into a compatible PostgreSQL /
PostGIS installation using the shared database instructions. Restoring the
database provides its stored records and original source bytes. Generated map
snapshots can then be written to a new output path. Links to local-only maps and
data in documentation work when the corresponding project files are present.

## History and Git commands

The first cleanup was a normal follow-up commit and left data in older commits.
On October 9, 2026, the user authorized removing those files from Git history.
The history rewrite removes 146 exact local-only paths across all seven source
commits, including the database dump, maps, caches, exports, and older plots.
The filtered current tree matches the previous tree before this policy update;
source files and geological values are unchanged. See
[GIT_HISTORY_CLEANUP.json](GIT_HISTORY_CLEANUP.json) for the path list, tool,
recovery locations, and checks.

The rewritten history has new commit IDs. The push targets only `master` and
checks its exact previous remote commit before replacing it. Other existing
clones should be re-cloned, or their local work carefully rebased onto the new
history; merging the old history back would reintroduce the large files.

A verified recovery bundle and commit mapping are stored outside this project
in the sibling `boardman_git_history_recovery_20261009_183510/` directory.
The original checkout retains old Git objects/reflogs locally for recovery;
they are not part of the rewritten remote branch. Do not push recovery history
back to the remote.

To inspect ignored local files without modifying them:

```bash
git status --ignored --short
git check-ignore -v <path>
```

Avoid `git add -f` for these data products. Avoid `git clean -fdx`: it deletes
ignored local data. Private database credentials remain in the ignored
`04_analysis/stratigraphy_sequences/database/runtime/` directory.
