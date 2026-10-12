CREATE OR REPLACE TEMP VIEW normalized AS
SELECT
    source_object,
    source_row,
    parse_ok,
    UPPER(TRIM(canonical.record_id)) AS record_id,
    UPPER(TRIM(canonical.sensor_id)) AS sensor_id,
    TRIM(canonical.event_time) AS event_time_raw,
    TRIM(canonical.ingest_time) AS ingest_time_raw,
    TRIM(canonical.reading) AS reading_raw,
    UPPER(TRIM(canonical.unit)) AS unit,
    TRY_CAST(canonical.ingest_time AS TIMESTAMPTZ) AS ingest_time_utc
FROM raw_envelopes;

CREATE OR REPLACE TEMP VIEW precheck AS
SELECT *,
    CASE
        WHEN parse_ok IS DISTINCT FROM TRUE THEN 'PARSE'
        WHEN record_id IS NULL
          OR NOT regexp_full_match(record_id, 'R[0-9]{6}')
          THEN 'KEY'
        WHEN ingest_time_utc IS NULL THEN 'INGEST_PARSE'
        ELSE NULL
    END AS primary_reason,

    list_filter(
        [
            CASE WHEN parse_ok IS DISTINCT FROM TRUE
                 THEN 'PARSE' END,
            CASE WHEN record_id IS NULL
                   OR NOT regexp_full_match(record_id, 'R[0-9]{6}')
                 THEN 'KEY' END,
            CASE WHEN ingest_time_utc IS NULL
                 THEN 'INGEST_PARSE' END
        ],
        x -> x IS NOT NULL
    ) AS all_reasons
FROM normalized;

SELECT
    COALESCE(primary_reason, 'ELIGIBLE') AS status,
    COUNT(*) AS total
FROM precheck
GROUP BY 1
ORDER BY 1;
