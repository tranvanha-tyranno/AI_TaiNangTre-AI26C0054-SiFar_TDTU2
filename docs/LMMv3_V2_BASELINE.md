# LMMv3 — bắt đầu lại từ LLMv2

Phiên bản hiện tại: `lmmv3-v2-baseline-v1`, nhánh `Bao_LMMv3`.

Theo yêu cầu bắt đầu lại, `--mode llm-v3` hiện dùng **chung đường xử lý và cùng cấu hình vận hành với llm-v2 hiện có trong repo**. Đây chưa phải bản cải tiến. Không tự áp dụng cấu hình Lite hoặc pipeline tám phase. Không khẳng định mã LLMv2 hiện tại giống hệt phiên chạy lịch sử 16/30, hoặc chắc chắn đạt lại số điểm đó.

Cả hai chế độ dùng `src/pipeline.py`; `src/variants.py` cấp chung cấu hình LLMv2: tối thiểu 6 API calls, 3 repairs, 3 inspections, review all, top_k ít nhất 6, preview ít nhất 60 như trước. LMMv3 chỉ có marker v3_base_variant=llm-v2 và pipeline_version riêng để theo dõi. Không thêm lượt đặc tả riêng, coverage gate hay cache/prompt mới.

## Sử dụng

Khởi động lại dashboard hiện có rồi chọn **LMMv3 · baseline từ LLMv2**. CLI vẫn dùng `--mode llm-v3`; chọn `--mode llm-v2` để chạy LLMv2 riêng. Hai lựa chọn hiện cùng thuật toán; khác biệt giữa các run có thể đến từ API/model chứ chưa phải một cải tiến.

Chưa chạy API hoặc dataset trong lần khôi phục. Kiểm tra giả lập xác nhận cấu hình vận hành và nội dung request giống nhau giữa hai chế độ.

## Lịch sử được giữ

- Bản tám phase: `src/lmmv3/pipeline.py`, tài liệu `docs/LMMv3.md`.
- Lite: `src/lmmv3/lite.py`, commit `4aa8d87`, tài liệu `docs/LMMv3_LITE.md`.
- Chúng được giữ để xem lại; không được CLI tự gọi trong baseline hiện tại. Các run cũ không bị xóa hay đổi nhãn phiên bản.

## Phát triển tiếp

Đầu tiên đo mốc LLMv2 trên dữ liệu độc lập. Sau đó mỗi lần chỉ thay một nhóm năng lực, giữ chế độ baseline đối chứng. Ưu tiên lỗi có bằng chứng, không thêm lại toàn bộ kiến trúc cũ một lượt và không sửa theo ID/tên file/đáp án public. So sánh độ đúng trước, rồi thời gian/token/chi phí. Chỉ kết luận cải thiện sau kiểm chứng.
