# Judge audit — kiểm tra bộ chấm AI

Nguồn: hai CSV công khai; các số bên dưới do `lab9.judge.calibrate` tính từ nhãn đang có. Đây là phân tích của AI dựa trên cột `note` được cung cấp, không giả nhận là một lượt gán nhãn mới bởi con người.

| Tiêu chí | n | κ | Precision | Recall | TP/FP/FN/TN (FAIL là dương tính) | Kết luận |
|---|---|---|---|---|---|---|
| tone | 100 | 0.757 | 0.857 | 0.8 | 24/4/6/66 | Đạt floors |
| helpful | 100 | 0.375 | 1.0 | 0.3 | 9/0/21/70 | Loại khỏi gate |

Floors: κ ≥ 0,6; precision ≥ 0,8; recall ≥ 0,7. Helpful bỏ sót 21/30 lỗi, nên precision cao vẫn không đủ để dùng làm gate. Tone chỉ đạt điều kiện calibration trên replay này; chưa chứng minh khả năng khái quát.
Rogan–Gladen: tone quan sát 0.28 → hiệu chỉnh 0.3; helpful 0.09 → 0.3. Không thay thế nhãn từng ca bằng tỷ lệ đã hiệu chỉnh.

| Case | Judge / người | Ai đúng theo bằng chứng sẵn có? | Căn cứ từ cột note | Đề xuất sửa rubric |
|---|---|---|---|---|
| H-008 | PASS / FAIL | Nhãn người theo note công khai | xưng 'em' + 'nha', quá suồng sã với khách; judge coi là thân thiện | Quy định xưng hô anh/chị, hạn chế em/nha trong hỗ trợ khiếu nại. |
| H-017 | PASS / FAIL | Nhãn người theo note công khai | xưng 'bạn' với khách lớn tuổi; judge coi là thân thiện | Không mặc định xưng bạn; chấm mức phù hợp với quy tắc dịch vụ trong nhãn. |
| H-029 | PASS / FAIL | Nhãn người theo note công khai | giọng ra lệnh ('không cần nhắn thêm'); judge chỉ thấy 'Dạ, vui lòng' | Chấm cả giọng mệnh lệnh, không chỉ từ khóa lịch sự ở đầu câu. |
| H-042 | FAIL / PASS | Nhãn người theo note công khai | ngắn nhưng đủ ý; judge phạt vì 'thiếu xin lỗi' | Không bắt buộc lời xin lỗi khi câu trả lời đã lịch sự và đủ ý. |
| H-051 | FAIL / PASS | Nhãn người theo note công khai | dùng từ 'refund' — CS LogiX cho phép; judge phạt vì tiếng Anh | Cho phép từ refund theo ghi chú chính sách trong fixture. |
| H-063 | PASS / FAIL | Nhãn người theo note công khai | hứa 'sẽ hoàn thêm' ngoài kết quả hệ thống | Tách hứa hẹn không có căn cứ thành tiêu chí groundedness; kiểm tiền bằng code. |
| H-070 | PASS / FAIL | Nhãn người theo note công khai | emoji không phù hợp ngữ cảnh khiếu nại | Thêm ví dụ emoji không phù hợp với khiếu nại. |
| H-081 | FAIL / PASS | Note cho rằng judge đúng, nhãn người sai; chưa đủ dữ liệu để xác minh độc lập | nhãn người sai (đọc nhầm ticket) — judge đúng, sửa nhãn | Cách ly ca cần kiểm lại nhãn; chưa sửa CSV khi thiếu ticket/rubric gốc. |
| H-088 | FAIL / PASS | Nhãn người theo note công khai | lặp 'Dạ' do lỗi gõ; người cho qua, judge phạt | Không phạt nặng lặp từ lịch sự do lỗi gõ nếu nội dung vẫn rõ. |
| H-094 | PASS / FAIL | Nhãn người theo note công khai | dịch máy, mất dấu tiếng Việt | Quy định rõ yêu cầu dấu tiếng Việt, thêm ví dụ mất dấu. |

Không sửa CSV hoặc tính lại số liệu để làm đẹp calibration. H-081 cần người dùng duyệt sau khi có ticket/rubric gốc nếu muốn đổi nhãn. Các sửa rubric ở trên là đề xuất, chưa có lượt judge mới để chứng minh hiệu quả.

Bằng chứng chạy: [tone](evidence/judge_tone.txt), [helpful](evidence/judge_helpful.txt). Cần tập held-out và người gán nhãn độc lập trước triển khai thực tế.
