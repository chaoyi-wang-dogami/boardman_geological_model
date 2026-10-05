"""Focused checks for the report-to-well decisions used in all figures."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from driller_analysis_common import canonical_name, well_units  # noqa: E402


class WellUnitTests(unittest.TestCase):
    def test_link_events_without_merging_distinct_or_untagged_wells(self):
        rows = [
            ("1", "100.0", "GARRY L ZOLLMAN", "1", "0", "B", "2020-01-01"),
            ("2", "100.0", "GARRY ZOLLMAN", "0", "1", "A", "2021-01-01"),
            ("3", "200.0", "GARRY ZOLLMAN", "1", "1", "A", "2022-01-01"),
            ("4", "", "OTHER", "1", "0", "A", "2022-01-01"),
            ("5", "", "OTHER", "1", "0", "A", "2022-01-01"),
            ("6", "300.0", "OTHER", "1", "0", "B", "2020-01-01"),
            ("7", "300.0", "OTHER", "1", "0", "A", "2021-01-01"),
            ("8", "400.0", "OTHER", "1", "0", "A", "2020-01-01"),
        ]
        wells = pd.DataFrame(rows, columns=["wl_id", "well_tag_nbr", "bonded_full_name",
                                                "work_new", "work_abandonment", "location_class",
                                                "complete_date_iso"])
        wells["wl_county_code"] = "UMAT"
        wells["bonded_license_nbr"] = wells.bonded_full_name.map(
            lambda name: "1881.0" if name in {"GARRY L ZOLLMAN", "GARRY ZOLLMAN"} else "")
        intervals = pd.DataFrame({
            "well_id": wells.wl_id,
            "from_ft": ["0"] * len(wells),
            "to_ft": ["1"] * len(wells),
            "material_raw": ["BASALT", "BENTONITE", "SAND", "CLAY", "CLAY",
                             "SAND", "GRAVEL", "SILT"],
        })
        location_audit = pd.DataFrame({"wl_id": wells.wl_id,
                                       "within_19_townships": [True] * 7 + [False]})
        units, audit = well_units(wells, intervals, location_audit)
        self.assertEqual(set(units.wl_id), {"1", "3", "4", "5", "6"})
        self.assertEqual(len(units), len(set(units.well_key)))
        self.assertEqual(audit.set_index("wl_id").loc["2", "selection_status"], "abandonment_only")
        self.assertEqual(audit.set_index("wl_id").loc["8", "selection_status"], "outside_townships")
        self.assertEqual(audit.set_index("wl_id").loc["7", "selection_status"], "linked_other_geology_report")
        self.assertTrue(audit.set_index("wl_id").loc["7", "different_geology_logs_for_well"])
        self.assertEqual(units.set_index("wl_id").loc["1", "bonded_full_name"], "GARRY ZOLLMAN")

    def test_zollman_alias_requires_recorded_license(self):
        self.assertEqual(canonical_name("GARRY L ZOLLMAN", "1881.0"), "GARRY ZOLLMAN")
        with self.assertRaises(ValueError):
            canonical_name("GARRY L ZOLLMAN", "other")


if __name__ == "__main__":
    unittest.main()
