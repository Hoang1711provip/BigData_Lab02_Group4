from pathlib import Path
import duckdb
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "task1/observation_envelopes.jsonl"
OUT = ROOT / "task3/evidence/c02"
OUT.mkdir(parents=True, exist_ok=True)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def logical_digest(rows):
    h = hashlib.sha256()
    for row in sorted(rows):
        h.update(json.dumps(
            row, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()

def run_ordered(order_name):
    con = duckdb.connect(":memory:")
    try:
        con.execute("SET threads = 2")
        con.execute("SET memory_limit = '512MB'")
        con.execute("SET TimeZone = 'UTC'")

        # Preserve physical IDs while changing input enumeration.
        con.execute("""
            CREATE TEMP TABLE raw_source AS
            SELECT *
            FROM read_json_auto(?, format='newline_delimited')
        """, [str(INPUT)])

        if order_name == "reversed":
            con.execute("""
                CREATE TEMP TABLE raw_envelopes AS
                SELECT * FROM raw_source
                ORDER BY source_object DESC, source_row DESC
            """)
        else:
            con.execute("""
                CREATE TEMP TABLE raw_envelopes AS
                SELECT * FROM raw_source
                ORDER BY hash(source_object, source_row, 2026)
            """)

        precheck = (
            ROOT / "task3/sql/precheck.sql"
        ).read_text(encoding="utf-8-sig")

        dedup = (
            ROOT / "task3/sql/deduplicate.sql"
        ).read_text(encoding="utf-8-sig")

        con.execute(precheck)
        con.execute(dedup)

        winner_rows = con.execute("""
            SELECT record_id, source_object, source_row
            FROM winners
        """).fetchall()

        duplicate_rows = con.execute("""
            SELECT source_object, source_row,
                   winner_source_object, winner_source_row
            FROM duplicates
        """).fetchall()

        precheck_rejected = con.execute("""
            SELECT source_object, source_row, primary_reason
            FROM precheck
            WHERE primary_reason IS NOT NULL
        """).fetchall()

        return {
            "winners": logical_digest(winner_rows),
            "duplicates": logical_digest(duplicate_rows),
            "precheck_quarantine": logical_digest(precheck_rejected),
            "counts": {
                "winners": len(winner_rows),
                "duplicates": len(duplicate_rows),
                "precheck_quarantine": len(precheck_rejected)
            }
        }
    finally:
        con.close()

reversed_result = run_ordered("reversed")
shuffled_result = run_ordered("shuffled")

passed = (
    reversed_result["winners"] == shuffled_result["winners"]
    and reversed_result["duplicates"] == shuffled_result["duplicates"]
    and reversed_result["precheck_quarantine"]
        == shuffled_result["precheck_quarantine"]
)

report = {
    "test": "C02_PARTIAL",
    "description": "Precheck and deduplication order invariance",
    "reversed": reversed_result,
    "shuffled": shuffled_result,
    "passed": passed
}

(OUT / "c02_dedup_replay.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("=== C02: DEDUP REPLAY ===")
for name in ("winners", "duplicates", "precheck_quarantine"):
    print(f"{name:22}:",
          "MATCH" if reversed_result[name] == shuffled_result[name]
          else "MISMATCH")

print("\nC02 DEDUP:", "PASS" if passed else "FAIL")

if not passed:
    raise SystemExit(1)
