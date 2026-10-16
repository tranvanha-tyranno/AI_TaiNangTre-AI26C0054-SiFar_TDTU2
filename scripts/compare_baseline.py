"""Offline strict paired evaluation. Never imported by the solver."""
import argparse
import json
from pathlib import Path
from scripts.evaluate import read


def compare(baseline, candidate, reference):
    if set(baseline) != set(reference) or set(candidate) != set(reference):
        raise ValueError('Both predictions must have exactly the reference IDs; partial runs are not comparable.')
    groups = {key: [] for key in ('both_correct', 'gained', 'regressed', 'both_wrong')}
    for key, expected in reference.items():
        before, after = baseline[key] == expected, candidate[key] == expected
        group = 'both_correct' if before and after else 'regressed' if before else 'gained' if after else 'both_wrong'
        groups[group].append(key)
    return {'metric': 'strict exact match; not the official BTC normalizer',
            'total': len(reference),
            'baseline_correct': len(groups['both_correct']) + len(groups['regressed']),
            'candidate_correct': len(groups['both_correct']) + len(groups['gained']),
            'net_gain': len(groups['gained']) - len(groups['regressed']),
            'questions': groups,
            'note': 'One dataset/run does not establish generalization. Pair only matching data, model and run conditions.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'reference', 'report'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    report = compare(read(args.baseline), read(args.candidate), read(args.reference))
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'questions'}, ensure_ascii=True))


if __name__ == '__main__':
    main()
