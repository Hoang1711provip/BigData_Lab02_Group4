CREATE OR REPLACE TEMP VIEW ranked AS
SELECT
    *,
    ROW_NUMBER() OVER (
        PARTITION BY record_id
        ORDER BY
            ingest_time_utc DESC,
            source_object ASC,
            source_row ASC
    ) AS rn
FROM precheck
WHERE primary_reason IS NULL;

CREATE OR REPLACE TEMP VIEW winners AS
SELECT *
FROM ranked
WHERE rn = 1;

CREATE OR REPLACE TEMP VIEW duplicates AS
SELECT
    d.source_object,
    d.source_row,
    d.record_id,
    w.source_object AS winner_source_object,
    w.source_row AS winner_source_row,
    'SUPERSEDED' AS reason
FROM ranked d
JOIN winners w
    ON d.record_id = w.record_id
WHERE d.rn > 1;

SELECT
    (SELECT COUNT(*) FROM precheck) AS total_raw,
    (SELECT COUNT(*) FROM precheck
        WHERE primary_reason IS NOT NULL) AS precheck_quarantine,
    (SELECT COUNT(*) FROM winners) AS winners,
    (SELECT COUNT(*) FROM duplicates) AS duplicates;
