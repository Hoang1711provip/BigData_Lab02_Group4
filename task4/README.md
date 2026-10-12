# Operational Metadata and Lineage Catalog

## Purpose & Synthetic Origin
This catalog and metadata suite operationalize data governance for the research telemetry pipeline. All datasets are derived from synthetic sensor measurements generated for educational and benchmarking purposes under strict contract constraints.

## Files and Keys
- **curated.parquet**: The primary candidate dataset (`record_id` as primary key).
- **quarantine.parquet**: Isolated non-conforming records with primary failure reasons.
- **duplicates.csv**: Supporting duplicate ledger tracking deduplication actions.
- **catalog.json**: Machine-readable dataset catalog adhering to course profile requirements.

## Timestamps and Units
All timestamps (`event_time_utc`, `ingest_time_utc`, `as_of`) are represented in standard ISO 8601 UTC format. Temperature values are converted to standard Celsius (`°C`) stored as `DECIMAL(8,2)`.

## Curation & Deduplication Policy
Incoming telemetry records are validated against contract rules. Business keys (`record_id`) undergo case-insensitive whitespace normalization (`UPPER(TRIM())`). Exact duplicates are deduplicated via deterministic ledger ordering, sending excess copies to the duplicate ledger while keeping valid unique entries.

## Quality Cohorts & Residual Limitations
Candidate quality is evaluated across eight distinct metrics (`Q_REQUIRED`, `Q_UNIQUE_KEY`, `Q_VALUE`, `Q_REGISTRY`, `Q_CHRONO`, `Q_TIMELY`, `Q_QA_COVERAGE`, `Q_QA_AGREEMENT`). Residual limitations include an allowable timeliness lag threshold of 95% (up to 900 seconds lag).

## Permitted Use & Access Boundary
This data is restricted strictly to synthetic teaching use. Production deployment or external re-distribution is prohibited. Raw and quarantine layers are classified as `RESTRICTED`, whereas the curated layer is classified as `INTERNAL`.

## Software Versions & Reproduction Instructions
- **DuckDB**: >= 0.9.0
- **Python**: >= 3.10
Run execution scripts via:
`python task4/scripts/generate_catalog_and_queries.py`
`python task4/scripts/generate_retention.py`
`python task4/scripts/generate_lineage_and_traces.py`
All machine-readable evidence outputs are saved directly under `task4/evidence/` and `task4/lineage/`.
