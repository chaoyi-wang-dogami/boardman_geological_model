# Raw lithology descriptions and driller patterns

This report uses OWRD records downloaded for 19 Boardman-area townships. A **report** is one OWRD `wl_id`. An **identified well unit** is one well tag within a county, or one report when no tag is available. Several reports can concern one tagged well. “Driller name” means the recorded `bonded_full_name`; it does not establish who wrote an interval description. The only approved name combination here is `GARRY L ZOLLMAN` with `GARRY ZOLLMAN`, both recorded under license `1881.0`, under the analysis label `GARRY ZOLLMAN`. Original names remain in the raw records and `artifacts/well_report_audit.csv`.

Generated figures, tables, and JSON summaries are in [`artifacts/`](artifacts/). The two Markdown reports stay in this directory.

Reproduce the tables and figures in this order:

```bash
uv run python scripts/profile_raw_lithology.py
uv run python scripts/compare_bonded_descriptions.py
uv run python scripts/investigate_bonded_naming_spatial.py
```

## Part I. Data Characteristics

### Motivation

Before comparing descriptions and locations, we need to check source joins, identify reports outside the study area, and avoid counting two reports for one tagged well as two independent wells.

### Method

`01_raw/owrd/wells_raw.csv` supplies report metadata. Per-report `lithology.csv` files supply structured intervals, combined in `03_processed/lithology/lithology_all_raw.csv`. We checked report ID and folder joins, compared every combined interval row with the per-report files, and flagged interval-depth issues. These source counts include **all** reports.

For coordinate QC, check each sourced point against the union of the 19 polygons in `02_gis/reference/plss_townships.geojson`, a cached [BLM PLSS township layer](https://gis.blm.gov/arcgis/rest/services/Cadastral/BLM_Natl_PLSS_CadNSDI/MapServer/1). Points on the boundary count as inside. The code validates all township names against `00_config/owrd_download.yml`; `artifacts/summary.json` records the boundary hash. There is no arbitrary buffer. The check concerns the **19-township union**, rather than the individually recorded township.

For driller calculations, group reports by county and well tag. If the tag is missing, keep that report as its own unit because a physical-well match is unproven. Exclude reports outside the boundary and **abandonment-only** reports (`work_new=0`, `work_abandonment=1`) from geological comparisons. A report marked both new and abandonment remains eligible; this occurs frequently for geotechnical holes. If several eligible geological reports share a tag, choose a new-work report first, then an A/B location, then the earliest completion date and report ID. Keep every alternative in `artifacts/well_report_audit.csv`, including a flag when its interval log differs from the selected one. This is an analysis choice, not a correction to the source.

Select a driller name when it has at least **10 independent A/B well units with structured lithology**. Do not filter on report type, township within the study area, completion decade, or depth. Exclude Zachary Neigel from driller comparisons: 58 of his 61 tagged wells share one coordinate and the same three-description set, so one project would dominate his score. His wells are **not** merged: all 61 tags differ.

### Results and limitations

The download has **7,402 reports** across 19 township keys. **3,067 reports** have structured intervals, totaling **15,586 rows**. All 7,402 metadata files and per-report lithology files are present, and every combined interval row agrees with its source file and report folder. There are zero source-row and folder mismatches.

| Report type | All reports | Reports with structured intervals | Interval rows |
|---|---:|---:|---:|
| Water Well | 4,908 | 1,661 | 12,383 |
| Geotechnical Hole | 1,625 | 1,220 | 2,620 |
| Monitoring Well | 869 | 186 | 583 |
| **Total** | **7,402** | **3,067** | **15,586** |

Among retained rows there are 0 blank descriptions, 0 invalid bounds, 13 zero-thickness rows, 2 rows sharing an interval number, 83 overlap flags, and 33 gap flags. The downloader omitted blank descriptions and rows without numeric bounds, so these zeros describe retained rows only. Source values were not corrected; see `artifacts/interval_qc.csv`.

Location classes come from this repository's rules applied to OWRD coordinate source and estimated horizontal error. **OWRD supplies the error estimate; this project chose the 50/100-foot cutoffs.** These are estimates, not independently surveyed guarantees.

| Class | Meaning | Spatial use |
|---|---|---|
| **A** | Sourced coordinates, estimated error ≤ 50 ft | Included |
| **B** | Sourced coordinates, error > 50 and ≤ 100 ft | Included |
| **C** | Sourced coordinates, error missing or > 100 ft | Excluded |
| **D** | No usable sourced coordinates, or PLSS/centroid-derived source | Excluded |

Of the **3,063 located interval reports before boundary QC**, 433 are A, 1,083 B, 153 C, and 1,394 D; four interval reports are absent from the location table. Boundary QC flags **53 of all 7,402 reports** outside the township union: 6 A, 1 B, 2 C, and 44 D. Three have structured lithology:

| Report ID | Recorded driller | Class | Distance outside | Effect |
|---|---|---|---:|---|
| 457804 | PATRICK WALLACE | A | 34.70 km | Excluded from derived driller analysis |
| 460853 | BRANDON C BROWN | A | 1.20 km | Excluded from derived driller analysis |
| 565542 | BRANDON BROWN | D | 0.29 km | Excluded from derived driller analysis |

The most distant point is report `562573`, about 196.36 km outside; it has no retained interval. Some class D points are just outside a township edge. The boundary flag alone does not establish whether the coordinate or recorded township is wrong. All outliers and source coordinates remain in `artifacts/coordinate_qc.csv`.

Of the 3,067 interval reports, the well-unit audit selects **2,916** for geological comparison, links **79** alternative geological reports to a selected tagged well, flags **69 abandonment-only** reports, and excludes the **3** outside reports. **71 tagged wells** have differing eligible geological interval logs; their alternatives remain available for review. **63 repeated tags** have more than one recorded driller name, often because a later event has a different driller; the selected geological report determines the analytical name. **1,670 of the 2,916 selected units lack a well tag** and therefore use report ID as a provisional key. Among the selected driller cohort, 172 of 1,196 units lack a tag, including 36 of the 619 A/B units. Those may include unrecognized repeat reports.

Kevin Chambers' 12 interval reports describe **six tagged wells**: six new-work logs and six later abandonment-only logs with `BENTONITE CHIPS`. After linking the reports, he has six eligible A/B well units and falls below the 10-well threshold. Aaron Adams has five eligible A/B units and Robert Stadeli has nine, so they also fall below it. The two recorded Zollman names map to one analytical name; their raw spellings remain separate in the audit. Other suspected aliases are **not** combined.

**The 14 selected driller names** below are used in Figures 2–5. Part II and Figure 3 use all their selected geological well units; Part IV uses the A/B subset.

| Analytical driller name | Geological well units | A/B well units |
|---|---:|---:|
| PATRICK WALLACE | 258 | 63 |
| GARRY ZOLLMAN | 233 | 176 |
| BRANDON BROWN | 171 | 112 |
| LARRY BURD | 149 | 28 |
| BRANDON C BROWN | 108 | 78 |
| EDWIN BROWN | 88 | 14 |
| CHAD COURTNEY | 44 | 44 |
| BEN DREYER | 39 | 13 |
| PETER LARSEN | 24 | 24 |
| J TRENT CASTNER | 21 | 14 |
| CHAD N GREGORY | 19 | 19 |
| TERRENCE JACQUES | 17 | 10 |
| CHAD GREGORY | 14 | 14 |
| PAUL SMITH | 11 | 10 |
| **Selected total** | **1,196** | **619** |

### Section summary

The source joins are consistent, but structured lithology covers only 3,067 of 7,402 reports. Location, repeat-report, and work-type checks reduce the comparative cohort to 1,196 identified well units under 14 driller names, including 619 class A/B units for spatial analysis. The original records and every selection decision remain auditable.

## Part II. Vocabulary

### Motivation

Raw interval descriptions are detailed free text. We need to see how many exact strings occur and how often a driller reuses them before designing standardized material labels.

### Method

Figure 1 counts each stored `material_raw` string in **all retained source intervals**, before well-unit selection. For selected drillers, Figure 2 uses one selected geological report per well unit. A phrase counts once per well unit even if it occurs in several intervals. Split each driller's distinct phrases into those found in one versus two or more of that driller's well units. No geological synonyms are merged.

### Results and limitations

Across all **15,586** retained source intervals, there are **3,336 distinct exact strings**. **2,306 (69.1%)** occur in one interval, and **653** more occur in two to four intervals. `BLACK BASALT` occurs in 1,406 intervals and `SAND` in 994. These overall counts include reports excluded from the driller comparison. Uppercasing and collapsing whitespace still yield 3,336 strings; spelling and detailed modifiers remain distinct.

![Fifteen most frequent exact descriptions](artifacts/vocabulary.png)

*Figure 1. The 15 most frequent exact description strings across all retained source intervals. Bar length is the number of interval rows containing that exact string.*

The selected 14 drillers contribute **9,312 intervals** and **1,953 distinct exact strings** across their chosen geological reports. Figure 2 shows each driller's distinct strings and their reuse across independent well units. `BRANDON BROWN` has **526** exact descriptions across **171** units; **135** occur in at least two units and **391** in one unit. These are wording variants and detailed observations, not 526 rock types.

![Exact description vocabulary and reuse for the selected drillers](artifacts/bonded_vocabulary.png)

*Figure 2. Exact descriptions for the 14 selected analytical driller names. Blue strings occur in two or more identified well units; gray strings occur in one. The number on or just beside the blue section gives its count; the number beyond the bar gives the total. The `n` beside each name is its geological well-unit count.*

The [BRANDON BROWN description list](BRANDON_BROWN.md) preserves all 526 strings and their counts. Its long tail includes material, color, hardness, and construction terms. Exact-string counting also treats `GRAY BASALT` and `GREY BASALT` separately. Vocabulary size grows with the amount of logging and detail, so it is not by itself a consistency score.

### Section summary

The source counts above show that most raw exact strings are rare, while Figure 1 identifies the most common ones. Figure 2 and the Brandon Brown list show both reused descriptions and extensive one-well detail. The next part compares *sets of descriptions between wells* to measure wording consistency more directly.

## Part III. Driller interpretation consistency

### Motivation

Do geological logs under the same recorded driller name use more similar descriptions than logs under different selected driller names?

### Method

Represent each selected well unit by the set of distinct exact descriptions in its chosen geological report. For two wells $A$ and $B$, Dice overlap is

$$
D(A,B)=\frac{2|A\cap B|}{|A|+|B|}.
$$

Zero means no shared exact string; one means identical sets. A phrase repeated within a report counts once. For each well, average its Dice score against other wells under the same analytical driller name, excluding itself. Separately, average against wells under the other 13 selected names. Average those well-level values within each driller, giving each well equal weight. Figure 3 uses all **1,196** selected geological well units; it does not filter by type, date, township within the boundary, depth, or location class. No name shuffling is used.

### Results and limitations

For **all 14 drillers**, the same-driller average exceeds the other-driller average. For example, `BRANDON BROWN` has **17.6%** mean overlap with other wells under that name versus **10.8%** with other names. `GARRY ZOLLMAN`, after the approved alias combination, has **23.0%** versus **12.5%**. The full values are in `artifacts/bonded_within_between_similarity.csv`.

![Average exact-description overlap with wells by the same and other drillers](artifacts/bonded_within_between_similarity.png)

*Figure 3. Each row is one analytical driller. Blue is mean Dice overlap with other selected wells under the same name; yellow is mean overlap with wells under other selected names. `n` is the number of selected geological well units.*

This is evidence of wording similarity **associated with a recorded driller**, not proof that a person interpreted identical rocks differently. Drillers may work in different geology or use templates. The recorded field does not identify the author. Untagged reports may still include repeat physical wells; 71 tagged wells have differing eligible logs, for which one representative was chosen.

### Section summary

Figure 3 answers the broad wording question for the revised well-unit cohort: under every selected driller name, different wells have more similar exact descriptions to one another than to wells under other names. Local geology and project practices may contribute to this pattern.

## Part IV. Spatial correlations of driller reports

### Motivation

We want to see whether wells associated with a driller occur near other wells under that name, and whether drillers with stronger local concentration also have more consistent descriptions.

### Method

Use the **619 class A/B identified well units** from the same 14 names. Convert their sourced coordinates to UTM zone 11N for metre distances. For each unit, find its **five nearest other units** and count those under the same analytical driller name. Sum those counts for each driller and divide by five times that driller's A/B unit count. Figure 4 compares this percentage (blue bar) with that driller's percentage of the 619-unit pool (yellow tick). A blue bar above the tick means the name occurs among nearby units more often than its overall share. Both metrics count one report per identified well unit.

Distinct tagged wells can still share a coordinate. As a sensitivity check, remove every selected unit at a coordinate shared with another selected unit and recalculate; the source records remain intact.

Figure 5 places each driller's **mean within-driller Dice on the A/B subset** on the x axis and its five-nearest-unit percentage on the y axis. The figure labels these “Lithology interpretation consistency” and “Spatial Correlation” for readability; they are exact-description overlap and a same-name neighbor percentage, respectively, rather than direct measures of geological interpretation or a spatial autocorrelation coefficient. Both scores use the **same 619 A/B units**. Each point is one driller, and its area reflects that driller's A/B unit count. The x-axis score is separately available in `artifacts/bonded_ab_within_between_similarity.csv`; it differs from Figure 3's broader Dice score because Figure 3 also includes C/D units. The plotted values are in `artifacts/bonded_spatial_vocabulary_relationship.csv`.

### Results and limitations

All 14 drillers have a same-name neighbor percentage above their share of the 619 units. `J TRENT CASTNER` has **81.4%** same-name neighbors versus a **2.3%** pool share; all 14 of his A/B units have distinct exact coordinates. `GARRY ZOLLMAN` has **36.8%** versus **28.4%**, across 176 A/B units. These are concentrations of recorded names, not measures of rock similarity.

![Same-driller share among five nearest well units versus each driller's pool share](artifacts/bonded_neighbor_fraction.png)

*Figure 4. Blue bars are the percentage of five-nearest-unit positions with the same driller name. Yellow ticks are that driller's percentage of all 619 selected A/B units. One unit contributes once, even when several reports share a well tag.*

![Within-driller Dice similarity versus five-nearest-unit percentage](artifacts/bonded_spatial_vocabulary_relationship.png)

*Figure 5. Each point is one of the 14 selected drillers. Horizontal position is mean exact-description Dice against other A/B wells under the same name; vertical position is the percentage of five-nearest-unit positions with that name. Point area reflects A/B well count; the size legend gives actual counts and their shares of the 619-well pool. Both axes use the same A/B well units.*

The plot shows **no clear positive relationship** between these two driller-level scores (Pearson correlation **−0.25**; rank correlation **−0.22**). With only 14 drillers, these descriptive numbers are sensitive to individual names and the choice of score. A driller's overall share of the pool affects its five-neighbor percentage; Figure 4 displays that baseline. Across the selected pool, **16 of 619 units** still share an exact coordinate with another selected unit; **603** remain in the unique-coordinate sensitivity check. The five-neighbor percentage does not measure distance in miles or test whether the *nearby wells themselves* share descriptions. It cannot establish that spatial concentration causes wording consistency.

### Section summary

Figure 4 shows that the selected driller names appear locally concentrated in the A/B pool. Figure 5 shows that drillers with stronger same-name spatial concentration do **not** consistently have higher within-driller description overlap. A direct test of whether nearby wells use more similar descriptions would compare Dice overlap against distance for pairs of wells under each driller.

## Conclusions

The source interval rows match their per-report files, but only 3,067 of 7,402 downloaded reports have retained structured lithology. Boundary QC flags 53 report coordinates outside the study area, including three reports with intervals. Linking repeated tagged-well reports and excluding abandonment-only events leaves 2,916 identified geological well units; 14 driller names meet the 10 A/B-unit threshold after combining the approved Zollman alias. Missing well tags and differing logs for 71 tagged wells limit physical-well identification and representative-log selection.

Exact wording has a long tail. Under each selected driller name, descriptions on different wells are more similar than descriptions under other names (Figure 3). Same-name well units also occur near one another more often than their pool shares suggest (Figure 4), but these driller-level spatial and wording scores do not show a clear positive relationship (Figure 5). Different geology, projects, templates, uncertain coordinates, and unverified report authorship limit interpretation.

The next step toward standardized interval names is to review the flagged alternative logs and remaining name aliases, then group spelling and wording variants while retaining raw text. To test a spatial explanation for wording, compare description Dice directly with distance between well pairs, with attention to shared projects and rock context. No formation-top or between-well geological correlation is inferred here.
