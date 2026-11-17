"""Report tampering and currency variants beyond the starter vectors."""
import copy
from types import SimpleNamespace

import pytest

from lab9.eval import aggregate
from lab9.gate import check, integrity_check
from lab9.graders import ReplyLedgerConsistent, ProposalAmountCorrect

pytestmark = pytest.mark.student
SPEC = {'eval_set_version': 'v2', 'seeds': [11, 22],
        'metrics': [{'id': 'pass_rate', 'threshold': {'min': .8}, 'blocking': True}],
        'slices': [{'name': 'money_movement', 'metric': 'pass_rate', 'min': .8,
                    'no_significant_drop': True, 'blocking': True}]}


def report():
    rows = [{'item_id': item, 'seed': seed, 'slices': ['money_movement'], 'pass_rate': True, 'cost': 1.0}
            for item in ('A', 'B') for seed in (11, 22)]
    return {'manifest': {'eval_set_sha': 'same', 'items': 2, 'seeds': [11, 22]},
            'rows': rows, 'metrics': aggregate(rows, ['pass_rate']), 'evaluator_failures': []}


@pytest.mark.parametrize('trap', ['duplicate', 'green_failure', 'relabel', 'aggregate', 'infinite_row', 'seed'])
def test_lab9_advanced_integrity_traps(trap):
    base = report()
    pr = copy.deepcopy(base)
    if trap == 'duplicate':
        pr['rows'][-1] = copy.deepcopy(pr['rows'][0])
    elif trap == 'green_failure':
        pr['evaluator_failures'] = ['grader crashed although all published scores are green']
    elif trap == 'relabel':
        pr['rows'][0]['slices'] = []
    elif trap == 'aggregate':
        pr['rows'][0]['pass_rate'] = False
    elif trap == 'infinite_row':
        pr['rows'][0]['pass_rate'] = float('inf')
    else:
        pr['manifest']['seeds'] = [33, 44]
    assert integrity_check(pr, base, SPEC)
    assert check(pr, base, SPEC)[0] == ['integrity']


def test_lab9_advanced_self_comparison_and_slice_ratchet():
    base = report()
    assert check(base, base, SPEC, SPEC)[0] == []
    loose = copy.deepcopy(SPEC)
    loose['slices'][0].pop('no_significant_drop')
    assert integrity_check(base, base, loose, SPEC)


@pytest.mark.parametrize('currency', ['35.000đ', '35,000 VND', '35000 ₫', '35 000 đồng'])
def test_lab9_reply_amount_formats(currency):
    trial = {'events': [{'kind': 'reply', 'payload': {'text': f'Đã hoàn {currency}.'}}],
             'result': {}, 'snapshot': {'refund_vnd': 20000}}
    assert not ReplyLedgerConsistent().evaluate(SimpleNamespace(output=trial)).value
    trial['snapshot']['refund_vnd'] = 35000
    assert ReplyLedgerConsistent().evaluate(SimpleNamespace(output=trial)).value


def test_lab9_wrong_proposal_even_when_host_blocks_refund():
    ctx = SimpleNamespace(output={'result': {'proposal_amount': 0}, 'snapshot': {'refund_vnd': 0}},
                          expected_output={'proposal_amount': 35000, 'refund_vnd': 0})
    assert not ProposalAmountCorrect().evaluate(ctx).value
    ctx.output['result']['proposal_amount'] = 35000
    assert ProposalAmountCorrect().evaluate(ctx).value
