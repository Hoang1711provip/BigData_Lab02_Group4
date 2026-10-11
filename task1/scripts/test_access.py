import os
import json
import uuid
import boto3

from datetime import datetime, timezone
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET_RAW = "research-raw"
BUCKET_RELEASE = "research-release"
RAW_KEY = "lab2/inputs/batch-01/sensors.csv"

s3 = boto3.client(
    "s3",
    endpoint_url="http://objects:8333",
    region_name="us-east-1",
    aws_access_key_id=os.environ["accessKey"],
    aws_secret_access_key=os.environ["secretKey"],
    config=Config(s3={"addressing_style": "path"})
)

evidence = {
    "test_id": "I04",
    "principal": "ingestor",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "tests": [],
    "status": "FAIL"
}

# I04-A: GET research-raw
try:
    response = s3.get_object(
        Bucket=BUCKET_RAW,
        Key=RAW_KEY
    )

    data = response["Body"].read()
    http = response["ResponseMetadata"]["HTTPStatusCode"]

    passed = http == 200 and len(data) == 256

    evidence["tests"].append({
        "name": "GET_RAW",
        "bucket": BUCKET_RAW,
        "key": RAW_KEY,
        "http": http,
        "bytes": len(data),
        "status": "PASS" if passed else "FAIL"
    })

    print("GET RAW:", http, "PASS" if passed else "FAIL")

except ClientError as e:
    http = e.response["ResponseMetadata"]["HTTPStatusCode"]
    code = e.response["Error"]["Code"]

    evidence["tests"].append({
        "name": "GET_RAW",
        "bucket": BUCKET_RAW,
        "key": RAW_KEY,
        "http": http,
        "error": code,
        "status": "FAIL"
    })

    print("GET RAW:", http, code, "FAIL")


# I04-B: PUT research-release
# Dùng key ngẫu nhiên để tránh ghi đè dữ liệu release.
probe_key = "lab2/access-probes/i04-" + uuid.uuid4().hex + ".txt"

try:
    response = s3.put_object(
        Bucket=BUCKET_RELEASE,
        Key=probe_key,
        Body=b"I04 access boundary probe"
    )

    http = response["ResponseMetadata"]["HTTPStatusCode"]

    evidence["tests"].append({
        "name": "PUT_RELEASE",
        "bucket": BUCKET_RELEASE,
        "key": probe_key,
        "http": http,
        "status": "FAIL",
        "error": "WRITE_UNEXPECTEDLY_ALLOWED"
    })

    print("PUT RELEASE:", http, "FAIL - WRITE ALLOWED")

except ClientError as e:
    http = e.response["ResponseMetadata"]["HTTPStatusCode"]
    code = e.response["Error"]["Code"]

    passed = http == 403 and code == "AccessDenied"

    evidence["tests"].append({
        "name": "PUT_RELEASE",
        "bucket": BUCKET_RELEASE,
        "key": probe_key,
        "http": http,
        "error": code,
        "status": "PASS" if passed else "FAIL"
    })

    print("PUT RELEASE:", http, code, "PASS" if passed else "FAIL")


evidence["status"] = (
    "PASS"
    if len(evidence["tests"]) == 2
    and all(t["status"] == "PASS" for t in evidence["tests"])
    else "FAIL"
)

with open("/tmp/I04.json", "w", encoding="utf-8") as f:
    json.dump(evidence, f, indent=2)

print("OVERALL:", evidence["status"])
print("EVIDENCE: /tmp/I04.json")

if evidence["status"] != "PASS":
    raise SystemExit(1)
