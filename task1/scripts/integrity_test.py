import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "task1" / "snapshot"
EVIDENCE = ROOT / "task1" / "evidence" / "integrity-test.json"

TARGET = SNAPSHOT / "observations_a.csv"

# Gia tri SHA256 da xac minh trong local preflight
EXPECTED_SHA256 = (
    "5157418915d867980fac8d84551a8b856bba1669ca2e33cef91a15ee82101aea"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify(data, expected_hash):
    actual_hash = sha256(data)

    if actual_hash != expected_hash:
        return {
            "valid": False,
            "error_code": "INPUT_INTEGRITY",
            "actual_sha256": actual_hash
        }

    return {
        "valid": True,
        "error_code": None,
        "actual_sha256": actual_hash
    }


def main():
    if not TARGET.is_file():
        raise SystemExit(f"Missing input file: {TARGET}")

    original_bytes = TARGET.read_bytes()
    original_sha256 = sha256(original_bytes)

    # Phai xac minh file goc truoc khi thuc hien mutation
    if original_sha256 != EXPECTED_SHA256:
        raise SystemExit(
            "INPUT_INTEGRITY: original file does not match expected SHA256"
        )

    if not original_bytes:
        raise SystemExit("Input file is empty")

    with tempfile.TemporaryDirectory(prefix="lab2_i03_") as temp_dir:
        mutated_file = Path(temp_dir) / TARGET.name

        # Tao ban sao rieng, khong sua file goc
        mutated_file.write_bytes(original_bytes)

        # Thay doi dung mot byte
        with mutated_file.open("r+b") as file:
            original_byte = file.read(1)[0]
            file.seek(0)
            file.write(bytes([original_byte ^ 0x01]))

        mutated_bytes = mutated_file.read_bytes()

        result = verify(mutated_bytes, EXPECTED_SHA256)

        changed_bytes = sum(
            a != b for a, b in zip(original_bytes, mutated_bytes)
        )

        original_unchanged = (
            TARGET.read_bytes() == original_bytes
            and sha256(TARGET.read_bytes()) == EXPECTED_SHA256
        )

        detected = (
            result["valid"] is False
            and result["error_code"] == "INPUT_INTEGRITY"
        )

        passed = (
            detected
            and changed_bytes == 1
            and len(original_bytes) == len(mutated_bytes)
            and original_unchanged
        )

        evidence = {
            "test": "I03",
            "mode": "LOCAL_PREFLIGHT",
            "source_object": TARGET.name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mutation": {
                "type": "single_byte_flip",
                "byte_offset": 0,
                "changed_bytes": changed_bytes
            },
            "expected_sha256": EXPECTED_SHA256,
            "original_sha256": original_sha256,
            "mutated_sha256": result["actual_sha256"],
            "integrity_error": result["error_code"],
            "detected": detected,
            "original_unchanged": original_unchanged,
            "status": "LOCAL-PASS" if passed else "FAIL"
        }

        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print(json.dumps(evidence, indent=2, ensure_ascii=False))

        if not passed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
