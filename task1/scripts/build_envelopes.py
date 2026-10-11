import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "task1" / "snapshot"
OUTPUT = ROOT / "task1" / "observation_envelopes.jsonl"
EVIDENCE = ROOT / "task1" / "evidence"

EVIDENCE.mkdir(parents=True, exist_ok=True)

CSV_MAPPING = {
    "record_id": "record_id",
    "sensor_id": "sensor_id",
    "event_time": "event_time",
    "ingest_time": "ingest_time",
    "reading": "reading",
    "unit": "unit",
    "operator_email": "operator_email"
}

JSON_MAPPING = {
    "id": "record_id",
    "sensor": "sensor_id",
    "timestamp": "event_time",
    "arrived_at": "ingest_time",
    "temperature": "reading",
    "temperature_unit": "unit",
    "operator": "operator_email"
}

counts = {
    "observations_a.csv": 0,
    "observations_b.jsonl": 0
}

physical_keys = set()
malformed_count = 0
total = 0


def normalize(record, mapping):
    return {
        canonical: record.get(source)
        for source, canonical in mapping.items()
    }


def write_envelope(output, envelope):
    global total

    key = (
        envelope["source_object"],
        envelope["source_row"]
    )

    if key in physical_keys:
        raise RuntimeError(f"Duplicate physical key: {key}")

    physical_keys.add(key)

    output.write(
        json.dumps(envelope, ensure_ascii=False) + "\n"
    )

    total += 1


with OUTPUT.open("w", encoding="utf-8") as output:

    csv_path = SNAPSHOT / "observations_a.csv"

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row_number, record in enumerate(reader, start=1):

            envelope = {
                "source_object": csv_path.name,
                "source_row": row_number,
                "parse_ok": True,
                "canonical": normalize(record, CSV_MAPPING)
            }

            write_envelope(output, envelope)

            counts[csv_path.name] += 1

    json_path = SNAPSHOT / "observations_b.jsonl"

    with json_path.open(
        "r",
        encoding="utf-8-sig"
    ) as file:

        for line_number, line in enumerate(file, start=1):

            try:
                record = json.loads(line)

                if not isinstance(record, dict):
                    raise ValueError("Expected JSON object")

                envelope = {
                    "source_object": json_path.name,
                    "source_row": line_number,
                    "parse_ok": True,
                    "canonical": normalize(record, JSON_MAPPING)
                }

            except (json.JSONDecodeError, ValueError) as error:

                malformed_count += 1

                envelope = {
                    "source_object": json_path.name,
                    "source_row": line_number,
                    "parse_ok": False,
                    "parse_error": str(error),
                    "raw_line": line.rstrip("\r\n"),
                    "canonical": None
                }

            write_envelope(output, envelope)

            counts[json_path.name] += 1


expected_total = sum(counts.values())

status = (
    "LOCAL-PASS"
    if (
        total == expected_total
        and len(physical_keys) == total
        and counts["observations_a.csv"] == 5000
        and counts["observations_b.jsonl"] == 5205
        and malformed_count == 5
    )
    else "FAIL"
)

result = {
    "test": "I02",
    "mode": "LOCAL_PREFLIGHT",
    "source_counts": counts,
    "total_envelopes": total,
    "unique_physical_keys": len(physical_keys),
    "malformed_jsonl_preserved": malformed_count,
    "status": status
}

evidence_path = EVIDENCE / "I02.json"

evidence_path.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print(json.dumps(result, indent=2, ensure_ascii=False))

if status != "LOCAL-PASS":
    raise SystemExit("I02 FAILED")
