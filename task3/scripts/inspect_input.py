from pathlib import Path
import duckdb
import json

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "task1" / "observation_envelopes.jsonl"

if not INPUT.exists():
    raise SystemExit(f"INPUT NOT FOUND: {INPUT}")

con = duckdb.connect(":memory:")

try:
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '512MB'")

    con.execute("""
        CREATE TEMP TABLE raw_envelopes AS
        SELECT *
        FROM read_json_auto(
            ?,
            format='newline_delimited'
        )
    """, [str(INPUT)])

    total = con.execute(
        "SELECT COUNT(*) FROM raw_envelopes"
    ).fetchone()[0]

    print("\n=== TASK 3 INPUT ===")
    print("Total envelopes:", total)
    print("Expected:", 10205)
    print("Count check:", "PASS" if total == 10205 else "FAIL")

    print("\n=== SCHEMA ===")
    for row in con.execute("DESCRIBE raw_envelopes").fetchall():
        print(row[0], ":", row[1])

    print("\n=== SAMPLE ENVELOPE ===")
    with INPUT.open("r", encoding="utf-8") as f:
        obj = json.loads(f.readline())

    # Only display field names and types; do not print raw payload or email.
    print("Top-level fields:", list(obj.keys()))

    canonical = obj.get("canonical")
    if isinstance(canonical, dict):
        print("Canonical fields:", list(canonical.keys()))

    if total != 10205:
        raise SystemExit("FAIL: Input count mismatch")

finally:
    con.close()
