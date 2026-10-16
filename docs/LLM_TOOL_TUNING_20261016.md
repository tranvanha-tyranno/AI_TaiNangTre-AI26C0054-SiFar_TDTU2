# Rà soát ba run mới và nâng LLM + Tools — 16/10/2026

Phạm vi: đọc toàn bộ câu hỏi, kế hoạch, lỗi kiểm tra, lượt review và usage của ba run gần nhất tại thời điểm bắt đầu. Không đưa đáp án tham chiếu vào planner hoặc executor. Các CSV tham chiếu chỉ dùng để chấm sau khi chạy.

## Ba run gốc

| Run | Dataset / chế độ | Exact Match | Thời gian | Lượt API | Chi phí API đã xác nhận |
|---|---|---:|---:|---:|---:|
| `20261016-112100-6d1b8b` | Public 1 / llm | 18/20 | 117.95 s | 32 | $0.013409402 |
| `20261016-095601-6a457d` | Public 2 / llm | 15/30 | 296.08 s | 74 | $0.025625620 |
| `20261016-100848-d609af` | Public 2 / llm-v2 | 13/30 | 485.84 s | 124 | $0.056907212 |

Không có câu lỗi API trong ba run này. Tăng số lượt gọi/review ở v2 đã tăng thời gian và chi phí nhưng giảm điểm; vì vậy giữ `llm` làm mặc định, không tăng vòng sửa một cách đồng loạt.

Các báo cáo đầy đủ theo từng câu nằm trong `outputs/tuning-20261016/audit/`. Log gốc được giữ nguyên.

## Lỗi và thay đổi

| Nhóm lỗi quan sát được | Ví dụ trong log gốc | Thay đổi chung |
|---|---|---|
| Không hiểu số tài chính dạng chuỗi | Public 2: 21, 22, 24 gặp `$1,882`, số âm kế toán | Đọc ký hiệu tiền, dấu âm Unicode, ngoặc kế toán, khoảng trắng phân nhóm; vẫn từ chối ký hiệu thiếu dữ liệu và dấu phân cách mơ hồ. |
| Thiếu thao tác so với kỳ trước | Public 2: 6 sinh `prev`, `shift` ngoài schema | Thêm `lag` với offset hữu hạn và nguồn ô của dòng trước. Cần lọc đúng kỳ và sắp xếp trước khi lag. |
| Làm mất tên nhóm hoặc tên sheet | Public 2: 1, 12, 15; câu 23 trả riêng số | `record` ghép các scalar thành một dòng; `read` có `_section`, `_section_row`, `_sheet`; thêm `fill_down`, `if`, `trim`, `length`, `round`. Nhãn có nguồn ô, không nhận literal số làm đáp án. |
| Chấp nhận thiếu thành phần hoặc ép nhãn thành số | Public 2: 2, 7, 10, 14, 23 | Nhận dạng template `nhãn, số`; kiểm tra cardinality và từng vị trí số; định dạng số không làm hỏng tên nhóm. |
| Suy luận phép tính từ tên metric | `average hours`, `total labor force` nhưng câu hỏi yêu cầu tên nhóm/năm | Phân biệt metric với kết quả được hỏi; tránh ép argmax/lookup thành mean/sum. |
| Không kiểm tra quy mô toàn ngành | Public 1: `p4_q008` trả 28 thay vì 9017 dù `validated=true` | Chặn cách lấy một cột bằng `read` một dòng rồi bọc `aggregate sum` để vượt kiểm tra phạm vi ngang. |
| DSL lặp lỗi dù đã có phản hồi | `ref` dùng cho cột, unary nhận object, sum boolean, steps bị JSON-encode lần hai | Chuẩn hóa cách viết tương đương, giữ raw plan và danh sách thay đổi. Sửa giới hạn dấu đóng container ngoài string; không sinh khóa, giá trị, phép tính hoặc hoàn tất JSON bị cắt. |
| Phản hồi sửa thiếu ngữ cảnh | Nhiều lượt lặp lại cùng kế hoạch sai | Gửi thêm các lỗi gần nhất, trace và mẫu dòng của lần tính trước. Preview giữ nhãn section thay vì lặp danh sách 500 dòng đầu. |
| Review tiêu hết lượt gọi | v2 review lặp hai lần, một số ứng viên bị mất do hết ngân sách review | Một review cho mỗi ứng viên. Review tùy chọn không khả dụng được ghi log; ứng viên đã qua kiểm tra xác định có thể được giữ. Review yêu cầu sửa vẫn phải xử lý. |
| Rủi ro dự toán giá theo context | Model catalog có nhiều bậc giá | Dự toán theo bậc giá cao nhất được công bố, ghi usage và chi phí thực tế như trước. |

`llm_seed: 42` được truyền khi model catalog công bố hỗ trợ `seed`; ghi seed trong từng call và run context. Seed là yêu cầu tới provider, không phải cam kết kết quả lặp tuyệt đối.

Theo hướng dẫn BTC mới xuất hiện trong `AGENTS.md` trong lúc làm việc, câu không trả lời được xuất `answer` rỗng. Ứng viên đã bị kiểm tra từ chối chỉ nằm trong log chẩn đoán; không xuất `N/A` hoặc âm thầm dùng ứng viên đó làm đáp án. Kiểm thử CLI xác nhận CSV vẫn có đủ một dòng cho câu lỗi và exit code 3.

## Kết quả kiểm chứng

| Lượt chạy thật, mã cuối `tools-v4` | Exact Match | Thời gian gồm khởi tạo | API calls | Phí API thực | Peak RAM tiến trình |
|---|---:|---:|---:|---:|---:|
| Public 1 / llm | 19/20 | 152.81 s | 30 | $0.01263403 | 83.7 MB |
| Public 2 / llm | 26/30 | 232.64 s | 55 | $0.01773606 | 89.7 MB |
| Probe / lần 1 với seed model | 6/6 | 50.58 s | 14 | $0.00314130 | 76.2 MB |
| Probe / lặp cùng seed | 4/6 | 60.08 s | 17 | $0.00370885 | 76.1 MB |

Bảng dùng lượt cuối đã chạy đủ câu, không lấy lượt tốt nhất. Public 1 từng đạt 20/20 ở các lượt trước trong phiên; lượt cuối đạt 19/20. So với ba run gốc, Public 2 `llm` tăng từ 15/30 lên 26/30. Đây là khớp các CSV mẫu đã cung cấp, không phải điểm tập ẩn.

Các lượt cuối: `outputs/tuning-20261016/seeded-public1`, `seeded-public2`, `seeded-probe`, `seeded-probe-repeat`; mỗi thư mục có `submission.csv`, `evaluation.json` và `logs/`. `verification.json` lưu số liệu tổng hợp, từng câu sai và kiểm tra hash mã nguồn. Cả bốn run khớp mã nguồn hiện tại tại lúc kiểm chứng.

Chi phí câu cao nhất đo được là $0.001841926, gồm mọi lượt gọi của câu đó, dưới $0.10. Đây là phép đo local; RAM ghi riêng từng tiến trình. Một số run được thực hiện đồng thời, mỗi run đặt concurrency=1. `estimated_cost_usd` dùng bậc giá bảo thủ nên có thể cao hơn phí API thực nhiều lần.

Kiểm thử: **95 Python tests qua**, gồm các fixture mà workspace bổ sung trong lúc làm việc; `node tests/chart_math.cjs` qua; `git diff --check` không báo lỗi whitespace. CSV đủ 20/30/6/6 dòng, đúng header, không có ID thừa. Các run có câu lỗi vẫn tạo CSV với trường đáp án rỗng; không xem chúng là lượt hoàn thành toàn bộ câu trả lời.

Độ lặp probe: **4/6 đáp án giống nhau** giữa hai lượt cùng code, đầu vào, temperature=0 và seed=42. Lượt đầu của probe trước các chỉnh sửa đạt 3/6; hai lượt cuối đạt 6/6 và 4/6. Kết quả này chưa đủ để tuyên bố model ổn định; seed không loại hết biến động ở provider.

Lỗi còn lại ở lượt cuối:

- Public 1 `p4_q011`: câu Yes/No bị từ chối vì model lặp `answer_field=null`; CSV để trống.
- Public 2 `15`: trả nhãn lớp quy mô thay vì ngành; `17`: JSON lỗi lặp lại, CSV trống; `23`: chọn sai sheet/giá trị so sánh; `30`: bỏ phép trừ trong câu tiếng Trung và trả riêng một ô.
- Probe lặp: câu 4 (nhãn + chênh lệch) và 5 (mã sáu chữ số, ô thiếu) chưa tạo được ứng viên hợp lệ, CSV để trống.

Các câu 15, 23 và 30 của Public 2 vẫn có `validated=true` dù khớp mẫu sai. Đây là giới hạn kiểm tra ngữ nghĩa hiện tại, không phải lỗi đã được giải quyết. V2 được cải thiện ở các lượt trung gian nhưng chưa có benchmark cuối với cùng toàn bộ thay đổi; không suy ra điểm v2 cuối từ điểm của llm.

## Khả năng dùng cho dữ liệu mới

Đây là cải tiến prompt, hợp đồng tool và phản hồi trong từng câu hỏi; không fine-tune trọng số hoặc tự học đáp án giữa các dataset. Solver không đọc các file expected/sample submission. Không thêm bộ nhớ đáp án theo tên file hay ID câu hỏi.

`scripts/gen_generalization_probe.py` tạo sáu bài độc lập với số tiền ngẫu nhiên, năm đảo thứ tự, nhãn section mới, template nhãn/số, mã có số 0 đầu và câu tiếng Hàn. Chạy bằng seed mới để kiểm tra hồi quy khi đầu vào thay đổi. Probe được thiết kế theo các nhóm lỗi đã thấy; không đại diện cho tập kiểm thử ẩn. Điểm lần đầu được giữ riêng với các lượt sau khi tinh chỉnh.

Các unit test kiểm tra thay đổi giá trị làm thay đổi đúng đáp án, nguồn ô của nhãn và giá trị lag, không mất số 0, mã sáu chữ số, precision, từ chối literal bịa, chuẩn hóa không đoán cột/scalar chưa tồn tại và không xuất ứng viên bị từ chối.

Model vẫn có thể chọn sai dòng, kỳ, cột, nhóm cha/con hoặc phép tính dù kế hoạch chạy được. `validated=true` không phải chứng minh câu trả lời đúng. Các lượt chạy lại trong cùng phiên cho thấy chất lượng biến động; không sử dụng lượt tốt nhất để tuyên bố hệ thống đã ổn định trên dữ liệu chưa thấy.

## Chạy lại

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
node tests/chart_math.cjs
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir Public_data_2/xlsx_files --queries Public_data_2/queries.json --output outputs/recheck/submission.csv --log-dir outputs/recheck/logs
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/recheck/submission.csv --reference Public_data_2/sample_submission.csv
.\.venv\Scripts\python.exe scripts/gen_generalization_probe.py --output outputs/probe-new --seed 9461
```

`scripts/replay_run.py` phát lại các kế hoạch đã lưu với tool/validator mới, không gọi API. Replay không mô phỏng planner hoặc semantic review mới; không cộng điểm replay vào kết quả chạy thật. Dữ liệu probe, audit và các run phát triển nằm trong `outputs/tuning-20261016/`, không thuộc gói nộp bài mặc định.
