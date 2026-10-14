"""Compare CSV answers exactly; the reference is not used by the solver."""
import argparse
import csv
import json
from pathlib import Path


def read(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["id", "answer"]:
            raise ValueError(f"Invalid CSV header: {path}")
        rows = list(reader)
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError(f"Duplicate IDs: {path}")
    return {row['id']: row['answer'] for row in rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--report", default="outputs/evaluation.json")
    args = parser.parse_args()
    predicted, expected = read(args.prediction), read(args.reference)
    mismatches = [{"id": key, "expected": value, "actual": predicted.get(key)}
                  for key, value in expected.items() if predicted.get(key) != value]
    extra = sorted(set(predicted) - set(expected))
    report = {"reference_kind": "provided sample; not independently verified gold",
              "correct": len(expected) - len(mismatches), "total": len(expected),
              "exact_match": (len(expected) - len(mismatches)) / max(1, len(expected)),
              "mismatches": mismatches, "extra_ids": extra}
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return int(bool(mismatches or extra))


if __name__ == "__main__":
    raise SystemExit(main())
