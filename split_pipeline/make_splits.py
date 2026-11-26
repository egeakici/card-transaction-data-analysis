"""Build deterministic merchant splits from the canonical eleven-source population."""
from __future__ import annotations

CONFIG = {
    "input": "derived/analysis.parquet",
    "output": "train-test-datasets",
    "profile_manifest": "outputs/manifest.csv",
    "profile_exclusions": "derived/excluded_rows.parquet",
    # Historical counts verified against the legacy CSV before its deletion;
    # retained in train-test-datasets/excluded_summary.csv, outside the canonical population.
    "historical_exclusions": [
        {"source": "indonesia", "row_status": "out_of_scope", "rows": 53916,
         "reason": "outside the eleven-source study"},
        {"source": "oklahoma", "row_status": "superseded_input", "rows": 900000,
         "reason": "replaced by canonical FY2009-FY2027 inputs"},
    ],
    "decisions": "outputs/DECISIONS.md",
    "audit_root": "real-world-datas-regex-labelled/_taxonomy_analysis",
    "taxonomy": "outputs/taxonomy/taxonomy.json",
    "source_configs": "data_profile/config/sources",
    "included_sources": ["bristol", "delaware", "dwp", "eden", "indiana", "ipo", "moneydata",
                         "oklahoma", "solihull", "stockport", "sunderland"],
    "columns": {
        "merchant_key": "key_loose",
        "merchant_key_strict": "key_strict",
        "source": "source_id",
        "label": "taxonomy_label",
        "merchant_raw": "merchant_raw",
        "mcc_code": "mcc_code",
        "mcc_generic": "mcc_generic",
        "mcc_origin": "original if mcc_code is populated; otherwise linked",
        "record_type": "record_type",
        "merchant_masked": "merchant_masked",
        "date": "txn_date",
    },
    "schema_rows": 1000,
    "validation_rows_per_source": 10000,
    "minimum_key_match_rate": 0.995,
    "minimum_oklahoma_label_join_rate": 0.95,
    "compression": "zstd",
    "parquet_row_group_size": 100000,
    "hash_block_bytes": 8 * 1024 * 1024,
    "row_id_offset": 1,
    "rare_class_min_merchants": 30,
    "rare_fold_sequence": [9, 8, 0, 1, 2, 3, 4, 5, 6, 7],
    "row_status_precedence": ["no_key", "masked", "unlabeled", "not_a_transaction",
                              "excluded_class", "unresolved", "labeled"],
    "unresolved_labels": ["UNRESOLVED_INSUFFICIENT_EVIDENCE", "UNRESOLVED_AMBIGUOUS",
                          "UNRESOLVED_OUT_OF_TAXONOMY"],
    "split_expected_shares": {"train": 0.8, "validation": 0.1, "test": 0.1},
    "class_deviation_threshold": 0.05,
    "mcc_within_source_purity_threshold": 0.9,
    "leakage_pair_limit": 200,
    "excluded_l2": [
        "ENTERTAINMENT_AND_RECREATION.gambling",
        "SOFTWARE_AND_DIGITAL.online_subscriptions",
        "EDUCATION.exams_and_certification",
    ],
}

if __package__ in {None, ""}:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from split_pipeline.pipeline import run


if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
