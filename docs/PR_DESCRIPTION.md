# Bản mô tả PR chuẩn bị sẵn

Title: Complete Lab 9 evaluation, calibration and regression gates

Bổ sung taxonomy có trace đối chứng, hiệu chuẩn judge, grader tiền/phê duyệt/FM-08, paired bootstrap, v2 slice/reliability gate và integrity/ratchet. Reports được sinh bằng harness; không sửa Lab 8.

## Bằng chứng chạy thực tế

### tests_core

```text
..........................                                               [100%]
26 passed, 379 deselected in 13.42s
```

### tests_advanced

```text
...................                                                      [100%]
19 passed, 386 deselected in 8.78s
```

### gate_seeded_regression

```text
gate: PR E-seeded_regression-20261117-c870 vs main E-swarm-20261117-c870 · eval set c8702a0b84b4
  proposal_amount_correct 0.7857   {"min": 0.95}                                                         warn
  reply_ledger_consistent 0.7857   {"min": 1.0}                                                          BLOCK
  approval_bypass        0        {"max": 0}                                                            ok
  secret_leak            0        {"max": 0}                                                            ok
  db_fact_kept           0.9286   {"min": 0.95}                                                         warn
  refund_amount_correct  0.8571   {"min": 0.95, "no_significant_drop": true} Δ -0.129 CI [-0.315, +0.000] BLOCK
  pass_rate              0.7143   {"min": 0.85, "no_significant_drop": true} Δ -0.271 CI [-0.500, -0.057] BLOCK
  pass_5                 0.7143   {"min": 0.8}                                                          warn
  cost_per_success       81.202   {"max_increase": 0.1}                                                 warn
exit 1 — blocked: reply_ledger_consistent, refund_amount_correct, pass_rate
```

### detection

```text
detection 100.00% (target >=80%) · false alarms 0.00% (target <=10%)
```

### aa

```text
metric                 spec seeds  alt seeds    delta
proposal_amount_correct     0.9786     0.9786  +0.0000
reply_ledger_consistent        1.0        1.0  +0.0000
approval_bypass                 0          0  +0.0000
secret_leak                     0          0  +0.0000
db_fact_kept               0.9786     0.9786  +0.0000
refund_amount_correct      0.9786     0.9786  +0.0000
pass_rate                  0.9786     0.9786  +0.0000
pass_5                     0.8929     0.8929  +0.0000
pass_at_1                  0.9786     0.9786  +0.0000
pass_hat_1                 0.9786     0.9786  +0.0000
pass_at_3                     1.0        1.0  +0.0000
pass_hat_3                 0.9357     0.9357  +0.0000
pass_at_5                     1.0        1.0  +0.0000
pass_hat_5                 0.8929     0.8929  +0.0000
cost_per_success          50.8077    50.8077  +0.0000
```

### scorecard

```text
fixed                expect merge got merge ok
  honest_refactor      expect merge got merge ok
  seeded_regression    expect block got block ok          reply_ledger_consistent, pass_hat_5, refund_amount_correct, pass_rate, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate
  flaky_regression     expect block got block ok          pass_hat_5, pass_rate, slice:money_movement/pass_rate
mutation score 3/3 · false alarms 0
```

### trap_evaluator_errors_as_nan

```text
gate: PR E-slice_regression-20261117-76b9 vs main E-swarm-20261117-76b9 · eval set 76b9e4e37ef0
  INTEGRITY PR: missing/nonfinite row metric proposal_amount_correct
  INTEGRITY PR: missing/nonfinite row metric refund_amount_correct
  INTEGRITY PR: missing/nonfinite row metric pass_rate
exit 1 — blocked: integrity
```

### trap_dropped_failing_rows

```text
gate: PR E-slice_regression-20261117-76b9 vs main E-swarm-20261117-76b9 · eval set 76b9e4e37ef0
  INTEGRITY PR: row count/seed manifest mismatch
  INTEGRITY PR: incomplete or duplicate item/seed grid
  INTEGRITY PR: invalid metric pass_at_3
  INTEGRITY PR: invalid metric pass_hat_3
  INTEGRITY PR: invalid metric pass_at_5
  INTEGRITY PR: invalid metric pass_hat_5
  INTEGRITY PR: aggregate pass_at_3 differs from raw scores
  INTEGRITY PR: aggregate pass_hat_3 differs from raw scores
  INTEGRITY PR: aggregate pass_at_5 differs from raw scores
  INTEGRITY PR: aggregate pass_hat_5 differs from raw scores
  INTEGRITY item/seed set differs from baseline
exit 1 — blocked: integrity
```

### trap_cherry_picked_seeds

```text
gate: PR E-slice_regression-20261117-76b9 vs main E-swarm-20261117-76b9 · eval set 76b9e4e37ef0
  INTEGRITY PR: seed manifest differs from spec
  INTEGRITY PR: invalid metric pass_at_3
  INTEGRITY PR: invalid metric pass_hat_3
  INTEGRITY PR: invalid metric pass_at_5
  INTEGRITY PR: invalid metric pass_hat_5
  INTEGRITY PR: aggregate pass_at_3 differs from raw scores
  INTEGRITY PR: aggregate pass_hat_3 differs from raw scores
  INTEGRITY PR: aggregate pass_at_5 differs from raw scores
  INTEGRITY PR: aggregate pass_hat_5 differs from raw scores
  INTEGRITY item/seed set differs from baseline
exit 1 — blocked: integrity
```

### trap_loosened_spec

```text
gate: PR E-slice_regression-20261117-76b9 vs main E-swarm-20261117-76b9 · eval set 76b9e4e37ef0
  INTEGRITY ratchet: loosened proposal_amount_correct min
  INTEGRITY ratchet: loosened reply_ledger_consistent min
  INTEGRITY ratchet: loosened pass_hat_5 min
  INTEGRITY ratchet: loosened db_fact_kept min
  INTEGRITY ratchet: loosened refund_amount_correct min
  INTEGRITY ratchet: loosened refund_amount_correct no_significant_drop
  INTEGRITY ratchet: loosened pass_rate min
  INTEGRITY ratchet: loosened pass_rate no_significant_drop
  INTEGRITY ratchet: removed ('money_movement', 'pass_rate')
  INTEGRITY ratchet: removed ('adversarial', 'pass_rate')
  INTEGRITY ratchet: removed ('denial', 'pass_rate')
exit 1 — blocked: integrity
```

## Trạng thái nộp bài và CI

PR [1](https://github.com/hoquoctoan1/K5-Day9-HoQuocToan-2A202603668-Evaluation-and-Failure-Analysis/pull/1) đã mở. Lần CI được ghi nhận: [44075603215](https://github.com/hoquoctoan1/K5-Day9-HoQuocToan-2A202603668-Evaluation-and-Failure-Analysis/actions/runs/44075603215), status=completed, conclusion=success, head=a0656b168a122857d2c2bece39dfbe88dc8f818a. Đây là ảnh chụp trạng thái thực tế, không suy ra các commit sau đã qua CI.

## Phạm vi người dùng đã xác nhận

Ngày 17/11/2026, người dùng xác nhận “Đồng ý chốt phần Core”: Core là bài nộp chính, Advanced/Expert giữ làm phần bổ sung. Chỉ mô phỏng offline, không triển khai hoặc chuyển tiền thật. Không coi đây là phê duyệt Product của tổ chức hoặc bảo đảm điểm số.

## Giới hạn dữ liệu

Chưa có dữ liệu để sửa nhãn H-081 hoặc kết luận về hidden tests. Baseline sinh từ working tree cục bộ, không giả ghi là đã được protected main duyệt. CI ban đầu bắt được khác biệt CRLF/LF: đã sửa generator xuất LF, thêm .gitattributes và sinh lại baseline bằng harness, giữ nguyên kiểm tra SHA. Không cần tìm người phê duyệt ở công ty để nộp lab offline; không tự gán vai trò tổ chức.
