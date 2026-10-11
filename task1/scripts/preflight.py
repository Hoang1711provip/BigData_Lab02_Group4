from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "input"

EXPECTED = {
    "observations_a.csv": (
        421028,
        "5157418915d867980fac8d84551a8b856bba1669ca2e33cef91a15ee82101aea"
    ),
    "observations_b.jsonl": (
        1037439,
        "3072ad0b725ea3763ad4d1a7c744465f997614892dd1460f9cd815094ec61b70"
    ),
    "qa_reference.csv": (
        1423,
        "129463c2a4e63f2dabfa2a5dd31b92e4fe4858d2415d3c7ef495cc6c6d7b65c2"
    ),
    "sensors.csv": (
        256,
        "02c390e127c37b9d12e9ca156eae23a450ad1ae037001cddd9651bb6516b9bde"
    )
}

results = []

for name, (expected_size, expected_hash) in EXPECTED.items():
    path = INPUT / name

    if not path.exists():
        results.append({
            "file": name,
            "status": "MISSING"
        })
        continue

    content = path.read_bytes()
    actual_hash = hashlib.sha256(content).hexdigest()

    results.append({
        "file": name,
        "bytes": len(content),
        "sha256": actual_hash,
        "status": (
            "MATCH"
            if len(content) == expected_size
            and actual_hash == expected_hash
            else "MISMATCH"
        )
    })

print(json.dumps(results, indent=2))

if not all(item["status"] == "MATCH" for item in results):
    raise SystemExit("PREFLIGHT FAILED")

print("LOCAL INPUT PREFLIGHT PASSED")
