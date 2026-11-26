"""Hash-only assignment followed by the single authorized rare-class exception."""
import polars as pl

from .common import collect, hash_fold, sha1_key, split_expr, valid_key


def hash_only_merchants(scan, config):
    merchants = collect(scan.filter(valid_key()).group_by("key_loose").agg(
        pl.len().cast(pl.UInt64).alias("n_rows"),
        pl.col("source_id").n_unique().alias("n_sources"),
        pl.col("source_id").unique().sort().alias("sources"),
    ).rename({"key_loose": "merchant_key"}).sort("merchant_key"))
    return merchants.with_columns(
        pl.col("merchant_key").map_elements(hash_fold, return_dtype=pl.Int64).cast(pl.Int8).alias("fold_hash"),
    ).with_columns(
        pl.col("fold_hash").alias("fold"), pl.lit(False).alias("fold_override"),
        pl.lit(None, dtype=pl.String).alias("majority_l2"),
        pl.lit(None, dtype=pl.String).alias("majority_l1"),
        pl.lit(0, dtype=pl.UInt64).alias("n_labeled_rows"),
        pl.lit(None, dtype=pl.Float64).alias("label_purity"),
    ).with_columns(split_expr().alias("split")).select(
        "merchant_key", "fold_hash", "fold", "split", "fold_override", "majority_l2", "majority_l1",
        "n_rows", "n_labeled_rows", "n_sources", "sources", "label_purity")


def majority_and_overrides(base_merchants, annotated, included_labels, config):
    counts = collect(annotated.filter(pl.col("row_status") == "labeled")
                     .group_by("key_loose", "taxonomy_label").len()
                     .sort(["key_loose", "len", "taxonomy_label"], descending=[False, True, False]))
    counts = counts.rename({"key_loose": "merchant_key"})
    totals = counts.group_by("merchant_key").agg(pl.col("len").sum().cast(pl.UInt64).alias("n_labeled_rows"))
    majority = counts.unique("merchant_key", keep="first", maintain_order=True).select(
        "merchant_key", pl.col("taxonomy_label").alias("majority_l2"), pl.col("len").alias("majority_n"),
    ).join(totals, on="merchant_key", validate="1:1")
    merchants = base_merchants.drop("majority_l2", "majority_l1", "n_labeled_rows", "label_purity").join(
        majority, on="merchant_key", how="left", validate="1:1",
    ).with_columns(
        pl.col("n_labeled_rows").fill_null(0),
        pl.col("majority_l2").str.split_exact(".", 1).struct.field("field_0").alias("majority_l1"),
        (pl.col("majority_n") / pl.col("n_labeled_rows")).alias("label_purity"),
    )
    class_counts = dict(merchants.filter(pl.col("majority_l2").is_not_null())
                        .group_by("majority_l2").len().iter_rows())
    rare = []
    overrides = []
    for label in included_labels:
        size = class_counts.get(label, 0)
        if size >= config["rare_class_min_merchants"]:
            continue
        keys = merchants.filter(pl.col("majority_l2") == label)["merchant_key"].to_list()
        keys.sort(key=lambda key: (sha1_key(key), key))
        rare.append({"l2": label, "majority_merchants": size, "override_merchants": len(keys),
                     "fewer_than_three": size < 3})
        for index, key in enumerate(keys):
            overrides.append({"merchant_key": key,
                              "override_fold": config["rare_fold_sequence"][index % len(config["rare_fold_sequence"])],
                              "l2": label, "sha1": sha1_key(key)})
    override_df = pl.DataFrame(overrides, schema={"merchant_key": pl.String, "override_fold": pl.Int8,
                                                "l2": pl.String, "sha1": pl.String})
    merchants = merchants.join(override_df.select("merchant_key", "override_fold"),
                               on="merchant_key", how="left", validate="1:1").with_columns(
        pl.col("override_fold").is_not_null().alias("fold_override"),
        pl.coalesce("override_fold", "fold_hash").cast(pl.Int8).alias("fold"),
    ).with_columns(split_expr().alias("split")).sort("merchant_key").select(base_merchants.columns)
    return merchants, counts, rare, overrides


def classify_rows(frame, included_labels, config):
    label = pl.col("taxonomy_label")
    # An empty key cannot be assigned a fold, even when another exclusion also applies.
    return frame.with_columns(
        pl.when(~valid_key()).then(pl.lit("no_key"))
        .when(pl.col("merchant_masked").fill_null(False)).then(pl.lit("masked"))
        .when(label.is_null() | (label == "")).then(pl.lit("unlabeled"))
        .when(label == "NOT_A_TRANSACTION").then(pl.lit("not_a_transaction"))
        .when(label.is_in(config["excluded_l2"])).then(pl.lit("excluded_class"))
        .when(label.is_in(config["unresolved_labels"])).then(pl.lit("unresolved"))
        .when(label.is_in(included_labels)).then(pl.lit("labeled"))
        .otherwise(pl.lit("INVALID_LABEL")).alias("row_status")
    )
