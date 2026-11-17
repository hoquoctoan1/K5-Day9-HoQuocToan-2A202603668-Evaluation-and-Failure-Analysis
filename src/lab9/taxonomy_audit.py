"""Replay isolated failure switches against fixed; write reproducible M1 evidence.

Run from src: python -m lab9.taxonomy_audit
Does not alter Lab 8, the public variants, or their graders.
"""
from __future__ import annotations

import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab8.shapes import SHAPES
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

CASES = [
    ('FM-01', 'leaky_trace', 'C-001'),
    ('FM-02', 'ignore_denied', 'C-007'),
    ('FM-03', 'ticket_trust', 'C-002'),
    ('FM-04', 'sum_parts', 'C-014'),
    ('FM-04', 'round_down', 'C-001'),
    ('FM-05', 'pre_deducted', 'C-014'),
    ('FM-06', 'stale_clause', 'C-006'),
    ('FM-07', 'sibling_refund', 'C-010'),
    ('FM-08', 'misreport', 'C-008'),
    ('FM-09', 'extra_lookup', 'C-005'),  # negative control: scope boundary must hold
]


def main():
    utf8_stdio()
    evidence = []
    for fm, bug, claim in CASES:
        shape = f'audit_{bug}'
        SHAPES[shape] = make_shape(shape, {'no_override', bug})
        bad = investigate(shape, claim, 11)
        good = investigate('fixed', claim, 11)
        evidence.append({'fm': fm, 'bug': bug, 'claim': claim, 'seed': 11,
                         'variant': bad, 'fixed': good})
        t, g = bad['trial'], good['trial']
        print(f"{fm} {bug} {claim}@11: variant={'PASS' if t['lab8_pass'] else 'FAIL'} ({t['lab8_reason']}), fixed={'PASS' if g['lab8_pass'] else 'FAIL'}")
        print(f" ledger {t['snapshot']} unexpected={t['unexpected_rows']}")
        for i, e in enumerate(t['events'], 1):
            # Do not repeat secret values in the console.
            payload = '<redacted: contains claim secrets>' if e['kind'] == 'debug_claim_row' else json.dumps(e.get('payload'), ensure_ascii=False)
            print(f" {i} {e['kind']}: {payload}")
    out = Path('../docs/taxonomy_evidence.json')
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {out}')
    return int(any(e['fixed']['trial']['lab8_pass'] is not True for e in evidence))


if __name__ == '__main__':
    raise SystemExit(main())
