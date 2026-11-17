"""Shape B (single) boundaries: the model cannot write money, and the trace stays clean."""

from __future__ import annotations

from pathlib import Path

from lab8.db import connect, init_store
from lab8.shapes import single
from tests.conftest import CLAIMS, WORLD

ORDERS = {order["order_id"]: order for order in WORLD["orders"]}
PII_FIELDS = ("phone", "address", "internal_note", "item_name")


def test_model_asking_for_issue_refund_is_rejected(public_db, monkeypatch):
    # A "model" that ignores its read-only tools and tries to pay C-001 itself.
    def rogue_decide(*_args, **_kwargs):
        return lambda seen: {"tool": "issue_refund", "args": {"claim_id": "C-001", "amount_vnd": 999_999}}

    monkeypatch.setattr(single, "_make_decide", rogue_decide)
    result = single.run_claim("C-001", seed=11, store_path=str(public_db))

    assert result.status == "failed"
    assert result.error_reason == "tool_rejected"
    assert result.refund_effects == []
    assert result.committed_audit_count == 0
    conn = connect(public_db)
    try:
        rows = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()["n"]
    finally:
        conn.close()
    assert rows == 0


def test_trace_never_holds_ticket_secret_or_order_pii(tmp_path):
    for claim in CLAIMS:
        store = tmp_path / f"{claim['claim_id']}.sqlite"
        init_store(store, WORLD, CLAIMS).close()
        result = single.run_claim(claim["claim_id"], seed=11, store_path=str(store))

        forbidden = [claim["ticket"], claim.get("parent_secret")]
        forbidden += [str(value) for value in (claim.get("raw_headers") or {}).values()]
        order = ORDERS.get(claim.get("order_id") or "", {})
        forbidden += [order.get(field) for field in PII_FIELDS]

        text = Path(result.trace_path).read_text(encoding="utf-8")
        leaked = [value for value in forbidden if value and value in text]
        assert not leaked, f"{claim['claim_id']} trace leaked {len(leaked)} forbidden value(s)"
