"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import Decide, ToolRejected, run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.trace import Trace

SHAPE = "single"
MAX_STEPS = 8


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _make_decide(facts: dict[str, Any], *, claim_id: str, seed: int, budget: Budget, trace: Trace) -> Decide:
    """The model's turn: read what the last tool returned, pick the next read tool or stop.

    Every turn is one MockLLM call. Tool results land in `facts`; the code after the
    loop reads money and status from there, never from the model or the ticket text.
    """

    def act(tool: str, args: dict[str, Any]) -> dict[str, Any]:
        trace.add("react_step", {"tool": tool})  # tool name only: results can carry the ticket
        return {"tool": tool, "args": args}

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        complete(budget, seed=seed, purpose="react", prompt=json.dumps(seen, ensure_ascii=False, sort_keys=True))
        if "last_tool" in seen:
            facts[seen["last_tool"]] = seen["last_result"]

        claim = facts.get("get_claim_view")
        if claim is None:
            return act("get_claim_view", {"claim_id": claim_id})
        if not claim["found"] or not claim["order_id"]:
            return {"final": {}}

        view = facts.get("lookup_order")
        if view is None:
            return act("lookup_order", {"order_id": claim["order_id"], "principal_id": claim["principal_id"]})
        if not view["visible"]:
            return {"final": {}}

        if "compute_compensation" not in facts:
            # Quote from the order row as returned by the tool. Ticket numbers are ignored.
            return act("compute_compensation", {"order": view["order"]})
        return {"final": {}}

    return decide


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int = 0, reason: str | None = None) -> RunResult:
        trace.add("decision", {"status": status, "proposal_amount": proposal, "reason": reason})
        complete(budget, seed=seed, purpose="draft", prompt=f"status={status} proposal={proposal}")
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    facts: dict[str, Any] = {}
    decide = _make_decide(facts, claim_id=claim_id, seed=seed, budget=budget, trace=trace)
    try:
        loop = run_react(conn, budget, observation={"claim": {"claim_id": claim_id}}, decide=decide, max_steps=MAX_STEPS)
    except ToolRejected:
        # The model asked for a write or unknown tool. run_claim must not raise.
        return done("failed", reason="tool_rejected")
    if loop["stopped"] != "final":
        return done("failed", reason="step_cap")

    # From here on, code decides. The model only chose which read tools to call.
    claim = facts["get_claim_view"]
    if not claim["found"]:
        return done("failed", reason="unknown_claim")
    if not claim["order_id"]:
        return done("needs_info", reason="missing_order_id")

    view = facts["lookup_order"]
    if not view["visible"]:
        return done("escalated", reason=view["reason"])
    trace.add("order", view["order"])  # allowlisted ORDER_FIELDS, no phone/address/item/note

    quoted = facts["compute_compensation"]
    trace.add("quote", quoted)
    proposal = int(quoted["amount_vnd"])
    if proposal <= 0:
        return done("denied", reason=quoted["reason"])

    # Full quote: the host checks approval and subtracts earlier refunds on the same order.
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    if outcome["ok"]:
        return done("resolved", proposal)
    return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])
