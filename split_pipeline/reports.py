"""Canonical-population counts and local-only audit reports."""
from collections import defaultdict

import polars as pl

from .common import collect, md_table, write_csv
from .leakage import find_pairs


def exclusions(frame, root, output, config):
    excluded = collect(frame.filter(
        (pl.col("row_status") == "no_key")
        | ((pl.col("fold") < 9) & (pl.col("row_status") != "labeled"))
    ).group_by("source_id", "row_status").len().sort("source_id", "row_status"))
    rows = [{"source": row["source_id"], "row_status": row["row_status"], "rows": row["len"],
             "population": "canonical", "in_canonical_reconciliation": True,
             "reason": "no fold" if row["row_status"] == "no_key" else "non-labeled in folds 0-8"}
            for row in excluded.to_dicts()]
    profile = collect(pl.scan_parquet(root / config["profile_exclusions"]).group_by("source_id", "reason").len())
    for record in profile.to_dicts():
        rows.append({"source": record["source_id"],
                     "row_status": "blank_source_row" if record["reason"] == "blank" else "not_a_transaction",
                     "rows": record["len"], "population": "profile_noncanonical",
                     "in_canonical_reconciliation": False, "reason": record["reason"]})
    # Frozen historical counts preserve the report without reopening deleted data.
    # population records their original provenance, not a current file dependency.
    for record in config["historical_exclusions"]:
        rows.append({**record, "population": "legacy_csv", "in_canonical_reconciliation": False})
    rows.sort(key=lambda row: (row["population"], row["source"], row["row_status"]))
    write_csv(output / "excluded_summary.csv", rows,
              ["source", "row_status", "rows", "population", "in_canonical_reconciliation", "reason"])
    return rows


def produce_reports(frame, merchants, label_counts, rare, overrides, included_labels, output, config):
    reports = output / "reports"
    labeled = frame.filter(pl.col("row_status") == "labeled")
    row_splits = collect(labeled.group_by("split").agg(pl.len().alias("rows"),
                                                      pl.col("key_loose").n_unique().alias("merchants")))
    labeled_splits = {row["split"]: row for row in row_splits.to_dicts()}
    total_labeled = sum(row["rows"] for row in labeled_splits.values())
    assigned_total = merchants["n_rows"].sum()
    merchant_splits = merchants.group_by("split").agg(pl.len().alias("merchants"), pl.col("n_rows").sum().alias("rows"))
    split_totals = {row["split"]: row for row in merchant_splits.to_dicts()}
    summary = []
    for split in config["split_expected_shares"]:
        all_rows = split_totals.get(split, {"merchants": 0, "rows": 0})
        eligible = labeled_splits.get(split, {"merchants": 0, "rows": 0})
        summary.append({"split": split, "all_merchants": all_rows["merchants"],
                        "merchant_share": all_rows["merchants"] / merchants.height,
                        "all_assigned_rows": all_rows["rows"], "assigned_row_share": all_rows["rows"] / assigned_total,
                        "labeled_merchants": eligible["merchants"], "labeled_rows": eligible["rows"],
                        "labeled_row_share": eligible["rows"] / total_labeled})
    dominant = merchants.select("merchant_key", "split", "n_rows").to_dicts()
    for row in dominant:
        row["max_absolute_contribution_pp"] = 100 * row["n_rows"] / assigned_total * (
            1 - config["split_expected_shares"][row["split"]])
    dominant.sort(key=lambda row: (-row["max_absolute_contribution_pp"], row["merchant_key"]))
    (reports / "01_split_summary.md").write_text(
        "# Split summary\n\nAll merchants include keys with any row status. All assigned rows include "
        "non-labeled rows; labeled rows describe train/validation/test model files. No-key rows have no split. "
        "test_pool_all overlaps test and must not be added to it. No deduplication or balancing is performed.\n\n"
        + md_table(summary, list(summary[0]))
        + "\n\n## Top 10 contributors to row-share deviations\n\n"
        "Each key contributes n_rows / all_keyed_rows times (indicator(split) - expected_share) "
        "to each split's deviation. Ranked by its largest absolute contribution, in percentage points.\n\n"
        + md_table(dominant[:10], ["merchant_key", "split", "n_rows", "max_absolute_contribution_pp"])
        + "\n\nlabel_purity is majority-label rows / labeled rows for that merchant. "
        "Majorities use only row_status=labeled; ties use alphabetical L2. Status precedence is "
        + ", ".join(config["row_status_precedence"]) + ".\n", encoding="utf-8")

    by_class = collect(labeled.group_by("taxonomy_label", "split").agg(
        pl.len().alias("rows"), pl.col("key_loose").n_unique().alias("merchants")))
    observed = {(row["taxonomy_label"], row["split"]): row for row in by_class.to_dicts()}
    class_merchants = label_counts.join(merchants.select("merchant_key", "split"), on="merchant_key", validate="m:1")
    groups = defaultdict(list)
    for row in class_merchants.iter_rows(named=True):
        groups[row["taxonomy_label"]].append(row)
    class_rows = []
    coverage = {}
    for label in included_labels:
        total_rows = sum(observed.get((label, split), {}).get("rows", 0) for split in config["split_expected_shares"])
        total_merchants = sum(observed.get((label, split), {}).get("merchants", 0) for split in config["split_expected_shares"])
        coverage[label] = {}
        for split, expected in config["split_expected_shares"].items():
            record = observed.get((label, split), {"rows": 0, "merchants": 0})
            coverage[label][split] = record["merchants"]
            share = record["rows"] / total_rows if total_rows else 0
            flagged = abs(share - expected) > config["class_deviation_threshold"]
            cause = max(groups[label], key=lambda row: (row["len"] * abs((row["split"] == split) - expected),
                                                        row["merchant_key"])) if groups[label] else None
            class_rows.append({"l2": label, "split": split, "rows": record["rows"], "merchants": record["merchants"],
                               "class_row_share_within_split": record["rows"] / labeled_splits[split]["rows"],
                               "class_merchant_share_within_split": record["merchants"] / labeled_splits[split]["merchants"],
                               "class_rows_in_this_split_share": share,
                               "class_merchants_in_this_split_share": record["merchants"] / total_merchants if total_merchants else 0,
                               "expected_split_share": expected, "row_deviation_pp": 100 * (share - expected),
                               "deviation_over_5pp": flagged,
                               "largest_contributor": cause["merchant_key"] if flagged and cause else "",
                               "contributor_split": cause["split"] if flagged and cause else "",
                               "contributor_class_rows": cause["len"] if flagged and cause else 0,
                               "contribution_pp": 100 * cause["len"] / total_rows * ((cause["split"] == split) - expected)
                               if flagged and cause and total_rows else 0})
    write_csv(reports / "02_l2_by_split.csv", class_rows, list(class_rows[0]))
    (reports / "02_l2_by_split.md").write_text(
        "# L2 by split\n\nAll 69 included classes, recomputed from joined canonical labeled rows. "
        "Merchant counts count a key under every label it carries, not just its majority label. "
        "A deviation over 5 percentage points is flagged, with the named key making the largest exact "
        "contribution to that split's class-share deviation. This is an allocation decomposition, not a causal claim.\n\n"
        + md_table(class_rows, list(class_rows[0])) + "\n", encoding="utf-8")

    sources = collect(labeled.group_by("source_id", "split").agg(
        pl.len().alias("rows"), pl.col("key_loose").n_unique().alias("merchants")))
    source_map = {(row["source_id"], row["split"]): row for row in sources.to_dicts()}
    source_rows = [{"source": source, "split": split,
                    "rows": source_map.get((source, split), {}).get("rows", 0),
                    "merchants": source_map.get((source, split), {}).get("merchants", 0)}
                   for source in config["included_sources"] for split in config["split_expected_shares"]]
    write_csv(reports / "03_source_by_split.csv", source_rows, list(source_rows[0]))
    test = collect(labeled.filter(pl.col("split") == "test").group_by("source_id", "taxonomy_label").agg(
        pl.len().alias("rows"), pl.col("key_loose").n_unique().alias("merchants")))
    test_map = {(row["source_id"], row["taxonomy_label"]): row for row in test.to_dicts()}
    test_rows = [{"source": source, "l2": label, "rows": test_map.get((source, label), {}).get("rows", 0),
                  "merchants": test_map.get((source, label), {}).get("merchants", 0)}
                 for source in config["included_sources"] for label in included_labels]
    write_csv(reports / "04_test_l2_by_source.csv", test_rows, list(test_rows[0]))
    for row in rare:
        row.update({split + "_merchants": coverage[row["l2"]][split] for split in config["split_expected_shares"]})
        row["missing_splits"] = ",".join(split for split, count in coverage[row["l2"]].items() if count == 0)
    detail = []
    lookup = {row["merchant_key"]: row for row in merchants.select("merchant_key", "fold_hash", "fold", "split").to_dicts()}
    for override in overrides:
        detail.append({**override, **lookup[override["merchant_key"]]})
    (reports / "05_rare_classes.md").write_text(
        "# Rare-class exception\n\nRare means fewer than " + str(config["rare_class_min_merchants"])
        + " merchants with that majority L2, computed only after canonical label linkage and row-status filtering. "
        "Sort keys by full SHA-1, then verbatim key; repeat " + str(config["rare_fold_sequence"])
        + ". Every selected merchant is marked fold_override=True, even if its new fold equals its hash fold. "
        "No other folds change. One- and two-merchant classes cannot cover all three splits; actual gaps follow.\n\n"
        + md_table(rare, ["l2", "majority_merchants", "override_merchants", "fewer_than_three",
                          "train_merchants", "validation_merchants", "test_merchants", "missing_splits"])
        + "\n\n## Every overridden merchant\n\n"
        + md_table(detail, ["l2", "merchant_key", "sha1", "fold_hash", "fold", "split"])
        + "\n", encoding="utf-8")
    pairs = find_pairs(merchants, config["leakage_pair_limit"])
    fields = ["key_a", "split_a", "rows_a", "key_b", "split_b", "rows_b", "combined_rows", "rules"]
    (reports / "06_leakage_audit.md").write_text(
        "# Candidate cross-split brand leakage\n\nExact merchant keys are disjoint across splits. "
        "This audit flags different keys whose literal strings have a prefix relation or whose first two "
        "whitespace-separated tokens are equal. Ranked by the sum of their canonical row counts, up to "
        + str(config["leakage_pair_limit"]) + " pairs. These are possible related brands, not confirmed identities. "
        "No key or fold is changed. Residual alias/truncation leakage is a known limitation.\n\n"
        + md_table(pairs, fields) + "\n", encoding="utf-8")
    excluded_counts = collect(frame.filter(pl.col("taxonomy_label").is_in(config["excluded_l2"]))
                              .group_by("taxonomy_label").len())
    excluded_map = dict(excluded_counts.iter_rows())
    excluded_rows = [{"l2": label, "canonical_rows": excluded_map.get(label, 0),
                      "model_metric_rows": 0} for label in config["excluded_l2"]]
    (reports / "07_excluded_classes.md").write_text(
        "# Defined excluded classes\n\nThese three classes are excluded from every model file and metric. "
        "For the model population they are 'defined, not observed'. Underlying canonical records are "
        "retained in the fold-9 all-status pool or counted in exclusions; eight exam/certification records "
        "are not deleted. Counts below describe input inventory, not model metrics.\n\n"
        + md_table(excluded_rows, list(excluded_rows[0])) + "\n", encoding="utf-8")
    missing = {split: [label for label in included_labels if coverage[label][split] == 0]
               for split in config["split_expected_shares"]}
    return {"split_summary": summary, "rare_classes": rare, "override_merchants": len(overrides),
            "missing_classes": missing, "top_deviation_merchants": dominant[:10],
            "leakage_pairs": len(pairs), "excluded_class_counts": excluded_rows}
