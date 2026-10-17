# Đánh giá hướng nâng cấp — 17/10/2026

## Kết luận từ mã hiện tại

Có thể cải thiện bằng sửa cơ chế đọc, tính và kiểm tra; không cần nạp thêm
đáp án vào prompt. `error_memory` là truy xuất hướng dẫn cục bộ, không phải
fine-tuning hoặc cập nhật trọng số Qwen.

Hiện đường DSL trong `src/pipeline.py` có gọi memory, còn
`answer_with_program` không gọi `load_memory`/`augment`. Vì thế thêm bài học
vào `config/error_memory.json` không tự tác động đến đường xử lý bảng dài.
Muốn nối memory vào đường đó phải có thí nghiệm đối chứng riêng, tránh
đưa lại các giả định theo ngành/bộ mẫu vào prompt chung.

Trong `src/program_pipeline.py`, các hàm `canonical_*_program(question)`
chọn chương trình theo từ khóa nhưng không nhận schema workbook. Chúng có
giả định cố định về `t1`/`t2`/`t3`, chữ cột, mã thực thể và thời kỳ. Ví dụ
nhánh peak dùng `NM-040`; nhánh revision dùng `E-000500-4`; nhánh civic dùng
`2028-12`. Dù kết quả được tính từ ô thật, những ràng buộc này không chứng
minh chương trình đã giải đúng câu hỏi mới.

Luồng cũ còn chấp nhận kết quả trước review nếu `method` bắt đầu bằng
`Canonical event resolver`. Vì `method` cũng có thể do mô hình trả về,
nội dung mô tả không thể là quyền miễn kiểm tra.

## Bản sửa đầu tiên: `lmmv3-program-v2`

- Ngừng gọi các adapter theo từ khóa trong luồng trả lời bảng dài. Mọi
  chương trình đều được lập từ câu hỏi và preview/schema workbook được cấp.
- Bỏ nhánh miễn review theo `method`. Kết quả phải thực thi được, qua kiểm
  tra định dạng và được reviewer chấp nhận trước khi gắn `validated`.
- Giữ ngân sách API, chi phí, thời gian và giao diện CLI. CLI chỉ xuất CSV.

Các định nghĩa adapter cũ còn trong file để bảo toàn chỉnh sửa đã có trong
workspace; chúng không được gọi bởi luồng trả lời mới. Đường DSL cho workbook
không được chọn vào program pipeline không thay đổi trong bản sửa này.

Kiểm thử mới dùng bảng/cột khác cấu trúc mẫu, câu hỏi Việt/Pháp có từ khóa
từng kích hoạt adapter, và phản hồi mô hình tự nhận là canonical nhưng bị
reviewer từ chối. Tất cả dùng client giả, không gửi API thật.

Kiểm chứng: `.venv/Scripts/python.exe -m unittest discover -s tests -q`
qua **142/142 test**, gồm test CLI/SDK với server giả lập local. Bộ test
program riêng qua **24/24**. Đây là kiểm chứng offline trong môi trường
phát triển hiện có, chưa build lại Docker hoặc đo điểm dataset sau sửa.

## Những nâng cấp nên làm tiếp, theo từng thí nghiệm

1. **Ràng buộc nguồn trước tính toán:** biểu diễn rõ metric, entity, thời gian,
   bộ lọc, đơn vị, khóa join, phép tính và định dạng. Mọi ràng buộc lấy từ
   câu hỏi/header; không tự suy ra luật ngành từ bộ test đã thấy.
2. **Quan sát đầy đủ nhưng gọn:** profile cột/khóa từ toàn vùng, phân biệt
   numeric text và identifier, thống kê missing và join không khớp. Preview
   là mẫu xem; tính tổng/rank vẫn đọc toàn vùng phù hợp.
3. **Kiểm tra bất biến tính toán:** xác minh đơn vị, chiều tỷ giá, số thực
   thể trước/sau join, tập dòng của tử/mẫu và phạm vi Total. Chỉ tự sửa
   điều có bằng chứng xác định; nghi vấn ngữ nghĩa đưa qua repair/review.
4. **Dùng lỗi làm ca kiểm thử:** đọc trace và workbook để xác nhận nguyên
   nhân; tạo biến thể đổi cột/sheet/nhãn/dữ liệu. Chỉ đưa hướng dẫn tổng quát
   đã kiểm chứng vào memory, không đưa answer/reference/ID/tên file/tọa độ
   cố định. Không tiếp tục thêm lesson chỉ để khớp từng lỗi đã thấy.

## Cách chứng minh cải thiện

Chạy baseline và bản mới trên cùng model/config/budget; giữ riêng bộ hồi quy
đã dùng sửa và bộ mới chưa dùng sửa. Suite 23–28 đã được phân tích/chỉnh theo
lỗi nên hiện là bộ hồi quy, không còn là holdout mới.

Báo riêng strict exact match, câu rỗng, API calls, input/reasoning token,
chi phí và thời gian. Không ghép các lần chạy con thành điểm toàn bộ. Dùng
biến thể đổi thứ tự sheet/cột và mã thực thể để phát hiện giả định cố định.
Điểm tăng trên public không chứng minh khả năng tổng quát trên tập ẩn.

Bản sửa này chưa benchmark OpenRouter: bỏ adapter sẽ dùng lượt plan/review
thật thay cho đường tắt, có thể tăng thời gian/chi phí và thay đổi điểm. Ledger
hiện có vẫn áp dụng; chưa có chứng nhận tài nguyên hoặc điểm mới.
