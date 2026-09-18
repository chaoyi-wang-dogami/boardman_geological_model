#!/usr/bin/env python3
"""Download OWRD well metadata, lithology tables, and original well reports.

The script queries OWRD's public ArcGIS FeatureServer, creates one directory per
well report, classifies coordinate quality, and writes CSV and GeoPackage files
for pandas, ArcGIS Pro, and later geological-model preparation.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import re
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import pandas as pd
import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


LOGGER = logging.getLogger("owrd_downloader")
LITHOLOGY_COLUMNS = [
    "well_id",
    "well_log",
    "interval_no",
    "from_ft",
    "to_ft",
    "thickness_ft",
    "material_raw",
    "static_water_level_raw",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download OWRD records for the configured townships."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Configuration YAML (default: 00_config/owrd_download.yml).",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root (default: parent of the scripts directory).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N wells; useful for a smoke test.",
    )
    parser.add_argument(
        "--skip-lithology",
        action="store_true",
        help="Do not request or parse OWRD detail pages.",
    )
    parser.add_argument(
        "--skip-pdfs",
        action="store_true",
        help="Do not download original scanned well reports.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing per-well files.",
    )
    return parser.parse_args()


def project_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    inferred_root = Path(__file__).resolve().parents[1]
    root = (args.project_root or inferred_root).resolve()
    config = (args.config or root / "00_config" / "owrd_download.yml").resolve()
    return root, config


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration is not a mapping: {path}")
    return config


def build_session(config: dict[str, Any]) -> requests.Session:
    owrd = config["owrd"]
    retry = Retry(
        total=int(owrd.get("retries", 4)),
        connect=int(owrd.get("retries", 4)),
        read=int(owrd.get("retries", 4)),
        status=int(owrd.get("retries", 4)),
        backoff_factor=float(owrd.get("retry_backoff_seconds", 1.0)),
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": str(owrd.get("user_agent", "boardman-geological-model/0.1")),
            "Accept": "application/json,text/html,application/pdf,*/*",
        }
    )
    return session


def normalize_tr_key(value: str, meridian: str = "WM") -> str:
    """Convert forms such as 'T5N R25E' to OWRD's 'WM5.00N25.00E'."""
    cleaned = re.sub(r"\s+", "", value.upper())
    if re.fullmatch(r"[A-Z]{2}\d+(?:\.\d+)?[NS]\d+(?:\.\d+)?[EW]", cleaned):
        return cleaned
    match = re.fullmatch(
        r"T?(?P<t>\d+(?:\.\d+)?)(?P<ns>[NS])R?(?P<r>\d+(?:\.\d+)?)(?P<ew>[EW])",
        cleaned,
    )
    if not match:
        raise ValueError(f"Unsupported township/range value: {value!r}")
    return (
        f"{meridian.upper()}"
        f"{float(match.group('t')):.2f}{match.group('ns')}"
        f"{float(match.group('r')):.2f}{match.group('ew')}"
    )


def build_where_clause(config: dict[str, Any]) -> tuple[str, list[str]]:
    study = config["study_area"]
    tr_keys = [
        normalize_tr_key(value, study.get("meridian", "WM"))
        for value in study["townships"]
    ]
    quoted = ", ".join("'" + key.replace("'", "''") + "'" for key in tr_keys)
    return f"tr_key IN ({quoted})", tr_keys


def request_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        error = payload["error"]
        raise RuntimeError(
            f"ArcGIS API error {error.get('code')}: {error.get('message')} "
            f"{error.get('details', '')}"
        )
    return payload


def validate_layer(
    session: requests.Session, config: dict[str, Any]
) -> tuple[list[str], int]:
    owrd = config["owrd"]
    timeout = float(owrd.get("request_timeout_seconds", 90))
    payload = request_json(session, owrd["layer_url"], {"f": "json"}, timeout)
    fields = [item["name"] for item in payload.get("fields", [])]
    required = {
        "OBJECTID",
        "wl_id",
        "wl_county_code",
        "wl_nbr",
        "tr_key",
        "latitude_dec",
        "longitude_dec",
        "coordinate_source",
        "est_horizontal_error",
        "well_log_url",
    }
    missing = sorted(required.difference(fields))
    if missing:
        raise RuntimeError(f"OWRD layer is missing required fields: {missing}")
    service_max = int(payload.get("maxRecordCount", 2000))
    return fields, service_max


def query_wells(
    session: requests.Session,
    config: dict[str, Any],
    where: str,
    service_max: int,
) -> list[dict[str, Any]]:
    owrd = config["owrd"]
    query_url = owrd["layer_url"].rstrip("/") + "/query"
    timeout = float(owrd.get("request_timeout_seconds", 90))
    page_size = min(int(owrd.get("page_size", 2000)), service_max)
    offset = 0
    records: list[dict[str, Any]] = []

    while True:
        payload = request_json(
            session,
            query_url,
            {
                "f": "json",
                "where": where,
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": 4326,
                "orderByFields": "OBJECTID ASC",
                "resultOffset": offset,
                "resultRecordCount": page_size,
            },
            timeout,
        )
        features = payload.get("features", [])
        for feature in features:
            attrs = dict(feature.get("attributes") or {})
            geometry = feature.get("geometry") or {}
            attrs["map_longitude"] = geometry.get("x")
            attrs["map_latitude"] = geometry.get("y")
            records.append(attrs)

        LOGGER.info("Retrieved %s records", len(records))
        exceeded = bool(payload.get("exceededTransferLimit"))
        if not features or (len(features) < page_size and not exceeded):
            break
        offset += len(features)

    return records


def finite_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def classify_location(record: dict[str, Any], config: dict[str, Any]) -> str:
    quality = config["location_quality"]
    lat = finite_number(record.get("latitude_dec"))
    lon = finite_number(record.get("longitude_dec"))
    source = str(record.get("coordinate_source") or "").strip()
    inferred_pattern = quality.get("inferred_source_pattern")
    inferred = bool(source and inferred_pattern and re.search(inferred_pattern, source))
    if lat is None or lon is None or not source or inferred:
        return "D"

    error = finite_number(record.get("est_horizontal_error"))
    if error is None:
        return "C"
    if error <= float(quality.get("class_a_max_error_ft", 50)):
        return "A"
    if error <= float(quality.get("class_b_max_error_ft", 100)):
        return "B"
    return "C"


def iso_date_from_epoch_ms(value: Any) -> str | None:
    number = finite_number(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number / 1000, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def report_name(record: dict[str, Any]) -> str:
    county = str(record.get("wl_county_code") or "UNKN").strip().upper()
    number = record.get("wl_nbr")
    try:
        base = f"{county}_{int(number):07d}"
    except (TypeError, ValueError):
        base = f"{county}_WLID_{record.get('wl_id', 'UNKNOWN')}"
    version = record.get("wl_version")
    try:
        if version is not None and int(version) > 1:
            base += f"_v{int(version)}"
    except (TypeError, ValueError):
        pass
    return re.sub(r"[^A-Z0-9_.-]+", "_", base)


def enrich_record(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(record)
    location_class = classify_location(record, config)
    source_lon = finite_number(record.get("longitude_dec"))
    source_lat = finite_number(record.get("latitude_dec"))
    map_lon = finite_number(record.get("map_longitude"))
    map_lat = finite_number(record.get("map_latitude"))
    enriched.update(
        {
            "well_folder": report_name(record),
            "location_class": location_class,
            "location_is_high_confidence": location_class in {"A", "B"},
            "display_longitude": source_lon if source_lon is not None else map_lon,
            "display_latitude": source_lat if source_lat is not None else map_lat,
            "start_date_iso": iso_date_from_epoch_ms(record.get("start_date")),
            "complete_date_iso": iso_date_from_epoch_ms(record.get("complete_date")),
            "received_date_iso": iso_date_from_epoch_ms(record.get("received_date")),
            "detail_url": config["owrd"]["detail_url_template"].format(
                wl_id=record.get("wl_id")
            ),
        }
    )
    return enriched


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if pd.isna(value):
        return None
    return value


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(
        path,
        json.dumps(json_safe(payload), indent=2, ensure_ascii=False, allow_nan=False) + "\n",
    )


def normalized_column_name(value: Any) -> str:
    if isinstance(value, tuple):
        pieces = [str(item) for item in value if not str(item).startswith("Unnamed")]
        value = " ".join(dict.fromkeys(pieces))
    text = re.sub(r"\s+", " ", str(value)).strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def find_column(columns: Iterable[str], kind: str) -> str | None:
    columns = list(columns)
    patterns = {
        "row": (r"^row$", r"row_number", r"^no$"),
        "from": (r"^from$", r"(^|_)from(_|$)", r"depth_from"),
        "to": (r"^to$", r"(^|_)to(_|$)", r"depth_to"),
        "material": (r"^material$", r"(^|_)material(_|$)", r"description", r"litholog"),
        "swl": (r"static.*water", r"^swl"),
    }
    for pattern in patterns[kind]:
        for column in columns:
            if re.search(pattern, column):
                return column
    return None


def parse_lithology_html(
    html: str, well_id: Any, well_log: str
) -> pd.DataFrame:
    try:
        tables = pd.read_html(StringIO(html))
    except ValueError:
        return pd.DataFrame(columns=LITHOLOGY_COLUMNS)

    for table in tables:
        candidate = table.copy()
        candidate.columns = [normalized_column_name(col) for col in candidate.columns]
        from_col = find_column(candidate.columns, "from")
        to_col = find_column(candidate.columns, "to")
        material_col = find_column(candidate.columns, "material")
        swl_col = find_column(candidate.columns, "swl")
        # Several OWRD construction tables contain From/To/Material columns
        # (seal, backfill, filter pack). The lithology table is distinguished
        # by its Static Water Level column, even when all values are blank.
        if not (from_col and to_col and material_col and swl_col):
            continue

        row_col = find_column(candidate.columns, "row")
        output = pd.DataFrame()
        output["from_ft"] = pd.to_numeric(candidate[from_col], errors="coerce")
        output["to_ft"] = pd.to_numeric(candidate[to_col], errors="coerce")
        output["material_raw"] = candidate[material_col].astype("string").str.strip()
        output = output[
            output["from_ft"].notna()
            & output["to_ft"].notna()
            & output["material_raw"].notna()
            & (output["material_raw"] != "")
        ].copy()
        if output.empty:
            continue

        if row_col:
            interval_numbers = pd.to_numeric(
                candidate.loc[output.index, row_col], errors="coerce"
            )
            fallback = pd.Series(range(1, len(output) + 1), index=output.index)
            output["interval_no"] = interval_numbers.fillna(fallback).astype(int)
        else:
            output["interval_no"] = range(1, len(output) + 1)
        output["well_id"] = well_id
        output["well_log"] = well_log
        output["thickness_ft"] = output["to_ft"] - output["from_ft"]
        output["static_water_level_raw"] = (
            candidate.loc[output.index, swl_col].astype("string").str.strip()
            if swl_col
            else pd.NA
        )
        return output[LITHOLOGY_COLUMNS].reset_index(drop=True)

    return pd.DataFrame(columns=LITHOLOGY_COLUMNS)


def fetch_lithology(
    session: requests.Session,
    record: dict[str, Any],
    destination: Path,
    config: dict[str, Any],
    overwrite: bool,
) -> tuple[pd.DataFrame, str]:
    if destination.exists() and not overwrite:
        return pd.read_csv(destination), "skipped_existing"

    url = record["detail_url"]
    timeout = float(config["owrd"].get("request_timeout_seconds", 90))
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    frame = parse_lithology_html(
        response.text, record.get("wl_id"), record["well_folder"]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    frame.to_csv(temporary, index=False)
    os.replace(temporary, destination)
    return frame, "downloaded" if not frame.empty else "no_structured_lithology"


def download_well_report(
    session: requests.Session,
    record: dict[str, Any],
    well_dir: Path,
    config: dict[str, Any],
    overwrite: bool,
) -> tuple[Path | None, str]:
    url = str(record.get("well_log_url") or "").strip()
    if not url:
        return None, "missing_url"
    url = urljoin(config["owrd"]["layer_url"], url)
    pdf_path = well_dir / "well_report.pdf"
    if pdf_path.exists() and not overwrite:
        return pdf_path, "skipped_existing"

    timeout = float(config["owrd"].get("request_timeout_seconds", 90))
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").lower()
    is_pdf = response.content.startswith(b"%PDF") or "application/pdf" in content_type
    if not is_pdf:
        raise RuntimeError(
            f"Expected PDF but received Content-Type={content_type!r} from {response.url}"
        )
    well_dir.mkdir(parents=True, exist_ok=True)
    temporary = pdf_path.with_name(pdf_path.name + ".part")
    temporary.write_bytes(response.content)
    os.replace(temporary, pdf_path)
    return pdf_path, "downloaded"


def append_download_log(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp_utc",
        "well_id",
        "well_folder",
        "stage",
        "status",
        "message",
        "url",
    ]
    new_file = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if new_file:
            writer.writeheader()
        writer.writerow({field: event.get(field, "") for field in fields})


def log_event(
    log_path: Path,
    record: dict[str, Any],
    stage: str,
    status: str,
    message: str = "",
    url: str = "",
) -> None:
    append_download_log(
        log_path,
        {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "well_id": record.get("wl_id"),
            "well_folder": record.get("well_folder"),
            "stage": stage,
            "status": status,
            "message": message,
            "url": url,
        },
    )


def resolve_output(root: Path, config: dict[str, Any], key: str) -> Path:
    return root / config["outputs"][key]


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    frame.to_csv(temporary, index=False)
    os.replace(temporary, path)


def csv_has_data_row(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return not pd.read_csv(path, nrows=1).empty
    except (pd.errors.EmptyDataError, OSError):
        return False


def write_gis_outputs(
    wells: pd.DataFrame, root: Path, config: dict[str, Any]
) -> None:
    all_csv = resolve_output(root, config, "wells_all_csv")
    high_csv = resolve_output(root, config, "wells_high_confidence_csv")
    write_csv_atomic(wells, all_csv)
    high = wells[wells["location_class"].isin(["A", "B"])].copy()
    write_csv_atomic(high, high_csv)

    try:
        import geopandas as gpd
    except ImportError as exc:
        raise RuntimeError(
            "GeoPackage output requires geopandas; run uv sync from the project root"
        ) from exc

    valid = wells[
        wells["display_longitude"].notna() & wells["display_latitude"].notna()
    ].copy()
    valid_high = valid[valid["location_class"].isin(["A", "B"])].copy()
    geometry_all = gpd.points_from_xy(
        valid["display_longitude"], valid["display_latitude"], crs="EPSG:4326"
    )
    geometry_high = gpd.points_from_xy(
        valid_high["display_longitude"],
        valid_high["display_latitude"],
        crs="EPSG:4326",
    )
    gdf_all = gpd.GeoDataFrame(valid, geometry=geometry_all)
    gdf_high = gpd.GeoDataFrame(valid_high, geometry=geometry_high)
    gpkg = resolve_output(root, config, "wells_geopackage")
    gpkg.parent.mkdir(parents=True, exist_ok=True)
    if gpkg.exists():
        gpkg.unlink()
    gdf_all.to_file(gpkg, layer="wells_all", driver="GPKG", engine="pyogrio")
    gdf_high.to_file(
        gpkg,
        layer="wells_high_confidence",
        driver="GPKG",
        engine="pyogrio",
        append=True,
    )


def main() -> int:
    args = parse_args()
    root, config_path = project_paths(args)
    config = load_config(config_path)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    overwrite = bool(args.overwrite or config["downloads"].get("overwrite_existing"))
    fetch_lithology_enabled = bool(
        config["downloads"].get("fetch_lithology", True) and not args.skip_lithology
    )
    fetch_pdfs_enabled = bool(
        config["downloads"].get("fetch_well_reports", True) and not args.skip_pdfs
    )
    session = build_session(config)
    _, service_max = validate_layer(session, config)
    where, tr_keys = build_where_clause(config)
    LOGGER.info("Querying %s township/range keys: %s", len(tr_keys), ", ".join(tr_keys))
    raw_records = query_wells(session, config, where, service_max)
    if not raw_records:
        raise RuntimeError(
            "The OWRD query returned zero wells. Check the configured townships and "
            f"the generated tr_key values: {tr_keys}"
        )

    records = [enrich_record(record, config) for record in raw_records]
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be at least 1")
        records = records[: args.limit]
        LOGGER.info("Smoke-test limit active: processing %s wells", len(records))

    raw_frame = pd.DataFrame(records)
    raw_csv = resolve_output(root, config, "raw_wells_csv")
    write_csv_atomic(raw_frame, raw_csv)
    log_path = resolve_output(root, config, "download_log_csv")
    wells_root = resolve_output(root, config, "per_well_directory")
    combined_frames: list[pd.DataFrame] = []
    delay = float(config["owrd"].get("delay_between_wells_seconds", 0.25))

    for index, record in enumerate(records, start=1):
        well_dir = wells_root / record["well_folder"]
        well_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = well_dir / "metadata.json"
        if overwrite or not metadata_path.exists():
            write_json(metadata_path, record)

        LOGGER.info("[%s/%s] %s", index, len(records), record["well_folder"])
        if fetch_lithology_enabled:
            lithology_path = well_dir / "lithology.csv"
            try:
                frame, status = fetch_lithology(
                    session, record, lithology_path, config, overwrite
                )
                if not frame.empty:
                    combined_frames.append(frame)
                log_event(
                    log_path,
                    record,
                    "lithology",
                    status,
                    url=record["detail_url"],
                )
            except Exception as exc:  # continue so one bad report does not stop the run
                LOGGER.warning("Lithology failed for %s: %s", record["well_folder"], exc)
                log_event(
                    log_path,
                    record,
                    "lithology",
                    "failed",
                    str(exc),
                    record["detail_url"],
                )

        if fetch_pdfs_enabled:
            try:
                _, status = download_well_report(
                    session, record, well_dir, config, overwrite
                )
                log_event(
                    log_path,
                    record,
                    "well_report",
                    status,
                    url=str(record.get("well_log_url") or ""),
                )
            except Exception as exc:  # continue so one bad report does not stop the run
                LOGGER.warning("PDF failed for %s: %s", record["well_folder"], exc)
                log_event(
                    log_path,
                    record,
                    "well_report",
                    "failed",
                    str(exc),
                    str(record.get("well_log_url") or ""),
                )
        if delay > 0 and index < len(records):
            time.sleep(delay)

    combined_path = resolve_output(root, config, "combined_lithology_csv")
    if fetch_lithology_enabled:
        combined = (
            pd.concat(combined_frames, ignore_index=True)
            if combined_frames
            else pd.DataFrame(columns=LITHOLOGY_COLUMNS)
        )
        write_csv_atomic(combined, combined_path)

    # Re-read metadata flags from generated per-well files into the output table.
    raw_frame["lithology_available"] = raw_frame["well_folder"].map(
        lambda name: csv_has_data_row(wells_root / name / "lithology.csv")
    )
    raw_frame["well_report_downloaded"] = raw_frame["well_folder"].map(
        lambda name: (wells_root / name / "well_report.pdf").exists()
    )
    write_gis_outputs(raw_frame, root, config)

    counts = raw_frame["location_class"].value_counts().sort_index().to_dict()
    LOGGER.info("Finished %s wells; location classes: %s", len(raw_frame), counts)
    LOGGER.info("ArcGIS output: %s", resolve_output(root, config, "wells_geopackage"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        LOGGER.error("Interrupted by user")
        raise SystemExit(130)
    except Exception as exc:
        LOGGER.error("Fatal error: %s", exc)
        raise SystemExit(1)
