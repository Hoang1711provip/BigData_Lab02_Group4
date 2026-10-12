
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "task3" / "candidate"
EVIDENCE = ROOT / "task3" / "evidence"

# Tìm file Parquet curated, không chọn file quarantine hoặc duplicates.
parquet_files = [
    p for p in CANDIDATE.glob("*.parquet")
    if "quarantine" not in p.name.lower()
    and "duplicate" not in p.name.lower()
]

if not parquet_files:
    raise SystemExit(
        f"FAIL: Không tìm thấy curated Parquet trong {CANDIDATE}"
    )

if len(parquet_files) > 1:
    print("Các file Parquet tìm thấy:")
    for p in parquet_files:
        print(" -", p.name)
    raise SystemExit(
        "Có nhiều file Parquet; hãy chọn đúng file curated trước khi chạy."
    )

PARQUET = parquet_files[0]
EVIDENCE.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(":memory:")

try:
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '512MB'")

    # Escape dấu nháy đơn trong đường dẫn Windows.
    parquet_path = str(PARQUET).replace("'", "''")

    con.execute(
        f"CREATE TEMP VIEW curated AS "
        f"SELECT * FROM read_parquet('{parquet_path}')"
    )

    columns = con.execute(
        "DESCRIBE curated"
    ).fetchall()

    count = con.execute(
        "SELECT COUNT(*) FROM curated"
    ).fetchone()[0]

    required = {
        "record_id": "VARCHAR",
        "sensor_id": "VARCHAR",
        "site": "VARCHAR",
        "event_time_utc": "TIMESTAMP",
        "ingest_time_utc": "TIMESTAMP",
        "temperature_c": "DECIMAL(8,2)",
        "is_late": "BOOLEAN",
        "source_object": "VARCHAR",
        "source_row": "BIGINT",
        "source_sha256": "VARCHAR",
    }

    actual = {name: dtype.upper() for name, dtype, *_ in columns}

    checks = {
        "correct_file_found": PARQUET.is_file(),
        "nonempty_dataset": count > 0,
        "exact_schema": actual == required,
    }

    print("=== C05: CURATED OUTPUT CHECK ===")
    print("File:", PARQUET.name)
    print("Rows:", count)

    print("\n=== SCHEMA ===")
    for name, dtype, *_ in columns:
        expected = required.get(name)
        ok = expected is not None and dtype.upper() == expected
        print(
            f"{'PASS' if ok else 'FAIL'} "
            f"{name}: {dtype}"
            + (f" (expected {expected})" if expected else "")
        )

    print("\n=== CHECKS ===")
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")

    result = {
        "test": "C05",
        "mode": "LOCAL",
        "input_file": PARQUET.name,
        "row_count": count,
        "schema": [
            {"name": name, "type": dtype}
            for name, dtype, *_ in columns
        ],
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }

    output = EVIDENCE / "C05.json"
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nEvidence:", output)
    print("C05:", result["status"])

    if result["status"] != "PASS":
        raise SystemExit(1)

finally:
    con.close()