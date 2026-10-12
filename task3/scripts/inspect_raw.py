from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
SQL_FILE = ROOT / "task3" / "sql" / "inspect_raw.sql"
INPUT_FILE = ROOT / "task1" / "observation_envelopes.jsonl"

if not INPUT_FILE.exists():
    raise SystemExit(f"ERROR: Input file not found: {INPUT_FILE}")

con = duckdb.connect(database=":memory:")

try:
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '512MB'")

    con.execute("""
        CREATE TEMP TABLE raw_envelopes AS
        SELECT *
        FROM read_json_auto(
            ?,
            format = 'newline_delimited'
        )
    """, [str(INPUT_FILE)])

    print("=== TASK 3: INPUT VERIFICATION ===")

    total = con.execute("""
        SELECT COUNT(*) FROM raw_envelopes
    """).fetchone()[0]

    print(f"Total envelopes: {total}")
    print(f"Expected: 10205")

    if total != 10205:
        raise SystemExit("FAILED: Unexpected envelope count")

    print("STATUS: PASS")

    print("\n=== RAW SCHEMA ===")

    schema = con.execute("""
        DESCRIBE raw_envelopes
    """).fetchall()

    for column in schema:
        print(f"{column[0]:25} {column[1]}")

finally:
    con.close()
