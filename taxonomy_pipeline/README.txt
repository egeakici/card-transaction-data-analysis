REAL-WORLD TAXONOMY LABELING

Scope: all CSV and XLSX files under real-world-datas, including original
workbooks, conversions and concatenations. Non-data documents are copied byte
for byte. Original inputs are never opened for writing.

Commands, from the repository root:
  python taxonomy_pipeline/run.py --resume
  python taxonomy_pipeline/analyze.py
  python taxonomy_pipeline/verify.py

Main deliverable: real-world-datas-regex-labelled/ANALIZ_RAPORU.html
File-level distributions and row-addressed evidence are in _taxonomy_analysis.
Every source record has a label or an explicit operational status.

taxonomy_label uses MAIN_CATEGORY.subcategory; 16 parents, 72 leaves.
Operational status values are not additions to the user's taxonomy:
  UNRESOLVED_INSUFFICIENT_EVIDENCE
  UNRESOLVED_AMBIGUOUS
  UNRESOLVED_OUT_OF_TAXONOMY
  NOT_A_TRANSACTION

Rules are deterministic, reviewable weak annotations, not human gold labels.
Explicit, narrow product/purpose evidence has priority. Multiple recognized
product categories trigger ambiguity. Then merchant rules, MCC code/title
crosswalks, procurement text and narrow original source labels are considered.
Some broad MCCs deliberately do not map to a single leaf. Rules do not detect
every possible multi-category basket. Source category fields are evidence, not
independent validation. Refunds and repeated purchases are kept as supplied.

No new fuzzy MCC linkage is performed. The pre-existing pinned reference and
previously accepted exact/normalized/observed title links are reused. Additional
literal title interpretation rules are exported separately. New text rules
must not be described as an official payment-network crosswalk.

The general study pool avoids double counting conversions/concatenations.
This does not remove duplicates already present inside the original inputs.
Every physical file still has its own detailed distribution. Counts are record
counts, not unique transactions or currency-normalized spending totals.

Row-level audit parquet columns identify source_file through file_inventory.csv
(file_id), source_sheet and source_row. CSV source_row counts parsed CSV records,
not physical lines inside quoted strings. Original headers are excluded from
record distributions; preambles, notes and blank worksheet-extent rows are kept.
Original CSV row values/order are preserved; short rows are padded with empty
cells to align the appended field. Outputs use UTF-8 BOM and LF line endings.

XLSX label cells are authored with @oai/artifact-tool. The new string cells are
grafted into copies of the original worksheet XML to preserve formula caches,
all original cells, original styles, drawings, relationships and other parts.
The original dimension changes by one column; the label column gets a readable
width. CSV bulk processing and all scientific summaries use Python streaming.

Runtime: Python 3.13 with pyarrow, openpyxl, polars, numpy and matplotlib.
Node requires @oai/artifact-tool from the configured bundled runtime, exposed
via taxonomy_pipeline/node_modules (local ignored junction). Excel preview:
  node taxonomy_pipeline/preview.mjs real-world-datas-regex-labelled .data_processing/taxonomy_previews

Source permissions: three legacy CSVs cannot be read directly. Their existing
access copies are accepted only after matching the recorded original SHA-256.
Original file size and modification timestamp are also checked. Source baseline
hashes include every source document. verify.py independently checks every
original row/cell against the final copy and reconciles audit/distribution counts.

The qualitative review template contains capped first-distinct examples. It is
not a random sample and cannot establish statistical superiority. A blinded,
independent, stratified annotation study is required for an MCC superiority claim.

Artifacts stay local and are ignored by Git, following the repository's existing
raw-data convention. No data is uploaded, published or committed.
