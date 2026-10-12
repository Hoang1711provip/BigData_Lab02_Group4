SET threads = 2;
SET memory_limit = '512MB';

CREATE OR REPLACE TEMP TABLE raw_envelopes AS
SELECT *
FROM read_json_auto(
    'task1/observation_envelopes.jsonl',
    format = 'newline_delimited'
);

SELECT COUNT(*) AS total_raw
FROM raw_envelopes;

DESCRIBE raw_envelopes;
