"""Audit report coordinates against the configured 19-township study area."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import yaml
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union


BOUNDARY = Path("02_gis/reference/plss_townships.geojson")
SOURCE = "BLM National PLSS CadNSDI MapServer/1, Oregon Willamette Meridian; cached GeoJSON"


def load_boundary(root: Path):
    path = root / BOUNDARY
    payload = path.read_bytes()
    document = json.loads(payload)
    if document.get("type") != "FeatureCollection":
        raise ValueError("Township boundary is not a GeoJSON FeatureCollection")
    configured = yaml.safe_load((root / "00_config/owrd_download.yml").read_text())["study_area"]["townships"]
    features = []
    for feature in document["features"]:
        props = feature["properties"]
        if (props.get("STATEABBR"), props.get("PRINMER")) != ("OR", "Willamette Meridian"):
            raise ValueError("Unexpected township state or meridian")
        match = re.fullmatch(r"T0*(\d+)N R0*(\d+)E", props["TWNSHPLAB"])
        if match is None:
            raise ValueError(f"Unexpected township label: {props['TWNSHPLAB']}")
        label = f"T{int(match[1])}N R{int(match[2])}E"
        polygon = shape(feature["geometry"])
        if not polygon.is_valid or polygon.is_empty:
            raise ValueError(f"Invalid township polygon: {label}")
        features.append((label, polygon))
    if len(features) != 19 or set(label for label, _ in features) != set(configured):
        raise ValueError("Boundary features differ from the 19 configured townships")
    union = unary_union([polygon for _, polygon in features])
    return features, union, hashlib.sha256(payload).hexdigest()


def audit_locations(root: Path, wells: pd.DataFrame) -> tuple[pd.DataFrame, object, list, str]:
    """Return one audit row per source report; retain raw coordinate values."""
    features, boundary, digest = load_boundary(root)
    if wells.wl_id.duplicated().any():
        raise ValueError("Report IDs must be unique for coordinate audit")
    lon = pd.to_numeric(wells.longitude_dec, errors="coerce")
    lat = pd.to_numeric(wells.latitude_dec, errors="coerce")
    has_source = lon.between(-180, 180) & lat.between(-90, 90)
    map_lon = pd.to_numeric(wells.map_longitude, errors="coerce")
    map_lat = pd.to_numeric(wells.map_latitude, errors="coerce")
    has_map = map_lon.between(-180, 180) & map_lat.between(-90, 90)
    use_map = ~has_source & has_map
    x = lon.where(has_source, map_lon.where(use_map))
    y = lat.where(has_source, map_lat.where(use_map))
    basis = pd.Series("missing", index=wells.index)
    basis.loc[has_source] = "source"
    basis.loc[use_map] = "map_fallback"
    to_m = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True).transform
    boundary_m = transform(to_m, boundary)
    rows = []
    for i, well in wells.iterrows():
        located = bool(has_source.loc[i] or use_map.loc[i])
        if located:
            point = Point(float(x.loc[i]), float(y.loc[i]))
            inside = boundary.covers(point)
            distance = 0.0 if inside else transform(to_m, point).distance(boundary_m)
        else:
            inside, distance = False, None
        rows.append({
            "wl_id": well.wl_id, "well_folder": well.well_folder,
            "bonded_full_name": well.bonded_full_name.strip(), "tr_key": well.tr_key,
            "location_class": well.location_class, "coordinate_basis": basis.loc[i],
            "longitude": x.loc[i], "latitude": y.loc[i],
            "within_19_townships": inside if located else pd.NA,
            "distance_outside_m": distance,
        })
    audit = pd.DataFrame(rows)
    return audit, boundary, features, digest


def outside_ids(audit: pd.DataFrame) -> set[str]:
    return set(audit.loc[audit.within_19_townships.eq(False), "wl_id"])
