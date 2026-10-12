from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "task1" / "observation_envelopes.jsonl"
PRECHECK = ROOT / "task3" / "sql" / "precheck.sql"
DEDUP = ROOT / "task3" / "sql" / "deduplicate.sql"

con = duckdb.connect(":memory:")

try:
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '512MB'")

    con.execute("""
        CREATE TEMP TABLE raw_envelopes AS
        SELECT *
        FROM read_json_auto(?, format='newline_delimited')
    """, [str(INPUT)])

    # Only execute CREATE VIEW statements from precheck.sql.
    precheck_sql = PRECHECK.read_text(encoding="utf-8-sig")
    con.execute(precheck_sql)

    dedup_sql = DEDUP.read_text(encoding="utf-8-sig")
    row = con.execute(dedup_sql).fetchone()

    raw, quarantine, winners, duplicates = row

    print("\n=== TASK 3: DEDUPLICATION ===")
    print("Raw envelopes:       ", raw)
    print("Precheck quarantine: ", quarantine)
    print("Winners:             ", winners)
    print("Duplicates:          ", duplicates)

    print("\n=== RECONCILIATION ===")
    total = quarantine + winners + duplicates
    print(f"{quarantine} + {winners} + {duplicates} = {total}")

    assert total == raw == 10205
    assert con.execute("""
        SELECT COUNT(*) = COUNT(DISTINCT record_id)
        FROM winners
    """).fetchone()[0]

    print("PASS: Conservation and unique winner IDs")

finally:
    con.close()
