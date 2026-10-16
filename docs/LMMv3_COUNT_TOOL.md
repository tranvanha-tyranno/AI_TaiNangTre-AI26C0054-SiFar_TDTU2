# Thí nghiệm một nhóm lỗi: đếm có điều kiện

Nhánh `codex/llmv3-count-tool` bắt đầu từ đúng baseline `00f9822`. Giữ nguyên `codex/llmv3-best-27`; không đưa sửa chiều phép trừ hoặc thay đổi RAG của các nhánh khác vào đây.

## Cách bật và phạm vi

`--mode llm-v3`, `v3_reliability: true`, `v3_count_tool: true` bật version `lmmv3-v2-count-tool-v1`. Config nhánh thử nghiệm đã bật cờ. Tắt `v3_count_tool` khôi phục hành vi reliability-v2 trong nhánh này; muốn nguyên source baseline, dùng nhánh best-27. Cờ được lưu vào run_context.

Chỉ giới thiệu tool/schema mới khi answer contract hiện có xác định rõ một scalar count. Câu không phải count giữ nguyên request/schema của baseline; tests đối chiếu cả plan và review với đồng hồ cố định. Không thêm stage, lượt API, retry hoặc timeout. LLM vẫn có thể inspect hoặc dùng DSL cũ khi cần nested logic/join.

## Công cụ

LLM có thể gửi một object `action=count_rows`, gồm table, start_row/end_row, combine=all/any, missing=error/exclude và tối đa 12 conditions. Không có Python/SQL hoặc đáp án literal. Schema thêm một lựa chọn trong tool call hiện có, không đăng ký thêm dịch vụ AI.

Các điều kiện hỗ trợ:

- `number_eq/ne/gt/ge/lt/le`: một value số hữu hạn **hoặc** other_column; Python ép số có kiểm soát. Không cho cả hai hoặc literal boolean.
- `text_eq/ne`: trim khoảng trắng, giữ phân biệt hoa/thường và số 0 đầu mã.
- `text_contains`: trim và tìm chuỗi không phân biệt hoa/thường, đúng semantics contains hiện có.
- `digits`: số chữ số yêu cầu 1..30, không dùng độ dài text mù. Chuỗi số giữ zero đầu; mã số nguyên Excel được nhận; chuỗi dấu âm/dấu cộng/dấu chấm và text chữ không được coi là mã toàn chữ số. NFKC nhận các chữ số full-width tương ứng; không tuyên bố hỗ trợ mọi hệ chữ số Unicode.
- `is_number`, `is_null`, `not_empty`: điều kiện một cột, không có value.

`missing=exclude` làm một so sánh số không có giá trị số hợp lệ thành False; guard đặt **trong từng predicate** để OR không loại mất dòng còn nhánh khác đúng. `missing=error` báo lỗi ở phép so sánh được đánh giá; AND/OR vẫn short-circuit. Không coi ô thiếu là zero. digits trả 0 cho giá trị không phải mã chữ số, nên điều kiện digits không khớp; đây là semantics kiểm tra mã, không phải điền dữ liệu thiếu.

Conditions rỗng với combine=all đếm mọi dòng trong bounds; combine=any rỗng bị từ chối vì mơ hồ. Người lập kế hoạch chịu trách nhiệm loại header, total hoặc notes và xác định phạm vi. Tool không tự chọn năm, nhóm, cột, suy diễn điều kiện, deduplicate entity hoặc chứng nhận scope đủ. Count là số dòng khớp, không phải distinct count.

Python kiểm tra tham số rồi biên dịch sang read/filter/aggregate count hiện có. Kế hoạch có tối đa ba bước, số liệu và provenance do executor tạo. Request gốc lưu ở count_tool_requests và normalizations. Reviewer nhận kế hoạch đã biên dịch; response schema của review được reset về schema review cũ.

## Kiểm chứng

Tests tổng hợp gồm mã text/numeric/leading zero, số âm/phân số/chữ có cùng độ dài, số 0, kết quả 0, so sánh cột-cột, dữ liệu thiếu ở OR, missing policy, đổi vị trí cột/đảo dòng, từ chối bounds/cột/giá trị không hợp lệ, fallback DSL và hai lượt fake plan/review. Client thật không được gọi.

`outputs/count_tool_offline/verification.json` ghi hai thử nghiệm công cụ trên workbook có sẵn, với tham số được người phát triển bind từ nguồn: 34 và 33. Chưa đánh giá khả năng LLM tự tạo các request này, không tính thành điểm benchmark mới, không dùng đáp án mẫu để sinh request.

## Các giới hạn cần đánh giá tiếp

Outer JSON vẫn có thể lỗi; schema mới vẫn có fallback DSL. LLM có thể chọn sai cột, thiếu vùng hoặc khai báo missing policy không đúng. Tool đếm không sửa các lỗi đó bằng suy đoán. Count intent đa ngôn ngữ vẫn phụ thuộc contract hiện có; câu không được nhận diện không tự đổi route.

Khi chạy API đối chứng, giữ lịch số lần chạy được định trước, báo toàn bộ điểm (mean/min và từng run), lỗi xử lý, hồi quy ngoài câu đếm, request thực sự dùng tool, token/phí và thời gian. Không tăng điểm bằng chọn best-of-N hoặc chỉ chạy lại câu sai. Cần kiểm chứng dataset khác trước khi nhận vào baseline/main. Chưa có điểm API hoặc chứng nhận tài nguyên mới trong lần triển khai này.
