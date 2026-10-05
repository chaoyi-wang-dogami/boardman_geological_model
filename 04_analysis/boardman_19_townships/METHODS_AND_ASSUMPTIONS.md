# How the Boardman GemPy pilot was built

This document explains the current [build script](build_gempy_pilot.py), its explicit choices, and its material geological assumptions. It describes the pilot that produced the files in this directory; it is not a claim that the modeled surfaces are geologically verified. The shorter outcome and figures are in [FINDINGS.md](FINDINGS.md).

## 1. What the model represents

The pilot uses interpreted stratigraphy already present in Oregon's Groundwater Information System (GWIS). It represents three **upper boundaries**: the top of Saddle Mountains Basalt, the top of Wanapum Basalt, and the top of Grande Ronde Basalt. GemPy turns these into four broad volumes, from top to bottom:

| Voxel ID | Model volume | What the label means here |
|---:|---|---|
| 1 | Overburden | Everything above the modeled top of Saddle Mountains. It is **not** one mapped formation. |
| 2 | Saddle Mountains | Everything between the modeled tops of Saddle Mountains and Wanapum. This also absorbs interbeds and other units omitted from the pilot. |
| 3 | Wanapum | Everything between the modeled tops of Wanapum and Grande Ronde. This likewise absorbs omitted interbeds. |
| 4 | Grande Ronde and older | Everything below the modeled top of Grande Ronde. The bottom of Grande Ronde is **not** measured or modeled. |

The model is a **continuous, unfaulted, ordered layer stack**. It cannot represent a unit that disappears locally, a repeated sequence across a fault, or a sedimentary interbed as its own body. GemPy's structural-frame approach uses surface points and orientations to define contacts, and its default frame here contains one `default_formation` group with the three surfaces in the order listed above, plus a basement volume. The saved model can be inspected directly to verify that structure. [GemPy's structural-frame documentation](https://docs.gempy.org/tutorials/b_fundamentals/a01_basics.html) explains the surface and group concepts.

## 2. Inputs and identifiers

The script reads three files, leaving them unchanged:

1. [boardman_wells_stratigraphy.csv](../../03_processed/boardman_19_townships/boardman_wells_stratigraphy.csv): interpreted depth intervals, unit codes, source elevations, GWIS site IDs, well report IDs, and coordinates.
2. [boardman_wells_summary.csv](../../03_processed/boardman_19_townships/boardman_wells_summary.csv): each report's location class.
3. [plss_townships.geojson](../../02_gis/reference/plss_townships.geojson): the cached 19-township boundary used for the area of interest (AOI).

The stratigraphy file has **1,854 rows, 423 well report IDs, and 328 GWIS site IDs**. The script treats `gw_site_id` as the physical site identifier. Several report IDs point to the same GWIS site; counting them independently would overstate the amount of geological evidence. The summary file is joined by `well_id` with a `many_to_one` check. Neither `picked_by` nor `sample_source` is used to choose or weight picks. There is no use of lithology, drilling date, completed depth, or the newer county scrape in this pilot.

### Horizontal coordinates

The script treats the CSV latitude and longitude as EPSG:4326 and projects them to **EPSG:26911 (UTM zone 11N, metres)**. It reads the township polygons and projects them to the same CRS. This permits site-distance checks and interpolation in metres. It does not independently verify the original horizontal datum or the precision of every coordinate. The A/B/C/D location classes come from the processed well summary; this script does not calculate or recalibrate those classes.

For each GWIS site, it takes the distinct coordinates attached to reports with **class A or B**. It calculates the straight-line spread between their minimum and maximum easting/northing:

\[
d_{\rm spread}=\sqrt{(E_{\max}-E_{\min})^2+(N_{\max}-N_{\min})^2}.
\]

It uses the **median easting and median northing** of those A/B report locations as the site coordinate. A site is eligible only if that point intersects the 19-township polygon union and `d_spread ≤ 25 m`. The **25 m cutoff is my pragmatic QC choice**, not an error bound supplied by OWRD or a geological threshold. A and B coordinates are treated equally once admitted; the code records A if any A report is present, otherwise B. Four sites with A/B locations have spreads over 25 m; location failures are retained in the contact audit.

### Vertical coordinates

`start_depth` and `start_depth_elev` are taken from the stratigraphy CSV. The script treats depth as feet below the reported site surface and `start_depth_elev` as the corresponding source elevation in feet. It converts a contact elevation by

\[
z_{\rm contact,m}=0.3048\,z_{\rm start,source\ ft}.
\]

It makes **no vertical-datum conversion**. The formal datum of the GWIS elevation fields has not been verified. The calculations are internally in metres, but those Z values must not yet be combined with a DEM or independently surveyed elevations as if the datums were known to match.

For the later *display mask*, the script estimates a source ground elevation on each stratigraphy row as `start_depth + start_depth_elev` (feet), takes the median per GWIS site, and converts it to metres. This assumes both source fields refer to the same site reference and are internally consistent. It is not an independent topographic observation.

## 3. Turning interpreted intervals into contact candidates

The script maps `strat_unit` strings by **case-sensitive prefix**, with a dot boundary:

| Model contact | Accepted unit prefix | Examples |
|---|---|---|
| `top_saddle_mountains` | `Crbg.Smb` | `Crbg.Smb.Pomona`, `Crbg.Smb.ElephantMtn` |
| `top_wanapum` | `Crbg.Wb` | `Crbg.Wb.FrenchmanSprings.SentinelGap` |
| `top_grande_ronde` | `Crbg.Grb` | `Crbg.Grb.N2.SentinelBluffs` |

An exact prefix such as `Crbg.Wb` also matches. Every other label becomes `other` for this contact-extraction step. This mapping assumes the prefixes refer to those three broad basalt families and deliberately discards member- and flow-level distinctions. It does not assert that two detailed labels are equivalent, and it is not a validated, comprehensive stratigraphic correlation table.

Next, rows with identical `(gw_site_id, start_depth, end_depth, strat_unit, start_depth_elev)` are collapsed. This prevents a repeated GWIS site linked to multiple reports from contributing duplicate input points. Differences in interpreter, sample source, report ID, or coordinate are **not** part of this deduplication key. Distinct rows with competing unit names or depth limits remain; the code does not reconcile them.

Within each site, the remaining rows are sorted by `start_depth`, then `end_depth`, then `strat_unit`. For each of the three basalt families, the script selects only the **first (shallowest) interval** with that family. Its `start_depth_elev` becomes a *candidate* top. It assumes the first occurrence marks the upper boundary of the family. If a family is missing from a site, the script creates no candidate; it does **not** infer that the family is geologically absent there. If the family repeats deeper in a well, those deeper occurrences are ignored. Ties in depth follow the stated sort order, including alphabetical unit-name order; the script does not adjudicate competing interpretations at a tied depth.

The candidate is accepted as a recorded transition only if a preceding interpreted interval exists, has a different broad family, and ends within **1 ft** of the chosen interval's start:

\[
\left|d_{\rm previous\ end}-d_{\rm chosen\ start}\right|\leq 1\ {\rm ft}.
\]

The **1 ft tolerance is an analyst choice** for small depth differences. It is not a reported measurement accuracy. A target unit starting at the top of the available record is excluded, even if it could truly crop out, because the file does not establish the contact above it. Gaps or overlaps greater than 1 ft are also excluded. One immediately preceding row is examined; the script does not reconstruct a full geological sequence around each candidate.

Two further cases are rejected as `ambiguous_previous_unit`: a `Sediment.PreCrb` interval immediately above a candidate Saddle Mountains top, and a `Crbg.Undifferentiated` interval immediately above a candidate Grande Ronde top. The former is an apparent order conflict; the latter does not identify which basalt is above Grande Ronde. These two rows remain visible in [contact_audit.csv](artifacts/contact_audit.csv).

Exclusion reasons are assigned in this **priority order**: no adjacent transition; ambiguous preceding unit; ineligible location; missing source elevation. If a candidate has more than one problem, the audit records only the first reason. Thus the reason totals are mutually exclusive, not a count of every issue on every row.

| Stage | Count |
|---|---:|
| Site-and-surface candidates | 273 |
| No adjacent transition | 16 |
| Ambiguous preceding unit | 2 |
| Location not eligible | 35 |
| Missing elevation after the other checks | 0 |
| **Selected contacts** | **220 from 160 GWIS sites** |

The selected contacts are **148 Saddle Mountains**, **56 Wanapum**, and **16 Grande Ronde**. Counts refer to distinct site-and-surface picks, not all stratigraphy intervals. See [model_contacts.csv](artifacts/model_contacts.csv) for every chosen depth, source elevation, converted elevation, site coordinate, and immediately preceding unit.

The preceding label is important. For example, many Wanapum tops follow `EllensburgFm.Mabton`. The pilot treats that as the top of Wanapum but does not model the Mabton interbed as a separate volume. Some Wanapum tops follow `Sediment.PostCrb` or `AlkaliCanyonFm`; the script accepts those transitions without independently proving that Saddle Mountains is absent at those sites.

## 4. GemPy setup and computation

The local model X and Y coordinates are the UTM easting and northing **minus the minimum easting and northing of the township bounding box**. This translation keeps the numerical coordinates smaller; it does not change distances or the CRS. The offsets are stored as `utm_origin_m` in the voxel file. Z remains the converted source elevation in metres.

The script creates a GemPy `SurfacePointsTable` containing all 220 selected contact points and their three surface names. It then creates **one orientation for each surface** at the median X, median Y, and median contact Z of that surface's selected points. Each orientation is the pole vector `(0, 0, 1)`, corresponding to a locally horizontal plane. These are **synthetic constraints**. There are no measured strikes, dips, or orientation errors in the inputs. The medians are locations for the synthetic poles; they are not additional observed contacts. [GemPy documents orientations as pole vectors](https://docs.gempy.org/GemPy%20API/gempy.add_orientations.html).

The surface points and orientations form one `StructuralFrame`. `gp.create_geomodel` receives that frame, the model extent, a dense-grid resolution of **54 × 40 × 48 cells**, and `refinement=1`. Its local extent is approximately X `−500…50,643 m`, Y `−500…37,434 m`, and Z `−450…420 m`. The horizontal span comes from the township bounding box with 500 m padding on each side. The vertical limits were chosen manually to contain the selected contact elevations (about `−364…366 m`) with extra room above and below; they are **not** geological boundaries. Grid spacing is approximately **947 m east–west, 948 m north–south, and 18.125 m vertically**.

The explicit resolution produces the dense regular grid used for the voxel output. `refinement=1` is also passed to GemPy's interpolation options; it was not tuned or tested against other settings. No faults, unconformities, distinct sedimentary layers, topography grid, or independent regional orientation constraints are added to the GemPy model. `gp.compute_model` returns categorical volume IDs on the grid. The script assumes the returned IDs 1–4 correspond to the four volumes listed in Section 1; this correspondence was checked on the saved model. GemPy's [model-creation API](https://docs.gempy.org/GemPy%20API/gempy.create_geomodel.html) documents the extent and resolution arguments.

The `.gempy` file stores the model definition. The separate `.npz` stores computed voxel IDs and grid metadata. Loading the `.gempy` file requires recomputing the solution; GemPy's [save/load guide](https://docs.gempy.org/tutorials/b_fundamentals/f06_save_load.html) also warns that serialization compatibility may change across versions.

## 5. Approximate land surface and masking

The **GemPy computation itself is a rectangular block**, including cells above land and outside the township polygons. The script creates a second, display-oriented array after computing the model:

1. At each horizontal grid-cell center, find the **eight nearest eligible GWIS sites** with a derived ground elevation.
2. Interpolate those eight elevations using inverse squared distance. If a site is within 1 m of the cell center, its squared distance is floored at 1 m² to avoid division by zero:

   \[
   \widehat z(E,N)=\frac{\sum_{i=1}^{8} z_i/\max(d_i^2,1\,{\rm m}^2)}
   {\sum_{i=1}^{8}1/\max(d_i^2,1\,{\rm m}^2)}.
   \]

3. Set a voxel to ID **0** when its horizontal center lies outside the township polygon union or its vertical center lies above the interpolated ground elevation.

This is an **approximate visual mask, not a GemPy topography constraint or a surveyed DEM**. It interpolates and extrapolates site-derived elevations, including between sparsely spaced wells. ID 0 combines two distinct conditions—air and outside AOI—so it should not be interpreted as a geological unit. `contains_xy` tests cell centers rather than polygon-cell intersections; boundary cells may be treated differently from a full geometric clip. Both the raw and masked arrays are retained in [boardman_broad_units_voxels.npz](geological_model/boardman_broad_units_voxels.npz).

## 6. Figures, exports, and checks

The script writes three figures: [contact map](artifacts/pilot_contact_map.png), [central east–west voxel section](artifacts/pilot_block_section.png), and [3D contact-surface view](artifacts/pilot_contact_surfaces_3d.png). The section uses the middle Y grid index. The 3D figure extracts each surface from the uppermost voxel with the corresponding lower-unit ID, so its steps reflect the **grid resolution**, not exact smooth GemPy mesh geometry. Its apparent slopes also depend on the viewing angle and vertical display aspect.

The [ParaView export script](export_paraview.py) separately reads the saved `.npz`, restores the full UTM X/Y coordinates, writes [boardman_broad_units_paraview.vti](geological_model/boardman_broad_units_paraview.vti), and rereads it to verify voxel values, origin, and spacing. `unit_id` is the masked array; `unit_id_unmasked` is the full rectangular model. A separate ParaView session file may use display settings, but it is not used in model creation.

The build script calculates a **nearest-voxel, in-sample difference** at the contact sites that *were used to fit the model*. It finds the top voxel of each lower unit in the nearest X/Y grid column, compares that voxel boundary with the input contact elevation, and reports median and 90th-percentile absolute differences. These combine interpolation and coarse-grid placement error. They are **not** uncertainty estimates, cross-validation, or a test on unseen wells. The values in the current [model summary](artifacts/model_summary.json) are:

| Surface | Median absolute difference | 90th-percentile absolute difference |
|---|---:|---:|
| Top Saddle Mountains | 5.7 m | 17.6 m |
| Top Wanapum | 11.5 m | 27.4 m |
| Top Grande Ronde | 12.0 m | 47.8 m |

The model was saved, loaded, and recomputed in the tested environment. The recomputed grid matched the saved grid in **103,676 of 103,680 cells (99.996%)**; four cells differed. This checks technical round-trip behavior, not geology. The run records Python/GemPy versions, input SHA-256 hashes, model dimensions, counts, and assumptions in `model_summary.json`.

## 7. Decision and assumption register

| Decision or assumption | Why it was made | Consequence or unresolved question |
|---|---|---|
| Treat GWIS site ID as the independent site and collapse identical site intervals | Multiple well reports can link to one site | Different interpretations at one site remain and are not adjudicated; reports are not independent observations. |
| Accept location classes A/B only; use median of their report coordinates | Limit obvious location uncertainty and duplicate-site displacement | Excludes potentially useful C/D sites. The median is a pragmatic site position, not a surveyed position. |
| Require site spread ≤25 m and point inside the township union | Reject inconsistent duplicate locations and outside-AOI coordinates | Cutoff was chosen for this pilot; sensitivity to it has not been tested. |
| Match unit names by `Crbg.Smb`, `Crbg.Wb`, `Crbg.Grb` prefixes | Obtain enough broad contacts for an initial block | Member, flow, and sediment distinctions are lost; broad matching can conceal interpretation differences. |
| Use only the shallowest occurrence of each family per site | Approximate its top | Repeated or faulted sequences and conflicting same-depth labels are not resolved. |
| Require an adjacent, different preceding interval within 1 ft | Avoid creating a top from a truncated log or a major gap | May reject a real surface contact or a valid pick with a larger recording gap. |
| Reject `Sediment.PreCrb` above Saddle Mountains and undifferentiated basalt above Grande Ronde | Avoid two especially ambiguous tops | These are analyst exclusions, retained for review in the audit. Other geological anomalies have not been comprehensively screened. |
| Convert source feet to metres but apply no datum correction | A metric model is needed; the formal GWIS vertical datum is unverified | Absolute Z cannot yet be compared directly with an external DEM or elevation dataset. |
| Use one horizontal synthetic pole per surface | No measured orientations were available | Dip and curvature away from control points are model-generated, not measured. |
| Place all three surfaces in one unfaulted stack | Test a simple, computable regional model | Faults, pinch-outs, unconformities, and sedimentary interbeds are omitted. |
| Model the entire township bounding rectangle and clip only the exported voxels | Simple reproducible grid and AOI display | Surfaces extrapolate through areas with no nearby picks; the mask does not make those regions reliable. |
| Use eight-site inverse-distance ground elevation for a display mask | Avoid rendering a large volume above land | This is not independent topography, uses an arbitrary neighborhood, and has no quantified error. |
| Use a 54 × 40 × 48 grid with fixed extents | Keep the pilot quick to compute and inspect | Cells are nearly 1 km wide; features smaller than that cannot be resolved by the voxel export. |
| Report only in-sample nearest-voxel differences | Check whether the exported grid approximately honors its inputs | Predictive skill, geological validity, and uncertainty remain unmeasured. |

## 8. What would be needed before geological use

The most important next checks are: establish the GWIS vertical datum and site elevation provenance; inspect a sample of picks against original GWIS pages and well reports; review the broad-unit mapping and interbeds with a geologist; map distance to the nearest control point for each surface; test contact elevations on **spatially withheld sites**; compare a verified DEM with the source site elevations; and examine evidence for faults or missing units. In particular, the Grande Ronde surface has only **16 selected sites** across this large AOI. The current model shows that GemPy can compute a 3D block from the available picks; it does not establish that the block is accurate enough for groundwater or other geological decisions.
