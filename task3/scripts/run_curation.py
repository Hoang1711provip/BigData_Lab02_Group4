from pathlib import Path
import duckdb
import json
import hashlib
import csv

ROOT = Path(__file__).resolve().parents[2]
TASK3 = ROOT / "task3"
OUT = TASK3 / "candidate"
EVIDENCE = TASK3 / "evidence"
OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

INPUT = ROOT / "task1/observation_envelopes.jsonl"
SENSORS = ROOT / "task1/snapshot/sensors.csv"
CONTRACT = ROOT / "contracts/contract.json"

contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sql_string(value):
    return "'" + str(value).replace("'", "''") + "'"

def sql_path(path):
    return sql_string(str(path.resolve()).replace("\\", "/"))

con = duckdb.connect(":memory:")

try:
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '512MB'")
    con.execute("SET TimeZone = 'UTC'")

    con.execute("""
        CREATE TEMP TABLE raw_envelopes AS
        SELECT *
        FROM read_json_auto(?, format='newline_delimited')
    """, [str(INPUT)])

    con.execute(
        (TASK3 / "sql/precheck.sql").read_text(encoding="utf-8-sig")
    )
    con.execute(
        (TASK3 / "sql/deduplicate.sql").read_text(encoding="utf-8-sig")
    )

    con.execute("""
        CREATE TEMP TABLE sensor_registry AS
        SELECT DISTINCT
            UPPER(TRIM(sensor_id)) AS sensor_id,
            TRIM(site) AS site
        FROM read_csv_auto(?)
    """, [str(SENSORS)])

    # Map source_object to the original snapshot files.
    # Never substitute the envelope hash for the source-file hash.
    sources = {}
    for name in ("observations_a.csv", "observations_b.jsonl"):
        path = ROOT / "task1/snapshot" / name
        if not path.exists():
            raise RuntimeError(f"Missing original snapshot: {path}")
        sources[name] = sha256(path)

    # Validate the actual source_object values before exporting.
    source_objects = [
        r[0] for r in con.execute(
            "SELECT DISTINCT source_object FROM raw_envelopes"
        ).fetchall()
    ]

    source_hashes = []
    for obj in source_objects:
        matches = [
            digest for name, digest in sources.items()
            if obj == name or obj.replace("\\", "/").endswith("/" + name)
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Cannot map source_object to snapshot: {obj}")
        source_hashes.append((obj, matches[0]))

    con.execute("""
        CREATE TEMP TABLE source_hashes(
            source_object VARCHAR,
            source_sha256 VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO source_hashes VALUES (?, ?)",
        source_hashes
    )

    min_c = float(contract["temperature_range_c"]["min"])
    max_c = float(contract["temperature_range_c"]["max"])
    late = int(contract["late_threshold_seconds"])
    as_of = sql_string(contract["as_of"])
    units = ", ".join(
        sql_string(u) for u in contract["supported_units"]
    )

    validation_sql = f"""
    CREATE TEMP TABLE winner_typed AS
    SELECT
        w.source_object,
        w.source_row,
        w.record_id,
        w.sensor_id,
        w.event_time_raw,
        w.ingest_time_raw,
        w.reading_raw,
        w.unit,
        s.site,
        TRY_CAST(w.reading_raw AS DOUBLE) AS reading_num,
        TRY_CAST(w.event_time_raw AS TIMESTAMPTZ) AS event_ts,
        TRY_CAST(w.ingest_time_raw AS TIMESTAMPTZ) AS ingest_ts,
        CASE
            WHEN w.unit = 'C'
                THEN TRY_CAST(w.reading_raw AS DOUBLE)
            WHEN w.unit = 'F'
                THEN (TRY_CAST(w.reading_raw AS DOUBLE) - 32) * 5 / 9
            ELSE NULL
        END AS temperature_num
    FROM winners w
    LEFT JOIN sensor_registry s
      ON w.sensor_id = s.sensor_id;

    CREATE TEMP TABLE winner_checks AS
    SELECT *,
        (
            record_id IS NULL OR record_id = ''
            OR sensor_id IS NULL OR sensor_id = ''
            OR event_time_raw IS NULL OR event_time_raw = ''
            OR ingest_time_raw IS NULL OR ingest_time_raw = ''
            OR reading_raw IS NULL OR reading_raw = ''
            OR unit IS NULL OR unit = ''
        ) AS fail_required,

        (
            reading_num IS NULL
            OR NOT COALESCE(isfinite(reading_num), FALSE)
        ) AS fail_numeric,

        (unit IS NULL OR unit NOT IN ({units})) AS fail_unit,

        (
            temperature_num IS NOT NULL
            AND isfinite(temperature_num)
            AND (temperature_num < {min_c}
                 OR temperature_num > {max_c})
        ) AS fail_range,

        (event_ts IS NULL) AS fail_time_parse,

        (
            event_ts IS NOT NULL
            AND ingest_ts IS NOT NULL
            AND (
                event_ts > ingest_ts
                OR ingest_ts > CAST({as_of} AS TIMESTAMPTZ)
            )
        ) AS fail_time_order,

        (site IS NULL) AS fail_reference
    FROM winner_typed;

    CREATE TEMP TABLE validated AS
    SELECT *,
        list_filter([
            CASE WHEN fail_required THEN 'REQUIRED' END,
            CASE WHEN fail_numeric THEN 'NUMERIC' END,
            CASE WHEN fail_unit THEN 'UNIT' END,
            CASE WHEN fail_range THEN 'RANGE' END,
            CASE WHEN fail_time_parse THEN 'TIME_PARSE' END,
            CASE WHEN fail_time_order THEN 'TIME_ORDER' END,
            CASE WHEN fail_reference THEN 'REFERENCE' END
        ], x -> x IS NOT NULL) AS all_reasons,

        CASE
            WHEN fail_required THEN 'REQUIRED'
            WHEN fail_numeric THEN 'NUMERIC'
            WHEN fail_unit THEN 'UNIT'
            WHEN fail_range THEN 'RANGE'
            WHEN fail_time_parse THEN 'TIME_PARSE'
            WHEN fail_time_order THEN 'TIME_ORDER'
            WHEN fail_reference THEN 'REFERENCE'
            ELSE NULL
        END AS primary_reason
    FROM winner_checks;

    CREATE TEMP TABLE curated AS
    SELECT
        v.record_id::VARCHAR AS record_id,
        v.sensor_id::VARCHAR AS sensor_id,
        v.site::VARCHAR AS site,
        CAST(v.event_ts AT TIME ZONE 'UTC' AS TIMESTAMP)
            AS event_time_utc,
        CAST(v.ingest_ts AT TIME ZONE 'UTC' AS TIMESTAMP)
            AS ingest_time_utc,
        CAST(ROUND(v.temperature_num, 2) AS DECIMAL(8,2))
            AS temperature_c,
        (date_diff('second', v.event_ts, v.ingest_ts) > {late})
            AS is_late,
        v.source_object::VARCHAR AS source_object,
        v.source_row::BIGINT AS source_row,
        h.source_sha256::VARCHAR AS source_sha256
    FROM validated v
    JOIN source_hashes h USING (source_object)
    WHERE v.primary_reason IS NULL;

    CREATE TEMP TABLE quarantine AS
    SELECT
        source_object,
        source_row,
        record_id,
        primary_reason,
        array_to_string(all_reasons, '|') AS all_reasons
    FROM precheck
    WHERE primary_reason IS NOT NULL

    UNION ALL

    SELECT
        source_object,
        source_row,
        record_id,
        primary_reason,
        array_to_string(all_reasons, '|') AS all_reasons
    FROM validated
    WHERE primary_reason IS NOT NULL;
    """

    con.execute(validation_sql)

    # Guard against duplicate registry entries multiplying winners.
    registry_duplicates = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT sensor_id
            FROM sensor_registry
            GROUP BY sensor_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    if registry_duplicates:
        raise RuntimeError("Duplicate normalized sensor IDs in registry")

    counts = {}
    for table in ("raw_envelopes", "curated", "quarantine", "duplicates"):
        counts[table] = con.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    print("\n=== TASK 3 CURATION ===")
    for name, value in counts.items():
        print(f"{name:20}: {value}")

    total = (
        counts["curated"]
        + counts["quarantine"]
        + counts["duplicates"]
    )
    if total != counts["raw_envelopes"]:
        raise RuntimeError("FAIL: Reconciliation count mismatch")

    print("\n=== WINNER VALIDATION REASONS ===")
    for reason, count in con.execute("""
        SELECT COALESCE(primary_reason, 'VALID'), COUNT(*)
        FROM validated
        GROUP BY 1
        ORDER BY 1
    """).fetchall():
        print(f"{reason:20}: {count}")

    # Output only after basic checks pass.
    con.execute(
        f"COPY curated TO {sql_path(OUT / 'curated.parquet')} "
        "(FORMAT PARQUET)"
    )
    con.execute(
        f"COPY quarantine TO {sql_path(OUT / 'quarantine.csv')} "
        "(HEADER, DELIMITER ',')"
    )
    con.execute(
        f"COPY duplicates TO {sql_path(OUT / 'duplicates.csv')} "
        "(HEADER, DELIMITER ',')"
    )

    evidence = {
        "counts": counts,
        "reconciled": total == counts["raw_envelopes"],
        "input_sha256": sha256(INPUT),
        "contract_sha256": sha256(CONTRACT),
        "script_sha256": sha256(Path(__file__)),
        "source_file_sha256": sources,
    }

    (EVIDENCE / "reconciliation.json").write_text(
        json.dumps(evidence, indent=2),
        encoding="utf-8"
    )

    print("\nPASS: Count reconciliation")
    print("Candidate files written to:", OUT)

finally:
    con.close()

