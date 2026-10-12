from pathlib import Path
import duckdb
import json

ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "task3/candidate/curated.parquet"
EVIDENCE = ROOT / "task3/evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)

expected = [
    ("record_id", "VARCHAR"),
    ("sensor_id", "VARCHAR"),
    ("site", "VARCHAR"),
    ("event_time_utc", "TIMESTAMP"),
    ("ingest_time_utc", "TIMESTAMP"),
    ("temperature_c", "DECIMAL(8,2)"),
    ("is_late", "BOOLEAN"),
    ("source_object", "VARCHAR"),
    ("source_row", "BIGINT"),
    ("source_sha256", "VARCHAR"),
]

con = duckdb.connect(":memory:")

try:
    schema = con.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(PARQUET)]
    ).fetchall()

    actual = [(r[0], r[1]) for r in schema]

    print("=== C03: SCHEMA AND PRIVACY ===")

    passed = actual == expected

    for i, item in enumerate(actual):
        expected_item = expected[i] if i < len(expected) else None
        status = "PASS" if item == expected_item else "FAIL"
        print(f"{status:5} {item[0]:22} {item[1]}")

    forbidden = {"operator_email", "raw_payload"}
    actual_names = {name.lower() for name, _ in actual}

    privacy_pass = not bool(actual_names & forbidden)

    null_source_hashes = con.execute("""
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE source_sha256 IS NULL
           OR NOT regexp_full_match(source_sha256, '[0-9a-f]{64}')
    """, [str(PARQUET)]).fetchone()[0]

    print("\nColumn count:", len(actual))
    print("Privacy check:", "PASS" if privacy_pass else "FAIL")
    print("Invalid source hashes:", null_source_hashes)

    passed = passed and privacy_pass and null_source_hashes == 0

    report = {
        "test": "C03",
        "expected_schema": expected,
        "actual_schema": actual,
        "privacy_pass": privacy_pass,
        "invalid_source_hashes": null_source_hashes,
        "passed": passed
    }

    (EVIDENCE / "c03_schema_privacy.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\nC03:", "PASS" if passed else "FAIL")

    if not passed:
        raise SystemExit(1)

finally:
    con.close()
