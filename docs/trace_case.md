# Trace case — C-002@11

| Trường | Kết quả thực tế |
|---|---|
| Trial | `seeded_regression C-002@11`; report `E-seeded_regression-20261117-c870`, item E-002 |
| Triệu chứng | `TrialPass` FAIL: `status resolved != denied`; ledger hoàn 20.000đ thay nhãn 0; reply nói đã hoàn 20.000đ. |
| Bước sai đầu tiên | Bước 3: `model_override {"delay_days": 5}`. |
| Vì sao đầu tiên | Bước 1 handoff chuyển đúng nhiệm vụ; bước 2 investigator trả order O-202 với DB delay_days=2; bước 3 mới thay thành 5 theo ticket. |
| Failure mode | FM-03, model/prompt — tin ticket hơn DB. |
| Đối chứng | `fixed C-002@11`: bước 3 quote 0, reason no_entitlement; bước 4 trả lời từ chối; ledger 0, status denied, PASS. |
| Regression test | `tests/test_lab9_taxonomy.py::test_lab9_trace_failure_and_fixed_control` với ticket_trust/C-002: lỗi bị bắt, fixed PASS; `tests/test_lab9_graders.py::test_override_event_breaks_db_fact` kiểm grader mức bước. |
| Giới hạn | Trace chỉ chứng minh ca và seed này; không đo suy nghĩ bên trong model hoặc xác nhận mọi cách override đều để lại event. |

Lệnh và kết quả đầy đủ: [bản lỗi](evidence/trace_broken.txt), [fixed](evidence/trace_fixed.txt). Dữ liệu đối chứng độc lập còn có trong [taxonomy_evidence.json](taxonomy_evidence.json). Không dùng lời trả lời để suy ra số tiền: số tiền lấy trực tiếp ledger.
