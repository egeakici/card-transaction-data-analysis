# Canonical merchant splits

Run from the repository root:

```powershell
python split_pipeline/make_splits.py
python -m split_pipeline.verify_splits
python -m unittest split_pipeline.test_pipeline
```

All parameters and column roles live in CONFIG at the start of make_splits.py.
Processing is local, with Polars, PyYAML, psutil and imported data_profile code.
No model is trained. The population is the eleven-source analysis.parquet selected
in outputs/DECISIONS.md. CONFIG.historical_exclusions retains the counts verified
before deleting the legacy global CSV: 53,916 out-of-scope Indonesia rows and
900,000 superseded Oklahoma rows. They remain in excluded_summary.csv under
population=legacy_csv as historical provenance, outside canonical reconciliation.
The deleted CSV is not read or required; its rows never enter row outputs.
Obsolete legacy-CSV diagnostics are removed by explicit filenames.

Hash-only merchant folds are written before reading any label, with a snapshot
in intermediate/merchant_folds_hash_only.parquet. Existing keys are used verbatim.
Diagnostic verification checks up to 10,000 evenly spaced canonical ranks per
source with imported data_profile normalization and its DWP location adapter.
Smaller sources are checked in full. This sampling never changes the population.

Labels join on source + file_id + sheet + original parsed record number.
outputs/manifest.csv maps original files to audit inventory entries. Every entry
must be a primary input with a matching original-file SHA-256. Each original file
is joined separately to bound memory. Conversions and merge-file audits are never
used. Missing labels become unlabeled. Oklahoma coverage below 95% or any source's
independent key match below 99.5% stops the run before row splitting.

SHA-1(key UTF-8) modulo 10 assigns folds 0-7 to train, 8 to validation, 9 to test.
Only the authorized rare exception changes folds: majority labels use labeled
rows and alphabetical ties; classes below 30 majority-label merchants receive
the repeating 9,8,0,1,2,3,4,5,6,7 sequence in SHA-1 order. Every selected merchant
is marked as an override, including unchanged folds. Registry majorities and
class distributions use the newly linked canonical rows exclusively.

Status precedence is no_key, masked, unlabeled, not_a_transaction, excluded_class,
unresolved, labeled, as recorded in CONFIG. No-key rows have no fold. Label purity
is majority rows / labeled rows for that merchant. No row is deduplicated or
balanced; original Parquet fields and types are retained in every row output.

test_pool_all contains every fold-9 row; test is its labeled subset. The merchant
sampling frame uses the full pool, including strict variants, top-three raw
variants, source/status distributions, dates and MCC diagnostics. MCC disagreement
compares source majorities among known generic MCC rows. Within-source flags use
a majority share below 0.9 among known MCC rows; unknown codes alone do not imply
disagreement. Mode ties are alphabetical. Majority MCC origin uses all pool rows.

Canonical conservation is analysis = train + validation + test_pool_all +
non-labeled folds 0-8 (counts only) + no_key (counts only). Do not add test again.
Noncanonical documentation, notes, blanks and superseded/out-of-scope rows have
separate population flags in the exclusion summary and are outside this equation.
Moneydata documentation and Solihull notes are not_a_transaction there and are
outside the canonical key-verification denominator.

Verification asserts isolation, routing, test content subset, original types,
class exclusions, conservation and train coverage. It independently rebuilds the
registry and compares the complete Parquet SHA-256. A second identical full run
also compares the previous registry hash; results and run counts are recorded in
reports/pipeline_state.json. Validation/test class gaps are reported without error.

All generated data and private reports remain under the gitignored
train-test-datasets directory. Do not commit datasets, merchant examples or row
audits. Inputs and existing profiling/taxonomy artifacts are read-only.
