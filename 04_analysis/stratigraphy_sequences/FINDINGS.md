# Boardman stratigraphy sequence audit

The 328 recorded GWIS-site interpretations are numerically consistent within individual intervals, but sequence cleaning needs to preserve their varying geological resolution and report histories. There are four internal gaps, two overlaps, repeated labels at 44 sites, and two sites with label-based ordering questions. Shared reports contain identical saved interpretations; retaining their report links is essential because their drilling depths, dates, locations, and lithology coverage differ.

This exploratory audit was prepared on October 8, 2026 from the three authoritative processed CSVs in `03_processed/boardman_19_townships`. Source values remain unchanged. The audit includes both tops and bottoms as candidate contacts, with no name replacement, boundary adjustment, inferred formation, or elevation-datum assignment. [summary.json](artifacts/summary.json) records the source hashes and exact counts. The conclusions below describe this source snapshot.

## Reproduce and inspect the audit

From the repository root:

```bash
python3 scripts/audit_boardman_stratigraphy.py
python3 -m unittest discover -s tests -p test_stratigraphy_sequence_audit.py -v
```

The audit script requires only Python's standard library. It writes derived outputs here and rejects an output directory inside the authoritative input directory. Re-running replaces these audit artifacts; it does not rewrite the source files. The findings document is a reviewed snapshot; reconcile it with new results if the source hashes change.

| Output | Purpose |
|---|---|
| [row_audit.csv](artifacts/row_audit.csv) | All 1,854 original stratigraphy rows and original columns, with source-row references, hashes, parsed depth columns, and every applicable flag |
| [findings.csv](artifacts/findings.csv) | 380 findings, classified as numerical issues, geometry, metadata gaps, coverage notes, provenance notes, or geological review questions |
| [site_audit.csv](artifacts/site_audit.csv) | All 328 sites, sequence comparisons, report metadata differences, and issue counts |
| [sequence_intervals.csv](artifacts/sequence_intervals.csv) | 1,408 unmodified site interval occurrences, each linked to every equivalent source occurrence; this is an audit representation, not an accepted cleaned sequence |
| [site_report_links.csv](artifacts/site_report_links.csv) | All 423 linked reports and their original summary fields |
| [unit_frequency.csv](artifacts/unit_frequency.csv) | All 44 source labels, counts by interval/report/site/interpreter, and provisional ranks |
| [unit_interpreter_frequency.csv](artifacts/unit_interpreter_frequency.csv) | Frequencies for every unit and recorded interpreter spelling, including blank interpreter values |
| [hierarchy_draft.csv](artifacts/hierarchy_draft.csv) | 48 label-tree nodes, including four unrecorded intermediate nodes, with draft geological roles and unapplied `.general` candidates |
| [observed_transitions.csv](artifacts/observed_transitions.csv) | All 1,080 adjacent site-sequence transitions, retaining the source interval IDs and signed depth separation |
| [contact_lithology_candidates.csv](artifacts/contact_lithology_candidates.csv) | All 1,068 top/bottom candidates in the 121 paired reports, nearest lithology boundaries, and containing/adjacent source rows |
| [strat_lithology_overlaps.csv](artifacts/strat_lithology_overlaps.csv) | 1,389 positive overlaps between interpreted intervals and original lithology intervals, with unchanged material text |
| [paired_lithology_audit.csv](artifacts/paired_lithology_audit.csv) | All 1,342 lithology rows in the paired reports, including rows with unusable geometry and exact thickness residuals |
| [lithology_named_unit_checks.csv](artifacts/lithology_named_unit_checks.csv) | Literal named-unit evidence in lithology; one disagreement requiring review |
| [examples.json](artifacts/examples.json) | Up to five findings per issue code, with every affected original row; empty lists for checks with no findings |
| [proposed_schemas.json](artifacts/proposed_schemas.json) | Row-audit schema, proposed cleaned-interval schema, and a versioned correction register |

`source_row` is a one-based **CSV record ordinal including the header**: the first data record is 2. It is not necessarily a physical file line because quoted material descriptions can contain newlines. Stratigraphy and lithology record references always name their respective source table. The summary source-row reference in `site_report_links.csv` refers to the summary table.

## Verified inventory and joins

All requested count checks passed. Identifiers join without unmatched records, `well_id` and `wl_id` are one-to-one, and the summary's coverage flags and interval counts agree with the actual tables.

| Measure | Verified count |
|---|---:|
| Unique well-report records in summary | 7,402 |
| Configured township/range keys | 19 |
| Morrow reports | 2,553 |
| Umatilla reports | 4,848 |
| Gilliam reports | 1 |
| Stratigraphy interval rows | 1,854 |
| Reports with stratigraphy | 423 |
| GWIS sites with stratigraphy | 328 |
| Reports at shared GWIS sites | 166 |
| Shared GWIS sites | 71 |
| Reports at sites represented by one report | 257 |
| Reports with stratigraphy and processed lithology | 121 |
| GWIS sites represented by the paired reports | 112 |
| Stratigraphy reports without processed lithology | 302 |
| Processed lithology rows across the inventory | 15,586 |
| Reports with processed lithology across the inventory | 3,067 |

These are reports selected for the configured 19 townships, not a complete inventory of Morrow and Umatilla counties. A report record is not automatically an independent borehole, and a GWIS site identifier is not proof of a unique physical borehole.

## Source schemas and missing values

The README and all three schemas were inspected before generating the audit. Complete field lists and per-field blank counts are in `summary.json` under `source_schemas`.

| Table | Grain and principal fields | Relevant cautions |
|---|---|---|
| Summary, 18 columns | One report: `well_id`, `wl_id`, `wl_nbr`, county, township, `gw_site_id`, completed depth/date, received date, coverage flags/counts, URLs, coordinates, location class | `wl_nbr` alone is not globally unique. Report positions and completed depths remain report attributes. |
| Stratigraphy, 21 columns | One report-linked site interval: all three IDs, `start_depth`, `end_depth`, endpoint elevations, `depth_thickness`, `strat_unit`, `sample_source`, `picked_by`, age/error, report metadata, URL, `source_kind`, `scraped_at` | Depth field names omit units; calculations follow the repository's feet convention. Formal elevation datum is unverified. Acquisition dates are not interpretation ages. |
| Lithology, 15 columns | One report interval: report IDs, county, `interval_no`, `from_ft`, `to_ft`, `thickness_ft`, `material_raw`, water-level text, report metadata, coordinates, detail URL | Raw lithology is not a formation identification. Every original description and row remains available. |

All stratigraphy tops, bottoms, thicknesses, labels, report IDs, and site IDs are populated. Five rows lack both endpoint elevations; all belong to site 6676. `sample_source` is blank in 483 rows and `picked_by` in 26 rows. Both age fields are blank in all 1,854 rows, so the data cannot supply numerical geological ages for ordering. Completed depth is blank in 26 of the 423 reports, affecting 92 stratigraphy rows; seven other reports record completed depth as `0.0`. No sentinel replacement was inferred.

Stratigraphy provenance comprises 1,557 `gwis_live` rows and 297 `existing_county_scrape` rows. Scientific sequence comparison includes unit, both depths/elevations, thickness, sample source, interpreter, and age fields. It excludes report-specific metadata, URL, and acquisition metadata from the comparison while preserving them in the audit. Thus identical saved interpretations do not establish independent geological agreement or original-pick accuracy.

## Every recorded stratigraphic label

Rows below count original report-linked intervals, not independent observations. The interpreter column counts distinct nonblank **recorded strings**. A person can appear under several strings. The full interpreter-by-unit table keeps each spelling separately and gives interval/report/site frequencies for it.

| Source `strat_unit` | Interval rows | Reports | GWIS sites | Interpreter strings |
|---|---:|---:|---:|---:|
| AlkaliCanyonFm | 158 | 156 | 122 | 15 |
| Crbg.Grb | 5 | 5 | 1 | 1 |
| Crbg.Grb.N2 | 17 | 17 | 9 | 3 |
| Crbg.Grb.N2.SentinelBluffs | 15 | 10 | 7 | 5 |
| Crbg.Grb.N2.WinterWater | 3 | 3 | 1 | 1 |
| Crbg.Smb.ElephantMtn | 141 | 141 | 117 | 12 |
| Crbg.Smb.Pomona | 203 | 203 | 152 | 16 |
| Crbg.Smb.Umatilla | 101 | 101 | 76 | 14 |
| Crbg.Undifferentiated | 148 | 114 | 82 | 11 |
| Crbg.Undifferentiated.WeatheredFlowTop | 19 | 19 | 13 | 4 |
| Crbg.Wb | 8 | 8 | 5 | 2 |
| Crbg.Wb.FrenchmanSprings | 39 | 35 | 17 | 4 |
| Crbg.Wb.FrenchmanSprings.Ginkgo | 5 | 5 | 4 | 4 |
| Crbg.Wb.FrenchmanSprings.SandHollow | 38 | 27 | 24 | 9 |
| Crbg.Wb.FrenchmanSprings.SentinelGap | 69 | 50 | 38 | 11 |
| Crbg.Wb.FrenchmanSprings.SilverFalls | 3 | 3 | 2 | 2 |
| Crbg.Wb.PriestRapids | 30 | 24 | 17 | 7 |
| Crbg.Wb.PriestRapids.Lolo | 23 | 23 | 17 | 5 |
| Crbg.Wb.PriestRapids.Rosalia | 2 | 2 | 1 | 1 |
| EllensburgFm | 34 | 31 | 22 | 6 |
| EllensburgFm.Byron | 2 | 2 | 1 | 1 |
| EllensburgFm.Mabton | 32 | 32 | 28 | 9 |
| EllensburgFm.Quincy-SquawCreek | 25 | 25 | 20 | 6 |
| EllensburgFm.RattlesnakeRidge | 100 | 100 | 78 | 12 |
| EllensburgFm.Selah | 117 | 117 | 81 | 13 |
| EllensburgFm.SquawCreek | 6 | 6 | 4 | 3 |
| EllensburgFm.Vantage | 25 | 25 | 12 | 5 |
| Other | 2 | 2 | 2 | 1 |
| Sediment.AlluvialFan | 3 | 2 | 2 | 1 |
| Sediment.Interbed.Undifferentiated | 2 | 1 | 1 | 1 |
| Sediment.Loess | 36 | 36 | 31 | 4 |
| Sediment.MissoulaFlood | 9 | 9 | 8 | 5 |
| Sediment.MissoulaFlood.Coarse | 54 | 54 | 45 | 4 |
| Sediment.MissoulaFlood.Fine | 35 | 35 | 28 | 4 |
| Sediment.MissoulaFlood.Gravel | 75 | 71 | 61 | 9 |
| Sediment.MissoulaFlood.Sand | 57 | 54 | 51 | 9 |
| Sediment.MissoulaFlood.Silt | 30 | 26 | 21 | 4 |
| Sediment.PostCrb | 175 | 173 | 122 | 12 |
| Sediment.PreCrb | 1 | 1 | 1 | 1 |
| Sediment.Quaternary | 1 | 1 | 1 | 1 |
| Sediment.Quaternary.Alluvium | 2 | 2 | 1 | 1 |
| Sediment.Quaternary.Alluvium.Coarse | 1 | 1 | 1 | 1 |
| Sediment.Topsoil | 2 | 2 | 2 | 1 |
| Unknown | 1 | 1 | 1 | 1 |

There are 21 nonblank interpreter strings. Case-only groups include `KARL WOZNIAK`/`Karl Wozniak`, `JOSH HACKETT`/`Josh Hackett`, `TERRY TOLAN`/`Terry Tolan`, and four capitalizations of `Jen Woody`. `T TOLAN`, `TL Tolan`, `woodyj1`, organization names, and joint names need an evidence-based identity crosswalk. The audit generates comparison keys but does not merge any identities.

## Draft hierarchy and geological roles

Dot-delimited labels establish a recorded containment tree. That tree mixes geological rank, polarity, facies, age, and weathering attributes; the number of dots does not establish formal rank. The draft expands `Crbg` to Columbia River Basalt Group and its `Smb`, `Wb`, and `Grb` branches to Saddle Mountains, Wanapum, and Grande Ronde Basalt. These are formations in the published group framework. [USGS group overview](https://www.usgs.gov/observatories/cvo/science/columbia-river-basalt-group-stretches-oregon-idaho)

| Recorded branch | Draft role and containment |
|---|---|
| `Crbg` | Group-level intermediate node; no interval is labeled exactly `Crbg` |
| `Crbg.Smb` | Saddle Mountains Basalt formation; intermediate node only; Elephant Mountain, Pomona, and Umatilla are member labels |
| `Crbg.Wb` | Wanapum Basalt formation, with both broadly labeled intervals and Frenchman Springs/Priest Rapids member branches |
| `Crbg.Wb.FrenchmanSprings.*` | Ginkgo, Silver Falls, Sand Hollow, and Sentinel Gap are informal flow units or packages, not four formations |
| `Crbg.Wb.PriestRapids.*` | Lolo and Rosalia distinguish flow/chemical-type packages inside Priest Rapids; retain their occurrence intervals |
| `Crbg.Grb.N2` | N2 is a magnetostratigraphic interval; retain it as a polarity attribute as well as the source-tree node |
| `Crbg.Grb.N2.SentinelBluffs`, `.WinterWater` | Sentinel Bluffs and Winter Water are member names, despite occupying the same token depth as informal Frenchman Springs flow labels |
| `Crbg.Undifferentiated` | Unresolved basalt at group level; do not assign it to a particular basalt formation |
| `Crbg.Undifferentiated.WeatheredFlowTop` | A weathering/flow-top description applied to unresolved basalt; it does not identify a named regional flow |
| `AlkaliCanyonFm` | Named formation indicated by the source code; source-specific nomenclature confirmation remains pending |
| `EllensburgFm`, `EllensburgFm.*` | Broad formation label and named sedimentary interbeds. Byron, Mabton, Quincy-Squaw Creek, Rattlesnake Ridge, Selah, Squaw Creek, and Vantage remain separate; member versus informal rank needs unit-specific confirmation |
| `Sediment.MissoulaFlood.*` | Depositional family with coarse/fine/gravel/sand/silt facies; no universal vertical order follows from those texture names |
| `Sediment.Quaternary.*` | Age and depositional labels with alluvium/coarse subdivisions; not all formal lithostratigraphic ranks |
| `Sediment.PostCrb`, `.PreCrb`, `.Loess`, `.AlluvialFan`, `.Topsoil` | Relative-age, material, depositional, and soil labels. Possible overlap with named formations cannot be resolved from the strings alone |
| `Sediment.Interbed.Undifferentiated`, `Other`, `Unknown` | Explicit unresolved categories; retain them without inventing a formation |

The formal/informal distinction matters: Geolex identifies Sentinel Gap as an informal basalt within Frenchman Springs, while Sentinel Bluffs is a member of Grande Ronde. N2 describes magnetic polarity. [Sentinel Gap](https://ngmdb.usgs.gov/Geolex/Units/SentinelGap_16757.html), [Sentinel Bluffs](https://ngmdb.usgs.gov/Geolex/Units/SentinelBluffs_16754.html), [Winter Water and mapped units](https://pubs.usgs.gov/of/1999/0141/readme.html), [Grande Ronde polarity framework](https://www.usgs.gov/publications/regional-correlation-grande-ronde-basalt-flows-columbia-river-basalt-group-washington)

For broadly resolved parent intervals, the audit proposes separate, unapplied names such as `Crbg.Wb.general`, `Crbg.Wb.FrenchmanSprings.general`, `Crbg.Wb.PriestRapids.general`, `Crbg.Grb.general`, `Crbg.Grb.N2.general`, `EllensburgFm.general`, `Sediment.MissoulaFlood.general`, `Sediment.Quaternary.general`, and `Sediment.Quaternary.Alluvium.general`. These are representation candidates, not new formations. `Crbg.Undifferentiated` already explicitly expresses unresolved basalt, so the audit does not append another `.general` suffix to it. Whether it should map to `Crbg.general` with a separate weathering attribute requires approval.

`EllensburgFm.Quincy-SquawCreek` and `EllensburgFm.SquawCreek` are distinct source labels. Do not treat them as automatic synonyms. Modern naming and the composite label require a reviewed crosswalk; the Geolex Frenchman Springs reference notes a subsequent name change involving Squaw Creek. [Geolex Frenchman Springs history](https://ngmdb.usgs.gov/Geolex/UnitRefs/FrenchmanSpringsRefs_5359.html)

The ordering screen uses a **partial** regional expectation: Saddle Mountains above Wanapum above Grande Ronde; Elephant Mountain → Rattlesnake Ridge → Pomona → Selah → Umatilla → Mabton → Wanapum; Vantage between Wanapum and Grande Ronde; Sentinel Gap above Sand Hollow above Ginkgo; and Lolo above Rosalia. These expectations flag nonoverlapping reversed pairs for review. Silver Falls ordering, Byron, composite interbeds, unresolved basalt, and sediment texture order are not assigned an unverified total rank. The regional report and Geolex references support the partial framework; some publication pages/PDFs were accessible only as indexed passages during this audit, so the detailed geological crosswalk remains provisional. [Regional stratigraphic column and interbeds, report pages 8–9](https://pubs.usgs.gov/wri/1987/4268/report.pdf), [Frenchman Springs history](https://ngmdb.usgs.gov/Geolex/UnitRefs/FrenchmanSpringsRefs_5359.html), [Lolo and Rosalia](https://pubs.usgs.gov/of/1981/0797/report.pdf)

## Verified numerical and geometric findings

Depth calculations use exact decimal arithmetic with no gap/overlap tolerance. Gaps are uncovered ranges between recorded intervals, calculated using the deepest preceding bottom so nested overlaps do not create false gaps. Overlap checks compare every valid interval pair. A numerical gap or overlap is verified; its cause and geological correction are not.

| Check | Findings | GWIS sites | Linked reports affected | Meaning |
|---|---:|---:|---:|---|
| Missing, nonnumeric, or nonfinite top/bottom depths | 0 | 0 | 0 | Every stratigraphy depth is assessable |
| Negative depths | 0 | 0 | 0 | No violations of the positive-down convention |
| Reversed top/bottom depths | 0 | 0 | 0 | Every bottom is deeper than its top |
| Zero-thickness stratigraphy | 0 | 0 | 0 | Every interpreted interval has positive thickness |
| Missing/invalid recorded thickness or depth-thickness mismatch | 0 | 0 | 0 | Every thickness equals bottom minus top |
| Duplicate label/top/bottom intervals within a report sequence | 0 | 0 | 0 | Shared-report copies are counted separately from this check |
| Missing endpoint elevations | 5 | 1 | 1 | Five original intervals remain usable for depth auditing |
| Nonnumeric/nonfinite elevations, elevation-thickness mismatch, inconsistent depth-plus-elevation offsets | 0 | 0 | 0 | Where populated, elevations are algebraically consistent; this does not verify their datum |
| Internal uncovered gaps | 4 | 3 | 3 | Preserve uncovered ranges; do not insert units |
| Overlapping interval pairs | 2 | 1 | 1 | Both at site 940 |
| First recorded top below zero | 16 | 16 | 17 | Coverage notes, not inferred missing formations |

The 1,080 adjacent transitions comprise 1,074 touching pairs, four gaps, and two overlaps. Category counts are not mutually exclusive across sites. Each finding can reference multiple intervals and linked reports; `source_interval_rows` in the summary counts distinct affected original records.

### All four gaps

| GWIS site | `well_id` | `wl_id` | Stratigraphy source records | Original boundaries | Gap |
|---|---|---|---|---|---:|
| 17692 | UMAT_0005342 | 250508 | 688, 689 | AlkaliCanyonFm ends 110.00; Pomona starts 111.00 | 1.00 ft |
| 15900 | UMAT_0005858 | 250956 | 748, 749 | MissoulaFlood.Gravel ends 154.00; ElephantMtn starts 154.50 | 0.50 ft |
| 15899 | UMAT_0005859 | 250957 | 752, 753 | Loess ends 5.00; MissoulaFlood.Gravel starts 8.00 | 3.00 ft |
| 15899 | UMAT_0005859 | 250957 | 753, 754 | MissoulaFlood.Gravel ends 148.00; ElephantMtn starts 151.00 | 3.00 ft |

The gaps total 7.50 ft across these sequences; they do not establish a particular omitted unit. Even the 0.50 ft gap remains visible rather than being silently rounded away.

### Both overlaps at site 940

Report `MORR_0001751`, `wl_id=223676`:

| Stratigraphy source records | Original intervals | Overlap | Midpoint that could be tested after approval |
|---|---|---:|---:|
| 314, 315 | EllensburgFm.Selah 202.00–273.00; Crbg.Wb.PriestRapids.Lolo 260.00–320.00 | 13.00 ft | 266.50 ft |
| 316, 317 | Crbg.Wb.FrenchmanSprings.SentinelGap 320.00–519.00; Crbg.Wb.FrenchmanSprings.SandHollow 461.00–555.00 | 58.00 ft | 490.00 ft |

Those midpoint numbers are arithmetic illustrations only. A split would change the earlier bottom and later top and could require derived elevation changes; it must retain original boundaries and a decision record. Nearby interpretations, the original picks, and geological review must establish whether a split is appropriate. No split was applied.

### Elevation and incomplete-coverage examples

Site 6676, `MORR_0000561`, `wl_id=222879`, has blank top and bottom elevations in all five intervals, stratigraphy records 48–52: PostCrb 0–10 ft, Alkali Canyon 10–22 ft, Lolo 22–134 ft, Quincy-Squaw Creek 134–140 ft, and Frenchman Springs 140–633 ft. The depth sequence can be audited without filling its elevations.

First recorded tops include site 16273 (`UMAT_0001540`) at 25 ft, site 17224 (`UMAT_0002133`) at 215 ft, and site 16205 (`UMAT_0006262`) at 150 ft. These are the starts of recorded interpretation coverage. They do not prove that the overlying units are absent and do not disqualify the recorded top as a candidate contact.

## Verified occurrences requiring geological review

| Review flag | Findings | GWIS sites | Linked reports affected |
|---|---:|---:|---:|
| Same source label occurs more than once | 62 site/unit groups | 44 | 56 |
| Recorded ancestor and descendant labels coexist | 24 site/label pairs | 9 | 13 |
| Undifferentiated basalt coexists with identified basalt subdivisions | 17 site groups | 17 | 25 |
| Unexpected label-based order | 4 interval pairs | 2 | 2 |
| Site interval bottom exceeds linked report completed depth | 167 original rows | 81 | 98 |
| Nonpositive report completed depth | 7 report findings | 7 | 7 |
| Literal lithology unit name differs from overlapping interpreted label | 1 | 1 | 1 |

Repeated labels are verified occurrences, not demonstrated mistakes. Adjacent repetitions can represent separate flows or separately described intervals; separated repetitions can represent recurring facies, unresolved packages, or an interpretation problem. Merging them would lose interval occurrences even when their names match.

Concrete examples:

- Site 9413, `MORR_0000591`, `wl_id=222902`: Sentinel Gap occurs at 352–435, 450–575, and 589–742 ft, separated by undifferentiated basalt at 435–450 and 575–589 ft. Another undifferentiated interval runs 742–753 ft, followed by Sand Hollow at 753–790 ft. Keep all three named occurrences and all intervening intervals; the names do not establish three separate regional formations.
- Site 17693, `UMAT_0002307`, `wl_id=252008`, records Missoula-flood gravel 0–38 ft, silt 38–50 ft, then gravel 50–53 ft (records 888–890). A global gravel-before-silt rule would destroy a legitimate recorded alternation unless independent evidence shows a mistake.
- Site 14827, `UMAT_0056806`, `wl_id=448079`, has adjacent AlluvialFan intervals 19–57 and 57–62 ft (records 1411–1412). Their lithology includes a transition to `CALECHI` at 57 ft. Removing the boundary because the unit label repeats would lose that source distinction.
- Site 941, `MORR_0000598`, `wl_id=222907`, has Sentinel Gap 445–705 ft, Sand Hollow 705–870 ft, and the broader Frenchman Springs label 870–950 ft (records 116–118). The broad interval may be correctly resolved only to member level; it need not be forced into a named flow.
- Site 833, `MORR_0000512`, `wl_id=222856`, has N2 793–945 ft followed by Winter Water 945–1,060 ft (records 11–12). This mixes polarity-level resolution with a member name, rather than demonstrating an overlap.
- Site 75, `UMAT_0001183`, `wl_id=251841`, mixes named Selah/Mabton/Vantage with broad Ellensburg at 657–659 ft, and Sentinel Gap with broad Frenchman Springs below it. The same interpretation is linked to `UMAT_0050954`; these report copies do not provide two independent sequences.

There are no inversions among the tested named regional basalt formations, the major ordered Saddle Mountains/interbed framework, the tested partial Frenchman Springs flow order, or Lolo/Rosalia. The two flagged sites instead concern the meaning of relative-age sediment labels:

1. Site 1064, `UMAT_0002049`, `wl_id=248534`, records PostCrb 0–20 ft → undifferentiated basalt 20–40 → PostCrb 40–120 → basalt 120–200 → PostCrb 200–280 → basalt 280–500 (records 537–542). Three nonoverlapping basalt/PostCrb pairs trigger the screen. The alternation is verified; whether `PostCrb` was used loosely for interbeds, or the interpretation needs revision, is unresolved.
2. Site 14804, `MORR_0000711`, `wl_id=313399`, records PreCrb 0–13 ft above Elephant Mountain 13–110 ft (records 1198–1199). The label-based expectation is contradicted, but relabeling PreCrb requires checking its original meaning and source evidence.

### Report depth discrepancies

Of the 98 affected reports, 91 have a positive recorded completed depth and seven record zero. Zero is retained and flagged; it is not treated as a verified missing-value code. The comparison establishes a discrepancy between saved site and report attributes, not a rule for clipping the site interpretation.

At site 42, `MORR_0000563` records a completed depth of 263 ft, while `MORR_0051047` records 861 ft; both link the same site interpretation reaching 861 ft. At site 67, `UMAT_0000463` records 240 ft and `UMAT_0054135` records 430 ft, while the interpretation reaches 430 ft. At site 1, both linked reports record 680 ft, while the Umatilla interval ends at 688 ft. These different cases deserve separate source-history checks rather than one automatic truncation rule.

## Shared interpretations and information loss

All 71 shared sites have identical scientific interval multisets across their linked reports, including interpreter and sample-source fields. The numeric-equivalent comparison, geometry comparison, and original scientific row-order comparison also show one variant at every site. There are **zero saved linked-report interpretation conflicts**.

Grouping equivalent report copies produces 1,408 site interval occurrences from 1,854 report-linked rows: 446 repeated copies can be excluded from geological sample counts. This does not mean dropping 446 source records. The full row audit retains them, and every site occurrence has a list of its equivalent original records. Repeated intervals inside one report are never deduplicated by this procedure.

Reducing 423 report records to one per site would remove 95 report links unless a separate link table is retained. Among the 71 shared sites, all have differing completion dates, 59 have differing completed depths, 13 have differing latitude/longitude values, and eight have differing location classes. Some differences include blanks, so these are differences in recorded values, not necessarily physical displacement or contradictory drilling measurements.

For a concrete deterministic loss example, keeping only the alphabetically first `well_id` at each site would retain 96 of the 121 paired reports. It would discard 25 paired report observations and eliminate processed-lithology coverage for 16 of the 112 paired sites. The audit's representative row is only a serialization choice; all report links and all available lithology comparisons remain intact.

This grouping preserves the saved interpretation content. It does not prove sites are independent physical boreholes, establish the provenance of every original pick, or justify assigning a single site coordinate from one linked report.

## Contacts compared with lithology

The paired subset has 534 report-linked stratigraphy intervals and 1,342 lithology rows. Comparing both ends of every interpreted interval gives 1,068 candidate endpoint rows:

| Geometric relationship | Top/bottom candidate rows | Distinct report/depth locations |
|---|---:|---:|
| Exactly matches a valid lithology endpoint | 777 | 499 |
| Falls inside a valid lithology interval | 188 | 97 |
| Falls outside recorded lithology extent | 103 | 60 |
| Falls in an internal lithology gap or cannot be assessed | 0 | 0 |
| Total | 1,068 | 656 |

An adjacent unit bottom and next unit top can be the same depth. Both candidate roles are retained, but the 656 distinct report/depth count prevents confusing them with 1,068 independent contacts. Neither denominator represents distinct formation-top observations or unique physical boreholes. Exact matches include the first and last lithology endpoints, so a match can have evidence on only one side.

Examples directly checked against original rows:

| Report and site | Stratigraphy candidate | Original lithology evidence | Implication |
|---|---|---|---|
| `UMAT_0000450`, site 63, `wl_id=247545` | Alkali Canyon bottom / Lolo top at 159 ft, stratigraphy 415–416 | Lithology 118 ends `SHALE BLACK HARD` at 159 ft; row 119 starts `BASALT` at 159 ft | Exact sediment/basalt transition supports checking the contact; it does not independently identify Lolo |
| `UMAT_0001543`, site 1049, `wl_id=248252` | Alkali Canyon bottom / Elephant Mountain top at 148 ft, stratigraphy 455–456 | Lithology 301 is `GRAVEL`, 95–149 ft; nearest boundary is 149 ft | Candidate lies 1 ft inside a gravel interval; retain both source depths for review |
| Same report | Elephant Mountain bottom / Rattlesnake Ridge top at 167 ft, stratigraphy 456–457 | Lithology 303 is `ROCK, HARD, WITH CLAY SEAMS`, 155–197 ft | A broad driller description spans the interpreted contact; lack of an exact endpoint is not grounds to reject it |
| `UMAT_0005857`, site 15901, `wl_id=250955` | Rattlesnake Ridge at 102–109 ft, stratigraphy 745 | Lithology 851 is `SILT, ASH SANDY GRAVEL, SELAH INTERBED`, 102–104 ft | Explicit naming disagreement at an exact upper boundary; a geologist must adjudicate |
| Same report | Pomona bottom at 119 ft, stratigraphy 746 | Last lithology interval ends at 111 ft | Candidate is 8 ft beyond that report's lithology extent; it may still be a site-level interpretation |
| `UMAT_0006274`, site 10835 | PostCrb top at 0 ft, stratigraphy 785 | Recorded lithology begins at 440 ft | Outside coverage can occur above the recorded log as well as below it |

All 1,342 paired lithology records were also screened for literal names using the 19 explicit patterns saved in `summary.json`. The only positive named-unit overlap was the Selah/Rattlesnake Ridge discrepancy above. This restricted literal-text screen cannot identify unnamed formations or resolve abbreviations, synonyms, or reworked material.

Eleven paired lithology rows have numerical flags: one zero-thickness interval (`MORR_0052638`, record 12097, 1,076–1,076 ft) and ten exact thickness residuals smaller than 0.00000000000001 ft. The latter resemble floating-point serialization residue, such as `0.09999999999999432` for a 67.0–67.1 ft interval. Their original values and residuals remain visible; they are not evidence of geological boundary errors. The zero-thickness row is retained in the lithology audit and excluded only from positive-length geometric comparisons.

## Proposed schemas

The machine-readable specification is [proposed_schemas.json](artifacts/proposed_schemas.json). The present `sequence_intervals.csv` demonstrates occurrence keys and provenance links but leaves `unit_standardized`, `top_ft_corrected`, and `bottom_ft_corrected` blank.

| Table | Grain | Required content |
|---|---|---|
| Source row audit | One original stratigraphy row | Every original field; source file/hash/record ordinal; all three IDs; site/variant/occurrence links; parsed depths; all issue codes; nullable standardized name and corrected top/bottom; correction source/reason/review status |
| Finding/evidence table | One check affecting one or more rows | Finding ID; classification; site and variant; affected source rows/report IDs; exact numerical or label relationship; explanation; evidence links; review status |
| Accepted site interval | One occurrence in a reviewed site/interpretation version | Stable occurrence ID and order; `gw_site_id`; all linked `well_id`/`wl_id` values; all source rows/hashes; source and standardized labels; rank/parent/resolution; original and derived tops **and** bottoms, depths **and** elevations; units/datum status; independent contact statuses; decisions and issue flags; report-coordinate provenance links |
| Correction register | One versioned name or endpoint decision | Decision ID; interval/sequence version; field; original and derived value; mechanical or geological method; reason; evidence; reviewer/time/approval status; algorithm version |

Keep physical-borehole identity separate from report and GWIS identifiers until independently established. A shared site's lithology should remain linked to the report that supplied it. Keep N2 polarity and weathering as explicit attributes if an approved geological hierarchy separates them from formal rank.

## Deterministic cleaning workflow to review

1. Freeze the source snapshot with hashes and immutable row references. Retain all raw values and all report links. Verify joins, counts, and field-specific null conventions.
2. Build scientific sequence signatures as multisets. Group identical linked report copies for counting only, preserving occurrence multiplicity and complete provenance. Keep different signatures as separate interpretation variants; never select a winner automatically.
3. Parse depths with decimal arithmetic and order candidate intervals by top, bottom, label, and source occurrence. Retain the original row order. Generate every applicable QC flag rather than stopping at the first problem.
4. Review and version a unit-name crosswalk. Separate geological rank from facies, age, polarity, and weathering. Add approved `.general` representation to appropriate broad parents in derived columns only. Preserve unresolved labels and avoid implying that unrecorded children are absent.
5. Treat every recorded top and bottom as a candidate. Attach adjacent interval context, gaps/overlaps, repeated occurrences, report depth/coverage, lithology matches and descriptions, and naming conflicts. Do not require a preceding interval as a universal rule for admitting a top.
6. Review the two ordering sites, site 940 overlaps, and the explicit lithology naming disagreement against original GWIS picks and well reports. Add nearby-well comparisons, maps, and cross sections to the evidence. Review coordinate quality and report histories before deciding which reports represent comparable physical locations.
7. Resolve boundaries only in derived columns after approval. A gap may remain unknown. For an overlap, retain both original boundaries; test a midpoint alongside other supported interpretations rather than silently adopting it. Record any derived elevation change and its datum/offset evidence separately.
8. Export a versioned accepted sequence containing both interval endpoints and a top/bottom contact table with review statuses. Verify source values are recoverable, occurrence counts are conserved, shared copies do not increase sample weight, and every changed value has an approved decision. Leave unresolved observations explicitly available for later use.

Mechanical work supported now is parsing, provenance linking, exact arithmetic, duplicate-copy identification, reproducible ordering, and generation of review flags. Changing geological labels, merging repeated occurrences, filling gaps, splitting overlaps, clipping to report depth, inferring missing units, choosing site coordinates, and assigning/translating an elevation datum require additional evidence or approval.

## Interpretation questions before corrections

- Should broad parent observations use the proposed `.general` labels, and should group-level undifferentiated basalt retain its current label or map to `Crbg.general` with weathering separated? Which rank/alias reference should govern the formal crosswalk, especially N2, Winter Water, and the two Squaw Creek labels?
- For site 940, should a midpoint split be included as a **review-only scenario**, with candidate boundaries at 266.50 and 490.00 ft, or should source review precede any proposed boundary change?
- What original evidence should decide the PostCrb alternation at site 1064, the PreCrb label at site 14804, and Selah versus Rattlesnake Ridge at site 15901? No replacement name follows from this audit alone.
- How should drilling histories and source elevation provenance be verified before accepting intervals beyond a report's completed depth or comparing absolute elevations? The formal vertical datum remains unknown.

## Verification

All requested inventory counts were reproduced from the authoritative files. The audit checks source hashes before and after execution. Original stratigraphy columns are retained verbatim in the row audit, every source record maps to one occurrence, and every paired report contributes its own lithology comparison. Unit/interpreter counts, sequence findings, and candidate contacts are deterministic for this snapshot.

The audit tests cover exact decimal adjacency, nested overlaps and coverage gaps, missing/nonfinite/negative/reversed/zero depths, elevation identities, repeated versus duplicate occurrences, multiset signatures, interpreter conflicts, numeric versus literal equality, ancestor labels, broad versus named basalt resolution, partial order, incomplete upper coverage, tied lithology endpoints, lithology gaps, and literal/composite unit-name matching. Nearby-well geological validation, source-pick adjudication, formal vertical datum verification, and acceptance of the name hierarchy remain open review work.
