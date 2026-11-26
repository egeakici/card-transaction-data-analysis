"""Manifest-constrained label linkage and canonical key checks."""
import json

import polars as pl
import yaml

from data_profile.src.common import merchant_keys
from data_profile.src.sources import canonical_record

from .common import collect, deterministic_row_ids, md_table, sha256_file, sink, write_csv, write_json


def schema_report(scan, reports, config):
    schema = scan.collect_schema()
    sample = collect(scan.head(config["schema_rows"]))
    rows = []
    for name, dtype in schema.items():
        column = sample[name]
        empty = column.null_count()
        if dtype == pl.String:
            empty += (column == "").sum()
        rows.append({"column": name, "type": str(dtype), "empty_rows": empty,
                     "empty_rate": empty / sample.height if sample.height else None})
    mappings = [{"role": role, "column": value} for role, value in config["columns"].items()]
    (reports / "00_schema.md").write_text(
        "# Canonical schema audit\n\nInput: `derived/analysis.parquet`, read-only. "
        f"Inspected the schema and first {sample.height:,} records. All existing column types are retained; "
        "MCC codes and merchant keys are strings. Empty key means null or the exact empty string; "
        "no strip, lowercase conversion, or new normalization is applied.\n\n"
        + md_table(rows, ["column", "type", "empty_rows", "empty_rate"])
        + "\n\n## CONFIG column roles\n\n" + md_table(mappings, ["role", "column"])
        + "\n\nSource population is the eleven original-file sources in outputs/DECISIONS.md. "
        "row_id is the stable 1-based Parquet scan position. Rows are never deduplicated.\n",
        encoding="utf-8",
    )


def original_file_mapping(root, config):
    manifest = pl.read_csv(root / config["profile_manifest"], infer_schema=False)
    assert set(manifest["source_id"]) == set(config["included_sources"])
    inventory = pl.read_csv(root / config["audit_root"] / "file_inventory.csv", infer_schema=False)
    manifest = manifest.with_columns(pl.col("source_file").alias("canonical_source_file"),
                                     pl.col("source_file").str.strip_prefix("real-world-datas/"))
    assert manifest.select(pl.struct("source_id", "source_file").n_unique()).item() == manifest.height
    mapped = manifest.join(inventory, on=["source_id", "source_file"], how="left", validate="1:1")
    assert mapped["file_id"].null_count() == 0, "An original manifest file has no audit inventory entry"
    assert mapped.filter(pl.col("is_primary_input") != "True").is_empty(), "Derived-file labels are forbidden"
    assert mapped.filter(pl.col("sha256") != pl.col("source_sha256")).is_empty(), "Audit source snapshot differs"
    return mapped.sort("source_id", "canonical_source_file")


def attach_labels(scan, root, output, config, input_sha256):
    mapped = original_file_mapping(root, config)
    address = ["source_id", "file_id", "source_sheet", "source_row"]
    mapping = mapped.select("source_id", pl.col("canonical_source_file").alias("source_file"), "file_id")
    actual_files = collect(scan.select("source_id", "source_file").unique())
    assert actual_files.join(mapping, on=["source_id", "source_file"], how="anti").is_empty()
    parts_dir = output / "intermediate" / "label_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    selected = []
    code_hash = sha256_file(__file__, config["hash_block_bytes"])
    for record in mapped.iter_rows(named=True):
        path = root / config["audit_root"] / "audit" / (record["file_id"] + ".parquet")
        part_path = parts_dir / (record["file_id"] + ".parquet")
        cache_path = parts_dir / (record["file_id"] + ".json")
        provenance = {"input_sha256": input_sha256, "source_sha256": record["source_sha256"],
                      "audit_sha256": sha256_file(path, config["hash_block_bytes"]) if path.exists() else None,
                      "code_sha256": code_hash, "polars": pl.__version__,
                      "canonical_rows": int(record["canonical_rows"])}
        if part_path.exists() and cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("provenance") == provenance:
                assert collect(pl.scan_parquet(part_path).select(pl.len())).item() == provenance["canonical_rows"]
                parts.append((cached["first_row_id"], cached["last_row_id"], str(part_path)))
                selected.append({"source_id": record["source_id"], "file_id": record["file_id"],
                                 "source_file": record["canonical_source_file"], "source_sha256": record["source_sha256"],
                                 "audit_exists": path.exists()})
                continue
        base = scan.filter((pl.col("source_id") == record["source_id"])
                           & (pl.col("source_file") == record["canonical_source_file"])).with_columns(
            pl.lit(record["file_id"]).alias("file_id"))
        stats = collect(base.select(pl.len(), pl.struct("source_sheet", "source_row").n_unique().alias("unique"),
                                    pl.col("row_id").min().alias("first"), pl.col("row_id").max().alias("last"))).row(0)
        assert stats[0] == stats[1] == int(record["canonical_rows"])
        if path.exists():
            audit = pl.scan_parquet(path)
            assert collect(audit.filter(pl.col("source_id") != record["source_id"]).select(pl.len())).item() == 0
            audit_counts = collect(audit.select(pl.len(), pl.struct("source_sheet", "source_row").n_unique().alias("unique"))).row(0)
            assert audit_counts[0] == audit_counts[1], "Primary audit addresses are not unique"
            labels = audit.with_columns(pl.lit(record["file_id"]).alias("file_id")).select(
                *address, "taxonomy_label", "evidence_method", "rule_id", "mcc_code_linked", "mcc_only_label", "mcc_link_method",
                pl.col("needs_review").alias("taxonomy_needs_review"),
                pl.col("mcc_disagreement").alias("taxonomy_mcc_disagreement"),
                pl.lit(True).alias("label_address_found"))
        else:
            labels = pl.DataFrame(schema={
                "source_id": pl.String, "file_id": pl.String, "source_sheet": pl.String, "source_row": pl.Int64,
                "taxonomy_label": pl.String, "evidence_method": pl.String, "rule_id": pl.String,
                "mcc_code_linked": pl.String, "mcc_only_label": pl.String, "mcc_link_method": pl.String,
                "taxonomy_needs_review": pl.Boolean, "taxonomy_mcc_disagreement": pl.Boolean,
                "label_address_found": pl.Boolean}).lazy()
        result = base.join(labels, on=address, how="left", validate="1:1", maintain_order="left").with_columns(
            pl.col("label_address_found").fill_null(False),
            pl.when(pl.col("mcc_code").is_not_null() & (pl.col("mcc_code") != ""))
            .then(pl.lit("original"))
            .when(pl.col("mcc_analysis").is_not_null() & (pl.col("mcc_analysis") != ""))
            .then(pl.lit("linked")).otherwise(pl.lit("missing")).alias("mcc_origin"))
        sink(result, part_path, config)
        write_json(cache_path, {"provenance": provenance, "first_row_id": stats[2], "last_row_id": stats[3]})
        parts.append((stats[2], stats[3], str(part_path)))
        selected.append({"source_id": record["source_id"], "file_id": record["file_id"],
                         "source_file": record["canonical_source_file"], "source_sha256": record["source_sha256"],
                         "audit_exists": path.exists()})
    parts.sort()
    # Canonical file rows can interleave after upstream joins. row_id retains the
    # original position; row files need not be sorted by that position.
    original_columns = scan.collect_schema().names()
    path = output / "intermediate" / "canonical_labels.parquet"
    # File-sized joins avoid materializing a nine-million-row wide hash join.
    sink(pl.scan_parquet([part[2] for part in parts]), path, config)
    joined = pl.scan_parquet(path)
    rates = collect(joined.group_by("source_id").agg(
        pl.len().alias("canonical_rows"),
        (pl.col("label_address_found") & pl.col("taxonomy_label").is_not_null()
         & (pl.col("taxonomy_label") != "")).sum().alias("labeled_address_rows"),
    ).with_columns((pl.col("labeled_address_rows") / pl.col("canonical_rows")).alias("label_join_rate"))
                    .sort("source_id")).to_dicts()
    reports = output / "reports"
    write_csv(reports / "00_label_join_by_source.csv", rates, list(rates[0]))
    (reports / "00_label_join_by_source.md").write_text(
        "# Original-file label linkage\n\nKey: source_id + file_id + source_sheet + source_row. "
        "file_id is obtained exclusively by joining outputs/manifest.csv to the audit file_inventory.csv. "
        "All selected entries must be primary inputs with equal original-file SHA-256. "
        "Worksheet conversions, folder merges and global merges are never used.\n\n"
        + md_table(rates, list(rates[0]))
        + "\n\nMoneydata documentation and Solihull nontransaction notes are absent from the canonical "
        "population. They are counted separately as not_a_transaction in excluded_summary.csv; "
        "they are excluded from the 99.5% comparability denominator. Missing canonical labels "
        "become unlabeled and retain their merchant fold.\n",
        encoding="utf-8",
    )
    write_csv(reports / "00_selected_audit_files.csv", selected, list(selected[0]))
    return joined, rates, original_columns


def validate_existing_keys(root, scan, output, config):
    # Diagnostic sampling only: it never changes or subsamples the split population.
    rows = []
    mismatches = []
    for source in config["included_sources"]:
        source_config = yaml.safe_load((root / config["source_configs"] / (source + ".yaml")).read_text(encoding="utf-8"))
        source_scan = scan.filter(pl.col("source_id") == source).select(
            "row_id", "source_file", "source_sheet", "source_row", "merchant_raw", "key_loose", "key_strict")
        # Sample ranks within the source without assuming physical source contiguity.
        size = collect(source_scan.select(pl.len())).item()
        ranks = deterministic_row_ids(0, size, config["validation_rows_per_source"])
        sample = collect(source_scan.with_row_index("sample_rank")
                         .filter(pl.col("sample_rank").is_in(ranks)))
        exact = 0
        for record in sample.iter_rows(named=True):
            raw = record["merchant_raw"] or ""
            if source == "dwp":
                # Import the existing adapter; its location separation must not be rewritten here.
                field = source_config["column_priority"]["merchant"][0]
                canonical, _, _ = canonical_record(source_config, root / record["source_file"],
                                                   record["source_sheet"], record["source_row"], {field: raw})
                strict, loose = canonical["key_strict"], canonical["key_loose"]
            else:
                strict, loose, _ = merchant_keys(raw)
            equal = (strict, loose) == (record["key_strict"], record["key_loose"])
            exact += equal
            if not equal and sum(row["source_id"] == source for row in mismatches) < 50:
                mismatches.append({"source_id": source, "row_id": record["row_id"],
                                   "source_file": record["source_file"], "source_sheet": record["source_sheet"],
                                   "source_row": record["source_row"], "merchant_raw": raw,
                                   "stored_key_loose": record["key_loose"], "imported_key_loose": loose,
                                   "stored_key_strict": record["key_strict"], "imported_key_strict": strict})
        rows.append({"source_id": source, "canonical_rows": size, "sampled_rows": sample.height,
                     "exact_rows": exact, "exact_rate": exact / sample.height if sample.height else None})
    reports = output / "reports"
    write_csv(reports / "00_key_mismatches_first50.csv", mismatches,
              ["source_id", "row_id", "source_file", "source_sheet", "source_row", "merchant_raw",
               "stored_key_loose", "imported_key_loose", "stored_key_strict", "imported_key_strict"])
    write_csv(reports / "00_key_validation.csv", rows, list(rows[0]))
    (reports / "00_key_validation.md").write_text(
        "# Existing canonical key verification\n\nDeterministic evenly spaced ranks, up to 10,000 "
        "canonical rows per source, smaller sources checked in full. Imported data_profile.merchant_keys "
        "and the imported DWP adapter independently reproduce strict/loose keys. Existing keys are "
        "never rewritten. Noncanonical Moneydata documentation and Solihull notes are not in the denominator.\n\n"
        + md_table(rows, list(rows[0])) + "\n", encoding="utf-8")
    return rows
