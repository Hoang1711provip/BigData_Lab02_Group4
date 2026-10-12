from pathlib import Path
import duckdb

root = Path(__file__).resolve().parents[2]
con = duckdb.connect(":memory:")

try:
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '512MB'")

    con.execute("""
        CREATE TEMP TABLE raw_envelopes AS
        SELECT *
        FROM read_json_auto(?, format='newline_delimited')
    """, [str(root / "task1/observation_envelopes.jsonl")])

    con.execute(
        (root / "task3/sql/precheck.sql").read_text(encoding="utf-8-sig")
    )
    con.execute(
        (root / "task3/sql/deduplicate.sql").read_text(encoding="utf-8-sig")
    )

    print("=== WINNER UNIT DISTRIBUTION ===")

    rows = con.execute("""
        SELECT
            COALESCE(NULLIF(unit, ''), '<EMPTY>') AS unit_name,
            COUNT(*) AS total
        FROM winners
        GROUP BY 1
        ORDER BY total DESC
    """).fetchall()

    for unit, count in rows:
        print(f"{unit:12} {count:6}")

    print("\nTotal winners:", sum(count for _, count in rows))

finally:
    con.close()
