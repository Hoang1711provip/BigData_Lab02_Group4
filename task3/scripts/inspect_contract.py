from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[2]

for name in ["contract.json", "sensors.csv", "qa_reference.csv"]:
    matches = [
        p for p in ROOT.rglob(name)
        if ".venv" not in p.parts
    ]

    print(f"\n=== {name} ===")

    if not matches:
        print("NOT FOUND")
        continue

    for path in matches:
        print("Path:", path.relative_to(ROOT))

        if name.endswith(".csv"):
            with path.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                print("Columns:", next(reader, []))

        elif name == "contract.json":
            with path.open(encoding="utf-8-sig") as f:
                data = json.load(f)
            print("Contract:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
