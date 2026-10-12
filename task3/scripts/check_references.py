import duckdb

con = duckdb.connect()

sensors = con.execute("""
    SELECT COUNT(*)
    FROM read_csv_auto('task1/snapshot/sensors.csv')
""").fetchone()[0]

references = con.execute("""
    SELECT COUNT(*)
    FROM read_csv_auto('task1/snapshot/qa_reference.csv')
""").fetchone()[0]

print("Sensors:", sensors)
print("QA references:", references)

assert sensors == 20, "Unexpected sensor count"
assert references == 100, "Unexpected reference count"

print("PASS: Reference file counts")
