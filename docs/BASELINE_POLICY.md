# Baseline và quy trình cải tiến từng bước

## Bản chính

- Mode: `llm-v3`; version: `lmmv3-v2-dedup-v1`; `v3_deduplicate_context: true`.
- CLI và dashboard mặc định chọn LLMv3. V4 vẫn tồn tại trên nhánh thử nghiệm, không xóa code hay log và không merge main trong lần chốt này.
- Mốc lịch sử bất biến: commit `e07698f1f3549c17dd5d0364e7a591653c453477`, được ghi trong run `20261016-142856-ebdfbc/run_context.json`. Run Public_data_2 này đạt strict exact match 25/30; đây là kết quả lịch sử, không phải benchmark mới hay cam kết mọi lần chạy đều đạt 25/30.
- Mã hiện tại có thay đổi dùng chung từ sau mốc lịch sử. Không coi cùng chuỗi version là bằng chứng mã hoàn toàn giống nhau. Khi cần tái tạo đúng mốc lịch sử, dùng checkout riêng từ commit trên; khi đối chiếu mới, lưu `run_context.json` và cấu hình thực tế của cả hai bên.

## Quy trình tiếp theo

1. Giữ một run baseline đầy đủ cho mỗi dataset với dữ liệu/config/model được ghi nhận. Không chọn run cao nhất sau nhiều lần chạy; ghi riêng lần đầu và các lần lặp để đo dao động.
2. Khoanh vùng lỗi có bằng chứng: API, thiếu đáp án, thực thi, hoặc khác tham chiếu. Khác tham chiếu chưa đủ chứng minh phase sai. Tách trường hợp dữ liệu/tham chiếu không hợp lệ khỏi phân tích solver và công bố số bị loại.
3. Mỗi nhánh con bắt đầu từ baseline, sửa một cơ chế với giả thuyết và phản ví dụ rõ ràng. Ưu tiên lỗi tool xác định được; chưa thêm reviewer/gate/prompt dài nếu chưa có bằng chứng lợi ích.
4. Kiểm tra tổng hợp và hồi quy trước. Test API chỉ chạy khi người dùng yêu cầu. Dùng cùng dataset, model, ngân sách và cấu hình; lưu thời gian, usage, phí xác nhận và số lần sửa.
5. Báo cả gains và regressions bằng công cụ dưới đây. Giữ strict exact match; không đổi tham chiếu hoặc chuẩn hóa để tăng điểm. Điểm hòa chưa chứng minh tốt hơn; cần xem thời gian/token và dao động.
6. Chỉ nhận thay đổi sau khi có lợi trên nhiều dataset và không có hồi quy chưa được chấp nhận. Dành dataset chưa dùng để sửa solver làm kiểm chứng cuối; sau khi đã xem lỗi thì không gọi dataset đó là tập chưa thấy nữa.

## Đối chiếu offline, không gọi API

```powershell
python -m scripts.compare_baseline --baseline <baseline.csv> --candidate <candidate.csv> --reference <reference.csv> --report outputs/paired_evaluation.json
```

Báo cáo có ID các nhóm cùng đúng, sửa được, hồi quy và cùng sai; từ chối run thiếu/thừa ID. Chỉ dùng cho đánh giá, không import vào solver. Công cụ không tự xác nhận tính tương đương của dataset/config, không tự đo thời gian/chi phí và không tự quyết định merge.

Lần chốt này chỉ thay mặc định và thêm quy trình/công cụ đối chiếu; chưa chạy dataset, chưa tiêu tiền API, chưa nâng cấp thuật toán của LLMv3.
