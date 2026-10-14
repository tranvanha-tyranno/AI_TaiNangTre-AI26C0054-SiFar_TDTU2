# Mốc chạy đầu tiên

## Đã có
- CLI nhận đường dẫn Excel, câu hỏi và đầu ra.
- Bộ giải cục bộ cho các dạng dữ liệu công khai hiện tại.
- Nhánh LLM trực tiếp qua OpenRouter, cấu hình bằng ENV hoặc .env.
- Nhật ký từng câu và báo cáo so sánh CSV.

## Pipeline mục tiêu cần triển khai tiếp
1. Nhận diện nhiều bảng/sheet, giữ tọa độ ô và ngữ cảnh tiêu đề.
2. Retrieval chọn bảng; không cắt mất dữ liệu dùng để tính toán.
3. LLM tạo kế hoạch JSON được kiểm tra theo schema.
4. Bộ công cụ cố định thực hiện kế hoạch trên toàn bộ dữ liệu liên quan.
5. Kiểm chứng, retry có giới hạn, theo dõi chi phí và bộ nhớ.

Bản đầu hiện chưa triển khai RAG + planner + tool execution tổng quát. Nhánh LLM trực tiếp có cắt ngắn dữ liệu, không phù hợp để chứng minh độ chính xác trên bảng lớn. Kết quả khớp sample không chứng minh khả năng trả lời tập ẩn. Chưa xác minh giới hạn bộ nhớ, chi phí và thời gian online.

## Kết quả chạy 14/10/2026
- Môi trường .venv đã cài đủ thư viện; phiên bản lưu tại requirements-lock.txt.
- Offline: đủ 20 dòng, so sánh file mẫu khớp 20/20, khoảng 0.3 giây xử lý (không gồm khởi động Python).
- Kiểm tra CLI: đầu ra/nhật ký và từ chối ID trùng đều qua.
- Thử một câu online: OpenRouter trả HTTP 400 vì `qwen/qwen3-7-flash` không phải model ID hợp lệ. Chưa có đáp án online; không tự đổi model quy định.
