"""Build an exploratory GemPy block model from GWIS stratigraphic contacts.

Run from the repository root with a Python 3.12 environment containing
gempy==2026.0.3, geopandas, matplotlib, numpy, and pandas.
"""

from __future__ import annotations

import json
import hashlib
import platform
from pathlib import Path

import gempy as gp
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np
import pandas as pd
from shapely import affinity, contains_xy


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
MODEL_DIR = HERE / "geological_model"
SOURCE = ROOT / "03_processed/boardman_19_townships"
AOI_PATH = ROOT / "02_gis/reference/plss_townships.geojson"
MODEL_CRS = "EPSG:26911"
FEET_TO_METRES = 0.3048
CONTACTS = [
    ("top_saddle_mountains", "Crbg.Smb"),
    ("top_wanapum", "Crbg.Wb"),
    ("top_grande_ronde", "Crbg.Grb"),
]
RESOLUTION = (54, 40, 48)
COLORS = ["#e6d9aa", "#a97654", "#647e9a", "#4d526d"]


def family(unit: str) -> str:
    for name, prefix in CONTACTS:
        if str(unit).startswith(prefix + ".") or unit == prefix:
            return name
    return "other"


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(SOURCE / "boardman_wells_stratigraphy.csv", dtype={"gw_site_id": str})
    summary = pd.read_csv(SOURCE / "boardman_wells_summary.csv")
    raw = raw.merge(summary[["well_id", "location_class"]], on="well_id", validate="many_to_one")
    raw["contact_family"] = raw.strat_unit.map(family)

    aoi = gpd.read_file(AOI_PATH).to_crs(MODEL_CRS)
    aoi_union = aoi.geometry.union_all()
    minx, miny, maxx, maxy = aoi.total_bounds

    locations = raw[["gw_site_id", "well_id", "latitude", "longitude", "location_class"]].drop_duplicates()
    locations = locations[locations.location_class.isin(["A", "B"])].copy()
    points = gpd.GeoDataFrame(
        locations,
        geometry=gpd.points_from_xy(locations.longitude, locations.latitude),
        crs="EPSG:4326",
    ).to_crs(MODEL_CRS)
    points["east_m"] = points.geometry.x
    points["north_m"] = points.geometry.y

    site_locations = []
    for site, group in points.groupby("gw_site_id"):
        spread = float(np.hypot(group.east_m.max() - group.east_m.min(), group.north_m.max() - group.north_m.min()))
        east, north = float(group.east_m.median()), float(group.north_m.median())
        from shapely.geometry import Point

        site_locations.append(
            {
                "gw_site_id": site,
                "east_m": east,
                "north_m": north,
                "location_spread_m": spread,
                "location_class": "A" if "A" in set(group.location_class) else "B",
                "inside_aoi": bool(aoi_union.intersects(Point(east, north))),
                "location_eligible": bool(spread <= 25 and aoi_union.intersects(Point(east, north))),
                "report_ids": ";".join(sorted(set(group.well_id))),
            }
        )
    site_locations = pd.DataFrame(site_locations)
    source_surface_ft = (
        raw.assign(surface_elevation_ft=raw.start_depth + raw.start_depth_elev)
        .groupby("gw_site_id").surface_elevation_ft.median()
    )
    site_locations["surface_elevation_m"] = (
        site_locations.gw_site_id.map(source_surface_ft) * FEET_TO_METRES
    )

    # A GWIS site can appear under several linked well reports. Identical
    # site/depth/unit rows are one geological observation, not independent picks.
    intervals = raw.drop_duplicates(
        ["gw_site_id", "start_depth", "end_depth", "strat_unit", "start_depth_elev"]
    ).sort_values(["gw_site_id", "start_depth", "end_depth", "strat_unit"])
    candidates = []
    for site, group in intervals.groupby("gw_site_id"):
        group = group.reset_index(drop=True)
        for name, _ in CONTACTS:
            matches = group.index[group.contact_family.eq(name)]
            if len(matches) == 0:
                continue
            i = int(matches[0])
            row = group.iloc[i]
            previous = group.iloc[i - 1] if i else None
            if previous is None:
                edge = "top_of_record"
            elif abs(float(previous.end_depth) - float(row.start_depth)) > 1:
                edge = "gap_or_overlap"
            elif previous.contact_family == name:
                edge = "same_family"
            else:
                edge = "observed_transition"
            candidates.append(
                {
                    "gw_site_id": site,
                    "surface": name,
                    "strat_unit": row.strat_unit,
                    "from_depth_ft": float(row.start_depth),
                    "contact_elevation_source_ft": row.start_depth_elev,
                    "previous_strat_unit": previous.strat_unit if previous is not None else "",
                    "previous_end_depth_ft": previous.end_depth if previous is not None else np.nan,
                    "edge_kind": edge,
                }
            )
    candidates = pd.DataFrame(candidates).merge(site_locations, on="gw_site_id", how="left", validate="many_to_one")
    candidates["exclusion_reason"] = np.select(
        [
            candidates.edge_kind.ne("observed_transition"),
            candidates.previous_strat_unit.eq("Sediment.PreCrb")
            | candidates.previous_strat_unit.str.startswith("Crbg.Undifferentiated"),
            candidates.location_eligible.ne(True),
            candidates.contact_elevation_source_ft.isna(),
        ],
        ["no_adjacent_transition", "ambiguous_previous_unit", "location_not_eligible", "missing_elevation"],
        default="",
    )
    candidates["used_in_model"] = candidates.exclusion_reason.eq("")
    candidates["contact_elevation_m"] = candidates.contact_elevation_source_ft * FEET_TO_METRES
    candidates["model_x_m"] = candidates.east_m - minx
    candidates["model_y_m"] = candidates.north_m - miny
    candidates.to_csv(ARTIFACTS / "contact_audit.csv", index=False)
    selected = candidates[candidates.used_in_model].copy()
    selected.to_csv(ARTIFACTS / "model_contacts.csv", index=False)
    counts = selected.groupby("surface").gw_site_id.nunique().to_dict()
    if any(counts.get(name, 0) < 3 for name, _ in CONTACTS):
        raise RuntimeError(f"Insufficient contacts for the three-surface pilot: {counts}")

    names = selected.surface.to_numpy(dtype=str)
    surface_points = gp.data.SurfacePointsTable.from_arrays(
        x=selected.model_x_m.to_numpy(float),
        y=selected.model_y_m.to_numpy(float),
        z=selected.contact_elevation_m.to_numpy(float),
        names=names,
    )
    # Horizontal poles are explicit modeling assumptions, not measured dips.
    orientation_rows = selected.groupby("surface").agg(
        model_x_m=("model_x_m", "median"),
        model_y_m=("model_y_m", "median"),
        contact_elevation_m=("contact_elevation_m", "median"),
    ).reindex([name for name, _ in CONTACTS])
    orientations = gp.data.OrientationsTable.from_arrays(
        x=orientation_rows.model_x_m.to_numpy(float),
        y=orientation_rows.model_y_m.to_numpy(float),
        z=orientation_rows.contact_elevation_m.to_numpy(float),
        G_x=np.zeros(len(CONTACTS)),
        G_y=np.zeros(len(CONTACTS)),
        G_z=np.ones(len(CONTACTS)),
        names=np.array([name for name, _ in CONTACTS]),
        name_id_map=surface_points.name_id_map,
    )
    frame = gp.data.StructuralFrame.from_data_tables(
        surface_points=surface_points, orientations=orientations
    )
    extent = [-500.0, float(maxx - minx + 500), -500.0, float(maxy - miny + 500), -450.0, 420.0]
    model = gp.create_geomodel(
        project_name="Boardman_broad_stratigraphy_pilot",
        extent=extent,
        resolution=RESOLUTION,
        refinement=1,
        structural_frame=frame,
    )
    solution = gp.compute_model(model)
    ids = solution.raw_arrays.lith_block.astype(np.uint8).reshape(RESOLUTION)
    terrain, masked_ids = approximate_terrain_and_mask(
        ids, site_locations, aoi_union, extent, minx, miny
    )
    model_path = MODEL_DIR / "boardman_broad_units.gempy"
    gp.save_model(model, path=str(model_path))
    np.savez_compressed(
        MODEL_DIR / "boardman_broad_units_voxels.npz",
        unit_index=ids,
        unit_index_aoi_terrain_masked=masked_ids,
        approximate_land_surface_m=terrain,
        extent_m=np.array(extent),
        resolution=np.array(RESOLUTION),
        utm_origin_m=np.array([minx, miny]),
        unit_names=np.array(["overburden", "saddle_mountains", "wanapum", "grande_ronde_and_older"]),
    )
    make_figures(aoi, selected, masked_ids, terrain, extent, minx, miny)
    summary_json = {
        "gempy_version": gp.__version__,
        "python_version": platform.python_version(),
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [SOURCE / "boardman_wells_stratigraphy.csv", SOURCE / "boardman_wells_summary.csv", AOI_PATH]
        },
        "source_rows": len(raw),
        "source_reports": int(raw.well_id.nunique()),
        "source_gwis_sites": int(raw.gw_site_id.nunique()),
        "location_a_or_b_sites": len(site_locations),
        "location_spread_over_25m_sites": int((site_locations.location_spread_m > 25).sum()),
        "candidates": len(candidates),
        "selected_contacts": len(selected),
        "selected_sites": int(selected.gw_site_id.nunique()),
        "contacts_by_surface": counts,
        "excluded_by_reason": candidates.loc[~candidates.used_in_model, "exclusion_reason"].value_counts().to_dict(),
        "model_crs": MODEL_CRS,
        "vertical_reference": "GWIS source elevation in feet; formal vertical datum unverified",
        "origin_utm_m": [minx, miny],
        "extent_local_m": extent,
        "resolution": list(RESOLUTION),
        "unit_index": {"1": "overburden", "2": "saddle_mountains", "3": "wanapum", "4": "grande_ronde_and_older"},
        "voxel_unit_counts": {str(k): int(v) for k, v in zip(*np.unique(ids, return_counts=True))},
        "masked_voxel_unit_counts": {str(k): int(v) for k, v in zip(*np.unique(masked_ids, return_counts=True))},
        "in_sample_nearest_voxel_error_m": nearest_voxel_errors(ids, selected, extent),
        "assumptions": [
            "First observed unit of each basalt family marks its upper contact only when adjacent to a different interpreted interval.",
            "Ellensburg interbeds and other sediments are collapsed into broad adjacent units; their geometry is not represented.",
            "One horizontal orientation per contact surface is assumed; no measured dip is supplied.",
            "Raw GemPy block is rectangular; a separate voxel array masks outside the township polygons and above a well-elevation-derived approximate land surface.",
            "The approximate land surface is inverse-distance interpolation of GWIS site elevations, not an independent DEM.",
            "Model is exploratory and not validated against held-out boreholes.",
        ],
    }
    (ARTIFACTS / "model_summary.json").write_text(json.dumps(summary_json, indent=2) + "\n")
    print(json.dumps(summary_json, indent=2))


def nearest_voxel_errors(ids, contacts, extent):
    """Raster approximation error at used contacts; this is not held-out validation."""
    nx, ny, nz = ids.shape
    dz = (extent[5] - extent[4]) / nz
    results = {}
    for lower_id, (surface, _) in enumerate(CONTACTS, start=2):
        errors = []
        for row in contacts[contacts.surface.eq(surface)].itertuples():
            i = int(np.clip((row.model_x_m - extent[0]) / (extent[1] - extent[0]) * nx, 0, nx - 1))
            j = int(np.clip((row.model_y_m - extent[2]) / (extent[3] - extent[2]) * ny, 0, ny - 1))
            hits = np.flatnonzero(ids[i, j, :] == lower_id)
            if len(hits):
                modeled_top = extent[4] + (hits.max() + 1) * dz
                errors.append(modeled_top - row.contact_elevation_m)
        results[surface] = {
            "n": len(errors),
            "median_absolute_m": float(np.median(np.abs(errors))) if errors else None,
            "p90_absolute_m": float(np.quantile(np.abs(errors), .9)) if errors else None,
        }
    return results


def approximate_terrain_and_mask(ids, sites, aoi_union, extent, minx, miny):
    nx, ny, nz = ids.shape
    x = np.linspace(extent[0], extent[1], nx, endpoint=False) + (extent[1] - extent[0]) / (2 * nx)
    y = np.linspace(extent[2], extent[3], ny, endpoint=False) + (extent[3] - extent[2]) / (2 * ny)
    z = np.linspace(extent[4], extent[5], nz, endpoint=False) + (extent[5] - extent[4]) / (2 * nz)
    xx, yy = np.meshgrid(x + minx, y + miny, indexing="ij")
    surface_sites = sites[sites.location_eligible & sites.surface_elevation_m.notna()]
    site_xy = surface_sites[["east_m", "north_m"]].to_numpy()
    delta = np.stack([xx.ravel()[:, None] - site_xy[:, 0], yy.ravel()[:, None] - site_xy[:, 1]], axis=-1)
    distance2 = np.sum(delta * delta, axis=2)
    nearest = np.argpartition(distance2, kth=7, axis=1)[:, :8]
    near_distance2 = np.take_along_axis(distance2, nearest, axis=1)
    weights = 1 / np.maximum(near_distance2, 1)
    elevations = surface_sites.surface_elevation_m.to_numpy()[nearest]
    terrain = (np.sum(weights * elevations, axis=1) / np.sum(weights, axis=1)).reshape(nx, ny)
    inside = contains_xy(aoi_union, xx, yy)
    masked = ids.copy()
    masked[(~inside)[:, :, None] | (z[None, None, :] > terrain[:, :, None])] = 0
    return terrain, masked


def make_figures(aoi, contacts, ids, terrain, extent, minx, miny) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    colors = ["#a97654", "#647e9a", "#4d526d"]
    aoi_km = aoi.copy()
    aoi_km.geometry = aoi_km.geometry.map(lambda g: affinity.scale(g, xfact=.001, yfact=.001, origin=(0, 0)))
    aoi_km.boundary.plot(ax=ax, color="#777777", linewidth=0.7)
    for (name, _), color in zip(CONTACTS, colors):
        group = contacts[contacts.surface.eq(name)]
        ax.scatter(group.east_m / 1000, group.north_m / 1000, s=32, alpha=0.75,
                   color=color, edgecolor="black", linewidth=0.35,
                   label=f"Top {name.replace('top_', '').replace('_', ' ')} ({len(group)} sites)")
    ax.set(xlabel="UTM zone 11N easting (km)", ylabel="Northing (km)",
           title="Observed broad-unit contacts used in GemPy pilot")
    ax.set_aspect("equal")
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "pilot_contact_map.png", dpi=250)
    plt.close(fig)

    cmap = ListedColormap(["#ffffff", *COLORS])
    norm = BoundaryNorm([-.5, .5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    y_index = ids.shape[1] // 2
    section = ids[:, y_index, :].T
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.imshow(section, origin="lower", interpolation="nearest", aspect="auto",
              cmap=cmap, norm=norm,
              extent=[(extent[0] + minx) / 1000, (extent[1] + minx) / 1000, extent[4], extent[5]])
    x_centers = np.linspace(extent[0], extent[1], ids.shape[0], endpoint=False) + (extent[1] - extent[0]) / (2 * ids.shape[0])
    ax.plot((x_centers + minx) / 1000, terrain[:, y_index], color="black", linewidth=1.1,
            label="Approximate land surface")
    ax.set(xlabel="UTM zone 11N easting (km)", ylabel="GWIS source elevation (m; datum unverified)",
           title="GemPy pilot block: central east–west slice")
    from matplotlib.patches import Patch

    ax.legend(handles=[Patch(color=c, label=n) for c, n in zip(COLORS,
              ["Overburden", "Saddle Mountains", "Wanapum", "Grande Ronde and older"])] +
              [plt.Line2D([0], [0], color="black", label="Approximate land surface")],
              loc="lower left", ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "pilot_block_section.png", dpi=250)
    plt.close(fig)

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    x_centers_km = (x_centers + minx) / 1000
    y_centers = np.linspace(extent[2], extent[3], ids.shape[1], endpoint=False) + (extent[3] - extent[2]) / (2 * ids.shape[1])
    y_centers_km = (y_centers + miny) / 1000
    xx, yy = np.meshgrid(x_centers_km, y_centers_km, indexing="ij")
    dz = (extent[5] - extent[4]) / ids.shape[2]
    for lower_id, color in [(4, COLORS[3]), (3, COLORS[2]), (2, COLORS[1])]:
        has = np.any(ids == lower_id, axis=2)
        top_index = np.max(np.where(ids == lower_id, np.arange(ids.shape[2])[None, None, :], -1), axis=2)
        zz = np.where(has, extent[4] + (top_index + 1) * dz, np.nan)
        ax.plot_surface(xx, yy, zz, color=color, alpha=.82, linewidth=0, antialiased=False)
    ax.set(xlabel="Easting (km)", ylabel="Northing (km)", zlabel="Source elevation (m)",
           title="GemPy pilot contact surfaces (schematic)")
    ax.set_box_aspect((1, .8, .42))
    ax.view_init(elev=25, azim=-65)
    ax.legend(handles=[Patch(color=COLORS[i], label=label) for i, label in
               [(1, "Top Saddle Mountains"), (2, "Top Wanapum"), (3, "Top Grande Ronde")]],
              loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "pilot_contact_surfaces_3d.png", dpi=250)
    plt.close(fig)


if __name__ == "__main__":
    main()
