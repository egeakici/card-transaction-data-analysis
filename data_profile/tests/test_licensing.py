import copy
import unittest

from data_profile.src.licensing import (load_registry, validate_registry, render_data_card,
                                       ROOT)
import yaml


class Licensing(unittest.TestCase):
    def setUp(self):
        self.document = yaml.safe_load((ROOT / "licenses.yaml").read_text(encoding="utf-8"))

    def test_registry_covers_the_actual_source_contracts(self):
        from data_profile.src.sources import SOURCE_META, configurations
        records = load_registry(SOURCE_META)
        self.assertEqual(len(records), 11)
        for config in configurations():
            row = records[config["source_id"]]
            self.assertEqual(config["license"], row["license"])
            self.assertEqual(config["redistribution_tier"], row["redistribution_tier"])

    def test_unknown_duplicate_or_missing_sources_fail_closed(self):
        wrong = copy.deepcopy(self.document)
        wrong["sources"].append(wrong["sources"][0])
        with self.assertRaises(ValueError):
            validate_registry(wrong)
        with self.assertRaises(ValueError):
            load_registry({"missing_source"})
        wrong = copy.deepcopy(self.document)
        del wrong["sources"][0]["evidence_url"]
        with self.assertRaises(ValueError):
            validate_registry(wrong)

    def test_unresolved_permission_cannot_be_promoted_to_a_release_tier(self):
        wrong = copy.deepcopy(self.document)
        row = next(r for r in wrong["sources"] if r["permission_status"] == "not_verified")
        row["redistribution_tier"] = "conditional_source_terms"
        with self.assertRaises(ValueError):
            validate_registry(wrong)
        row["redistribution_tier"] = "hold"
        row["verified_at"] = "2026-11-04"
        with self.assertRaises(ValueError):
            validate_registry(wrong)

    def test_published_grants_require_a_terms_url_and_review_date(self):
        for field in ("license_url", "verified_at"):
            wrong = copy.deepcopy(self.document)
            row = next(r for r in wrong["sources"] if r["permission_status"] == "published_open_license")
            row[field] = None
            with self.assertRaises(ValueError):
                validate_registry(wrong)

    def test_data_card_refresh_preserves_metrics_and_is_idempotent(self):
        from data_profile.src.sources import configurations
        configs = configurations()
        original = "# Card\n\n| bristol | Old | UK | 17 | 2020 to 2021 | unspecified | 4 numeric |\n\n## Preprocessing\n\nUnchanged metrics: 17.\n"
        rendered = render_data_card(original, configs)
        self.assertIn("| 17 | 2020 to 2021 |", rendered)
        self.assertIn("| 4 numeric |", rendered)
        self.assertIn("Unchanged metrics: 17.", rendered)
        self.assertNotIn("unspecified", rendered)
        self.assertIn("LicenseRef-Bristol-Scope-Unresolved", rendered)
        self.assertEqual(rendered, render_data_card(rendered, configs))


if __name__ == "__main__":
    unittest.main()
