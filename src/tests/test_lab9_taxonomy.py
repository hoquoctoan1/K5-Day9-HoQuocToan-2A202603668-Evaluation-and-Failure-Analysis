"""Trace-derived regression checks, independent of output wording."""
from types import SimpleNamespace

import pytest

from lab8.shapes import SHAPES
from lab9.graders import ReplyLedgerConsistent
from lab9.taxonomy_audit import CASES
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

pytestmark = pytest.mark.student


@pytest.mark.parametrize('fm,bug,claim', CASES)
def test_lab9_trace_failure_and_fixed_control(fm, bug, claim):
    shape = f'test_taxonomy_{bug}'
    SHAPES[shape] = make_shape(shape, {'no_override', bug})
    bad = investigate(shape, claim, 11)
    good = investigate('fixed', claim, 11)
    assert good['trial']['lab8_pass'], good['trial']['lab8_reason']
    if fm == 'FM-09':
        # Public fixture demonstrates prevention, not a successful cross-principal leak.
        assert bad['trial']['lab8_pass']
        assert bad['trial']['result']['status'] == 'escalated'
        assert bad['trial']['snapshot']['refund_vnd'] == 0
    elif fm == 'FM-08':
        assert bad['trial']['lab8_pass']  # documents the existing grader's blind spot
        assert not ReplyLedgerConsistent().evaluate(SimpleNamespace(output=bad['trial'])).value
        assert ReplyLedgerConsistent().evaluate(SimpleNamespace(output=good['trial'])).value
    else:
        assert not bad['trial']['lab8_pass'], (fm, bug, claim)
