"""Export the pilot voxel arrays as a ParaView-readable VTK ImageData volume.

Run with Python, NumPy, and PyVista installed. No GemPy recomputation is needed.
"""

from pathlib import Path

import numpy as np
import pyvista as pv


MODEL_DIR = Path(__file__).resolve().parent / "geological_model"
SOURCE = MODEL_DIR / "boardman_broad_units_voxels.npz"
TARGET = MODEL_DIR / "boardman_broad_units_paraview.vti"


def main() -> None:
    with np.load(SOURCE) as data:
        raw = data["unit_index"]
        masked = data["unit_index_aoi_terrain_masked"]
        extent = data["extent_m"]
        origin_xy = data["utm_origin_m"]
    if raw.shape != masked.shape or raw.ndim != 3:
        raise ValueError("Expected matching 3D raw and masked unit arrays")
    if not np.isin(masked, [0, 1, 2, 3, 4]).all():
        raise ValueError("Unexpected unit index in masked array")

    nx, ny, nz = raw.shape
    spacing = (
        float((extent[1] - extent[0]) / nx),
        float((extent[3] - extent[2]) / ny),
        float((extent[5] - extent[4]) / nz),
    )
    origin = (
        float(origin_xy[0] + extent[0]),
        float(origin_xy[1] + extent[2]),
        float(extent[4]),
    )
    grid = pv.ImageData(dimensions=(nx + 1, ny + 1, nz + 1), spacing=spacing, origin=origin)
    # VTK stores cell values with X varying fastest; the model arrays have Z
    # varying fastest, so explicitly flatten in Fortran order for this export.
    grid.cell_data["unit_id"] = masked.ravel(order="F")
    grid.cell_data["unit_id_unmasked"] = raw.ravel(order="F")
    grid.save(TARGET)

    check = pv.read(TARGET)
    assert check.dimensions == (nx + 1, ny + 1, nz + 1)
    assert np.array_equal(check.cell_data["unit_id"].reshape(raw.shape, order="F"), masked)
    assert np.array_equal(check.cell_data["unit_id_unmasked"].reshape(raw.shape, order="F"), raw)
    assert np.allclose(check.origin, origin)
    assert np.allclose(check.spacing, spacing)
    print(f"Saved and verified {TARGET}")
    print(f"Cells: {raw.shape}; origin (UTM E, N, source elevation): {origin}; spacing (m): {spacing}")


if __name__ == "__main__":
    main()
