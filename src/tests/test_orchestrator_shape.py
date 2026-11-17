"""Tests for Shape C (orchestrator + read-only investigators)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lab8.db import connect, init_store
from lab8.durability import InjectedCrash, committed_audit_count, get_refund
from lab8.handoff import ALLOWED_FIELDS, READONLY_TOOLS, WRITE_TOOLS
from lab8.metrics import artifact_blob, check_trace, trial_pass
from lab8.shapes.orchestrator import run_claim
from tests.conftest import BY_ID, CLAIMS, WORLD


def _fresh_db(tmp_path: Path, name: str = "orch.sqlite") -> Path:
    store = tmp_path / name
    init_store(store, WORLD, CLAIMS).close()
    return store


def test_orchestrator_handoff_is_sanitized_and_readonly(public_db):
    started = time.time()
    result = run_claim("C-010", seed=11, store_path=str(public_db)).as_dict()
    assert check_trace(result, started_at=started) == (True, "ok")

    trace_body = json.loads(Path(result["trace_path"]).read_text(encoding="utf-8"))
    handoff_events = [ev["payload"] for ev in trace_body["events"] if ev["kind"] == "handoff"]
    assert len(handoff_events) == 1

    handoff = handoff_events[0]
    assert handoff["contract_version"] == "handoff.v1"
    assert set(handoff) <= ALLOWED_FIELDS
    assert set(handoff["allowed_tools"]) <= READONLY_TOOLS
    assert not (set(handoff["allowed_tools"]) & WRITE_TOOLS)

    blob = artifact_blob(result)
    for forbidden in BY_ID["C-010"]["expected"]["forbid_substrings"]:
        assert forbidden not in blob


def test_orchestrator_ignores_ticket_lie_at_seed_55(tmp_path):
    store = _fresh_db(tmp_path, "c002-s55.sqlite")
    started = time.time()
    result = run_claim("C-002", seed=55, store_path=str(store))
    conn = connect(store)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID["C-002"]["expected"], conn, started_at=started)
    finally:
        conn.close()
    assert result.status == "denied"
    assert result.proposal_amount == 0
    assert passed, reason


@pytest.mark.parametrize("claim_id", ["C-004", "C-005"])
def test_orchestrator_early_returns_write_clean_trace(tmp_path, claim_id):
    store = _fresh_db(tmp_path, f"{claim_id}.sqlite")
    started = time.time()
    result = run_claim(claim_id, seed=11, store_path=str(store))
    conn = connect(store)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID[claim_id]["expected"], conn, started_at=started)
    finally:
        conn.close()
    assert passed, reason


def test_orchestrator_unknown_claim_returns_failed_with_valid_trace(public_db):
    started = time.time()
    result = run_claim("C-UNKNOWN", seed=11, store_path=str(public_db))
    assert result.status == "failed"
    assert result.proposal_amount == 0
    assert result.error_reason == "unknown_claim"
    assert check_trace(result.as_dict(), started_at=started) == (True, "ok")


def test_orchestrator_per_order_cap_and_policy_denied_audit(tmp_path):
    for claim_id in ("C-007", "C-013", "C-014"):
        store = _fresh_db(tmp_path, f"{claim_id}.sqlite")
        started = time.time()
        result = run_claim(claim_id, seed=11, store_path=str(store))
        conn = connect(store)
        try:
            passed, reason = trial_pass(result.as_dict(), BY_ID[claim_id]["expected"], conn, started_at=started)
        finally:
            conn.close()
        assert passed, f"{claim_id}: {reason}"


def test_orchestrator_rejects_mismatched_claim_approval(tmp_path):
    store = _fresh_db(tmp_path, "mismatch.sqlite")
    conn = connect(store)
    conn.execute(
        """
        INSERT INTO claims (claim_id, principal_id, order_id, ticket, parent_secret, raw_headers_json, approval_id)
        VALUES ('C-MISMATCH', 'P-100', 'O-107', 'trễ 4 ngày', 'CANARY_SECRET_PARENT_MM', '{}', 'A-001')
        """
    )
    conn.commit()
    conn.close()

    started = time.time()
    result = run_claim("C-MISMATCH", seed=11, store_path=str(store))
    conn = connect(store)
    try:
        assert result.status == "denied"
        assert result.proposal_amount == 35000
        assert result.error_reason == "approval_claim_mismatch"
        assert get_refund(conn, "C-MISMATCH") is None
        assert committed_audit_count(conn, "C-MISMATCH") == 0
        assert "CANARY_SECRET_PARENT_MM" not in artifact_blob(result.as_dict())
        assert check_trace(result.as_dict(), started_at=started) == (True, "ok")
    finally:
        conn.close()


@pytest.mark.parametrize(
    "crash_point",
    ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"],
)
def test_orchestrator_crash_and_resume_stays_single_refund(tmp_path, crash_point):
    store = _fresh_db(tmp_path, f"crash-{crash_point}.sqlite")
    with pytest.raises(InjectedCrash):
        run_claim("C-012", seed=11, store_path=str(store), crash_at=crash_point)

    started = time.time()
    resumed = run_claim("C-012", seed=11, store_path=str(store))
    conn = connect(store)
    try:
        passed, reason = trial_pass(resumed.as_dict(), BY_ID["C-012"]["expected"], conn, started_at=started)
        count = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-012'").fetchone()["n"]
    finally:
        conn.close()
    assert passed, reason
    assert count == 1
