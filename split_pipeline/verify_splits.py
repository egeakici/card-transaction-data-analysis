"""Assert routing, merchant isolation, counts, class coverage and determinism."""
import json
from pathlib import Path

import polars as pl

from .common import collect, hash_fold, md_table, sha256_file, valid_key, write_json
from .folds import majority_and_overrides


def verify(config, state=None):
    root = Path(__file__).resolve().parents[1]
    output = root / config["output"]
    reports = output / "reports"
    if state is None:
        state = json.loads((reports / "pipeline_state.json").read_text(encoding="utf-8"))
    merchants = pl.read_parquet(output / "merchant_folds.parquet")
    routed = pl.scan_parquet(output / "intermediate" / "routed.parquet")
    canonical = pl.scan_parquet(root / config["input"])
    assert merchants.height == merchants["merchant_key"].n_unique()
    assert merchants["merchant_key"].null_count() == 0
    assert (merchants["merchant_key"] != "").all()
    expected_hashes = merchants["merchant_key"].map_elements(hash_fold, return_dtype=pl.Int64)
    assert (merchants["fold_hash"] == expected_hashes).all()
    assert merchants.filter(~pl.col("fold_override") & (pl.col("fold") != pl.col("fold_hash"))).is_empty()
    assert merchants.filter(~pl.col("fold").is_between(0, 9)).is_empty()
    disagreement = routed.filter(valid_key()).group_by("key_loose").agg(
        pl.col("fold").n_unique().alias("folds"), pl.col("split").n_unique().alias("splits"))
    assert collect(disagreement.filter((pl.col("folds") != 1) | (pl.col("splits") != 1)).select(pl.len())).item() == 0
    source_folds = routed.filter(valid_key()).select("key_loose", "source_id", "fold").unique()
    assert collect(source_folds.group_by("key_loose").agg(pl.col("fold").n_unique().alias("n"))
                   .filter(pl.col("n") != 1).select(pl.len())).item() == 0
    mismatched = routed.filter(valid_key()).select("key_loose", "fold", "split").unique().join(
        merchants.lazy().select(pl.col("merchant_key").alias("key_loose"),
                                pl.col("fold").alias("registry_fold"), pl.col("split").alias("registry_split")),
        on="key_loose", how="left", validate="m:1")
    assert collect(mismatched.filter(pl.col("registry_fold").is_null()
                                     | (pl.col("fold") != pl.col("registry_fold"))
                                     | (pl.col("split") != pl.col("registry_split"))).select(pl.len())).item() == 0

    input_count = collect(canonical.select(pl.len())).item()
    assert collect(routed.select(pl.len(), pl.col("row_id").n_unique().alias("unique"),
                                  pl.col("row_id").min().alias("first"), pl.col("row_id").max().alias("last"))).row(0) == (
                                      input_count, input_count, 1, input_count)
    assert set(collect(routed.select("source_id").unique())["source_id"]) == set(config["included_sources"])
    assert collect(routed.filter(~pl.col("row_status").is_in(config["row_status_precedence"]))
                   .select(pl.len())).item() == 0
    assert collect(routed.filter((pl.col("row_status") == "no_key")
                                 & (pl.col("fold").is_not_null() | pl.col("split").is_not_null())).select(pl.len())).item() == 0
    files = {}
    original_schema = canonical.collect_schema()
    for split in ["train", "validation", "test"]:
        data = pl.scan_parquet(output / (split + ".parquet"))
        files[split] = collect(data.select(pl.len())).item()
        schema = data.collect_schema()
        assert all(name in schema and schema[name] == dtype for name, dtype in original_schema.items())
        assert collect(data.filter((pl.col("row_status") != "labeled") | (pl.col("split") != split)
                                   | ~valid_key() | pl.col("merchant_masked")
                                   | pl.col("taxonomy_label").is_in(config["excluded_l2"]))
                       .select(pl.len())).item() == 0
        assert collect(data.select(pl.col("row_id").n_unique())).item() == files[split]
        expected = routed.filter((pl.col("split") == split) & (pl.col("row_status") == "labeled")).select("row_id")
        assert collect(expected.select(pl.len())).item() == files[split]
        assert collect(data.select("row_id").join(expected, on="row_id", how="anti").select(pl.len())).item() == 0
    pool = pl.scan_parquet(output / "test_pool_all.parquet")
    files["test_pool_all"] = collect(pool.select(pl.len())).item()
    assert collect(pool.filter((pl.col("fold") != 9) | (pl.col("split") != "test") | ~valid_key()).select(pl.len())).item() == 0
    expected_pool = routed.filter(pl.col("fold") == 9).select("row_id")
    assert collect(expected_pool.select(pl.len())).item() == files["test_pool_all"]
    assert collect(pool.select("row_id").join(expected_pool, on="row_id", how="anti").select(pl.len())).item() == 0
    assert collect(pool.select(pl.col("row_id").n_unique())).item() == files["test_pool_all"]
    test = pl.scan_parquet(output / "test.parquet")
    columns = test.collect_schema().names()
    # Row identity plus two independent complete-row fingerprints verify subset content.
    def fingerprints(frame):
        return frame.select("row_id", pl.struct(columns).hash(seed=0).alias("h0"),
                            pl.struct(columns).hash(seed=1).alias("h1"))
    subset = fingerprints(test).join(fingerprints(pool), on="row_id", how="left", suffix="_pool", validate="1:1")
    assert collect(subset.filter(pl.col("h0_pool").is_null() | (pl.col("h0") != pl.col("h0_pool"))
                                  | (pl.col("h1") != pl.col("h1_pool"))).select(pl.len())).item() == 0
    no_key = collect(routed.filter(pl.col("row_status") == "no_key").select(pl.len())).item()
    other_excluded = collect(routed.filter((pl.col("fold") < 9) & (pl.col("row_status") != "labeled"))
                            .select(pl.len())).item()
    exclusions = pl.read_csv(output / "excluded_summary.csv", infer_schema=False)
    counted_exclusions = exclusions.filter(pl.col("in_canonical_reconciliation") == "True")["rows"].cast(pl.UInt64).sum()
    assert counted_exclusions == other_excluded + no_key
    assert input_count == files["train"] + files["validation"] + files["test_pool_all"] + other_excluded + no_key

    labeled = routed.filter(pl.col("row_status") == "labeled")
    coverage = collect(labeled.group_by("taxonomy_label", "split").agg(pl.col("key_loose").n_unique().alias("merchants")))
    covered = {(row["taxonomy_label"], row["split"]): row["merchants"] for row in coverage.to_dicts()}
    missing = {split: [label for label in state["included_labels"] if covered.get((label, split), 0) == 0]
               for split in config["split_expected_shares"]}
    assert not missing["train"], "Included classes absent from train: " + str(missing["train"])
    base = pl.read_parquet(output / "intermediate" / "merchant_folds_hash_only.parquet")
    rebuilt, _, _, _ = majority_and_overrides(
        base, pl.scan_parquet(output / "intermediate" / "canonical_status.parquet"), state["included_labels"], config)
    assert rebuilt.equals(merchants), "Merchant registry differs on independent recomputation"
    rebuilt_path = output / "intermediate" / "merchant_folds_rebuilt.parquet"
    rebuilt.write_parquet(rebuilt_path, compression=config["compression"], row_group_size=config["parquet_row_group_size"])
    registry_hash = sha256_file(output / "merchant_folds.parquet", config["hash_block_bytes"])
    assert sha256_file(rebuilt_path, config["hash_block_bytes"]) == registry_hash, "Parquet content hash is not deterministic"
    assert sha256_file(root / config["input"], config["hash_block_bytes"]) == state["input_sha256"]

    sampling = pl.scan_parquet(output / "test_merchants.parquet")
    test_merchants = merchants.filter(pl.col("fold") == 9)
    assert collect(sampling.select(pl.len(), pl.col("merchant_key").n_unique().alias("unique"))).row(0) == (
        test_merchants.height, test_merchants.height)
    assert collect(sampling.select(pl.col("n_rows").sum())).item() == files["test_pool_all"]
    assert collect(sampling.select("merchant_key").join(test_merchants.lazy().select("merchant_key"),
                                                        on="merchant_key", how="anti").select(pl.len())).item() == 0
    assert collect(sampling.filter(
        (pl.col("source_row_counts").list.eval(pl.element().struct.field("n_rows")).list.sum() != pl.col("n_rows"))
        | (pl.col("row_status_distribution").list.eval(pl.element().struct.field("n_rows")).list.sum() != pl.col("n_rows"))
        | (pl.col("top_merchant_raw_variants").list.len() > 3)).select(pl.len())).item() == 0
    reconciliation = [{"component": name, "rows": count} for name, count in [
        ("input canonical", input_count), ("train", files["train"]), ("validation", files["validation"]),
        ("test_pool_all (includes test)", files["test_pool_all"]),
        ("folds 0-8 non-labeled, counted only", other_excluded), ("no_key, counted only", no_key)]]
    result = {"status": "PASS", "input_rows": input_count, "file_rows": files, "no_key": no_key,
              "non_labeled_folds_0_8": other_excluded, "missing_classes": missing,
              "merchant_folds_sha256": registry_hash, "deterministic_rebuild": True}
    write_json(reports / "verification.json", result)
    message = ("# Split verification\n\nAll assertions: PASS.\n\n"
               + md_table(reconciliation, ["component", "rows"])
               + "\n\nExact canonical reconciliation: PASS. test is a subset of test_pool_all and is not added twice. "
               "Noncanonical exclusions are separately identified and are not included in this equation.\n\n"
               "Merchant isolation across all rows and sources: PASS. Verbatim SHA-1 folds outside the rare exception: PASS. "
               "Original column types, routing, unique row_ids, excluded classes and test content subset: PASS. "
               "All 69 classes have at least one train merchant: PASS.\n\n"
               f"Missing validation classes: {missing['validation'] or 'none'}.\n\n"
               f"Missing test classes: {missing['test'] or 'none'}.\n\n"
               "Independent registry rebuild and exact Parquet SHA-256 comparison: PASS.\n\n"
               f"merchant_folds SHA-256: `{registry_hash}`.\n\nInput SHA-256 unchanged: PASS.\n")
    (reports / "08_verification.md").write_text(message, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return result


if __name__ == "__main__":
    from split_pipeline.make_splits import CONFIG
    verify(CONFIG)
