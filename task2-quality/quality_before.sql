-- key_eligible: parse ok, id matches pattern, ingest time parseable
CREATE OR REPLACE VIEW key_eligible AS
SELECT * FROM typed
WHERE parse_ok
  AND regexp_full_match(coalesce(record_id,''),'R[0-9]{6}')
  AND ingest_ts IS NOT NULL;

CREATE OR REPLACE VIEW winners AS
SELECT * EXCLUDE(rn) FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY record_id
     ORDER BY ingest_ts DESC, source_object ASC, source_row ASC) AS rn
  FROM key_eligible) WHERE rn = 1;

CREATE OR REPLACE VIEW w_flags AS
SELECT w.*,
  (record_id IS NOT NULL AND trim(coalesce(sensor_id,''))<>'' AND trim(coalesce(event_time,''))<>''
   AND trim(coalesce(ingest_time,''))<>'' AND trim(coalesce(reading,''))<>'' AND trim(coalesce(unit,''))<>'') AS req_ok,
  CASE WHEN value_num IS NOT NULL AND isfinite(value_num) AND unit='C' THEN value_num
       WHEN value_num IS NOT NULL AND isfinite(value_num) AND unit='F' THEN (value_num-32)*5.0/9 END AS temp_c,
  coalesce(sensor_id IN (SELECT sensor_id FROM registry), false) AS ref_ok,
  coalesce(event_ts IS NOT NULL AND ingest_ts IS NOT NULL AND event_ts<=ingest_ts
           AND ingest_ts<=TIMESTAMP '2026-02-09 00:00:00', false) AS time_ok,
  CASE WHEN event_ts IS NOT NULL AND ingest_ts IS NOT NULL THEN epoch(ingest_ts)-epoch(event_ts) END AS lag_s
FROM winners w;
