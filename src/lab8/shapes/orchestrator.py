"""Shape C — orchestrator plus read-only investigators. Student work.

1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
   `lookup_refund_history` is a read-only tool you may hand to an investigator.
4. Trace the sanitized handoff, not the parent context.

An LLM summary of the parent context is not a sanitizer. Use the allowlist.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import dispatch, run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Run one claim using an orchestrator + read-only investigators."""
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    run_id = make_run_id("orchestrator", claim_id, seed)
    trace = Trace(run_id)

    def _done(
        status: str,
        proposal_amount: int,
        error_reason: str | None = None,
    ) -> RunResult:
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal_amount,
            budget=budget,
            trace=trace,
            error_reason=error_reason,
        )

    # 1. Read only the allowlisted claim view (never SELECT * / parent_secret / raw_headers).
    claim_view = dispatch(
        conn,
        budget,
        "get_claim_view",
        {"claim_id": claim_id},
        worker=False,
    )
    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return _done("failed", 0, "unknown_claim")

    trace.add(
        "claim_view",
        {
            "claim_id": claim_view["claim_id"],
            "has_order_id": bool(claim_view.get("order_id")),
        },
    )

    if not claim_view.get("order_id"):
        complete(budget, seed=seed, purpose="draft", prompt=f"claim={claim_id} status=needs_info")
        trace.add("decision", {"status": "needs_info", "reason": "missing_order_id"})
        return _done("needs_info", 0, "missing_order_id")

    # 2. Orchestrator plans and creates a typed, allowlist-sanitized handoff for read-only workers.
    complete(
        budget,
        seed=seed,
        purpose="plan",
        prompt=f"claim={claim_id} order={claim_view['order_id']}",
    )
    handoff = make_handoff(
        request_id=f"REQ-{run_id}",
        claim_id=claim_id,
        task="investigate_order_policy_and_refund_history",
        facts={},
        allowed_tools=["lookup_order", "lookup_policy", "lookup_refund_history"],
    )
    trace.add("handoff", safe_dump(handoff))

    investigated = _run_investigator(conn, budget, handoff, claim_view["principal_id"], trace)
    order_view = investigated["order_view"]
    if not order_view.get("visible"):
        reason = order_view.get("reason") or "outside_principal_scope"
        complete(budget, seed=seed, purpose="draft", prompt=f"claim={claim_id} status=escalated")
        trace.add("decision", {"status": "escalated", "reason": reason})
        return _done("escalated", 0, reason)

    # 3. Deterministic quote from structured order fields; ignore delay numbers in ticket text.
    order = dict(order_view["order"])
    quote_payload = dispatch(conn, budget, "compute_compensation", {"order": order}, worker=False)
    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", safe_dump(quote_payload))

    if proposal <= 0:
        reason = quote_payload.get("reason") or "no_entitlement"
        complete(budget, seed=seed, purpose="draft", prompt=f"claim={claim_id} status=denied")
        trace.add("decision", {"status": "denied", "reason": reason})
        return _done("denied", 0, reason)

    # 4. Write boundary stays in the orchestrator; pass full quote so the host applies per-order cap.
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    trace.add("refund_outcome", safe_dump(outcome))
    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        if status == "denied":
            complete(budget, seed=seed, purpose="draft", prompt=f"claim={claim_id} status=denied")
        return _done(status, proposal, outcome["reason"])

    complete(
        budget,
        seed=seed,
        purpose="draft",
        prompt=f"claim={claim_id} status=resolved proposal={proposal}",
    )
    return _done("resolved", proposal, None)


def _run_investigator(
    conn: sqlite3.Connection,
    budget: Budget,
    handoff: dict[str, Any],
    principal_id: str,
    trace: Trace,
) -> dict[str, Any]:
    investigated = run_readonly_investigators(
        conn,
        budget,
        handoff,
        principal_id=principal_id,
    )
    tools_out = investigated["tools"]
    order_view = tools_out.get("lookup_order") or {}
    history_view = tools_out.get("lookup_refund_history") or {}
    policy_view = tools_out.get("lookup_policy") or {}
    trace.add(
        "investigator",
        {
            "lookup_order": safe_dump(order_view),
            "lookup_refund_history": safe_dump(history_view),
            "policy_count": len(policy_view.get("policies") or []),
        },
    )
    return {"order_view": order_view, "history_view": history_view, "policy_view": policy_view}
