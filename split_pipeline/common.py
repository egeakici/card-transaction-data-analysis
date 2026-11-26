"""Local helpers; source merchant keys are always used verbatim."""
import csv
import hashlib
import json
from pathlib import Path

import polars as pl


def collect(frame):
    return frame.collect(engine="streaming")


def sha256_file(path, block_bytes):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(block_bytes):
            value.update(block)
    return value.hexdigest()


def hash_fold(key):
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest(), 16) % 10


def sha1_key(key):
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def valid_key(column="key_loose"):
    return pl.col(column).is_not_null() & (pl.col(column) != "")


def split_expr(column="fold"):
    return (pl.when(pl.col(column) < 8).then(pl.lit("train"))
            .when(pl.col(column) == 8).then(pl.lit("validation"))
            .when(pl.col(column) == 9).then(pl.lit("test"))
            .otherwise(pl.lit(None, dtype=pl.String)))


def sink(frame, path, config):
    frame.sink_parquet(path, compression=config["compression"],
                       row_group_size=config["parquet_row_group_size"], maintain_order=True)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def md_table(rows, fields):
    def cell(value):
        if isinstance(value, float):
            value = f"{value:.8f}"
        return str("" if value is None else value).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(fields) + " |",
                      "| " + " | ".join("---" for _ in fields) + " |",
                      *("| " + " | ".join(cell(row.get(field)) for field in fields) + " |" for row in rows)])


def write_csv(path, rows, fields):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in rows)


def deterministic_row_ids(start, count, target):
    target = min(count, target)
    if target == 0:
        return []
    if target == 1:
        return [start]
    return [start + (index * (count - 1)) // (target - 1) for index in range(target)]
