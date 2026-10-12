from pathlib import Path
import duckdb
import json
import sys

ROOT = Path(__file__).resolve().parents[2]

RAW = ROOT / "task1/observation_envelopes.jsonl"
CURATED = ROOT / "task3/candidate/curated.parquet"
QUARANTINE = ROOT / "task3/candidate/quarantine.csv"
DUPLICATES = ROOT / "task3/candidate/duplicates.csv"

EVIDENCE = ROOT / "task3/evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)

for path in [RAW, CURATED, QUARANTINE, DUPLICATES]:
    if not path.exists():
        sys.exit(f"ERROR: Missing file: {path}")

con = duckdb.connect(":memory:")

try:
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '512MB'")

    # Load raw envelopes
    con.execute("""
        CREATE TEMP TABLE raw_ids AS
        SELECT
            source_object::VARCHAR AS source_object,
            source_row::BIGINT AS source_row
        FROM read_json_auto(
            ?, format='newline_delimited'
        )
    """, [str(RAW)])

    # Load curated
    con.execute("""
        CREATE TEMP TABLE curated AS
        SELECT * FROM read_parquet(?)
    """, [str(CURATED)])

    # Load quarantine
    con.execute("""
        CREATE TEMP TABLE quarantine AS
        SELECT * FROM read_csv_auto(?)
    """, [str(QUARANTINE)])

    # Load duplicates
    con.execute("""
        CREATE TEMP TABLE duplicates AS
        SELECT * FROM read_csv_auto(?)
    """, [str(DUPLICATES)])

    # Combine all terminal dispositions
    con.execute("""
        CREATE TEMP TABLE output_ids AS

        SELECT source_object, source_row, 'CURATED' AS disposition
        FROM curated

        UNION ALL

        SELECT source_object, source_row, 'QUARANTINE'
        FROM quarantine

        UNION ALL

        SELECT source_object, source_row, 'DUPLICATE'
        FROM duplicates
    """)

    queries = {
        "raw_count": """
            SELECT COUNT(*) FROM raw_ids
        """,

        "curated_count": """
            SELECT COUNT(*) FROM curated
        """,

        "quarantine_count": """
            SELECT COUNT(*) FROM quarantine
        """,

        "duplicates_count": """
            SELECT COUNT(*) FROM duplicates
        """,

        "output_count": """
            SELECT COUNT(*) FROM output_ids
        """,

        "missing_ids": """
            SELECT COUNT(*) FROM (
                SELECT source_object, source_row FROM raw_ids
                EXCEPT
                SELECT source_object, source_row FROM output_ids
            )
        """,

        "invented_ids": """
            SELECT COUNT(*) FROM (
                SELECT source_object, source_row FROM output_ids
                EXCEPT
                SELECT source_object, source_row FROM raw_ids
            )
        """,

        "repeated_raw_ids": """
            SELECT COUNT(*) FROM (
                SELECT source_object, source_row
                FROM raw_ids
                GROUP BY 1, 2
                HAVING COUNT(*) > 1
            )
        """,

        "repeated_output_ids": """
            SELECT COUNT(*) FROM (
                SELECT source_object, source_row
                FROM output_ids
                GROUP BY 1, 2
                HAVING COUNT(*) > 1
            )
        """,

        "repeated_business_ids": """
            SELECT COUNT(*) FROM (
                SELECT record_id
                FROM curated
                GROUP BY record_id
                HAVING COUNT(*) > 1
            )
        """,

        "null_raw_ids": """
            SELECT COUNT(*) FROM raw_ids
            WHERE source_object IS NULL OR source_row IS NULL
        """,

        "null_output_ids": """
            SELECT COUNT(*) FROM output_ids
            WHERE source_object IS NULL OR source_row IS NULL
        """
    }

    results = {
        name: con.execute(sql).fetchone()[0]
        for name, sql in queries.items()
    }

    expected_total = 10205

    passed = (
        results["raw_count"] == expected_total
        and results["output_count"] == expected_total
        and results["output_count"] == (
            results["curated_count"]
            + results["quarantine_count"]
            + results["duplicates_count"]
        )
        and all(
            results[name] == 0
            for name in [
                "missing_ids",
                "invented_ids",
                "repeated_raw_ids",
                "repeated_output_ids",
                "repeated_business_ids",
                "null_raw_ids",
                "null_output_ids"
            ]
        )
    )

    print("\n" + "=" * 55)
    print("TASK 3 - C01 CONSERVATION VERIFICATION")
    print("=" * 55)

    for name, value in results.items():
        print(f"{name:28}: {value}")

    print("-" * 55)
    print("C01 RESULT:", "PASS" if passed else "FAIL")

    report = {
        "test": "C01",
        "expected_total": expected_total,
        "results": results,
        "passed": passed
    }

    output_path = EVIDENCE / "c01_conservation.json"

    output_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("Evidence:", output_path)

    if not passed:
        sys.exit(1)

finally:
    con.close()
