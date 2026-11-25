"""Validate source-licence evidence and refresh documentation without reading data."""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {"source_id", "publisher", "license", "license_url", "evidence_url", "verified_at",
            "permission_status", "redistribution_tier", "attribution_text"}
HOLD_STATUSES = {"not_verified", "scope_unresolved", "license_version_unresolved", "conflicting_terms"}
CONDITIONAL_STATUSES = {"published_open_license", "publisher_declared_public_domain", "published_custom_terms"}
CONFIG_FIELDS = ("publisher", "source_url", "license", "license_url", "evidence_url", "verified_at",
                 "permission_status", "redistribution_tier", "attribution_text")


def validate_registry(document, expected_ids=None):
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported licensing schema")
    rows = document.get("sources", [])
    found = {}
    for row in rows:
        missing = REQUIRED - row.keys()
        if missing:
            raise ValueError(f"Missing licensing fields: {sorted(missing)}")
        sid = row["source_id"]
        if not sid or sid in found:
            raise ValueError(f"Duplicate or empty source_id: {sid}")
        status = row["permission_status"]
        if status not in HOLD_STATUSES | CONDITIONAL_STATUSES:
            raise ValueError(f"Unknown permission status: {status}")
        tier = "hold" if status in HOLD_STATUSES else "conditional_source_terms"
        if row["redistribution_tier"] != tier:
            raise ValueError(f"Unsafe redistribution tier for {sid}")
        for field in ("publisher", "license", "attribution_text"):
            if not isinstance(row[field], str) or not row[field].strip() or row[field].lower() == "unspecified":
                raise ValueError(f"Uninformative {field} for {sid}")
        for field in ("evidence_url", "source_url"):
            if not str(row.get(field, "")).startswith("https://"):
                raise ValueError(f"Missing primary source URL for {sid}")
        if row["license_url"] is not None and not str(row["license_url"]).startswith("https://"):
            raise ValueError(f"Invalid licence URL for {sid}")
        if row["verified_at"] is not None:
            date.fromisoformat(str(row["verified_at"]))
        date.fromisoformat(str(row["checked_at"]))
        if status == "not_verified" and row["verified_at"] is not None:
            raise ValueError(f"Unverified grant cannot have verified_at: {sid}")
        if status in CONDITIONAL_STATUSES and (not row["verified_at"] or not row["license_url"]):
            raise ValueError(f"Published grant lacks terms or review date: {sid}")
        if row.get("written_permission_received"):
            raise ValueError("Written permission requires a schema update with scoped evidence before use")
        found[sid] = row
    if expected_ids is not None and set(found) != set(expected_ids):
        raise ValueError("Licensing registry and configured study sources differ")
    return found


def load_registry(expected_ids=None):
    document = yaml.safe_load((ROOT / "licenses.yaml").read_text(encoding="utf-8"))
    return validate_registry(document, expected_ids)


def apply_registry(configs):
    registry = load_registry(c["source_id"] for c in configs)
    return [dict(c, **{k: registry[c["source_id"]][k] for k in CONFIG_FIELDS}) for c in configs]


def inventory_table(configs):
    lines = ["| Source | Published licence / assessment | Permission status | Redistribution tier |",
             "| --- | --- | --- | --- |"]
    for c in sorted(configs, key=lambda x: x["source_id"]):
        lines.append(f'| {c["source_id"]} | [{c["license"]}]({c["evidence_url"]}) | {c["permission_status"]} | {c["redistribution_tier"]} |')
    return "\n".join(lines)


def render_data_card(text, configs):
    by_id = {c["source_id"]: c for c in configs}
    lines = []
    for line in text.splitlines():
        cells = line.split("|")
        if len(cells) == 9 and cells[1].strip() in by_id:
            c = by_id[cells[1].strip()]
            cells[2] = f' {c["publisher"]} '
            cells[6] = f' [{c["license"]}]({c["evidence_url"]}); {c["redistribution_tier"]} '
            line = "|".join(cells)
        lines.append(line)
    text = "\n".join(lines) + "\n"
    old = "Publicly accessible does not imply an open redistribution licence. Source licences are recorded as unspecified unless established from supplied provenance."
    new = "Public accessibility is not a redistribution grant. Source declarations, restrictions and unresolved terms are recorded in [licenses.yaml](../licenses.yaml); see [DATA_LICENSING.md](../DATA_LICENSING.md). No written permission has been received."
    text = text.replace(old, new)
    reviewed_at = yaml.safe_load((ROOT / "licenses.yaml").read_text(encoding="utf-8"))["reviewed_at"]
    section = ("## Licensing and permissions\n\n"
        f"The registry review is dated {reviewed_at} and does not certify the licence of every historical local file. "
        "Original software is [MIT-licensed](../LICENSE); data, source-derived content and third-party references are excluded from that software grant. "
        "No blanket CC BY licence, annotated v1.0 release, Zenodo DOI or ethics committee determination is claimed. "
        "See [attribution](../ATTRIBUTION.md), [availability](../DATA_AVAILABILITY.md) and [ethics](../ETHICS_STATEMENT.md). "
        "A `hold` blocks redistribution of source records and copied source content pending resolution; `conditional_source_terms` still requires snapshot, notice, excluded-rights and privacy review. "
        "Existing aggregate tables and screened examples are not automatically cleared by being public.\n\n"
        + inventory_table(configs) + "\n\n")
    text = re.sub(r"## Licensing and permissions\n.*?(?=## Preprocessing)", "", text, flags=re.S)
    text = text.replace("## Preprocessing", section + "## Preprocessing", 1)
    return text


def write_source_metadata(configs):
    fields = ["source_id", "publisher", "country", "org_type", "source_url", "license", "license_url",
              "evidence_url", "verified_at", "permission_status", "redistribution_tier", "attribution_text"]
    path = ROOT / "outputs/tables/source_metadata.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: c.get(k) for k in fields} for c in sorted(configs, key=lambda x: x["source_id"]))


def replace_section(path, begin, end, contents):
    text = path.read_text(encoding="utf-8")
    pattern = re.escape(begin) + r".*?" + re.escape(end)
    if len(re.findall(pattern, text, flags=re.S)) != 1:
        raise ValueError(f"Missing or duplicate managed section in {path.name}")
    text = re.sub(pattern, lambda _: begin + "\n\n" + contents + "\n\n" + end, text, flags=re.S)
    path.write_text(text, encoding="utf-8", newline="\n")


def refresh():
    from .sources import configurations
    configs = configurations()
    for c in configs:
        path = ROOT / "data_profile/config/sources" / (c["source_id"] + ".yaml")
        original = yaml.safe_load(path.read_text(encoding="utf-8"))
        original.update({key: c[key] for key in CONFIG_FIELDS})
        path.write_text(yaml.safe_dump(original, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
    path = ROOT / "outputs/DATA_CARD.md"
    path.write_text(render_data_card(path.read_text(encoding="utf-8"), configs), encoding="utf-8", newline="\n")
    write_source_metadata(configs)
    replace_section(ROOT / "DATA_LICENSING.md", "<!-- BEGIN LICENSE INVENTORY -->", "<!-- END LICENSE INVENTORY -->", inventory_table(configs))
    registry = load_registry()
    credits = []
    for sid in sorted(registry):
        c = registry[sid]
        licence = f' | [Terms]({c["license_url"]})' if c["license_url"] else " | Licence not verified"
        credits.append(f'### {sid} — {c["publisher"]}\n\n{c["attribution_text"]}\n\n[Source]({c["source_url"]}){licence} | Status: `{c["permission_status"]}`; tier: `{c["redistribution_tier"]}`.')
    replace_section(ROOT / "ATTRIBUTION.md", "<!-- BEGIN SOURCE CREDITS -->", "<!-- END SOURCE CREDITS -->", "\n\n".join(credits))
    print(f"Refreshed licensing metadata for {len(configs)} sources; no transaction files read or changed.")


if __name__ == "__main__":
    refresh()
