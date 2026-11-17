"""Shape A — deterministic workflow. Student work.

Signature (do not change):

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

Suggested steps. Money stays in code (`lab8.tools.compute_compensation`).

1. Open the store. Read the claim through `get_claim_view` (not SELECT *).
2. Missing order_id -> status `needs_info`. Do not write the ledger.
3. `lookup_order`. If not visible -> `escalated`. Do not copy phone, address, item, internal note.
4. Quote from the order row. Ignore delay numbers written in the ticket.
5. Quote amount 0 -> `denied`. Do not call issue_refund.
6. Quote amount > 0 -> `durability.issue_refund(conn, claim_id, <full quote>)`.
   Pass the FULL quote. The host checks the claim's own approval and subtracts
   what earlier claims already got for the same order (T13, T14). Do not
   subtract it yourself or the host subtracts twice.
   Auth failure or order already refunded -> `denied` (the host writes `policy_denied`).
   `proposal_amount` stays the full quote. Amount conflict -> `failed`.
7. Success -> `resolved`. One ledger row, one `refund_committed` audit.
8. Use MockLLM only to draft the reply text, if you want a model call at all.

The model must not choose the refund amount and must not commit the refund.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations


import sqlite3

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import (
    compute_compensation,
    get_claim_view,
    lookup_order,
    tool_cost,
)
from lab8.trace import Trace



def _process_claim(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    budget: Budget,
    trace: Trace,
    crash_at: str | None,
) -> tuple[str, int, str | None]:
    """Xử lý nghiệp vụ theo các bước cố định.

    Input:
        conn:
            Kết nối tới database đã được host khởi tạo.
        claim_id:
            Mã hồ sơ cần xử lý.
        budget:
            Bộ đếm lời gọi công cụ và chi phí mô phỏng.
        trace:
            Nhật ký chỉ chứa dữ liệu an toàn.
        crash_at:
            Điểm thử sự cố, hoặc None để chạy bình thường.

    Output:
        Bộ ba:
            (status, proposal_amount, error_reason)

        proposal_amount là khoản đề xuất ĐẦY ĐỦ,
        chưa trừ khoản đã hoàn trước đó.

    Công dụng:
        Đọc hồ sơ, tra đơn, tính quote và gọi cổng hoàn tiền.
        Không tự duyệt approval hoặc tự ghi ledger.
        Không thực hiện các chỉ dẫn nằm trong ticket.

        InjectedCrash được truyền ra ngoài để bộ kiểm thử
        kiểm tra khả năng phục hồi.
    """

    # BƯỚC 1: Đọc hồ sơ qua công cụ giới hạn trường dữ liệu.
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)

    # Chỉ ghi việc có tìm thấy hồ sơ hay không.
    # Không ghi nguyên claim vì có thể chứa thông tin nhạy cảm.
    trace.add(
        "claim_lookup",
        {"found": bool(claim.get("found"))},
    )

    if not claim.get("found"):
        return "failed", 0, "unknown_claim"

    # Thiếu mã đơn: yêu cầu bổ sung.
    # Không lấy hoặc đoán order_id từ nội dung ticket.
    if not claim.get("order_id"):
        return "needs_info", 0, "missing_order_id"

    # BƯỚC 2: Tra đơn và kiểm tra quyền xem.
    budget.add_tool(tool_cost())
    order_view = lookup_order(
        conn,
        claim["order_id"],
        claim["principal_id"],
    )

    visible = bool(order_view.get("visible"))
    trace.add("order_lookup", {"visible": visible})

    if not visible:
        # Không có đơn hoặc người yêu cầu không sở hữu đơn:
        # chuyển sang xử lý thủ công.
        return "escalated", 0, "order_not_visible"

    # BƯỚC 3: Tính tiền từ đơn chính thức và policy hiện hành.
    # Không dùng số ngày trễ hoặc số tiền khách viết trong ticket.
    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order_view["order"])

    proposal = int(quote["amount_vnd"])
    trace.add("quote", {"proposal_amount": proposal})

    if proposal <= 0:
        # Không đủ điều kiện thì không gọi cổng ghi tiền.
        return "denied", 0, "not_eligible"

    # BƯỚC 4: Yêu cầu host thực hiện hoàn tiền.
    #
    # Truyền số tiền quote ĐẦY ĐỦ.
    # KHÔNG tự trừ khoản đơn đã được hoàn trước đó.
    #
    # Host tự kiểm:
    # - Approval có hợp lệ và đúng claim không.
    # - Trần số tiền theo đơn.
    # - Khoản đã được hoàn.
    # - Idempotency để không hoàn trùng.
    budget.add_tool(tool_cost())
    trace.add(
        "refund_requested",
        {"proposal_amount": proposal},
    )

    outcome = issue_refund(
        conn,
        claim_id,
        proposal,
        crash_at=crash_at,
    )

    # Không bắt InjectedCrash ở đây.
    # Bộ test cần nhận được lỗi để mô phỏng chạy lại.

    if outcome.get("conflict"):
        # Đã có giao dịch nhưng số tiền lần gọi lại khác:
        # báo lỗi, giữ nguyên giao dịch cũ.
        return "failed", proposal, "amount_conflict"

    if not outcome.get("ok"):
        # Host đã ghi audit policy_denied.
        # Không tự tạo approval hoặc thử ghi vòng khác.
        #
        # Dùng mã lỗi cố định để tránh sao chép dữ liệu
        # không đáng tin cậy vào kết quả.
        return "denied", proposal, "refund_denied"

    return "resolved", proposal, None


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Điểm vào chuẩn để host chạy workflow cho một claim.

    Input:
        claim_id:
            Mã claim, ví dụ "C-001".
        seed:
            Số khởi tạo của lần chạy.
            Workflow không gọi model nên không đổi quyết định
            theo seed. Seed vẫn được lưu trong kết quả.
        store_path:
            Đường dẫn SQLite đã có dữ liệu do host chuẩn bị.
        crash_at:
            None hoặc điểm sự cố do bộ kiểm thử truyền vào.

    Output:
        Một đối tượng RunResult chứa:
        - Trạng thái xử lý.
        - Khoản tiền đề xuất đầy đủ.
        - Giao dịch hoàn tiền thực tế.
        - Số audit đã ghi.
        - Số lời gọi và chi phí công cụ.
        - Đường dẫn trace của chính lần chạy này.

    Công dụng:
        Khởi tạo budget và trace.
        Mở, đóng kết nối database.
        Gọi phần xử lý nghiệp vụ.
        Dùng finish() để đọc kết quả từ ledger thật.

        Không nuốt InjectedCrash.
    """

    budget = Budget()
    trace = Trace(make_run_id("workflow", claim_id, seed))
    conn = connect(store_path)

    try:
        try:
            status, proposal, reason = _process_claim(
                conn,
                claim_id,
                budget=budget,
                trace=trace,
                crash_at=crash_at,
            )

        except (sqlite3.Error, KeyError, TypeError, ValueError):
            # Xử lý lỗi dữ liệu hoặc SQLite.
            # Không in nguyên exception vì thông báo có thể
            # chứa dữ liệu nhạy cảm.
            #
            # InjectedCrash không thuộc các kiểu trên,
            # nên vẫn được truyền ra ngoài.
            conn.rollback()
            status = "failed"
            proposal = 0
            reason = "workflow_error"

        trace.add(
            "decision",
            {
                "status": status,
                "proposal_amount": proposal,
            },
        )

        # finish() đọc ledger thật để tạo RunResult.
        # Không tự điền số refund hoặc audit bằng tay.
        return finish(
            conn,
            shape="workflow",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    finally:
        # finally vẫn chạy khi InjectedCrash truyền ra ngoài.
        # Lưu trace cả khi sự cố khiến hàm chưa trả RunResult.
        try:
            trace.write()
        finally:
            conn.close()
   
