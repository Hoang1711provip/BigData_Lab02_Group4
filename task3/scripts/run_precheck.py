from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "task1" / "observation_envelopes.jsonl"
SQL = ROOT / "task3" / "sql" / "precheck.sql"

con = duckdb.connect(":memory:")

try:
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '512MB'")

    con.execute("""
        CREATE TEMP TABLE raw_envelopes AS
        SELECT *
        FROM read_json_auto(?, format='newline_delimited')
    """, [str(INPUT)])

    sql = SQL.read_text(encoding="utf-8-sig")
    results = con.execute(sql).fetchall()

    print("\n=== TASK 3: PRECHECK ===")
    for status, count in results:
        print(f"{status:20} {count:6}")

    print("\n=== RECONCILIATION ===")
    total = sum(count for _, count in results)
    print("Total classified:", total)
    print("Expected:", 10205)

    if total != 10205:
        raise SystemExit("FAIL: Count mismatch")

    print("PASS: All input envelopes accounted for")

finally:
    con.close()
