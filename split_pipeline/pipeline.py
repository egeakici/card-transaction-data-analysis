"""Canonical split orchestration. All inputs are opened read-only."""
import hashlib
import json
from pathlib import Path
import time

import polars as pl
import psutil

from .canonical import attach_labels, original_file_mapping, schema_report, validate_existing_keys
from .common import collect, md_table, sha256_file, sink, valid_key, write_json
from .folds import classify_rows, hash_only_merchants, majority_and_overrides
from .reports import exclusions, produce_reports
from .test_merchants import build_test_merchants
from .verify_splits import verify


def remove_obsolete_outputs(output):
    """Discard only this task's obsolete legacy-CSV diagnostics, never input data."""
    paths = [output / "intermediate" / name for name in [
        "keys_candidate.parquet", "row_lineage.parquet", "key_join_audit.parquet"]]
    old_reports = ["00_key_column_mapping.csv", "00_key_column_mapping.md", "00_key_join_rates.csv",
                   "00_key_join_rates.md", "00_key_mismatches_first50.csv", "00_key_mismatches_first50.md",
                   "00_key_preflight.json", "00_preflight_summary.md", "00_source_row_counts.csv",
                   "00_source_row_counts.md", "00_key_verification.txt"]
    paths.extend(output / "reports" / name for name in old_reports)
    for path in paths:
        assert path.resolve().is_relative_to(output.resolve())
        if path.is_file():
            path.unlink()


def run(config):
    root = Path(__file__).resolve().parents[1]
    output = root / config["output"]
    reports = output / "reports"
    intermediate = output / "intermediate"
    reports.mkdir(parents=True, exist_ok=True)
    intermediate.mkdir(parents=True, exist_ok=True)
    state_path = reports / "pipeline_state.json"
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    path = root / config["input"]
    input_stat = path.stat()
    started = time.perf_counter()
    steps = []
    state = {"status": "RUNNING", "input": config["input"], "canonical_sources": config["included_sources"],
             "split_started": False, "parameters": config}

    def checkpoint(stage):
        elapsed = round(time.perf_counter() - started, 3)
        steps.append({"stage": stage, "elapsed_seconds": elapsed,
                      "rss_mib": round(psutil.Process().memory_info().rss / 1024**2, 2)})
        print(f"[splits] {stage} ({elapsed}s)", flush=True)

    try:
        remove_obsolete_outputs(output)
        source = pl.scan_parquet(path)
        assert set(collect(source.select("source_id").unique())["source_id"]) == set(config["included_sources"])
        assert "key_loose" in source.collect_schema()
        schema_report(source, reports, config)
        state["input_sha256"] = sha256_file(path, config["hash_block_bytes"])
        scan = source.with_row_index("row_id", offset=config["row_id_offset"]).with_columns(pl.col("row_id").cast(pl.UInt64))
        checkpoint("canonical schema and read-only source snapshot")

        # Step 2 is intentionally completed before any label file is read.
        base = hash_only_merchants(scan, config)
        for destination in [output / "merchant_folds.parquet", intermediate / "merchant_folds_hash_only.parquet"]:
            base.write_parquet(destination, compression=config["compression"], row_group_size=config["parquet_row_group_size"])
        state["hash_only_registry_sha256"] = sha256_file(output / "merchant_folds.parquet", config["hash_block_bytes"])
        state["merchant_count"] = base.height
        checkpoint("label-independent merchant SHA-1 folds written")
        sink(scan.select("row_id", pl.col("source_id").alias("source"), "key_loose", "key_strict", "merchant_masked",
                         pl.lit("join").alias("key_method")), intermediate / "keys.parquet", config)
        key_checks = validate_existing_keys(root, scan, output, config)
        state["key_validation"] = key_checks
        if any(row["exact_rate"] is None or row["exact_rate"] < config["minimum_key_match_rate"] for row in key_checks):
            state["status"] = "STOPPED_KEY_VALIDATION"
            return 2
        checkpoint("all canonical key validation samples passed")

        joined, rates, _ = attach_labels(scan, root, output, config, state["input_sha256"])
        state["label_join_rates"] = rates
        oklahoma = next(row for row in rates if row["source_id"] == "oklahoma")
        if oklahoma["label_join_rate"] < config["minimum_oklahoma_label_join_rate"]:
            state["status"] = "STOPPED_OKLAHOMA_LABEL_LINKAGE"
            return 2
        checkpoint("only original-input labels linked; Oklahoma threshold passed")

        taxonomy = json.loads((root / config["taxonomy"]).read_text(encoding="utf-8"))
        labels = sorted(main + "." + leaf for main, leaves in taxonomy["categories"].items() for leaf in leaves)
        included = [label for label in labels if label not in config["excluded_l2"]]
        assert len(labels) == 72 and len(included) == 69
        state["included_labels"] = included
        classified = classify_rows(joined, included, config)
        assert collect(classified.filter(pl.col("row_status") == "INVALID_LABEL").select(pl.len())).item() == 0
        sink(classified, intermediate / "canonical_status.parquet", config)
        annotated = pl.scan_parquet(intermediate / "canonical_status.parquet")
        merchants, label_counts, rare, overrides = majority_and_overrides(base, annotated, included, config)
        merchants.write_parquet(output / "merchant_folds.parquet", compression=config["compression"],
                                row_group_size=config["parquet_row_group_size"])
        registry_hash = sha256_file(output / "merchant_folds.parquet", config["hash_block_bytes"])
        # Fingerprints include only the original audit files used for the new canonical population.
        selected = original_file_mapping(root, config)
        fingerprint_parts = {"input": state["input_sha256"], "config": config,
                             "manifest": sha256_file(root / config["profile_manifest"], config["hash_block_bytes"]),
                             "taxonomy": sha256_file(root / config["taxonomy"], config["hash_block_bytes"]),
                             "audits": {fid: sha256_file(root / config["audit_root"] / "audit" / (fid + ".parquet"),
                                                         config["hash_block_bytes"])
                                        for fid in selected["file_id"]
                                        if (root / config["audit_root"] / "audit" / (fid + ".parquet")).exists()}}
        fingerprint = hashlib.sha256(json.dumps(fingerprint_parts, sort_keys=True).encode("utf-8")).hexdigest()
        state["input_fingerprint"] = fingerprint
        state["merchant_folds_sha256"] = registry_hash
        if previous.get("input_fingerprint") == fingerprint and previous.get("status") == "COMPLETE":
            assert previous["merchant_folds_sha256"] == registry_hash, "Registry changed on a repeated identical run"
            state["identical_complete_run_count"] = previous.get("identical_complete_run_count", 1) + 1
            state["previous_run_registry_hash_matches"] = True
        else:
            state["identical_complete_run_count"] = 1
            state["previous_run_registry_hash_matches"] = None
        checkpoint("canonical majorities and authorized rare-class folds finalized")

        mapping = merchants.lazy().select(pl.col("merchant_key").alias("key_loose"),
                                           "fold_hash", "fold", "split", "fold_override", "majority_l2")
        routed = annotated.join(mapping, on="key_loose", how="left", validate="m:1", maintain_order="left").with_columns(
            pl.col("fold_override").fill_null(False))
        sink(routed, intermediate / "routed.parquet", config)
        routed = pl.scan_parquet(intermediate / "routed.parquet")
        state["split_started"] = True
        for split in config["split_expected_shares"]:
            sink(routed.filter((pl.col("split") == split) & (pl.col("row_status") == "labeled")),
                 output / (split + ".parquet"), config)
        sink(routed.filter(pl.col("fold") == 9), output / "test_pool_all.parquet", config)
        checkpoint("train, validation, test and complete test pool written")
        build_test_merchants(pl.scan_parquet(output / "test_pool_all.parquet"), merchants, output, config)
        exclusions(routed, root, output, config)
        checkpoint("test merchant sampling frame and counted exclusions written")
        state.update(produce_reports(routed, merchants, label_counts, rare, overrides, included, output, config))
        checkpoint("split, class, source, rare-class and leakage reports written")
        state["verification"] = verify(config, state)
        checkpoint("all required assertions and deterministic registry rebuild passed")
        state["status"] = "COMPLETE"
        return 0
    except Exception as error:
        state["status"] = "ERROR"
        state["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        after = path.stat()
        unchanged = (input_stat.st_size, input_stat.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        if "input_sha256" in state:
            unchanged = unchanged and sha256_file(path, config["hash_block_bytes"]) == state["input_sha256"]
        state["input_unchanged"] = unchanged
        assert unchanged, "The protected input changed"
        elapsed = time.perf_counter() - started
        memory = psutil.Process().memory_info()
        state["elapsed_seconds"] = round(elapsed, 3)
        state["process_peak_rss_mib"] = round(getattr(memory, "peak_wset", memory.rss) / 1024**2, 2)
        write_json(state_path, state)
        (reports / "00_run_log.md").write_text(
            f"# Run log\n\nStatus: {state['status']}.\n\nElapsed: {elapsed:.3f} seconds. "
            f"Peak process working set/RSS: {state['process_peak_rss_mib']:.2f} MiB. "
            "Windows peak_wset is used when available; otherwise final RSS. "
            f"Polars {pl.__version__}; streaming scans/collects and zstd Parquet sinks.\n\n"
            f"Input SHA-256 and metadata unchanged: {unchanged}.\n\n"
            + md_table(steps, ["stage", "elapsed_seconds", "rss_mib"])
            + "\n\nAll processing was local. No API/LLM/web service received data. No model training, "
            "random fold assignment, balancing, duplication or row deduplication was performed. "
            "Diagnostic key-validation samples do not change the dataset. Legacy CSV rows never enter row outputs.\n\n"
            f"Identical complete-run count: {state.get('identical_complete_run_count', 0)}. "
            f"Previous complete-run registry hash matches: {state.get('previous_run_registry_hash_matches')}.\n",
            encoding="utf-8")
        print(json.dumps({key: state.get(key) for key in ["status", "merchant_count", "override_merchants",
                                                          "identical_complete_run_count", "input_unchanged", "elapsed_seconds"]}), flush=True)
