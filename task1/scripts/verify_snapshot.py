import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET = "research-raw"
PREFIX = "lab2/inputs/batch-01/"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    snapshot_dir = Path(args.snapshot)
    evidence_path = Path(args.evidence)

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client(
        "s3",
        endpoint_url="http://objects:8333",
        region_name="us-east-1",
        aws_access_key_id=os.environ["accessKey"],
        aws_secret_access_key=os.environ["secretKey"],
        config=Config(s3={"addressing_style": "path"})
    )

    results = []
    expected_objects = manifest["objects"]

    for item in expected_objects:
        filename = item["key"]
        key = PREFIX + filename
        destination = snapshot_dir / filename

        result = {
            "source_bucket": BUCKET,
            "source_key": key,
            "expected_bytes": item["bytes"],
            "expected_sha256": item["sha256"],
            "status": "FAIL",
        }

        try:
            response = s3.get_object(Bucket=BUCKET, Key=key)

            digest = hashlib.sha256()
            byte_count = 0

            with destination.open("wb") as output:
                for chunk in response["Body"].iter_chunks(chunk_size=65536):
                    if not chunk:
                        continue
                    output.write(chunk)
                    digest.update(chunk)
                    byte_count += len(chunk)

            actual_hash = digest.hexdigest()

            result["http"] = response["ResponseMetadata"]["HTTPStatusCode"]
            result["actual_bytes"] = byte_count
            result["actual_sha256"] = actual_hash
            result["snapshot_path"] = str(destination)

            if (
                byte_count == item["bytes"]
                and actual_hash == item["sha256"]
                and result["http"] == 200
            ):
                result["status"] = "PASS"
            else:
                result["error"] = "INPUT_INTEGRITY"
                destination.unlink(missing_ok=True)

        except (ClientError, OSError) as exc:
            result["error"] = str(exc)
            destination.unlink(missing_ok=True)

        results.append(result)
        print(filename, result["status"])

    overall_pass = (
        len(results) == 4
        and all(item["status"] == "PASS" for item in results)
    )

    evidence = {
        "test_id": "I01",
        "status": "PASS" if overall_pass else "FAIL",
        "timestamp_utc": utc_now(),
        "fixture_version": manifest["fixture_version"],
        "as_of": manifest["as_of"],
        "bucket": BUCKET,
        "prefix": PREFIX,
        "objects": results,
    }

    evidence_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("OVERALL:", evidence["status"])
    print("EVIDENCE:", evidence_path)

    if not overall_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
