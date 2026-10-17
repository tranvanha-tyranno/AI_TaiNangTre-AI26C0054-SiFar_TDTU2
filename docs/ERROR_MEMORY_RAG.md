# RAG học từ log lỗi

## Cập nhật 17/10/2026 — hai public đạt 50/50 sau nâng cấp truy xuất

Theo yêu cầu người dùng, tiếp tục phân tích lỗi trên hai bộ public. Bản hiện tại là `lmmv3-v2-error-memory-v3`. Đây là cải tiến hồi quy trên dữ liệu đã dùng sửa; các kết quả holdout thấp bên dưới vẫn có giá trị, chưa có đánh giá holdout mới.

Lượt trước sửa `outputs/public-goal/run02/` đạt Public_data_1 **20/20**, Public_data_2 **29/30**. Trace câu so sánh giờ cho thấy dòng/section đúng nhưng một toán hạng lấy nhầm trạng thái việc làm dưới header phân cấp. Reviewer tập trung sửa filter rỗng rồi chấp nhận cặp cột sai. Bài học `header_column_mapping` đã có nhưng bị các bài học chung chiếm top 3.

Thay đổi: bài học có tín hiệu câu hỏi phù hợp và `column_hierarchy` nhiều cấp được cộng điểm cấu trúc; cấu trúc đơn lẻ không kích hoạt bài học không liên quan. Bài học yêu cầu kiểm tra đầy đủ đường dẫn header cho từng toán hạng ngay cả khi dòng và phép tính đúng. `complete_read_scope` không còn nhận nhầm “how many hours/more/percent/thousand” thành đếm toàn bộ dòng. Snapshot vẫn 22 family, tăng support của family đã xác minh thêm một trường hợp; không lưu đáp án, ID, tên file hoặc tọa độ mẫu vào memory. Giữ giới hạn top 3/3600 ký tự, API, repair và ngân sách hiện tại.

Lượt sau sửa `outputs/public-goal/run03/` chạy lại toàn bộ bằng `qwen/qwen3.7-flash`, concurrency 1, thông qua CLI hiện tại và wrapper đánh giá phát triển. Reference chỉ được wrapper so sánh sau khi solver trả kết quả, không truyền vào solver. Trace chỉ in terminal, CLI nộp bài vẫn chỉ ghi CSV.

| Bộ | Strict exact match | Thời gian CLI | Chi phí thực được ledger ghi nhận, làm tròn |
|---|---:|---:|---:|
| Public_data_1 | 20/20 (100%) | 132,5 giây | $0,017157 |
| Public_data_2 | 30/30 (100%) | 360,9 giây | $0,053837 |

Hai CSV cuối đã được đối chiếu độc lập: đúng header, đủ ID duy nhất, ID số tăng dần và tất cả answer khớp nguyên văn. Không ghép điểm từ chạy con. `python -m unittest discover -s tests -q`: **118 tests qua**, gồm kiểm tra header đổi vị trí, không kích hoạt bài học từ cấu trúc không liên quan và phân biệt lượng chênh lệch với đếm dòng. Không có benchmark Docker/RAM/disk mới trong lần này; 100% mô tả lượt public này, không chứng minh tập ẩn hoặc mọi lần chạy.

## Generalization holdouts — stopped after regression evidence

Đã thử các bộ mới chưa dùng để đạt Public_data_2: suite 23 civic service **26/30** baseline, suite 24 procurement/temporal **10/30**, suite 25 energy intervals **13/30**, suite 26 logistics/event versions **6/30**. Sau khi thêm bài học từ suite 23, chạy lại suite 23 giảm còn **22/30**, nên không coi việc thêm memory là cải thiện tổng quát. Bộ gộp 28 có 150 câu nhưng chạm timeout 40 phút sau 60 câu; kết quả đó không được dùng làm điểm.

Các holdout này cho thấy lỗi còn thuộc các lớp mới: nhiều bảng/join và cột dẫn xuất sau join, dữ liệu tài chính dạng chuỗi, thời gian/sự kiện version, tuple/list formatting và chọn đúng metric trong workbook dài. Việc tiếp tục thêm rule từ từng suite làm tăng rủi ro overfit và không có bằng chứng giữ điểm trên suite khác. Đã giữ các report/evaluation riêng trong `outputs/error-memory/` và không dùng expected answers trong runtime.

Điểm dừng được chọn sau bốn holdout mới có kết quả thấp và một lần hồi quy trực tiếp. Public_data_2 vẫn có run 30/30 (`20261017-015942-public2goal`), nhưng đó là bộ đã dùng để điều chỉnh. Muốn nâng tổng quát hóa tiếp cần thay đổi kiến trúc retrieval/plan grounding hoặc huấn luyện/evaluate theo split mới, không tiếp tục nạp bài học theo ID/câu hỏi. Không chạy thêm API trong vòng này.

## Public_data_2 đạt 30/30 — 17/10/2026

Run API đầy đủ **`20261017-015942-public2goal`** đạt **30/30 strict exact match (100%)** theo `Public_data_2/sample_submission.csv`, không ghép kết quả từ run khác. Giữ mode `llm-v3`, model thực tế từ môi trường `qwen/qwen3.7-flash`, snapshot 21 family SHA-256 `122656d966c8aaa9143c5307a5e76c27ea81d412788dfd1d1f9f466d74986452`. Đây là bộ public đã dùng điều chỉnh solver, không chứng minh 100% trên tập ẩn hay các lần chạy tiếp theo.

Đã trải qua các lượt đầy đủ 29/30, 29/30, 28/30, 29/30 rồi 30/30; mỗi lượt giữ riêng log, source fingerprint và memory hash. Thay đổi cuối gồm:

- Chuẩn hóa cú pháp đã khai báo: literal nằm nhầm cạnh binary operator được đưa vào mảng toán hạng; các predicate tách nhiều key được gom thành conjunction; bỏ field `missing` không được định nghĩa cho filter. Chỉ bật qua RAG v3, ghi raw plan và normalization. Không đổi cột/ngưỡng/toán tử hay đưa đáp án vào plan.
- Guard nhận diện lỗi so sánh cột toàn số với chuỗi nhãn; yêu cầu model kiểm tra header và row/column axis. Thêm bài học horizontal series và mapping header phân cấp.
- Reviewer không còn nhận phần GUIDANCE thực thi của planner; được nhắc kiểm tra plan cuối, các filter downstream và căn cứ cụ thể. Không đổi revise thành accept để đạt điểm và không trả ứng viên đã bị từ chối.
- V3 có RAG cho phép tối đa 8 lượt API/4 sửa plan, vẫn chung ledger $0.10/câu, timeout và model cũ. `llm`/`llm-v2` giữ cài đặt trước đó.

Kết quả run đạt 100%: thời gian pipeline **321,2 giây**, từ launcher tới kết thúc **327,6 giây**, **91 lượt API**, chi phí usage ghi nhận **$0.051482054** cho 30 câu. Tổng token API **1.460.607**, input+reasoning **1.440.422**; không đồng nhất hai chỉ số. RAM báo cáo là peak riêng main process, không phải chứng nhận cả container/disk.

Artifacts tại `outputs/runs/20261017-015942-public2goal/`: `submission.csv`, `strict-evaluation.json`, `analysis.json`, `questions.jsonl`, `summary.json`, `run_context.json`. Import lỗi trung gian từ chính run này không đổi hash snapshot. Toàn bộ 190 test offline đã qua trước run; lần xác minh cuối ghi trong log công việc.

## Học bổ sung từ run 20261017-005400-c32298

Run hoàn tất mới nhất tại thời điểm cập nhật gồm 50 câu của `public,public_data_2`, đạt **48/50 strict exact match**. Đã phân tích 30 bản ghi có lỗi cuối hoặc lỗi trung gian đã phục hồi. Hai câu không có đáp án cuối là `public_data_2::9` và `public_data_2::14`. Tên/ID này chỉ dùng báo cáo đánh giá, không đi vào catalog hướng dẫn hoặc bộ nhớ runtime.

Đối chiếu từng plan, trace, row sample, review với workbook:

- Câu 9: hai lượt đầu cấu trúc predicate sai (literal đứng ngoài array); sau đó filter đúng đã chọn một dòng thỏa cả hai bất đẳng thức. Reviewer phản đối không nhất quán với operator và số liệu thực tế, rồi trả revise không có issue. Bản chạy cuối bị từ chối ở review. Không lấy phản đối này làm bằng chứng cần đổi điều kiện hay đáp án.
- Câu 14: lượt đầu thiếu guard numeric nên đụng header/missing. Các lượt sau đã có guard ở cả hai operand, loại Total, chỉ còn hai dòng tính được; gap được sort/take đúng. Reviewer vẫn nhìn read ban đầu và cho rằng header đã vào phép trừ, bỏ qua filter trong dependency chain. Nhãn output còn padding cần trim theo yêu cầu. Sau inspect/repair/review, run hết lượt gọi và xuất rỗng.

Kho đã tăng từ **15 lên 19 family**: `threshold_semantics`, `header_missing_filter`, `review_evidence_consistency`, `final_output_binding`. Bài học reviewer yêu cầu căn cứ cụ thể từ trace, không cho phép bỏ qua validation/review hay tự chốt ứng viên bị từ chối. Nhóm cú pháp cũng nhận diện thêm lỗi `Expression must have one key`. Snapshot vẫn chỉ gồm lesson ID/support, giữ family cũ khi merge; support là số tín hiệu của corpus, không phải điểm đúng hoặc xác nhận mọi review là đúng.

Đã kiểm tra truy xuất offline: câu ngưỡng nhận threshold/cú pháp ở plan, thêm kiểm chứng review ở repair; câu gap nhận lọc header/missing ở plan và kiểm chứng review ở repair. Mỗi request vẫn tối đa 3 bài học, dưới 3600 ký tự. Model đọc qua đường request hiện có của `llm-v3`; không đổi model, API budget hoặc review policy trong lần cập nhật này.

Report đánh giá riêng: `outputs/error-memory/learn-20261017-005400-c32298.json`; audit truy xuất: `outputs/error-memory/latest-learn-retrieval.json`. Không chạy API mới trong lần học này; 48/50 là điểm lịch sử của snapshot cũ, chưa phải kết quả sau khi thêm bài học.

## Cập nhật v2 từ bốn lỗi còn lại

Version hiện tại là `lmmv3-v2-error-memory-v2`, thay mô tả v1 bên dưới. Đã đọc đủ plans/reviews/traces và workbook của run `20261017-001013-error-rag`. Snapshot hiện kích hoạt 15 nhóm bài học; support là tín hiệu liên quan, không phải số nguyên nhân đã xác nhận.

- Câu 7: đã tính max cột agriculture nhưng output ô nguồn ở một năm đoán sẵn; các lần sửa chuyển sang record dùng col mà không có input. Bổ sung record(input=dataset) để chiếu/đặt tên fields trên từng dòng với provenance; record không input vẫn chỉ đọc scalar refs. Không suy đoán dataset ngầm từ bước trước.
- Câu 12: chọn đúng các dòng/cột nhưng trả tên occupation, rồi collect các read datasets và cuối cùng nhãn literal không khớp heading. Bổ sung bài học concat các dòng, sort metric, take, output _section; nếu rút gọn dùng aliases theo câu hỏi. Không mở rộng phép ghép nhãn gần đúng; tên nhóm thực sự vẫn lấy từ ô Excel.
- Câu 17: read kết thúc dòng 337 dù bảng có 1071 dòng; 18 dòng thỏa mãn nằm sau vùng đọc. Câu 19: read dừng dòng 45 dù annual block kết thúc dòng 54; ba năm thỏa mãn bị bỏ ngoài vùng đọc. Thêm `src/read_scope.py`: hint identifier/year bounds từ workbook và guard từ chối scan thiếu cho câu đếm mã có số chữ số hoặc annual rows không giới hạn thời kỳ. Guard chỉ yêu cầu lập lại plan, không tự thêm dòng hay tạo đáp án. Câu nêu giới hạn năm/dòng được miễn guard tương ứng; nhận diện là heuristic, chưa phủ mọi cấu trúc/ngôn ngữ.
- Preview v3 có `identifier_profiles` và `year_axis_profiles`. Profile năm chỉ dựa các cột đầu và dãy năm gần liên tiếp, tránh nhầm metric/code là năm. Không dùng ID, tên file, số dòng hoặc đáp án cố định của dataset.
- Log lưu raw response bị giới hạn khi reviewer trả JSON/schema sai để chẩn đoán thay vì chỉ ghi unavailable.

Run API riêng bốn câu `outputs/runs/20261017-four-fix` đạt strict exact match **4/4**, 45 giây runtime. Lượt đầy đủ tiếp theo `20261017-004-fix-v2` chỉ đạt **27/30**: 7/17/19 đã đúng, 12 vẫn sai, 23/27 hồi quy. Đọc raw reviewer mới thấy cảnh báo revise đúng bị loại vì issue quá 300 ký tự; do đó bản cuối chuẩn hóa độ dài/count issue mà vẫn giữ verdict, thêm guard tên nhóm từ heading thực có trong question/workbook, bài học sheet identity từ `_sheet`, và chuẩn hóa output duy nhất của record một trường. Không ghép nhãn gần đúng và không lấy đáp án từ reviewer. Toàn bộ **185 unittest offline qua** sau các thay đổi này. Bộ public đã dùng sửa lỗi không chứng minh tổng quát trên tập ẩn. Không trộn kết quả run con vào điểm run đầy đủ.

Nhánh `improve/error-memory-rag` dựa trên `main` tại `7b607c8`. Mode `llm-v3` dùng thêm kho bài học cục bộ với version `lmmv3-v2-error-memory-v1`. Đây là truy xuất hướng dẫn thực hiện từ lỗi đã phân tích, không huấn luyện lại trọng số mô hình. Chưa có điểm API mới chứng minh cải thiện strict exact match.

## Phân tích log hiện có

Đã đọc ba run Public_data_2 dưới `outputs/runs/`: `20261016-215200-9ae292` (22/30), `20261016-221813-ae29d3` (20/30), `20261016-234204-72d91f` (21/30). Điểm là strict exact match theo reference lưu trong metadata; các run dùng code/config khác nhau, không phải thí nghiệm đối chứng cho thay đổi này.

Run gần nhất có 9 câu sai:

| ID đánh giá | Quan sát trong log/trace | Bài học dùng cho câu mới |
|---|---|---|
| 2 | Output cuối thiếu bước tồn tại/thiếu trường; sau đó record chứa nhãn literal không có căn cứ từ ô/điều kiện | Ghép hai trường trong record; nhãn lấy từ ô hoặc if phụ thuộc dữ liệu |
| 6 | Tham chiếu `result_E` như scalar dù bước result trả dataset; lần cuối chỉ xuất năm | Dùng col trong dataset; giữ năm và chênh lệch trong cùng dòng; lọc/sắp năm trước lag |
| 12 | Thu thập giá trị và nhãn riêng rồi chọn cột label không tồn tại trong tập giá trị | Ghép nhãn và giá trị từng nhóm trước concat/ranking |
| 15 | Lọc đúng nhãn kích thước nhưng output lại chính nhãn kích thước thay vì ngành | Kiểm tra section heading; trả tên nhóm thực sự |
| 17 | JSON steps bị encode thành chuỗi; cấu trúc biểu thức/ngoặc sai, lặp qua sửa | Tạo lại theo schema, steps array, mỗi operator nhận array |
| 19 | count trên cột boolean đếm cả False; trace cho số dòng ban đầu | Filter điều kiện trước aggregate count; kiểm tra annual-only |
| 23 | Trace so sánh số lưu dạng chuỗi cho kết quả ngược; reviewer phát hiện nhưng plan sửa vẫn lặp | Convert number trước so sánh; output đầy đủ sheet và số |
| 27 | div/mul không đúng cấu trúc expression; các lần sửa tiếp tục JSON lỗi | Biểu thức có array và value; giảm phần trăm dùng old-new trên old |
| 30 | answer_spec ghi difference, nhưng output chỉ tham chiếu ô nguồn thứ hai | Tính chênh lệch và đưa kết quả tính vào output; xác định đúng chiều |

Các run trước còn ghi nhận: ID 1 lọc rỗng/rank ngoài tập; ID 24 khai báo ratio nhưng không chia; ID 25 cộng dọc mọi loại hình thay vì cộng từng dòng rồi lấy max và đã bỏ điều kiện loại `any`; ID 26 xuất danh sách quan sát thay vì max-minus-min; ID 29 lỗi JSON biểu thức tỷ lệ. Đây là phân tích cho phát triển, ID không tham gia truy xuất runtime.

Lỗi số dạng text và boolean count đã có xử lý trong `v3_reliability` trên main. RAG bổ sung hướng dẫn cho planner/reviewer; không coi log cũ là bằng chứng code hiện tại chưa có các bản sửa đó. Review trả sai schema cũng xuất hiện nhiều lần; bài học nhắc reviewer giữ schema verdict/issues, nhưng chưa có đo API chứng minh giải quyết việc này.

Chi tiết máy đọc được: `outputs/error-memory/analysis.json` (evaluation-only, bị gitignore). Chẩn đoán từ lỗi validator là `observed`; suy luận từ từ ngữ/shape plan là `hypothesis`, cần kiểm tra workbook trước khi kết luận. Câu không có reference không được tính là sai theo exact match. Lỗi provider/API được báo riêng; RAG không chữa được lỗi dịch vụ.

## Cơ chế runtime

- `src/error_lessons.py`: catalog hướng dẫn tổng quát đã đọc và biên soạn từ log. Có thể thêm family mới sau khi kiểm tra căn cứ. Không chứa ID, tên workbook, tọa độ cố định hay đáp án mẫu.
- `config/error_memory.json`: snapshot gồm version, ID bài học và support count. Hiện có 11 family được kích hoạt từ ba run; count là số bản ghi có tín hiệu liên quan, không phải số nguyên nhân đã chứng minh hay độ chính xác. Family mean phân cấp có trong catalog nhưng không được tự kích hoạt khi corpus không cho tín hiệu.
- `src/error_memory.py`: truy xuất theo tín hiệu ngôn ngữ Unicode, answer contract, cấu trúc section và lỗi gần nhất. Đây là retrieval nhẹ dùng quy tắc, không embedding/dịch tự động; chưa phủ mọi cách diễn đạt/ngôn ngữ. Không truy xuất bằng query ID hoặc file name, không dùng support count để đoán đáp án.
- Pipeline lấy tối đa 3 bài học, tổng payload tối đa 3600 ký tự (hard cap 5 bài/6000 ký tự), cho cả plan, repair và review. Repair truy xuất lại bằng lỗi hiện tại. Không thêm lượt API; context tăng vẫn chịu ledger chi phí/thời gian hiện có.
- Log lưu lesson IDs, score, matched_by, chars và SHA-256 snapshot. run_context lưu hash snapshot/cấu hình và hash mã nguồn để đối chiếu.
- Runtime chỉ đọc snapshot, không mở outputs/reference/answer_checks và không sửa memory. Nội dung raw log/reviewer không được biến thành instruction; loader từ chối field tự do. Lỗi cấu hình memory được báo lỗi, không âm thầm dùng đáp án dự phòng.

Config mặc định của nhánh bật tính năng cho `llm-v3`. Tắt `v3_error_memory: false` để đối chứng cùng v3/reliability, giữ các cấu hình khác giống nhau. `llm`/`llm-v2` bỏ cờ này và giữ luồng cũ. Đường dẫn tương đối `error_memory_path` tính từ gốc mã nguồn, nên dùng được khi chạy CLI ở thư mục khác. Docker hiện đã copy `config` và `src`.

## Cập nhật từ run mới

Không cần API để phân tích:

```powershell
python scripts/learn_error_memory.py --run outputs/runs/<run-id> --report outputs/error-memory/new-analysis.json --memory-output outputs/error-memory/candidate.json --merge-memory config/error_memory.json
```

Có thể lặp `--run` để phân tích nhiều run. Log CLI có `questions.jsonl` hoặc `logs/questions.jsonl`; khi không có reference trong metadata, truyền `--reference <expected_submission.csv>` cùng một run để đánh giá. Reference chỉ dùng so sánh sau khi đọc kết quả, không xuất sang memory. Các lỗi đã sửa thành công trong cùng run cũng được ghi nhận với kind `recovered_error`.

Xem report rồi cập nhật snapshot trong `config/error_memory.json` bằng `--memory-output config/error_memory.json`. Import chỉ kích hoạt family đã biên soạn trong catalog; một lỗi hoàn toàn mới cần đọc trace và bổ sung hướng dẫn tổng quát cùng kiểm thử. Không tự chép câu hỏi/đáp án hoặc tin mọi đề xuất của reviewer. `--merge-memory` giữ family cũ và lấy max support giữa corpus mới/snapshot, không cộng lặp cùng corpus. Muốn count đầy đủ hãy truyền lại toàn bộ corpus cần dùng. Report và memory phải là hai file riêng.

## Kiểm chứng và giới hạn

`python -m unittest discover -s tests -q` chạy offline. Test mới dùng workbook giả lập/client giả: truy xuất cho câu mới nhiều ngôn ngữ, repair từ lỗi JSON, dùng chung ledger, giữ baseline, giới hạn context và chống rò đáp án/reference sang prompt. Test đó chỉ chứng minh cơ chế, không chứng minh mô hình sẽ làm theo bài học hay tăng điểm dataset.

Để đo hiệu quả, chạy cặp baseline/RAG với cùng inputs, config, seed và model; lưu kết quả lần đầu riêng, báo strict exact match, token, chi phí và thời gian. Không dùng replay plan cũ để tuyên bố planner đã tốt hơn. Cần đánh giá bộ chưa dùng tạo bài học để kiểm tra khả năng tổng quát; không có chứng nhận RAM/disk/chi phí bài chấm từ lần sửa này.


### K?t qu? ch?y cu?i

Run ??y ?? `outputs/runs/20261017-final-rag-v2` ??t **29/30 strict exact match (96,67%)**, so v?i 26/30 c?a v1. C? b?n c?u 7, 12, 17, 19 ??u ??ng; c?u 23 h?i quy do record d?ng literal t?n sheet kh?ng ph?i cell text. Th?i gian 396,8 gi?y; 101 request, 1.532.284 total tokens, chi ph? API ghi nh?n $0,04428. ??y l? ?i?m tr?n b? ?? d?ng ?i?u ch?nh, kh?ng ph?i ??i ch?ng t?p ?n.

B?n v? cu?i cho ph?p record ground literal kh?p CH?NH X?C t?n sheet th?c trong workbook, l?u ngu?n metadata `sheet!_sheet`; kh?ng cho literal t?y ?. Sau b?n v?, run ri?ng `outputs/runs/20261017-q23-final` tr? ??ng `table_1, 1307`; run b?n c?u `outputs/runs/20261017-four-fix-v2` v?n ??t 4/4. Ch?a ch?y ?? 30 c?u sau b?n v? metadata cu?i, kh?ng gh?p c?c run con ?? tuy?n b? ??t 30/30.
