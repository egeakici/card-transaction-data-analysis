"""Merchant-level gold-sample frame, using the complete held-out pool."""
import polars as pl

from .common import sink


def build_test_merchants(pool, merchants, output, config):
    key = "key_loose"
    raw_counts = pool.group_by(key, "merchant_raw").len().sort(
        [key, "len", "merchant_raw"], descending=[False, True, False])
    top_raw = raw_counts.group_by(key, maintain_order=True).agg(
        pl.struct(pl.col("merchant_raw"), pl.col("len").alias("n_rows")).head(3).alias("top_merchant_raw_variants"))
    strict = pool.group_by(key).agg(
        pl.col("key_strict").drop_nulls().filter(pl.col("key_strict") != "").unique().sort().alias("merchant_key_strict_variants"),
        pl.col("txn_date").filter(pl.col("txn_date").is_not_null() & (pl.col("txn_date") != "")).min().alias("first_date"),
        pl.col("txn_date").filter(pl.col("txn_date").is_not_null() & (pl.col("txn_date") != "")).max().alias("last_date"))
    by_source = pool.group_by(key, "source_id").len().sort(key, "source_id").group_by(key, maintain_order=True).agg(
        pl.struct("source_id", pl.col("len").alias("n_rows")).alias("source_row_counts"))
    statuses = pool.group_by(key, "row_status").len().sort(key, "row_status").group_by(key, maintain_order=True).agg(
        pl.struct("row_status", pl.col("len").alias("n_rows")).alias("row_status_distribution"))
    known_mcc = pool.filter(pl.col("mcc_generic").is_not_null() & (pl.col("mcc_generic") != ""))
    global_mcc = known_mcc.group_by(key, "mcc_generic").len().sort(
        [key, "len", "mcc_generic"], descending=[False, True, False]).group_by(key, maintain_order=True).agg(
            pl.col("mcc_generic").first().alias("majority_mcc_generic"))
    origin = pool.group_by(key, "mcc_origin").len().sort(
        [key, "len", "mcc_origin"], descending=[False, True, False]).group_by(key, maintain_order=True).agg(
            pl.col("mcc_origin").first().alias("majority_mcc_origin"))
    source_mcc_counts = known_mcc.group_by(key, "source_id", "mcc_generic").len()
    source_mcc = source_mcc_counts.sort([key, "source_id", "len", "mcc_generic"],
                                       descending=[False, False, True, False]).group_by(key, "source_id", maintain_order=True).agg(
        pl.col("mcc_generic").first().alias("source_majority_mcc"),
        (pl.col("len").first() / pl.col("len").sum()).alias("source_majority_mcc_share"))
    flags = source_mcc.group_by(key).agg(
        (pl.col("source_majority_mcc").n_unique() > 1).alias("mcc_disagreement_across_sources"),
        (pl.col("source_majority_mcc_share") < config["mcc_within_source_purity_threshold"]).any().alias("mcc_disagreement_within_source"),
        pl.col("source_majority_mcc_share").min().alias("minimum_source_mcc_majority_share"))
    result = merchants.lazy().filter(pl.col("fold") == 9).rename({"merchant_key": key})
    for frame in [strict, top_raw, by_source, statuses, global_mcc, origin, flags]:
        result = result.join(frame, on=key, how="left", validate="1:1")
    result = result.with_columns(
        pl.col("mcc_disagreement_across_sources").fill_null(False),
        pl.col("mcc_disagreement_within_source").fill_null(False),
    ).rename({key: "merchant_key"}).sort("merchant_key")
    sink(result, output / "test_merchants.parquet", config)
