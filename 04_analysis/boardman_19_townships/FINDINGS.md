# Boardman 19 townships: exploratory GemPy model

The contact-selection rules, GemPy setup, assumptions, and output checks are documented in [METHODS_AND_ASSUMPTIONS.md](METHODS_AND_ASSUMPTIONS.md).

## Finding

**A coarse 3D block model can be computed from the existing interpreted stratigraphy.** The saved GemPy model has three contact surfaces: the top of Saddle Mountains Basalt, Wanapum Basalt, and Grande Ronde Basalt. It is a technical and geological *pilot*, not yet a validated map of the subsurface. The main limits are sparse deep contacts, simplified sedimentary interbeds, an unverified elevation datum, and the lack of testing at withheld wells.

![Three broad contact surfaces in the exploratory GemPy model](artifacts/pilot_contact_surfaces_3d.png)

**Figure 1.** Computed broad-unit surfaces within the 19-township area. These are interpolated surfaces. Their smooth continuation between and beyond well controls is a modeling assumption; it is not additional observed geology.

## Inputs and method

The inputs are [Boardman stratigraphy](../../03_processed/boardman_19_townships/boardman_wells_stratigraphy.csv), [well summary and location classes](../../03_processed/boardman_19_townships/boardman_wells_summary.csv), and the cached [19-township boundary](../../02_gis/reference/plss_townships.geojson). The source contains 1,854 stratigraphy rows linked to 423 well reports and 328 GWIS sites. Repeated appearances of the same GWIS site under different reports count as one observation.

For each site, the first interval assigned to `Crbg.Smb`, `Crbg.Wb`, or `Crbg.Grb` supplies a possible *top* contact for that basalt family. I accepted it only when the preceding interpreted interval ends at approximately the same depth (within 1 ft) and has a different unit. This avoids turning the first row in a truncated log into an invented contact. I used locations classed A or B, required the site to lie in the cached township polygons, and excluded sites whose A/B report locations differ by more than 25 m. The source elevations were converted from feet to metres with 0.3048; longitude and latitude were projected into EPSG:26911. **The formal vertical datum of the GWIS elevation fields has not been verified**, so the model must not yet be merged with an independently referenced DEM or other elevation dataset.

The resulting GemPy model treats the three contacts as an ordered stack. It assumes a horizontal orientation at one representative point on each surface because the input has no measured dip. It collapses Ellensburg interbeds and other sedimentary intervals into the broad adjacent units. The raw GemPy result is a rectangular block. A separate voxel array masks cells outside the township polygons and above an **approximate** land surface interpolated from the GWIS site elevations. That surface is not a DEM.

![Map of contact control points](artifacts/pilot_contact_map.png)

**Figure 2.** The 220 distinct site-and-surface contacts used by the pilot. Several sites supply more than one contact. The Grande Ronde surface has much less control than the other two, particularly across large parts of the area.

| Contact | Distinct GWIS sites used |
|---|---:|
| Top Saddle Mountains | 148 |
| Top Wanapum | 56 |
| Top Grande Ronde | 16 |

Of 273 candidate contacts, 220 from 160 sites were used. Sixteen had no adjacent transition to establish a top. Two had ambiguous preceding units (`Sediment.PreCrb` above Saddle Mountains and `Crbg.Undifferentiated` above Grande Ronde). Another 35 failed the location screen, which includes unavailable A/B coordinates, locations outside the township polygons, or conflicting coordinates for one site. All candidates and their reasons are in [contact_audit.csv](artifacts/contact_audit.csv); the selected inputs are in [model_contacts.csv](artifacts/model_contacts.csv).

![East-west section through the pilot block](artifacts/pilot_block_section.png)

**Figure 3.** Central east–west slice through the voxel model. The black line is an approximate land surface from well elevations. Empty space above it is masked. The slice is one section through a 3D grid and does not show every input well.

## What the pilot establishes—and what it does not

GemPy 2026.0.3 computed and saved a four-volume block: overburden, Saddle Mountains, Wanapum, and Grande Ronde plus older material. The grid is 54 × 40 × 48 cells across approximately 51 × 38 × 0.87 km. The vertical cells are about 18 m thick, so stepped boundaries in Figure 3 partly reflect grid resolution. The model can be loaded and recomputed; a round-trip check agreed with the saved voxel grid in more than 99.99% of cells. [GemPy's documentation](https://docs.gempy.org/tutorials/b_fundamentals/f06_save_load.html) notes that its saved model format preserves the model definition and requires recomputation of the solution.

Comparing the grid with the *same contacts used to build it* gives median absolute differences of about 5.7 m, 11.5 m, and 12.0 m for the three surfaces respectively. These are **in-sample nearest-voxel differences**, affected by the coarse grid and horizontal placement. They do **not** measure predictive accuracy. Their 90th-percentile absolute differences are 17.6 m, 27.4 m, and 47.8 m. Details and software versions are recorded in [model_summary.json](artifacts/model_summary.json).

The largest geological uncertainties are:

- Only 16 independent sites constrain the top of Grande Ronde. Its continuation across the full 19-township area is strongly extrapolated.
- A name such as `EllensburgFm.Mabton` represents an interbed that this four-volume simplification cannot show. The category called “overburden” also groups several distinct sedimentary units.
- The chosen contact may depend on how much of a site's stratigraphy was interpreted, and duplicate well reports can provide different location coordinates for one GWIS site.
- No independent topography, measured orientations, faults, or spatially withheld wells were used to constrain or validate the pilot.
- The GWIS source elevation datum remains unverified. Only the source feet-to-metres conversion has been made.

## Artifacts and reproducibility

- [GemPy model definition](geological_model/boardman_broad_units.gempy)
- [Computed voxel arrays](geological_model/boardman_broad_units_voxels.npz), including the raw GemPy unit grid, the township-and-terrain-masked grid, approximate land surface, model extent, CRS origin, and unit names. Unit index 0 means air or outside the township area.
- [ParaView VTI volume](geological_model/boardman_broad_units_paraview.vti), exported from the voxel arrays with full EPSG:26911 easting and northing coordinates. `unit_id` is the masked grid; `unit_id_unmasked` is the rectangular GemPy result. The VTI format does not itself establish the vertical datum.
- [Build script](build_gempy_pilot.py) and [input audit](artifacts/contact_audit.csv)
- [ParaView export script](export_paraview.py), which reads the voxel arrays and verifies all cell values after writing the VTI.

The pilot was run with Python 3.12.14, GemPy 2026.0.3, NumPy 2.5.3, pandas 3.0.6, GeoPandas 1.2.0, and Matplotlib 3.11.2 in an isolated environment. To repeat it from the repository root:

```bash
uv venv --python 3.12 /tmp/boardman_gempy_venv
uv pip install --python /tmp/boardman_gempy_venv/bin/python gempy==2026.0.3 numpy==2.5.3 pandas==3.0.6 geopandas==1.2.0 matplotlib==3.11.2
/tmp/boardman_gempy_venv/bin/python 04_analysis/boardman_19_townships/build_gempy_pilot.py
uv pip install --python /tmp/boardman_gempy_venv/bin/python pyvista==0.47.1
/tmp/boardman_gempy_venv/bin/python 04_analysis/boardman_19_townships/export_paraview.py
```

### Viewing in ParaView

1. Open `geological_model/boardman_broad_units_paraview.vti` and click **Apply**.
2. Select the VTI source, add a **Threshold** filter, select the cell-data array `unit_id`, and retain values **1 through 4**. This removes 0, which marks air and cells outside the township area. Click **Apply**.
3. Set **Color By** to `unit_id` (cell data). In **Edit Color Map**, turn on **Interpret Values As Categories** and annotate 1 = Overburden, 2 = Saddle Mountains, 3 = Wanapum, and 4 = Grande Ronde and older. ParaView documents this categorical-color workflow in its [color-map guide](https://docs.paraview.org/en/latest/ReferenceManual/colorMapping.html).
4. To inspect the interior, apply **Slice** to the thresholded model. An east–west slice has normal `(0, 1, 0)`; move its Y origin to explore different northings. **Clip** is useful for seeing the interior of the 3D block.

The horizontal coordinates are EPSG:26911 metres. The Z values are metres converted from GWIS source elevations with an **unverified vertical datum**. The model spans about 51 km horizontally but less than 1 km vertically, so visual vertical exaggeration can help; a ParaView **Transform** scale of `(1, 1, 10)` changes the display only, not the underlying file.

The useful next checks are to verify the GWIS vertical datum, compare the contacts with an independently referenced DEM, review unit grouping and possible faults with a geologist, and evaluate contact elevations on spatially withheld sites. Those checks should come before using this block as a training target or adding ML-inferred contacts.
