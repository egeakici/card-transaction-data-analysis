import hashlib
from itertools import combinations
from pathlib import Path
import unittest
import uuid

import polars as pl

from split_pipeline.common import hash_fold
from split_pipeline.canonical import attach_labels
from split_pipeline.folds import classify_rows, hash_only_merchants, majority_and_overrides
from split_pipeline.leakage import find_pairs
from split_pipeline.make_splits import CONFIG
from split_pipeline.reports import exclusions
from split_pipeline.test_merchants import build_test_merchants


class SplitTests(unittest.TestCase):
    def test_exclusions_preserve_counts_without_the_deleted_legacy_csv(self):
        repo = Path(__file__).resolve().parents[1]
        directory = repo / "train-test-datasets" / "intermediate" / ("synthetic_" + uuid.uuid4().hex)
        assert directory.resolve().is_relative_to(repo.resolve())
        directory.mkdir(parents=True)
        try:
            pl.DataFrame({"source_id": ["s"] * 3,
                          "reason": ["blank", "blank", "documentation"]}).write_parquet(directory / "excluded.parquet")
            frame = pl.DataFrame({"source_id": ["s"] * 4,
                                  "row_status": ["labeled", "unresolved", "unresolved", "no_key"],
                                  "fold": [0, 0, 9, None]}).lazy()
            config = {**CONFIG, "profile_exclusions": "excluded.parquet"}
            self.assertNotIn("legacy_csv", config)
            rows = exclusions(frame, directory, directory, config)
            historical = [row for row in rows if row["population"] == "legacy_csv"]
            self.assertEqual({row["source"]: (row["row_status"], row["rows"]) for row in historical},
                             {"indonesia": ("out_of_scope", 53916), "oklahoma": ("superseded_input", 900000)})
            self.assertTrue(all(not row["in_canonical_reconciliation"] for row in historical))
            current = [row for row in rows if row["population"] == "canonical"]
            self.assertEqual({row["row_status"]: row["rows"] for row in current},
                             {"no_key": 1, "unresolved": 1})
            profile = [row for row in rows if row["population"] == "profile_noncanonical"]
            self.assertEqual({row["row_status"]: row["rows"] for row in profile},
                             {"blank_source_row": 2, "not_a_transaction": 1})
            saved = pl.read_csv(directory / "excluded_summary.csv")
            self.assertEqual(saved.height, len(rows))
            self.assertEqual(saved.filter(pl.col("population") == "legacy_csv")["rows"].sum(), 953916)
        finally:
            for path in directory.iterdir():
                assert path.resolve().is_relative_to(directory.resolve()) and path.is_file()
                path.unlink()
            directory.rmdir()

    def test_keys_are_verbatim_and_sha1_not_python_hash(self):
        for key in [" A ", "A", "İŞLETME", "0742", "a"]:
            self.assertEqual(hash_fold(key), int(hashlib.sha1(key.encode("utf8")).hexdigest(), 16) % 10)

    def test_exclusion_precedence_and_unlabeled(self):
        frame = pl.DataFrame({"key_loose": [None, "", "A", "B", "C", "D", "E", "F"],
                              "merchant_masked": [False, True, True, False, False, False, False, False],
                              "taxonomy_label": ["X.a", "X.a", "X.a", None, "NOT_A_TRANSACTION",
                                                 CONFIG["excluded_l2"][0], CONFIG["unresolved_labels"][0], "X.a"]})
        status = classify_rows(frame.lazy(), ["X.a"], CONFIG).collect()["row_status"].to_list()
        self.assertEqual(status, ["no_key", "no_key", "masked", "unlabeled", "not_a_transaction",
                                  "excluded_class", "unresolved", "labeled"])

    def test_majority_tie_and_rare_class_cover_three_splits(self):
        raw = pl.DataFrame({"key_loose": ["ONE", "ONE", "TWO", "THREE", "UNLABELED"],
                            "source_id": ["s1", "s2", "s1", "s2", "s1"],
                            "merchant_masked": [False] * 5,
                            "taxonomy_label": ["X.b", "X.a", "X.a", "X.a", None]})
        frame = classify_rows(raw.lazy(), ["X.a", "X.b"], CONFIG)
        base = hash_only_merchants(frame, CONFIG)
        registry, _, rare, overrides = majority_and_overrides(base, frame, ["X.a", "X.b"], CONFIG)
        one = registry.filter(pl.col("merchant_key") == "ONE").row(0, named=True)
        self.assertEqual(one["majority_l2"], "X.a")
        self.assertEqual(one["label_purity"], 0.5)
        selected = registry.filter(pl.col("majority_l2") == "X.a")
        self.assertEqual(set(selected["fold"]), {0, 8, 9})
        self.assertTrue(selected["fold_override"].all())
        unlabeled = registry.filter(pl.col("merchant_key") == "UNLABELED").row(0, named=True)
        self.assertFalse(unlabeled["fold_override"])
        self.assertIsNone(unlabeled["majority_l2"])
        self.assertEqual(unlabeled["n_labeled_rows"], 0)
        self.assertEqual(len(overrides), 3)
        rebuilt, _, _, _ = majority_and_overrides(base, frame, ["X.a", "X.b"], CONFIG)
        self.assertTrue(registry.equals(rebuilt))

    def test_no_override_at_threshold(self):
        config = {**CONFIG, "rare_class_min_merchants": 3}
        raw = pl.DataFrame({"key_loose": ["A", "B", "C"], "source_id": ["s"] * 3,
                            "row_status": ["labeled"] * 3, "taxonomy_label": ["X.a"] * 3})
        base = hash_only_merchants(raw.lazy(), config)
        registry, _, rare, overrides = majority_and_overrides(base, raw.lazy(), ["X.a"], config)
        self.assertFalse(registry["fold_override"].any())
        self.assertEqual(overrides, [])
        self.assertEqual(rare, [])
        self.assertTrue((registry["fold"] == registry["fold_hash"]).all())

    def test_leakage_top_k_matches_exhaustive_pairs(self):
        keys = ["HOLIDAY INN", "HOLIDAY INN EXPRESS", "HOLIDAY INN EXPRESS SU", "HOLIDAY INN NORTH",
                "ALPHA", "ALPHABET", "ACME SHOP ONE", "ACME SHOP TWO", "ACME SHOP THREE", "OTHER"]
        frame = pl.DataFrame({"merchant_key": keys, "split": ["train", "test", "validation", "train", "test",
                                                              "train", "test", "validation", "train", "test"],
                              "n_rows": [2**index for index in range(len(keys))]})
        expected = []
        for a, b in combinations(frame.to_dicts(), 2):
            ka, kb = a["merchant_key"], b["merchant_key"]
            related = ka.startswith(kb) or kb.startswith(ka) or (
                len(ka.split()) >= 2 and len(kb.split()) >= 2 and ka.split()[:2] == kb.split()[:2])
            if related and a["split"] != b["split"]:
                expected.append((a["n_rows"] + b["n_rows"], tuple(sorted([ka, kb]))))
        expected.sort(reverse=True)
        result = find_pairs(frame, 4)
        self.assertEqual([(row["combined_rows"], (row["key_a"], row["key_b"])) for row in result], expected[:4])

    def test_test_frame_mcc_flags_and_all_status_counts(self):
        root = Path(__file__).resolve().parents[1]
        directory = root / "train-test-datasets" / "intermediate" / ("synthetic_" + uuid.uuid4().hex)
        assert directory.resolve().is_relative_to(root.resolve())
        directory.mkdir(parents=True)
        try:
            pool = pl.DataFrame({"key_loose": ["SHOP"] * 4, "key_strict": ["SHOP A", "SHOP A", "SHOP B", "SHOP B"],
                                 "merchant_raw": ["Shop A", "Shop A", "Shop B", "Shop B"],
                                 "source_id": ["s1", "s1", "s2", "s2"], "txn_date": ["2020-01-01"] * 4,
                                 "mcc_generic": ["0742", "0742", "5411", "5812"],
                                 "mcc_origin": ["original", "original", "linked", "linked"],
                                 "row_status": ["labeled", "masked", "unlabeled", "unresolved"]})
            merchants = pl.DataFrame({"merchant_key": ["SHOP"], "fold": [9], "n_rows": [4],
                                      "sources": [["s1", "s2"]], "majority_l2": ["X.a"], "label_purity": [1.0]})
            build_test_merchants(pool.lazy(), merchants, directory, CONFIG)
            row = pl.read_parquet(directory / "test_merchants.parquet").row(0, named=True)
            self.assertTrue(row["mcc_disagreement_across_sources"])
            self.assertTrue(row["mcc_disagreement_within_source"])
            self.assertEqual(row["majority_mcc_generic"], "0742")
            self.assertEqual(sum(v["n_rows"] for v in row["row_status_distribution"]), 4)
        finally:
            for path in directory.iterdir():
                assert path.resolve().is_relative_to(directory.resolve()) and path.is_file()
                path.unlink()
            directory.rmdir()

    def test_original_file_linkage_handles_interleaved_canonical_rows(self):
        repo = Path(__file__).resolve().parents[1]
        directory = repo / "train-test-datasets" / "intermediate" / ("synthetic_" + uuid.uuid4().hex)
        assert directory.resolve().is_relative_to(repo.resolve())
        (directory / "audit" / "audit").mkdir(parents=True)
        (directory / "output" / "reports").mkdir(parents=True)
        try:
            pl.DataFrame({"source_id": ["s", "s"], "source_file": ["real-world-datas/s/a.csv", "real-world-datas/s/b.csv"],
                          "sha256": ["same-a", "same-b"], "canonical_rows": [2, 2]}).write_csv(directory / "manifest.csv")
            pl.DataFrame({"source_id": ["s", "s"], "source_file": ["s/a.csv", "s/b.csv"],
                          "file_id": ["a", "b"], "source_sha256": ["same-a", "same-b"],
                          "is_primary_input": ["True", "True"]}).write_csv(directory / "audit" / "file_inventory.csv")
            for fid in ["a", "b"]:
                pl.DataFrame({"source_id": ["s", "s"], "source_sheet": ["", ""], "source_row": [2, 3],
                              "taxonomy_label": ["X." + fid] * 2, "evidence_method": ["test"] * 2,
                              "rule_id": ["rule"] * 2, "mcc_code_linked": ["0742"] * 2,
                              "mcc_only_label": [""] * 2, "mcc_link_method": ["test"] * 2,
                              "needs_review": [False] * 2, "mcc_disagreement": [False] * 2}).write_parquet(
                                  directory / "audit" / "audit" / (fid + ".parquet"))
            scan = pl.DataFrame({"row_id": [1, 2, 3, 4], "source_id": ["s"] * 4,
                                 "source_file": ["real-world-datas/s/a.csv", "real-world-datas/s/b.csv"] * 2,
                                 "source_sheet": [""] * 4, "source_row": [2, 2, 3, 3],
                                 "mcc_code": ["0742"] * 4, "mcc_analysis": ["0742"] * 4}).lazy()
            config = {**CONFIG, "profile_manifest": "manifest.csv", "audit_root": "audit", "included_sources": ["s"]}
            joined, rates, _ = attach_labels(scan, directory, directory / "output", config, "input-hash")
            actual = joined.collect().sort("row_id")
            self.assertEqual(actual["taxonomy_label"].to_list(), ["X.a", "X.b", "X.a", "X.b"])
            self.assertEqual(actual["row_id"].n_unique(), 4)
            self.assertEqual(rates[0]["label_join_rate"], 1.0)
            cached, _, _ = attach_labels(scan, directory, directory / "output", config, "input-hash")
            self.assertTrue(cached.collect().sort("row_id").equals(actual))
        finally:
            for child in sorted(directory.rglob("*"), key=lambda path: len(path.parts), reverse=True):
                assert child.resolve().is_relative_to(directory.resolve())
                if child.is_file():
                    child.unlink()
                else:
                    child.rmdir()
            directory.rmdir()


if __name__ == "__main__":
    unittest.main()
