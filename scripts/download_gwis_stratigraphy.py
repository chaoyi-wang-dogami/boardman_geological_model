"""Incremental OWRD GWIS stratigraphy for the saved 19-township inventory.

GWIS interpretations belong to groundwater *sites*, which may reference several
well reports. Save the source rows alongside each linked report's existing files.
"""

from __future__ import annotations

import csv
import logging
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
from lxml import html

from download_owrd import build_session, write_csv_atomic


LOGGER = logging.getLogger("owrd_downloader")
SITE_LAYER = (
    "https://gis.wrd.state.or.us/server/rest/services/dynamic/"
    "Groundwater_Sites_by_Themes_WGS84/MapServer"
)
GWIS_URL = (
    "https://apps.wrd.state.or.us/apps/gw/gw_info/gw_info_report/"
    "gw_details.aspx?gw_site_id={site_id}"
)
STRAT_FIELDS = [
    "gw_site_id", "start_depth", "end_depth", "start_depth_elev",
    "end_depth_elev", "depth_thickness", "strat_unit", "sample_source",
    "picked_by", "est_age", "est_age_error", "gw_info_url", "source_kind",
    "scraped_at",
]
REPORT_FIELDS = ["well_folder", "wl_id", "wl_county_code", "wl_nbr", "gw_site_id", "link_source"]
PER_REPORT_FIELDS = ["well_folder", "wl_id", *STRAT_FIELDS]
SCRAPE_ROOT = "03_processed/waterwells_after2010_300ftplus_NM_04162026"
REPORT_LOOKUP_FIELDS = ["wl_id", "wl_county_code", "wl_nbr", "gw_site_id", "status"]


def number(value: object) -> str:
    """Normalize report and site numbers without changing the source CSV."""
    try:
        return str(int(float(str(value).strip())))
    except (ValueError, TypeError, OverflowError):
        return ""


def report_key(county: object, number_value: object) -> tuple[str, str]:
    return str(county or "").strip().upper(), number(number_value)


def query_site_links(session: requests.Session, counties: set[str], timeout: float) -> dict[tuple[str, str], str]:
    """Look up GWIS's primary report for each public groundwater site."""
    links: dict[tuple[str, str], str] = {}
    for county in sorted(counties):
        for layer in (4, 5, 6):  # current observation, former, other sites
            offset = 0
            while True:
                response = session.get(
                    f"{SITE_LAYER}/{layer}/query",
                    params={
                        "f": "json", "where": f"gw_wl_county_code='{county}'",
                        "outFields": "gw_site_id,gw_wl_county_code,gw_wl_nbr",
                        "returnGeometry": "false", "resultOffset": offset,
                        "resultRecordCount": 2000,
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                payload = response.json()
                if "error" in payload:
                    raise RuntimeError(f"GWIS site lookup failed: {payload['error']}")
                features = payload.get("features", [])
                for feature in features:
                    attrs = feature["attributes"]
                    key = report_key(attrs.get("gw_wl_county_code"), attrs.get("gw_wl_nbr"))
                    site_id = number(attrs.get("gw_site_id"))
                    if key[1] and site_id:
                        old = links.get(key)
                        if old and old != site_id:
                            raise ValueError(f"Conflicting GWIS sites for {key}: {old}, {site_id}")
                        links[key] = site_id
                offset += len(features)
                if len(features) < 2000:
                    break
    return links


def existing_scrape(root: Path) -> tuple[dict[tuple[str, str], str], dict[str, pd.DataFrame]]:
    """Reuse complete site tables from the separately scraped county files."""
    base = root / SCRAPE_ROOT
    links: dict[tuple[str, str], str] = {}
    site_rows: dict[str, pd.DataFrame] = {}
    for county_dir in base.glob("* County"):
        summaries = list(county_dir.glob("*summary*.csv"))
        strat_files = list(county_dir.glob("*stratigraphy*.csv"))
        if len(summaries) != 1 or len(strat_files) != 1:
            continue
        summary = pd.read_csv(summaries[0], dtype=str, keep_default_na=False)
        strat = pd.read_csv(strat_files[0], dtype=str, keep_default_na=False)
        grouped = {number(site): rows for site, rows in strat.groupby("gw_site_id", sort=False)}
        expected: dict[str, int] = {}
        for row in summary.to_dict("records"):
            site_id = number(row.get("gw_site_id"))
            key = report_key(row.get("county"), row.get("wl_nbr"))
            if site_id and key[1]:
                old = links.get(key)
                if old and old != site_id:
                    raise ValueError(f"Conflicting scraped GWIS sites for {key}: {old}, {site_id}")
                links[key] = site_id
            count = number(row.get("strat_count"))
            if site_id and count:
                old_count = expected.get(site_id)
                if old_count is not None and old_count != int(count):
                    raise ValueError(f"Conflicting stratigraphy counts for site {site_id}")
                expected[site_id] = int(count)
        for site_id, count in expected.items():
            rows = grouped.get(site_id, strat.iloc[0:0])
            if len(rows) != count:
                continue  # Incomplete scrape: fetch the site instead.
            frame = pd.DataFrame(columns=STRAT_FIELDS)
            for field in STRAT_FIELDS:
                if field in rows.columns:
                    frame[field] = rows[field].to_numpy()
            frame["gw_site_id"] = site_id
            frame["gw_info_url"] = GWIS_URL.format(site_id=site_id)
            frame["source_kind"] = "existing_county_scrape"
            if "scraped_at" not in rows:
                frame["scraped_at"] = ""
            site_rows[site_id] = frame[STRAT_FIELDS]
    return links, site_rows


def lookup_report_sites(
    root: Path, config: dict, reports: list[dict], known_keys: set[tuple[str, str]],
    *, refresh: bool, timeout: float,
) -> tuple[dict[tuple[str, str], str], set[tuple[str, str]]]:
    """Resolve secondary GWIS links from well-log pages, caching every result."""
    path = root / "01_raw/owrd/gwis_report_site_lookups.csv"
    cached: dict[tuple[str, str], dict] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                cached[report_key(row["wl_county_code"], row["wl_nbr"])] = row

    pending = []
    for report in reports:
        key = report_key(report["wl_county_code"], report["wl_nbr"])
        if key in known_keys:
            continue
        if refresh or key not in cached or cached[key]["status"] == "failed":
            pending.append(report)

    local = threading.local()

    def fetch(report: dict) -> tuple[tuple[str, str], dict]:
        if not hasattr(local, "session"):
            local.session = build_session(config)
        key = report_key(report["wl_county_code"], report["wl_nbr"])
        try:
            response = local.session.get(report["detail_url"], timeout=timeout)
            response.raise_for_status()
            ids = set(re.findall(r"gw_details\.aspx\?gw_site_id=(\d+)", response.text, re.I))
            if len(ids) > 1:
                raise ValueError(f"Report {key} links to multiple GWIS sites: {sorted(ids)}")
            site_id = next(iter(ids), "")
            status = "linked" if site_id else "no_site_link"
        except Exception as exc:
            LOGGER.warning("GWIS link lookup failed for %s: %s", key, exc)
            site_id, status = "", "failed"
        return key, {
            "wl_id": report["wl_id"], "wl_county_code": key[0], "wl_nbr": key[1],
            "gw_site_id": site_id, "status": status,
        }

    if pending:
        LOGGER.info("Checking %s unmatched well-log pages for secondary GWIS site links", len(pending))
        with ThreadPoolExecutor(max_workers=4) as pool:
            for index, future in enumerate(as_completed(pool.submit(fetch, report) for report in pending), start=1):
                key, row = future.result()
                cached[key] = row
                if index % 100 == 0:
                    write_csv_atomic(pd.DataFrame(cached.values(), columns=REPORT_LOOKUP_FIELDS), path)
                    LOGGER.info("GWIS report links checked %s/%s", index, len(pending))
        write_csv_atomic(pd.DataFrame(cached.values(), columns=REPORT_LOOKUP_FIELDS), path)

    links = {key: number(row["gw_site_id"]) for key, row in cached.items() if row["status"] == "linked"}
    failures = {key for key, row in cached.items() if row["status"] == "failed"}
    return links, failures


def parse_gwis_page(page: str, site_id: str) -> tuple[pd.DataFrame, set[tuple[str, str]], bool]:
    """Read the GWIS stratigraphy grid and cross-referenced well-log links."""
    tree = html.fromstring(page)
    report_links: set[tuple[str, str]] = set()
    for href in tree.xpath("//a[contains(@href, 'well_report.aspx')]/@href"):
        query = parse_qs(urlparse(href).query)
        key = report_key((query.get("wl_county_code") or [""])[0], (query.get("wl_nbr") or [""])[0])
        if key[1]:
            report_links.add(key)

    grids = tree.xpath("//table[@id='ctl00_PageData_uc_gw_stratigraphy_GridView1']")
    if not grids:
        # A valid GWIS page can omit the grid when no interpretations exist.
        if not tree.xpath("//*[@id='ctl00_PageData_div_stratigraphy']"):
            raise ValueError(f"GWIS site {site_id}: no stratigraphy section; page may have changed")
        return pd.DataFrame(columns=STRAT_FIELDS), report_links, False
    grid = grids[0]
    headings = [" ".join(cell.itertext()).strip() for cell in grid.xpath("./tr[1]/th")]
    if not headings and "No data matches search criteria" in " ".join(grid.itertext()):
        return pd.DataFrame(columns=STRAT_FIELDS), report_links, False
    expected = [
        "Start Depth", "End Depth", "Start Depth Elev.", "End Depth Elev.",
        "Depth Thickness", "Stratigraphy Unit", "Sample Source", "Picked By",
        "Est. Age", "Est. Age Err.",
    ]
    if headings != expected:
        raise ValueError(f"GWIS site {site_id}: unexpected stratigraphy columns {headings}")
    rows = []
    for tr in grid.xpath("./tr[contains(concat(' ', normalize-space(@class), ' '), ' row ') or contains(concat(' ', normalize-space(@class), ' '), ' rowalt ')]"):
        cells = [" ".join(" ".join(td.itertext()).split()).replace("\xa0", "").strip() for td in tr.xpath("./td")]
        if len(cells) != 10:
            raise ValueError(f"GWIS site {site_id}: unexpected stratigraphy row width {len(cells)}")
        rows.append(dict(zip(STRAT_FIELDS[1:11], cells)))
    frame = pd.DataFrame(rows, columns=STRAT_FIELDS[1:11])
    frame.insert(0, "gw_site_id", site_id)
    frame["gw_info_url"] = GWIS_URL.format(site_id=site_id)
    frame["source_kind"] = "gwis_live"
    frame["scraped_at"] = pd.Timestamp.now(tz="UTC").isoformat()
    pager = bool(grid.xpath(".//a[contains(@href, 'Page$') or contains(@href, 'Page%24')]"))
    return frame[STRAT_FIELDS], report_links, pager


def fetch_site(session: requests.Session, site_id: str, timeout: float) -> tuple[pd.DataFrame, set[tuple[str, str]]]:
    url = GWIS_URL.format(site_id=site_id)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    frame, links, pager = parse_gwis_page(response.text, site_id)
    if pager:
        tree = html.fromstring(response.text)
        fields = {
            node.get("name"): node.get("value", "")
            for node in tree.xpath("//input[@name]")
            if node.get("type", "").lower() in {"hidden", "text"}
        }
        fields["ctl00$PageData$uc_gw_stratigraphy$tb_recs_per_page"] = "1000"
        fields["ctl00$PageData$uc_gw_stratigraphy$btn_search"] = "Find"
        response = session.post(url, data=fields, timeout=timeout)
        response.raise_for_status()
        frame, links, pager = parse_gwis_page(response.text, site_id)
        if pager:
            # Never save a partial table as though it were complete.
            raise ValueError(f"GWIS site {site_id} exceeds the 1000-row page limit")
    return frame, links


def read_existing_site(
    wells_root: Path, site_id: str, keys: set[tuple[str, str]], by_key: dict
) -> pd.DataFrame | None:
    """Reuse a linked report's saved file instead of keeping a site folder."""
    for key in sorted(keys):
        path = wells_root / by_key[key]["well_folder"] / "stratigraphy.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        if list(frame.columns) != PER_REPORT_FIELDS:
            raise ValueError(f"Unexpected stratigraphy schema: {path}")
        if not frame.empty and set(frame["gw_site_id"]) != {site_id}:
            raise ValueError(f"Wrong GWIS site ID in {path}: expected {site_id}")
        return frame[STRAT_FIELDS].copy()
    return None


def write_report_stratigraphy(
    wells_root: Path, report: dict, frame: pd.DataFrame, *, refresh: bool
) -> None:
    destination = wells_root / report["well_folder"] / "stratigraphy.csv"
    if destination.exists() and not refresh:
        return
    output = frame.copy()
    output.insert(0, "wl_id", report["wl_id"])
    output.insert(0, "well_folder", report["well_folder"])
    write_csv_atomic(output, destination)


def download_stratigraphy(root: Path, config: dict, *, refresh: bool = False, limit: int | None = None) -> int:
    """Add GWIS files while leaving the original well inventory and downloads intact."""
    inventory = root / config["outputs"]["raw_wells_csv"]
    if not inventory.exists():
        raise FileNotFoundError(f"Saved 19-township inventory missing: {inventory}")
    with inventory.open(newline="", encoding="utf-8") as handle:
        reports = list(csv.DictReader(handle))
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be at least 1")
        reports = reports[:limit]
    by_key = {report_key(r["wl_county_code"], r["wl_nbr"]): r for r in reports}
    if len(by_key) != len(reports):
        raise ValueError("The saved inventory has duplicate county/report numbers")
    wells_root = root / config["outputs"]["per_well_directory"]
    timeout = float(config["owrd"].get("request_timeout_seconds", 90))
    session = build_session(config)
    primary = query_site_links(session, {key[0] for key in by_key}, timeout)
    scrape_links, scraped_sites = existing_scrape(root)
    previous_links: dict[tuple[str, str], str] = {}
    previous_sources: dict[tuple[str, str], str] = {}
    link_path = root / "01_raw/owrd/gwis_stratigraphy_links.csv"
    if link_path.exists():
        with link_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = report_key(row["wl_county_code"], row["wl_nbr"])
                previous_links[key] = number(row["gw_site_id"])
                previous_sources[key] = row["link_source"]
    site_to_keys: dict[str, set[tuple[str, str]]] = defaultdict(set)
    key_to_site: dict[tuple[str, str], str] = {}
    link_sources: dict[tuple[str, str], str] = {}
    for source, links in (
        ("previous_download", previous_links),
        ("gwis_primary_layer", primary),
        ("existing_county_scrape", scrape_links),
    ):
        for key, site_id in links.items():
            if key not in by_key:
                continue
            prior = key_to_site.get(key)
            if prior and prior != site_id:
                LOGGER.warning("Conflicting GWIS links for %s: %s vs %s; using %s", key, prior, site_id, prior)
                continue
            site_to_keys[site_id].add(key)
            key_to_site[key] = site_id
            link_sources.setdefault(
                key, previous_sources.get(key, source) if source == "previous_download" else source
            )

    direct_links, lookup_failures = lookup_report_sites(
        root, config, reports, set(key_to_site), refresh=refresh, timeout=timeout
    )
    for key, site_id in direct_links.items():
        if key not in by_key:
            continue
        prior = key_to_site.get(key)
        if prior and prior != site_id:
            LOGGER.warning("Well-log page changes GWIS site for %s: %s -> %s", key, prior, site_id)
            site_to_keys[prior].discard(key)
        site_to_keys[site_id].add(key)
        key_to_site[key] = site_id
        link_sources[key] = "well_log_detail_link"
    site_to_keys = defaultdict(set, {site: keys for site, keys in site_to_keys.items() if keys})

    fetched = reused = failed = 0
    site_frames: dict[str, pd.DataFrame] = {}
    delay = float(config["owrd"].get("delay_between_wells_seconds", 0.25))
    for index, site_id in enumerate(sorted(site_to_keys, key=int), start=1):
        frame = None if refresh else read_existing_site(wells_root, site_id, site_to_keys[site_id], by_key)
        if frame is not None:
            reused += 1
        elif site_id in scraped_sites and not refresh:
            frame = scraped_sites[site_id]
            reused += 1
        else:
            try:
                frame, links = fetch_site(session, site_id, timeout)
                for key in links & by_key.keys():
                    prior = key_to_site.get(key)
                    if prior and prior != site_id:
                        LOGGER.warning("Conflicting GWIS cross-reference for %s: %s vs %s", key, prior, site_id)
                        continue
                    site_to_keys[site_id].add(key)
                    key_to_site[key] = site_id
                    link_sources.setdefault(key, "gwis_site_cross_reference")
                fetched += 1
                if delay:
                    time.sleep(delay)
            except Exception as exc:
                failed += 1
                LOGGER.warning("GWIS site %s failed: %s", site_id, exc)
                continue
        site_frames[site_id] = frame
        for key in site_to_keys[site_id]:
            write_report_stratigraphy(wells_root, by_key[key], frame, refresh=refresh)
        if index % 100 == 0:
            LOGGER.info("GWIS sites %s/%s; fetched=%s reused=%s failed=%s", index, len(site_to_keys), fetched, reused, failed)

    link_rows = []
    for site_id, keys in site_to_keys.items():
        for key in sorted(keys):
            report = by_key[key]
            link_rows.append({
                "well_folder": report["well_folder"], "wl_id": report["wl_id"],
                "wl_county_code": key[0], "wl_nbr": key[1], "gw_site_id": site_id,
                "link_source": link_sources[key],
            })
            if site_id not in site_frames:
                continue
            write_report_stratigraphy(wells_root, report, site_frames[site_id], refresh=refresh)
    write_csv_atomic(pd.DataFrame(link_rows, columns=REPORT_FIELDS), link_path)
    audit_rows = []
    for report in reports:
        key = report_key(report["wl_county_code"], report["wl_nbr"])
        site_id = key_to_site.get(key, "")
        frame = site_frames.get(site_id)
        status = (
            "link_lookup_failed" if not site_id and key in lookup_failures else
            "no_gwis_site_link" if not site_id else
            "site_fetch_failed" if frame is None else
            "site_without_stratigraphy" if frame.empty else
            "has_stratigraphy"
        )
        audit_rows.append({
            "well_folder": report["well_folder"], "wl_id": report["wl_id"],
            "gw_site_id": site_id, "stratigraphy_rows": len(frame) if frame is not None else "",
            "status": status,
        })
    write_csv_atomic(
        pd.DataFrame(audit_rows), root / "01_raw/owrd/gwis_stratigraphy_audit.csv"
    )
    LOGGER.info(
        "GWIS stratigraphy: %s reports linked, %s site tables fetched, %s reused, %s failed; %s reports had no site link",
        len(link_rows), fetched, reused, failed, len(reports) - len(key_to_site),
    )
    return 1 if failed or lookup_failures else 0
