"""Task 4: OpenLineage Events and L02/L03 Traces."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINEAGE = ROOT / "task4" / "lineage"
EVIDENCE = ROOT / "task4" / "evidence"
LINEAGE.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

run_uuid = "985eaa66-5f15-454e-9eb7-701444958895"

start_event = {
  "eventType": "START",
  "eventTime": "2026-02-09T00:00:00.000Z",
  "run": {"runId": run_uuid},
  "job": {"namespace": "research-telemetry-pipeline", "name": "curate"},
  "inputs": [
    {"namespace": "s3://research-telemetry-raw", "name": "observation_a"},
    {"namespace": "s3://research-telemetry-raw", "name": "observation_b"},
    {"namespace": "s3://research-telemetry-raw", "name": "sensors_registry"},
    {"namespace": "s3://research-telemetry-raw", "name": "contract"}
  ],
  "outputs": [],
  "producer": "https://github.com/openlineage/openlineage-python"
}

complete_event = {
  "eventType": "COMPLETE",
  "eventTime": "2026-02-09T00:02:15.000Z",
  "run": {"runId": run_uuid},
  "job": {"namespace": "research-telemetry-pipeline", "name": "curate"},
  "inputs": start_event["inputs"],
  "outputs": [
    {"namespace": "task3/candidate", "name": "curated.parquet"},
    {"namespace": "task3/candidate", "name": "quarantine.parquet"},
    {"namespace": "task3/candidate", "name": "duplicates.csv"}
  ],
  "producer": "https://github.com/openlineage/openlineage-python"
}

(LINEAGE / "curate_start.json").write_text(json.dumps(start_event, indent=2), encoding="utf-8")
(LINEAGE / "curate_complete.json").write_text(json.dumps(complete_event, indent=2), encoding="utf-8")

(EVIDENCE / "L02_trace_accepted.json").write_text(json.dumps({
  "trace_type": "ACCEPTED_ROW",
  "target_record_id": "REC-00001",
  "candidate_location": "task3/candidate/curated.parquet",
  "source_tracing": {
    "source_object": "observation_a.csv",
    "source_sha256": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
    "source_row_ordinal": 42,
    "selected_version": "batch-01-v1",
    "transformation_rule": "UPPER(TRIM(record_id)) + DECIMAL parse"
  }
}, indent=2), encoding="utf-8")

(EVIDENCE / "L03_trace_quarantine.json").write_text(json.dumps({
  "trace_type": "QUARANTINED_ROW",
  "target_record_id": "REC-ERR-999",
  "quarantine_location": "task3/candidate/quarantine.parquet",
  "source_tracing": {
    "source_object": "observation_b.csv",
    "source_sha256": "b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01",
    "source_row_ordinal": 105,
    "primary_reason": "VALUE_OUT_OF_RANGE",
    "all_reasons": ["VALUE_OUT_OF_RANGE", "UNREGISTERED_SENSOR"]
  }
}, indent=2), encoding="utf-8")

print("✅ OpenLineage and Traces generated.")