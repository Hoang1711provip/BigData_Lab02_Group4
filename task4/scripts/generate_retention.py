"""Task 4: Generate retention-plan.json with 4 dry-run decisions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK4 = ROOT / "task4"

retention_plan = {
    "policy_version": "1.0.0",
    "course_policies": {
        "raw_input": "30 days from retrieval",
        "quarantine": "7 days from run completion",
        "approved_release": "90 days from publication"
    },
    "dry_run_cases": [
        {
            "case_id": "DRY_RUN_01",
            "description": "Expired scratch object; no hold; no dependent release.",
            "expected_result": "ELIGIBLE",
            "reason": "Object expired and has no active hold or downstream dependencies."
        },
        {
            "case_id": "DRY_RUN_02",
            "description": "Expired quarantine object under hold.",
            "expected_result": "KEEP / HOLD",
            "reason": "Expiration overridden by an active legal or debugging hold."
        },
        {
            "case_id": "DRY_RUN_03",
            "description": "Expired raw input referenced by an active approved release.",
            "expected_result": "KEEP / ACTIVE_DEPENDENCY",
            "reason": "Expiration overridden because an active approved release depends on this raw input."
        },
        {
            "case_id": "DRY_RUN_04",
            "description": "Unexpired object, no hold or dependency.",
            "expected_result": "KEEP / NOT_EXPIRED",
            "reason": "Retention duration has not yet elapsed."
        }
    ]
}

retention_file = TASK4 / "retention-plan.json"
retention_file.write_text(json.dumps(retention_plan, indent=2), encoding="utf-8")
print(f"✅ Created {retention_file}")