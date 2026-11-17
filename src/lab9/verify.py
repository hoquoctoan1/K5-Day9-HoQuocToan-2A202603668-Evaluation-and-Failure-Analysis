"""Reproduce submission evidence with real CLI exit codes; run from src/."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

from lab8.console import utf8_stdio


def main():
    utf8_stdio()
    evidence = Path('../docs/evidence')
    evidence.mkdir(parents=True, exist_ok=True)
    commands = [
        ('smoke', 0, ['lab9.smoke']),
        ('dependencies', 0, ['pip', 'check']),
        ('build_v1', 0, ['lab9.evalset', '--build', '--check']),
        ('build_v2', 0, ['lab9.evalset', '--v2', '--build']),
        ('tests_core', 0, ['pytest', '-q', '-m', 'student', '-o', 'addopts=', '-k', 'lab9 and not advanced']),
        ('tests_advanced', 0, ['pytest', '-q', '-m', 'student', '-o', 'addopts=', '-k', 'advanced']),
        ('judge_tone', 0, ['lab9.judge', '--csv', 'data/eval/judge_tone_public.csv', '--audit', '10']),
        ('judge_helpful', 1, ['lab9.judge', '--csv', 'data/eval/judge_helpful_public.csv', '--audit', '5']),
        ('taxonomy', 0, ['lab9.taxonomy_audit']),
        ('trace_broken', 0, ['lab9.trace_case', '--shape', 'seeded_regression', '--claim', 'C-002', '--seed', '11']),
        ('trace_fixed', 0, ['lab9.trace_case', '--shape', 'fixed', '--claim', 'C-002', '--seed', '11']),
    ]
    for shape, out in [('swarm', 'baseline_v1'), ('swarm', 'eval_pr'), ('fixed', 'eval_fixed'), ('seeded_regression', 'eval_seeded_regression')]:
        commands.append((out, 0, ['lab9.eval', '--shape', shape, '--out', f'reports/{out}.json']))
    commands.append(('ci_check', 0, ['lab9.ci_check', '--pr', 'reports/eval_pr.json', '--baseline', 'reports/baseline_v1.json']))
    for shape, expected in [('pr', 0), ('fixed', 0), ('seeded_regression', 1)]:
        commands.append((f'gate_{shape}', expected, ['lab9.gate', '--pr', f'reports/eval_{shape}.json', '--baseline', 'reports/baseline_v1.json']))
    commands += [
        ('detection', 0, ['lab9.mutation', '--detect']),
        ('baseline_v2', 0, ['lab9.eval', '--shape', 'swarm', '--spec', 'config/metric_spec_v2.yaml', '--out', 'reports/baseline_v2.json']),
        ('aa', 0, ['lab9.mutation', '--spec', 'config/metric_spec_v2.yaml', '--aa', '66,77,88,99,110']),
        ('scorecard', 0, ['lab9.mutation', '--spec', 'config/metric_spec_v2.yaml', '--baseline', 'reports/baseline_v2.json']),
        ('slice_regression', 0, ['lab9.eval', '--shape', 'slice_regression', '--spec', 'config/metric_spec_v2.yaml', '--out', 'reports/eval_slice_regression.json']),
        ('traps', 0, ['lab9.traps', '--pr', 'reports/eval_slice_regression.json', '--baseline', 'reports/baseline_v2.json', '--spec', 'config/metric_spec_v2.yaml']),
        ('self_v2', 0, ['lab9.gate', '--pr', 'reports/baseline_v2.json', '--baseline', 'reports/baseline_v2.json', '--spec', 'config/metric_spec_v2.yaml', '--base-spec', 'config/metric_spec_v2.yaml']),
    ]
    # Exercise every trap through the real CLI as well as the traps API.
    for trap in ['evaluator_errors_as_nan', 'dropped_failing_rows', 'cherry_picked_seeds', 'loosened_spec']:
        args = ['lab9.gate', '--pr', f'reports/traps/{trap}.json', '--baseline', 'reports/baseline_v2.json', '--spec', f'reports/traps/{trap}.spec.yaml' if trap == 'loosened_spec' else 'config/metric_spec_v2.yaml']
        if trap == 'loosened_spec':
            args += ['--base-spec', 'config/metric_spec_v2.yaml']
        commands.append((f'trap_{trap}', 1, args))
    results = []
    for name, expected, args in commands:
        print(f'Running {name}...', flush=True)
        proc = subprocess.run([sys.executable, '-X', 'utf8', '-m', *args], env={**os.environ, 'PYTHONUTF8': '1'}, capture_output=True, text=True, encoding='utf-8')
        (evidence / f'{name}.txt').write_text(f"python -m {' '.join(args)}\nexit_code={proc.returncode}; expected={expected}\n\n{proc.stdout}{proc.stderr}", encoding='utf-8')
        results.append({'name': name, 'args': args, 'exit_code': proc.returncode, 'expected': expected, 'ok': proc.returncode == expected})
        (evidence / 'validation.json').write_text(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'results': results}, indent=2), encoding='utf-8')
        print(f'{name}: exit {proc.returncode} (expected {expected})', flush=True)
        if proc.returncode != expected:
            print(proc.stdout + proc.stderr)
            return 1
    print('All local submission checks matched their expected exit codes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
