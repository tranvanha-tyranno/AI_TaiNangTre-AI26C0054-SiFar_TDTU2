# LMMv3 reliability — thử nghiệm độc lập từ baseline

## Bản sửa đầu ra/review `lmmv3-v2-reliability-v2`

Nhánh `codex/llmv3-output-review-fix` phát triển từ main đã nhận reliability-v1. Baseline nguyên trạng không đổi.

- Nếu contract yêu cầu count, answer_spec cũng khai báo count, nhưng output là filter không có columns: nối thêm aggregate count trên chính filter đó. Không tự tạo bộ lọc hoặc suy đoán cột; không sửa yêu cầu liệt kê có columns, không vượt 25 bước; mọi thay đổi ghi vào normalizations.
- Khi câu hỏi yêu cầu identity và kết quả xếp hạng trả lại chính literal dùng để lọc, phát hiện literal lặp dưới nhiều section trong phạm vi đã đọc. Chỉ kiểm tra mẫu sort/take và output đúng cột đang lọc; bỏ qua nếu header cột xác định rõ identity được hỏi hoặc chỉ một section. Báo lỗi có bằng chứng cho LLM sửa, không tự thay nhãn bằng đáp án tham chiếu. Đây là guard hẹp, chưa phải bộ hiểu identity đa ngôn ngữ hoàn chỉnh.
- Review nhận final_output.answer, final_output.values và normalizations của chính ứng viên hiện tại. Giữ nguyên raw tool trace/row_samples để kiểm tra nguồn và phép tính; chỉ dẫn reviewer không coi dấu phân cách ô gốc là lỗi còn tồn tại trong đầu ra đã chuẩn hóa. Không tự bỏ qua verdict revise hoặc thay đổi câu trả lời theo reviewer.

Replay offline log `20261016-233013-7aa485`: kế hoạch đếm đã sửa hoàn tất và trả 34; nhãn lớp lặp được phát hiện với bằng chứng section. Tests giả lập xác minh đường sửa identity và payload review, không thêm stage/API allowance. Chưa có điểm benchmark LLM mới, không bảo đảm reviewer luôn đúng.

Các mô tả v1 dưới đây là lịch sử và nền của bản sửa.

Nhánh `codex/llmv3-reliability` bắt đầu từ `e07698f`. Nhánh `codex/llmv3-restored-25` giữ nguyên. Không đưa các gate/schema/RAG của v4 trở lại baseline.

Chạy `--mode llm-v3` với `v3_reliability: true` trong config hiện tại để dùng version `lmmv3-v2-reliability-v1`. Tắt cờ để dùng luồng gốc trên nhánh này; muốn nguyên mã nguồn lịch sử dùng nhánh restored. Cờ được ghi trong run_context. Chế độ llm/llm-v2 không bật các thay đổi này.

## Bằng chứng trước sửa

Run `20261016-231412-6bc13b`: 24/30 strict exact match, 27 có đáp án; 3 lỗi xử lý (6,17,27) và 3 khác mẫu (15,19,23). Các bảng liên quan đều có trong tập vùng được cấp. Không dùng ID/tên file/tham chiếu để chọn đáp án.

| Nhóm lỗi | Cơ chế mới | Giới hạn |
|---|---|---|
| lag được viết bên trong derive.expr | Chuyển sang step lag khi source, column, offset được khai báo rõ và column trùng đích derive; giữ log | Không đoán hướng thời gian, bộ lọc, dấu giảm; first lag null vẫn cần kế hoạch lọc hợp lệ |
| So hai số lưu text theo thứ tự chữ | So Decimal cho ordering của hai chuỗi số rõ ràng; giữ equality của mã và chuỗi 0 dẫn đầu | Không đoán decimal comma/locale, không đổi dữ liệu ô hoặc mặc định sort |
| Boolean đi vào ép số Python | eq/ne giữa hai boolean; từ chối trộn boolean với số hoặc ordering | Chỉ bật trong execute reliability; ContextVar reset finally |
| count của biểu thức boolean trả số dòng kể cả False | Báo lỗi cụ thể, yêu cầu filter trước rồi count | Không tự biến nghĩa count thành count_true; cần LLM sửa kế hoạch trong ngân sách hiện tại |
| Nhầm nhãn dòng lặp với tiêu đề nhóm | Preview có section_row dẫn về section_labels gốc; nhắc dùng nguồn nhóm đã kiểm tra | Chỉ bổ sung bằng chứng, không tự đổi nhãn đáp án; không chứng nhận phát hiện nhóm đúng |
| JSON/operator/code-digit/percent-change sai cú pháp | Bổ sung chỉ dẫn ngắn và ví dụ cú pháp chung | Chưa có constrained decoding; vẫn có thể sinh JSON sai, không sửa đoán toán tử/số bị thiếu |
| Tuple yêu cầu số nguyên nhưng ô chứa dấu nhóm nghìn | Chuẩn hóa dấu nhóm nghìn rõ ràng chỉ ở numeric_positions được contract chỉ định, giữ value_sources và log | Không sửa trường nhãn/mã, không ép giá trị mơ hồ hoặc thay đổi đơn vị |

Replay offline kế hoạch cuối của câu so sánh text-number đã đổi đúng nhánh lựa chọn. Replay count boolean phát hiện đúng lỗi vốn bị chấp nhận; replay lag qua bước chuẩn hóa nhưng vẫn báo prior null. Đây không phải chạy LLM lại, không được tính là điểm benchmark mới.

## RAG

Giữ nguyên thuật toán xếp hạng và top-k trong lần này. Với sáu lỗi quan sát được, tăng số bảng/context chưa có bằng chứng giúp. Bổ sung section_row là tăng chất lượng bằng chứng hiển thị, không phải chứng minh tăng retrieval recall. Chỉ thử xếp hạng mới trên nhánh riêng khi có lỗi thiếu/sai vùng được xác nhận; đo recall vùng cần thiết, câu đúng mất/được, token và thời gian trước khi nhận thay đổi.

## Kiểm chứng và bước tiếp

Tests dùng dữ liệu tổng hợp, đổi trị số, leading-zero IDs, boolean, count False, lag mơ hồ và provenance section. Chưa gọi API benchmark, không tuyên bố sáu câu đều đã sửa hay tăng điểm. Không tăng retry, API allowance hoặc timeout. Chạy lại toàn dataset để phát hiện hồi quy; không chọn run điểm cao nhất làm baseline mới.
