"""Shared paths, deterministic parsing, normalization, and output helpers."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs'
DERIVED = ROOT / 'derived'
CONFIG = ROOT / 'data_profile/config'
SEED = 42
ACCESS_DATE = '2026-10-31'
ALIAS_CONFIG = yaml.safe_load((CONFIG / 'merchant_aliases.yaml').read_text())
PREFIXES = yaml.safe_load((CONFIG / 'intermediaries.yaml').read_text())['prefixes']
ADDRESS = re.compile(r'(?i)\b\d{1,5}\s+(?:[a-z][a-z\x27-]*\s+){1,5}(?:lane|road|street|avenue|drive|close|crescent|terrace|way|court|place|gardens|grove)\b')


def mkdirs():
    for directory in [OUT, DERIVED, OUT/'tables', OUT/'reports', OUT/'figures', OUT/'reference', OUT/'annotation', OUT/'logs', DERIVED/'parts']:
        directory.mkdir(parents=True, exist_ok=True)


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def json_save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def table(name, records, columns=None):
    path = OUT/'tables'/name
    if isinstance(records, pl.DataFrame):
        if records.height and records.width:
            records=records.sort(records.columns,nulls_last=True,maintain_order=True)
        records.write_csv(path)
        return records
    records = list(records)
    records.sort(key=lambda r:json.dumps(r,sort_keys=True,ensure_ascii=False,default=str))
    if columns is None:
        columns = list(dict.fromkeys(k for r in records for k in r)) if records else ['status']
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)
    return pl.read_csv(path, infer_schema_length=10000, null_values='') if records else pl.DataFrame(schema={c:pl.String for c in columns})


@lru_cache(maxsize=250000)
def normalize_label(value):
    s = unicodedata.normalize('NFKC', str(value or '')).upper().replace('&', ' AND ')
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', s)).strip()


@lru_cache(maxsize=250000)
def merchant_keys(raw):
    s = unicodedata.normalize('NFKC', str(raw or '')).upper().strip()
    intermediary = ''
    for prefix in PREFIXES:
        if s.startswith(prefix):
            intermediary = prefix.strip()
            # Retain the marketplace identity when a reference alone follows.
            s = s[len(prefix):]
            break
    s = re.sub(r'#\s*\d+', ' ', s)
    s = re.sub(r'\b(?=\w*\d)(?=\w*[A-Z])\w+\b|\d{3,}', ' ', s)
    strict = re.sub(r'\s+', ' ', re.sub(r'[^\w\s-]', ' ', s)).strip()
    if not strict and intermediary.startswith(('AMZN', 'AMAZON')):
        strict = 'AMAZON'
    loose = strict
    for target, patterns in ALIAS_CONFIG['aliases'].items():
        if any(re.search(pattern, loose) for pattern in patterns):
            loose = target
            break
    for suffix in ALIAS_CONFIG['location_suffixes']:
        loose = re.sub(r'\s+' + re.escape(suffix) + r'$', '', loose).strip()
    return strict, loose, intermediary


def redact_address(value):
    return 'ADDRESS_REDACTED' if ADDRESS.search(str(value or '')) else str(value or '')


@lru_cache(maxsize=250000)
def parse_date(value, country='UK'):
    s = str(value or '').strip()
    if not s or s.lower() in {'nan','none','null','nat','date','transaction date'}:
        return None, 'missing'
    if re.fullmatch(r'\d{5}(?:\.0+)?', s) and 20000 <= float(s) <= 60000:
        return (datetime(1899,12,30)+timedelta(days=float(s))).date().isoformat(), 'excel_serial'
    if re.match(r'^\d{4}-\d{2}-\d{2}', s):
        try:
            return datetime.fromisoformat(s.replace('Z','+00:00')).date().isoformat(), 'iso'
        except ValueError:
            pass
    order = ['%m/%d/%Y','%m-%d-%Y','%d/%m/%Y','%d-%m-%Y'] if country=='USA' else ['%d/%m/%Y','%d-%m-%Y','%m/%d/%Y','%m-%d-%Y']
    for fmt in order + ['%d/%m/%y','%m/%d/%y','%d-%b-%Y','%d %b %Y','%d-%b-%y','%d %B %Y','%d/%m/%Y %H:%M:%S','%m/%d/%Y %H:%M:%S']:
        try:
            return datetime.strptime(s,fmt).date().isoformat(), fmt
        except ValueError:
            continue
    return None, 'unparsed'


@lru_cache(maxsize=100000)
def parse_amount(value):
    s = str(value or '').strip()
    if not s or s.lower() in {'nan','none','null','n/a','-'}:
        return None
    negative = s.startswith('(') and s.endswith(')')
    s = re.sub(r'[^0-9.\-]', '', s)
    try:
        n = float(s)
        return -abs(n) if negative else n
    except ValueError:
        return None


def split_mcc(value):
    m = re.match(r'^\s*(\d{4})\s*[-:]\s*(.+)', str(value or ''))
    return (m.group(1), m.group(2)) if m else ('', str(value or ''))


def split_card(value):
    return {'JPMCP':('JPMorgan','P'), 'JPMCT':('JPMorgan','T'), 'USBKP':('US Bank','P'), 'USBKT':('US Bank','T')}.get(str(value).strip().upper(), ('unknown','unknown'))


def entropy(counts):
    counts = np.asarray(counts, dtype=float)
    p = counts[counts>0]/counts.sum() if counts.sum() else np.array([])
    return float(-np.sum(p*np.log2(p))) if len(p) else 0.0


def normalized_entropy(counts):
    c = np.asarray(counts)
    k = np.count_nonzero(c)
    return entropy(c)/np.log2(k) if k>1 else 0.0


def public_merchant_id(key):
    return 'm_' + hashlib.sha256(str(key).encode()).hexdigest()[:16]


def report(name, questions, method, limitations, body, inputs='derived/canonical.parquet; derived/purchase_labels.parquet'):
    (OUT/'reports'/name).write_text(f'# {name[3:-3].replace("_", " ").title()}\n\nResearch questions: {questions}.\n\nInputs: {inputs}.\n\nMethod: {method}\n\nLimitations: {limitations}\n\n{body}\n', encoding='utf-8')


def canonical_scan():
    return pl.scan_parquet(DERIVED/'canonical.parquet')


def collect(lazy):
    return lazy.collect(engine='streaming')
