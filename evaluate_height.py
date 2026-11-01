"""Evaluate independently labelled height scans; never train on self-reported height.

Usage: python evaluate_height.py validation.json
Input: [{"subject_id":"test-001", "estimated_cm":172.3,
         "measured_cm":172.8, "ground_truth_method":"stadiometer"}, ...]
"""
import json
import math
import statistics
import sys


def evaluate(records):
    if not records:
        raise ValueError('Supply independently measured validation scans.')
    errors = []
    subjects = set()
    repeated = {}
    for row in records:
        subject = row['subject_id']
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError('Use an anonymous nonempty subject ID.')
        if row.get('ground_truth_method') not in ('stadiometer', 'wall_and_tape'):
            raise ValueError('Ground truth must be independently measured, not entered or inferred height.')
        estimated, measured = row['estimated_cm'], row['measured_cm']
        for value in (estimated, measured):
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 60.96 <= value <= 254:
                raise ValueError('Height must be a finite number in cm, within the supported range.')
        subjects.add(subject)
        errors.append(estimated - measured)
        repeated.setdefault(subject, []).append(estimated)
    absolute = sorted(abs(e) for e in errors)
    repeat_spreads = [max(values) - min(values) for values in repeated.values() if len(values) > 1]
    return {'scan_count': len(records), 'subject_count': len(subjects),
            'mean_signed_error_cm': statistics.mean(errors),
            'mean_absolute_error_cm': statistics.mean(absolute),
            'p95_absolute_error_cm': absolute[max(0, math.ceil(0.95 * len(absolute)) - 1)],
            'max_absolute_error_cm': max(absolute),
            'within_one_inch_fraction': sum(e <= 2.54 + 1e-9 for e in absolute) / len(absolute),
            'subjects_with_repeat_scans': len(repeat_spreads),
            'mean_repeat_range_cm': statistics.mean(repeat_spreads) if repeat_spreads else None,
            'production_ready': False,
            'note': 'Descriptive evaluation only. This is not accuracy certification or model training.'}


if __name__ == '__main__':
    try:
        with open(sys.argv[1], encoding='utf-8') as source:
            print(json.dumps(evaluate(json.load(source)), indent=2, allow_nan=False))
    except (IndexError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Evaluation failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
