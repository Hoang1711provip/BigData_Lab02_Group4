import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

root = Path.cwd()

schema = json.loads(
    (root / "schemas/observation_contract_schema.json").read_text(encoding="utf-8-sig")
)
contract = json.loads(
    (root / "contracts/contract.json").read_text(encoding="utf-8-sig")
)

validator = Draft202012Validator(schema, format_checker=FormatChecker())
errors = list(validator.iter_errors(contract))

if errors:
    for error in errors:
        print("FAIL:", error.message)
    raise SystemExit(1)

print("PASS: contract.json matches observation_contract_schema.json")
