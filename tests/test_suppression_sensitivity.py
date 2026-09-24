from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from gba_ops_reanalysis.suppression_sensitivity import parse_tips_procedure


class SuppressionParserTest(unittest.TestCase):
    def test_visible_count_is_preserved_in_all_scenarios(self) -> None:
        procedure = ET.fromstring(
            "<Prozedur><OPS_301>8-839.88</OPS_301><Anzahl>4</Anzahl></Prozedur>"
        )
        parsed = parse_tips_procedure(procedure)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["visible_count"], 4)
        self.assertFalse(parsed["suppression_flag"])
        self.assertEqual((parsed["lower_count"], parsed["midpoint_count"], parsed["upper_count"]), (4, 4, 4))

    def test_empty_privacy_tag_maps_to_one_two_three(self) -> None:
        procedure = ET.fromstring(
            "<Prozedur><OPS_301>8-839.81</OPS_301><Anzahl_Datenschutz/></Prozedur>"
        )
        parsed = parse_tips_procedure(procedure)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["visible_count"], 0)
        self.assertTrue(parsed["suppression_flag"])
        self.assertEqual((parsed["lower_count"], parsed["midpoint_count"], parsed["upper_count"]), (1, 2, 3))

    def test_nested_privacy_metadata_is_not_a_visible_case(self) -> None:
        procedure = ET.fromstring(
            """
            <Prozedur>
              <OPS_301>8-839.83</OPS_301>
              <Anzahl_Gesamtbericht_mit_Datenschutz>
                <Anzahl_FA_Datenschutz>1</Anzahl_FA_Datenschutz>
              </Anzahl_Gesamtbericht_mit_Datenschutz>
            </Prozedur>
            """
        )
        parsed = parse_tips_procedure(procedure)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["visible_count"], 0)
        self.assertTrue(parsed["suppression_flag"])
        self.assertEqual((parsed["lower_count"], parsed["midpoint_count"], parsed["upper_count"]), (1, 2, 3))

    def test_non_tips_entry_is_ignored(self) -> None:
        procedure = ET.fromstring(
            "<Prozedur><OPS_301>8-800.0</OPS_301><Anzahl_Datenschutz/></Prozedur>"
        )
        self.assertIsNone(parse_tips_procedure(procedure))

    def test_ambulatory_tag_can_be_identified_but_is_not_a_pipeline_pattern(self) -> None:
        procedure = ET.fromstring(
            "<Ambulante_Operation><OPS_301>8-839.81</OPS_301><Anzahl_Datenschutz/></Ambulante_Operation>"
        )
        parsed = parse_tips_procedure(procedure)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed["suppression_flag"])


if __name__ == "__main__":
    unittest.main()
