# Giới hạn thời gian và điều kiện thực thi

Nguồn: AGENTS.md, mục 4 của đề thi và [giải đáp BTC](docs/AI2026_Giai_dap_thac_mac_Vong_khu_vuc_bang_C.pdf), câu 03–07. Cập nhật ngày 16/10/2026. Dùng các giới hạn này làm tiêu chí khi thiết kế, triển khai và đánh giá giải pháp; đây không phải chứng nhận mã nguồn hiện tại đã đáp ứng.

- Model trong hướng dẫn nộp bài là `qwen/qwen3.7-flash`; dùng model và base URL do BTC truyền qua CLI, ưu tiên trên ENV/config. Cách viết `qwen/qwen3-7-flash` trong tài liệu cũ được thay bằng tên chính thức này.
- Cấu hình thông tin truy cập API từ bên ngoài; không hard-code hoặc commit khóa API.
- Tổng chi phí LLM không vượt quá 0.10 USD/câu hỏi cho mỗi lần chấm, bao gồm retry; BTC xác định theo mức sử dụng API ghi nhận.
- Tối đa 40 phút cho 20 câu hỏi, từ khi bắt đầu chạy đến khi tạo xong `submission.csv`, bao gồm xử lý dữ liệu và gọi API. Đây là giới hạn tổng thời gian, không phải hạn cứng 2 phút cho từng câu.
- Máy chấm: 6 core vCPU, 12 GB RAM.
- Giải đáp câu 03 đính chính: tổng dung lượng **đĩa (disk) ≤ 1 GB**, tổng **RAM ≤ 4 GB**. Không còn áp dụng cách hiểu “RAM ≤ 1 GB”; 12 GB là RAM máy chấm. Phạm vi tính disk chưa được mô tả chi tiết; cần đối chiếu template/hướng dẫn tiếp theo.
- Tệp ZIP nộp bài không vượt quá 100 MB.
- Thời gian build Docker (gồm tải/cài) không tính vào thời gian chạy chính thức. Không tự miễn thời gian tiền xử lý trong runtime.
- Được xử lý/gửi request song song trong tài nguyên được cấp; PDF chưa nêu rate limit cụ thể.
- Chỉ dùng Internet để install và gọi OpenRouter API. Được dùng bất kỳ công cụ AI khi phát triển; giải pháp cuối chỉ dùng AI/LLM do BTC cung cấp.
- Token xếp hạng theo giải đáp câu 06: **input + reasoning**. Giữ riêng usage API và chi phí; chưa có giải đáp đầy đủ về output không phải reasoning hoặc cách đo thời gian trung bình.
- Vi phạm một trong các giới hạn trên: bài không được chấm điểm.

Ưu tiên xếp hạng: Exact Match, sau đó thời gian trung bình/câu, sau đó token LLM trung bình/câu.

Các ràng buộc I/O được làm rõ: CSV UTF-8, ID số tự nhiên khi chấm, dòng theo ID tăng dần, câu không trả lời được ghi chuỗi rỗng. BTC có chuẩn hóa đáp án, nhưng chưa công bố mã chuẩn hóa; công cụ so chuỗi nội bộ không đại diện hoàn toàn cho bộ chấm. Xem AGENTS.md mục 11–12 để biết quy ước mean “across all…” và danh sách điểm mã nguồn cần cải tiến.
