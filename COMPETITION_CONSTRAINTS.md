# Giới hạn thời gian và điều kiện thực thi

Nguồn: AGENTS.md, mục 4 của đề thi. Dùng các giới hạn này làm tiêu chí khi thiết kế, triển khai và đánh giá giải pháp.

- Nếu dùng LLM để trả lời, phải hỗ trợ model `qwen/qwen3-7-flash` qua OpenRouter theo đề thi.
- Cấu hình thông tin truy cập API từ bên ngoài; không hard-code hoặc commit khóa API.
- Tổng chi phí LLM không vượt quá 0.10 USD/câu hỏi cho mỗi lần chấm, bao gồm retry; BTC xác định theo mức sử dụng API ghi nhận.
- Tối đa 40 phút cho 20 câu hỏi, từ khi bắt đầu chạy đến khi tạo xong `submission.csv`, bao gồm xử lý dữ liệu và gọi API. Đây là giới hạn tổng thời gian, không phải hạn cứng 2 phút cho từng câu.
- Máy chấm: 6 core vCPU, 12 GB RAM.
- Tổng bộ nhớ sử dụng khi chạy trên tập kiểm thử không vượt quá 1 GB; không được coi 12 GB RAM của máy là ngân sách bộ nhớ của bài.
- Tệp ZIP nộp bài không vượt quá 100 MB.
- Vi phạm một trong các giới hạn trên: bài không được chấm điểm.

Ưu tiên xếp hạng: Exact Match, sau đó thời gian trung bình/câu, sau đó token LLM trung bình/câu.
