"""Checks for GWIS table extraction and report-to-site identifiers."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from download_gwis_stratigraphy import lookup_report_sites, parse_gwis_page, report_key


class GwisStratigraphyTests(unittest.TestCase):
    def test_report_numbers_match_zero_padded_inventory(self):
        self.assertEqual(report_key("morr", "0051846"), ("MORR", "51846"))

    def test_site_table_and_secondary_report_link(self):
        page = """
        <div id="ctl00_PageData_div_stratigraphy"></div>
        <a href="well_report.aspx?q=basic&amp;wl_county_code=MORR&amp;wl_nbr=51846">Log</a>
        <a href="well_report.aspx?q=basic&amp;wl_county_code=MORR&amp;wl_nbr=51847">Log</a>
        <table id="ctl00_PageData_uc_gw_stratigraphy_GridView1">
          <tr><th>Start Depth</th><th>End Depth</th><th>Start Depth Elev.</th>
          <th>End Depth Elev.</th><th>Depth Thickness</th><th>Stratigraphy Unit</th>
          <th>Sample Source</th><th>Picked By</th><th>Est. Age</th><th>Est. Age Err.</th></tr>
          <tr class="row"><td>0.00</td><td>150.00</td><td>1095.00</td>
          <td>945.00</td><td>150.00</td><td><span>AlkaliCanyonFm</span></td>
          <td>WELL LOG</td><td>JOSH HACKETT</td><td>&nbsp;</td><td>&nbsp;</td></tr>
        </table>"""
        frame, links, pager = parse_gwis_page(page, "14045")
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0]["strat_unit"], "AlkaliCanyonFm")
        self.assertEqual(links, {("MORR", "51846"), ("MORR", "51847")})
        self.assertFalse(pager)

    def test_empty_site_is_not_a_failed_parse(self):
        page = """
        <div id="ctl00_PageData_div_stratigraphy"></div>
        <table id="ctl00_PageData_uc_gw_stratigraphy_GridView1">
          <tr><td>No data matches search criteria.</td></tr>
        </table>"""
        frame, _, pager = parse_gwis_page(page, "48330")
        self.assertTrue(frame.empty)
        self.assertFalse(pager)

    def test_unmatched_lookup_is_cached(self):
        class Response:
            text = '<a href="gw_details.aspx?gw_site_id=14045">Groundwater Site</a>'

            def raise_for_status(self):
                pass

        class Session:
            calls = 0

            def get(self, url, timeout):
                self.calls += 1
                return Response()

        session = Session()
        report = {
            "wl_id": "437563", "wl_county_code": "MORR", "wl_nbr": "51846",
            "detail_url": "https://example.test/well-log",
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "download_gwis_stratigraphy.build_session", return_value=session
        ):
            root = Path(directory)
            links, failures = lookup_report_sites(
                root, {}, [report], set(), refresh=False, timeout=1
            )
            self.assertEqual(links, {("MORR", "51846"): "14045"})
            self.assertFalse(failures)
            self.assertEqual(session.calls, 1)
            links, failures = lookup_report_sites(
                root, {}, [report], set(), refresh=False, timeout=1
            )
            self.assertEqual(session.calls, 1)
            self.assertEqual(links[("MORR", "51846")], "14045")


if __name__ == "__main__":
    unittest.main()
