from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
con = duckdb.connect(":memory:")

try:
    con.execute("SET memory_limit = '512MB'")

    con.execute("""
        CREATE TEMP VIEW raw_ids AS
        SELECT source_object, source_row
        FROM read_json_auto(
            'task1/observation_envelopes.jsonl',
            format='newline_delimited'
        )
    """)

    con.execute("""
        CREATE TEMP VIEW output_ids AS
        SELECT source_object, source_row, 'CURATED' AS disposition
        FROM read_parquet('task3/candidate/curated.parquet')

        UNION ALL

        SELECT source_object, source_row, 'QUARANTINE'
        FROM read_csv_auto('task3/candidate/quarantine.csv')

        UNION ALL

        SELECT source_object, source_row, 'DUPLICATE'
        FROM read_csv_auto('task3/candidate/duplicates.csv')
    """)

    result = con.execute("""
        SELECT
            (SELECT COUNT(*) FROM raw_ids) AS raw_count,
            (SELECT COUNT(*) FROM output_ids) AS output_count,

            (SELECT COUNT(*) FROM (
                SELECT source_object, source_row
                FROM raw_ids
                EXCEPT
                SELECT source_object, source_row
                FROM output_ids
            )) AS missing_ids,

            (SELECT COUNT(*) FROM (
                SELECT source_object, source_row
                FROM output_ids
                EXCEPT
                SELECT source_object, source_row
                FROM raw_ids
            )) AS invented_ids,

            (SELECT COUNT(*) FROM (
                SELECT source_object, source_row
                FROM output_ids
                GROUP BY 1, 2
                HAVING COUNT(*) > 1
            )) AS repeated_output_ids,

            (SELECT COUNT(*) FROM (
                SELECT source_object, source_row
                FROM raw_ids
                GROUP BY 1, 2
                HAVING COUNT(*) > 1
            )) AS repeated_raw_ids,

            (SELECT COUNT(*) FROM (
                SELECT record_id
                FROM read_parquet('task3/candidate/curated.parquet')
                GROUP BY 1
                HAVING COUNT(*) > 1
            )) AS repeated_business_ids
    """).fetchone()

    names = [
        "raw_count",
        "output_count",
        "missing_ids",
        "invented_ids",
        "repeated_output_ids",
        "repeated_raw_ids",
        "repeated_business_ids"
    ]

    print("\n=== C01: CONSERVATION ===")
    for name, value in zip(names, result):
        print(f"{name:25}: {value}")

    passed = (
        result[0] == 10205
        and result[1] == 10205
        and all(value == 0 for value in result[2:])
    )

    print("\nC01:", "PASS" if passed else "FAIL")

    if not passed:
        raise SystemExit(1)

finally:
    con.close()
