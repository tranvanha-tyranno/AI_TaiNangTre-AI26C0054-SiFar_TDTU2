# Sửa lỗi đáp án trả dư giá trị và thiếu tổng — 14/10/2026

Baseline: `outputs/runs/20261014-170251-4f423d`, bộ `06_people_filters`, 26/30 khớp đáp án mẫu.

| Câu | Lỗi đã quan sát | Đáp án đúng |
|---|---|---|
| 06_q011 | Lọc đúng 8 người Engineering/Active, nhưng trả từng Score thay vì tổng | 560 |
| 06_q019 | Hỏi vị trí 1 nhưng trả cả 40 ID đã sắp xếp | P023 |
| 06_q021 | Hỏi vị trí 3 nhưng trả cả 40 ID đã sắp xếp | P036 |
| 06_q023 | Hỏi top 3 nhưng trả 32 ID. `output.limit=3` bị bộ thực thi cũ bỏ qua | P023, P013, P036 |

Các kế hoạch này từng được đánh dấu validated: bộ kiểm tra chỉ nhận dạng `Answer with only`, chưa bao phủ `Answer only`, tiếng Việt và số phần tử của top K. Đây là lỗi bộ kiểm tra, bên cạnh bước tính bị thiếu trong kế hoạch LLM.

## Thay đổi

- `src/answer_contract.py` suy ra dạng đáp án chỉ từ câu hỏi: scalar/list, số phần tử, vị trí, phép tổng/trung bình/đếm, số thập phân, Yes/No. Thông tin này được đưa vào prompt và lưu ở `answer_contract` trong log.
- Kiểm tra số phần tử thực tế trước khi chấp nhận. Không đếm bằng cách tách chuỗi theo dấu phẩy: tên `O'Neil, Jr.` vẫn là một giá trị.
- Kiểm tra kế hoạch thực sự dùng `take` đúng offset/limit khi trả vị trí/top K từ kết quả sort. Không tự cắt danh sách đầu ra để che sai vị trí.
- Kết quả tổng không được là các dòng chưa cộng. Có thể dùng aggregate sum hoặc ô Total in sẵn đúng phạm vi. Từ Total trong nhãn được trích dẫn không tự biến một câu lookup thành yêu cầu cộng lại.
- Bộ thực thi từ chối trường output không hỗ trợ; limit/offset phải là tham số của bước take. Không còn âm thầm bỏ qua chúng.
- Lỗi cộng Total cùng chi tiết nêu nhãn/dòng/địa chỉ ô Total để LLM có thông tin sửa. Prompt nói rõ Total có sẵn là kết quả hợp lệ, không bắt buộc cộng lại.
- Báo cáo phân biệt lỗi API với regression của bộ giải. Exact match vẫn tính đáp án trống là không khớp, nhưng danh sách regression không gộp câu chưa được chạy vì API lỗi vào lỗi suy luận.

## Kết quả và giới hạn

| Lượt | Kết quả | Chi phí API ghi nhận |
|---|---:|---:|
| People baseline 17:02:51 | 26/30 | $0.011695296 |
| People mới `20261014-171811-d116aa` | 30/30 | $0.011222214 |
| Public kiểm tra `20261014-171956-0177c1` | 19/20 | $0.011003246 |
| Public sau sửa thông báo Total `20261014-172439-8b308d` | Không đánh giá được bộ giải: 20 HTTP 402 | Usage/chi phí không được API trả, không kết luận miễn phí |

People: 4 câu được sửa, 0 regression, API calls 38 → 36, token 403896 → 388701, CLI 104.672 → 101.781 giây, thời gian dashboard khoảng 104.33 giây. Xem `outputs/runs/20261014-171811-d116aa/analysis.json`.

Public: 19 câu đúng, câu p4_q012 bị từ chối do LLM lặp lại phép cộng Total+chi tiết. Thông báo lỗi và prompt đã được làm rõ; kiểm tra sửa bằng client giả xác nhận kế hoạch sau đó có thể dùng ô Total và trả 35. Chưa xác nhận việc sửa này với LLM online: API credits trả về số dư đã hết, lượt cuối bị HTTP 402. Không có tuyên bố Public bản cuối đạt 20/20.

46 kiểm tra tự động qua. Replay bằng mã hiện tại chấp nhận 26 kế hoạch People đúng, từ chối cả 4 kế hoạch sai và chấp nhận 20 kế hoạch đúng của lần Public trước nâng cấp. Các bộ Test khác chưa được đánh giá online trong lượt này. Nhận diện câu hỏi vẫn là heuristic, không bảo đảm mọi cách diễn đạt hoặc mọi lỗi ngữ nghĩa.
