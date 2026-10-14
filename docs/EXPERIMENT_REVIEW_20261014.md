# Đánh giá thực nghiệm ngày 14/10/2026

Lần chạy được đọc khi bắt đầu: `outputs/runs/20261014-162415-1a02a9`, Public, Qwen `qwen/qwen3.7-flash`. 19/20 khớp file mẫu; mọi câu có trạng thái `ok`, nhưng một câu sai vẫn được đánh dấu `validated=true`. Kiểm tra cấu trúc không chứng minh đúng ngữ nghĩa.

## Lỗi có bằng chứng

| Trường hợp | Sai ở đâu | Thay đổi |
|---|---|---|
| `p4_q008`: 28 thay vì 9017 | Chỉ trừ B11−B9, cột khai khoáng. Câu hỏi yêu cầu tất cả ngành B–M. Tổng hai dòng là 14564 và 5547. | `sum_columns` cộng ngang cột được chỉ định; kiểm tra một số kế hoạch scalar thiếu phạm vi và yêu cầu LLM sửa. |
| `p4_q012` trong lượt kiểm tra đầu: 86 thay vì 35 | Cộng E7:E16 gồm Total và chi tiết, cả nhóm 16–19 lẫn các nhóm con 16–17/18–19. | Sum từ chối cộng Total cùng chi tiết; prompt yêu cầu dùng Total hoặc phân hoạch không chồng lặp. |
| `p4_q007` trong lượt kiểm tra thứ hai: đáp án trống | Aggregate bỏ `input` ba lần, lỗi cũ chỉ nói `Row dataset does not exist: None`. | Schema riêng cho mỗi thao tác, trường bắt buộc, lỗi nêu tên bước và dataset khả dụng. |
| `p4_q004` trong lượt kiểm tra thứ ba: số thay vì No | Trả giá trị 2024 mà chưa so sánh với 2023. | Kiểm tra câu yêu cầu Yes/No và yêu cầu kế hoạch trả phép so sánh boolean. |
| `p4_q010` trong lượt kiểm tra thứ ba: đáp án trống | Unpivot rồi lọc cột A đã bị bỏ; sau đó nhầm nhãn ngành với nhãn nhóm tuổi. | `unpivot.keep_columns`, hướng dẫn lọc dòng trước khi unpivot và thông báo lỗi nêu cột hiện có. |

Preview bỏ văn bản lặp của các ô trong vùng gộp nhưng giữ giá trị mở rộng cho công cụ, cùng tọa độ và thông tin merge. Log mới lưu preview, trace/lỗi của từng kế hoạch, model/cấu hình an toàn và SHA-256 mã nguồn/Excel/câu hỏi. `scripts/analyze_run.py` tạo báo cáo so sánh, chỉ so câu hỏi và reference không đổi.

## Kết quả sau thay đổi

Không chọn riêng câu tốt: mỗi lượt dưới đây chạy đủ 20 câu Public. Các lượt giữa dùng các phiên bản đang sửa khác nhau.

| Lần chạy | Khớp | Chi phí thực tế USD |
|---|---:|---:|
| Baseline `20261014-162415-1a02a9` | 19/20 | 0.009420700 |
| `20261014-164032-5ab091` | 19/20 | 0.009679248 |
| `20261014-164454-a8d453` | 19/20 | 0.009540366 |
| `20261014-164959-5e3b8e` | 18/20 | 0.011224092 |
| Final `20261014-165436-35b78c` | 20/20 | 0.009932218 |

Lần cuối: 27 lượt API, 383319 token, 93.015 giây xử lý CLI, khoảng 97.8 giây từ lúc dashboard bắt đầu đến khi hoàn thành; peak memory tiến trình CLI khoảng 81.98 MB. So baseline, cải thiện `p4_q008`, không có regression trong lần cuối. Token và chi phí tăng nhẹ; chưa chứng minh tối ưu tốc độ/chi phí.

Tất cả log được giữ ở `outputs/runs/`. Báo cáo cuối ở `outputs/runs/20261014-165436-35b78c/analysis.json`; danh sách câu sai rỗng. `run_context.json` lưu hash cả mã chưa commit, không chỉ Git revision. Có thể chọn lần chạy này trên dashboard.

## Kiểm tra và giới hạn

36 kiểm tra tự động đã qua, gồm replay 19 kế hoạch baseline đúng, từ chối kế hoạch thiếu cột/cộng đôi, sửa Yes/No, giữ nhãn và căn cứ sau unpivot, bảo vệ log khỏi API key, và phân biệt sửa đáp án mẫu với cải thiện solver.

Đây là một lần chạy cuối khớp mẫu, không bảo đảm kết quả ổn định ở mọi lần gọi hoặc trên tập ẩn. Các lượt trung gian cho thấy LLM có thể dao động dù temperature=0. Chưa chạy online 212 câu Test trong lần nâng cấp này. Kiểm tra phạm vi áp dụng thận trọng cho kế hoạch scalar và bảng không có Total riêng; vẫn có thể bỏ sót lỗi chọn nhóm tuổi, ngành, đơn vị hoặc tổng chồng lặp khi không có nhãn Total.

Không đọc sample_submission hay expected_submission trong bộ giải. Đáp án tham chiếu chỉ dùng sau chạy để đánh giá. Snapshot reference của các log cũ vẫn giữ nguyên; ví dụ bộ smoke cũ từng có đáp án tuổi sai, không được coi đó là lỗi solver nếu Excel cho đáp án khác.
