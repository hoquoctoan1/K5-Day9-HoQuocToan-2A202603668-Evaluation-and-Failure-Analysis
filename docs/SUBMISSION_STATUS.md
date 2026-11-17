# Trạng thái nộp bài

Ngày kiểm tra: 17/11/2026. Nhánh local: `starter/d09`.

## Đã xác minh cục bộ

- M0 PASS; pip check không phát hiện phụ thuộc hỏng.
- Eval set v1: 14 item, 14 nhãn; v2: 28 item, 28 nhãn; checker 0 lỗi.
- Taxonomy có bằng chứng chạy đối chứng cho 8 FM; FM-09 chỉ có bằng chứng chặn truy cập đúng, không tuyên bố rò dữ liệu đã xảy ra.
- Core: 26 tests PASS; Advanced: 19 tests PASS; 3 tests CLI evalset riêng cũng PASS.
- Tone đạt floors; helpful không đạt. Audit 10 bất đồng dựa trên nhãn/note CSV, không giả nhận là nhãn người mới.
- Detection 100%, false alarm 0% sau khi thêm ProposalAmountCorrect; giữ log lần đầu 75% để giải thích thay đổi.
- Gate cho swarm và fixed qua, chặn seeded_regression; pass_rate Δ −0,271, CI [−0,500; −0,057].
- A/A: mọi metric delta 0; mutation score 3/3, false alarms 0.
- Cả bốn trap công khai đều bị CLI chặn exit 1; baseline v2 so với chính nó qua gate.
- Báo cáo do harness sinh; không sửa mã Lab 8. Harness map và workflow được bổ sung.

30 lệnh kiểm tra chính và exit code thực tế: [validation.json](evidence/validation.json). Lệnh tái hiện từ `src`: `python -m lab9.verify`; sinh lại tài liệu bằng `python -m lab9.submission_docs` sau khi verify thành công. Hash code/dữ liệu đánh giá: [input_hashes.json](evidence/input_hashes.json).

## Chưa thể xác nhận / cần người dùng duyệt

- Chưa push hoặc mở PR; chưa có URL lần chạy GitHub Actions nên không ghi CI từ xa đã xanh. Nội dung PR chuẩn bị tại [PR_DESCRIPTION.md](PR_DESCRIPTION.md).
- Chưa có xác nhận ai là Product/Eval owner hoặc ai duyệt waiver; PRD ghi rõ chưa phê duyệt.
- H-081 có note nghi nhãn người sai; chưa có ticket/rubric gốc nên giữ nguyên CSV, không tự sửa nhãn.
- Không có hidden tests và key anchor giảng viên; không tuyên bố điểm số ẩn hoặc đạt 100 điểm.
- Chưa có dữ liệu người dùng/model thật; chỉ đánh giá offline, chưa duyệt triển khai thực tế.

Những mục trên không được tự điền thành kết quả đã đạt. Cần người dùng duyệt bước công bố/nộp PR và cung cấp người phụ trách nếu muốn hoàn tất phần phê duyệt PRD.
