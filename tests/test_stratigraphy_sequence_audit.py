"""Exercise scientifically consequential audit edge cases with small fixtures."""
import importlib.util
import sys
import unittest
from decimal import Decimal
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_boardman_stratigraphy.py"
spec = importlib.util.spec_from_file_location("sequence_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def interval(label="A", top="0", bottom="10", row=2, **extra):
    t, b = audit.number(top), audit.number(bottom)
    result = {k: "" for k in audit.SCIENTIFIC}
    result.update(strat_unit=label, start_depth=top, end_depth=bottom,
        source_row=row, start_depth_elev=str(100 - t) if t is not None else "",
        end_depth_elev=str(100 - b) if b is not None else "",
        depth_thickness=str(b - t) if None not in (t, b) else "", picked_by="Person")
    result.update(extra)
    return result


class SequenceAuditTests(unittest.TestCase):
    def codes(self, rows):
        return [r["issue_code"] for r in audit.audit_sequence(rows)]

    def test_exact_decimal_touching_without_float_gap(self):
        self.assertEqual(self.codes([interval(bottom="0.1"), interval("B", "0.1", "0.3", 3)]), [])

    def test_nested_overlap_does_not_create_false_gap(self):
        rows = [interval(bottom="100"), interval("B", "10", "20", 3), interval("C", "50", "60", 4)]
        self.assertEqual(self.codes(rows).count("overlap"), 2)
        self.assertNotIn("gap", self.codes(rows))

    def test_actual_gap_after_nested_interval(self):
        rows = [interval(bottom="100"), interval("B", "10", "20", 3), interval("C", "105", "110", 4)]
        gaps = [f for f in audit.audit_sequence(rows) if f["issue_code"] == "gap"]
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["source_rows"], [2, 4])

    def test_all_invalid_depths_and_nonfinite(self):
        self.assertIn("missing_depth", self.codes([interval(top="")]))
        self.assertIn("invalid_depth", self.codes([interval(top="NaN")]))
        self.assertIn("invalid_depth", self.codes([interval(bottom="Infinity")]))
        both = self.codes([interval(top="", bottom="bad")])
        self.assertIn("missing_depth", both)
        self.assertIn("invalid_depth", both)
        self.assertIn("negative_depth", self.codes([interval(top="-1")]))
        self.assertIn("reversed_depth", self.codes([interval(top="20", bottom="10")]))
        self.assertIn("zero_thickness", self.codes([interval(top="10", bottom="10")]))

    def test_elevation_checks_are_separate_from_depths(self):
        codes = self.codes([interval(start_depth_elev="101")])
        self.assertIn("elevation_thickness_mismatch", codes)
        self.assertIn("implied_surface_inconsistent", codes)
        self.assertIn("missing_elevation", self.codes([interval(start_depth_elev="")]))
        self.assertIn("invalid_elevation", self.codes([interval(start_depth_elev="bad")]))

    def test_repeated_unit_is_not_duplicate_interval(self):
        codes = self.codes([interval(), interval(top="10", bottom="20", row=3)])
        self.assertIn("repeated_unit", codes)
        self.assertNotIn("duplicate_interval", codes)

    def test_duplicates_preserved_in_multiset(self):
        first = interval()
        second = interval(row=3)
        self.assertIn("duplicate_interval", self.codes([first, second]))
        self.assertNotEqual(audit.sequence_signature([first]), audit.sequence_signature([first, second]))

    def test_parent_child_and_prefix_boundary(self):
        rows = [interval("Crbg.Wb", bottom="10"), interval("Crbg.Wb.FrenchmanSprings", "10", "20", 3)]
        self.assertIn("parent_child_mixed", self.codes(rows))
        self.assertNotIn("parent_child_mixed", self.codes([interval("Crbg.Wb"), interval("Crbg.Wbx", "10", "20", 3)]))

    def test_report_variants_preserve_interpreter_disagreement(self):
        a = interval()
        b = interval(picked_by="Other person")
        self.assertEqual(len(audit.variants({"A": [a], "B": [b]})), 2)
        self.assertEqual(audit.sequence_signature([a], audit.GEOMETRY), audit.sequence_signature([b], audit.GEOMETRY))

    def test_numeric_equivalence_distinct_from_verbatim(self):
        a, b = interval(bottom="10.00"), interval(bottom="10.0")
        self.assertNotEqual(audit.sequence_signature([a]), audit.sequence_signature([b]))
        self.assertEqual(audit.sequence_signature([a], numeric=True), audit.sequence_signature([b], numeric=True))

    def test_order_flags_are_partial_and_do_not_rank_facies(self):
        a = interval("Crbg.Grb.N2")
        b = interval("Crbg.Wb.PriestRapids", "10", "20", 3)
        self.assertIn("unexpected_order", self.codes([a, b]))
        self.assertNotIn("unexpected_order", self.codes([interval("Sediment.MissoulaFlood.Sand"), interval("Sediment.MissoulaFlood.Silt", "10", "20", 3)]))
        self.assertNotIn("unexpected_order", self.codes([interval("Crbg.Grb.N2", bottom="20"), interval("Crbg.Wb.PriestRapids", "10", "30", 3)]))

    def test_missing_upper_sequence_is_coverage_note(self):
        self.assertIn("first_pick_below_zero", self.codes([interval(top="25", bottom="30")]))
        self.assertNotIn("gap", self.codes([interval(top="25", bottom="30")]))

    def test_lithology_contact_retains_tied_boundaries(self):
        rows = [{"from_ft": "0", "to_ft": "10", "source_row": 2},
                {"from_ft": "10", "to_ft": "20", "source_row": 3},
                {"from_ft": "20", "to_ft": "20", "source_row": 4}]
        contact = audit.lithology_contact(Decimal(10), rows)
        self.assertEqual(contact["status"], "exact_lithology_boundary")
        self.assertEqual(contact["adjacent_rows_json"], "[2,3]")
        self.assertEqual(audit.lithology_contact(Decimal(5), rows)["status"], "inside_lithology_interval")
        self.assertEqual(audit.lithology_contact(Decimal(21), rows)["status"], "outside_lithology_extent")

    def test_lithology_gap_and_unassessable_contact(self):
        rows = [{"from_ft": "0", "to_ft": "10", "source_row": 2}, {"from_ft": "20", "to_ft": "30", "source_row": 3}]
        self.assertEqual(audit.lithology_contact(Decimal(15), rows)["status"], "in_lithology_gap")
        self.assertEqual(audit.lithology_contact(None, rows)["status"], "unassessable")

    def test_unresolved_basalt_mixed_resolution_without_path_ancestry(self):
        codes = self.codes([interval("Crbg.Undifferentiated"), interval("Crbg.Smb.Pomona", "10", "20", 3)])
        self.assertIn("broad_named_basalt_mixed", codes)
        self.assertNotIn("parent_child_mixed", codes)

    def test_literal_name_screen_and_composite_name(self):
        self.assertEqual(audit.literal_mentions("SILT, SELAH INTERBED"), ["EllensburgFm.Selah"])
        self.assertEqual(audit.literal_mentions("QUINCY SQUAW CREEK"), ["EllensburgFm.Quincy-SquawCreek"])
        self.assertEqual(audit.literal_mentions("GRAY BASALT"), [])


if __name__ == "__main__":
    unittest.main()
