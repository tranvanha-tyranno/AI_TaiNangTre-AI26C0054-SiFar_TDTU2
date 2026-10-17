# AGENTS.md — Chủ đề 2: Hỏi đáp trên bảng tính Excel

> Ngữ cảnh dành cho agent/đội phát triển, tổng hợp từ đề chính thức và PDF **Giải đáp thắc mắc của đội thi — Vòng Khu vực, Bảng C** (3 trang), cập nhật ngày **16/10/2026**.
>
> Nguồn giải đáp được lưu tại [docs/AI2026_Giai_dap_thac_mac_Vong_khu_vuc_bang_C.pdf](docs/AI2026_Giai_dap_thac_mac_Vong_khu_vuc_bang_C.pdf). Với những điểm được BTC đính chính trực tiếp, dùng nội dung giải đáp thay cách hiểu cũ; phần chưa được trả lời không tự suy đoán thành quy định. Mục 11 ghi nội dung BTC làm rõ, mục 12 là đề xuất triển khai và các việc còn cần làm. Cập nhật tài liệu không đồng nghĩa mã nguồn đã đáp ứng các quy định mới.

---

## 1. Mục tiêu (Objective)

Xây dựng **giải pháp tự động trả lời câu hỏi bằng ngôn ngữ tự nhiên** dựa trên dữ liệu trong các tệp Excel.

Đặc thù dữ liệu Excel:
- Nhiều trang tính (sheets), nhiều bảng trên cùng một trang.
- Tiêu đề phân cấp, ô gộp (merged cells), cấu trúc không đồng nhất.

Yêu cầu: giải pháp phải **xác định đúng thông tin liên quan** và đưa ra **câu trả lời chính xác**.

---

## 2. Dữ liệu được cung cấp

BTC cung cấp bộ dữ liệu công khai để các đội phát triển và tự đánh giá, gồm:

| Thành phần | Nội dung |
|---|---|
| `xlsx_files/` | Thư mục chứa các tệp Excel (`.xlsx`) |
| `queries.json` | Danh sách câu hỏi với các trường `id`, `file_name` và `query` |
| `sample_submission.csv` | Tệp mẫu kết quả gồm hai cột `id` và `answer` |

Chi tiết:

- Trong `queries.json`: `id` là mã câu hỏi; `file_name` là tên tệp Excel tương ứng; `query` là nội dung câu hỏi.
- Theo giải đáp câu 04, ID khi chấm sẽ được thống nhất thành **số tự nhiên**. Dữ liệu công khai hiện có ID chuỗi như `p4_q001`; giữ tương thích khi kiểm thử, không dùng hình dạng ID công khai để suy luận đáp án. Template chính thức sẽ làm rõ giao diện đọc dữ liệu/chạy bài.
- Hình minh họa dữ liệu trong tệp Excel: bảng có các cột như `Quang`, `Van`, `Bui`, ngày sinh, điểm số, v.v. (ô gộp / tiêu đề phân cấp).

### Ví dụ `queries.json`

```json
[
  {"id": 1, "file_name": "sample.xlsx", "query": "How many people have a score higher than 80?"},
  {"id": 2, "file_name": "sample.xlsx", "query": "What is the last name of the person with the highest score?"}
]
```

### Ví dụ `submission.csv` tương ứng

```csv
id,answer
1,11
2,Ngo
```

### Tập kiểm thử

- Bài dự thi được đánh giá trên **tập kiểm thử ẩn** do BTC xây dựng theo quy trình tương tự bộ dữ liệu công khai.
- Bộ dữ liệu công khai đợt 1: *Truy cập tại đây* (link do BTC cung cấp).

---

## 3. Yêu cầu đối với bài dự thi

1. **I/O:** Giải pháp nhận đầu vào là **thư mục chứa các tệp `.xlsx`** và **tệp `queries.json`**; kết quả phải được xuất ra **tệp `submission.csv`** đúng định dạng mẫu.
2. **Một dòng / một câu hỏi:** Mỗi `id` trong `queries.json` tương ứng với đúng một dòng kết quả. CSV dùng **UTF-8**, dòng kết quả theo **ID tăng dần** (ID số phải sắp theo giá trị số). Trường `answer` **chỉ ghi đáp án cuối cùng**, không kèm giải thích; nếu không trả lời được, ghi **chuỗi rỗng**, không tự thay bằng `N/A` hay thông báo lỗi (giải đáp câu 04, trang 2).
3. **Nộp bài:** Mỗi đội nộp **một tệp `.zip`** gồm mã nguồn, các tệp cấu hình/phụ thuộc cần thiết và **tệp `README.md`** hướng dẫn cài đặt, cấu hình, chạy chương trình bằng dòng lệnh.
4. **Tính khả tái tạo:** Giải pháp phải có khả năng **chạy lại với dữ liệu đầu vào mới**, không phụ thuộc vào đường dẫn cố định của dữ liệu mẫu. Bài không chạy được hoặc không tạo ra tệp kết quả hợp lệ sẽ **không được chấm**.

---

## 4. Giới hạn thời gian và điều kiện thực thi

| Hạng mục | Quy định |
|---|---|
| **Mô hình ngôn ngữ (LLM)** | Nếu dùng LLM để trả lời, phải hỗ trợ mô hình thống nhất khi chấm thi là **Qwen3.7-Flash** (`qwen/qwen3-7-flash`), truy cập qua **OpenRouter** (`https://openrouter.ai/qwen/qwen3-7-flash`). Phải cho phép **cấu hình thông tin truy cập API** (không hard-code khóa API vào mã nguồn). Quy định này không hạn chế việc dùng công cụ AI trong quá trình phát triển. |
| **Chi phí LLM** | Tổng chi phí LLM trên tập kiểm thử **không vượt quá 0.10 USD / câu hỏi** cho mỗi lần chấm, tính cả các lượt gọi lại (retry). Chi phí xác định theo mức sử dụng API do BTC ghi nhận. |
| **Thời gian thực thi** | Tối đa **40 phút cho 20 câu hỏi**, tính từ lúc bắt đầu chạy đến khi tạo xong `submission.csv`, bao gồm xử lý dữ liệu và gọi API. Máy chấm của BTC: **6 core vCPU, 12 GB RAM**. |
| **Dung lượng đĩa & RAM** | Tệp `.zip` nộp bài **≤ 100 MB**. Giải đáp câu 03 (trang 1) làm rõ: tổng dung lượng **đĩa (disk) ≤ 1 GB**, tổng **RAM ≤ 4 GB**. Không dùng cách hiểu cũ “RAM ≤ 1 GB”, cũng không lấy toàn bộ 12 GB RAM của máy làm ngân sách bài thi. Phạm vi đo disk chưa được mô tả chi tiết. |
| **Build & Internet** | Thời gian build Docker, gồm tải/cài đặt, không tính vào thời gian chạy chính thức. Chỉ dùng Internet để install và request đến OpenRouter API. Được xử lý/gửi request song song trong tài nguyên được cấp (giải đáp câu 05, trang 2). |
| **AI trong bài chạy cuối** | Được dùng bất kỳ công cụ AI nào khi phát triển; giải pháp cuối chỉ được dùng AI/LLM do BTC cung cấp (giải đáp câu 07, trang 3). |
| **Lưu ý** | Vi phạm một trong các giới hạn trên → **không được chấm điểm**. |

---

## 5. Chấm điểm và xếp hạng

BTC chạy các bài dự thi hợp lệ trên **tập kiểm thử ẩn**. Thứ tự xếp hạng theo các tiêu chí ưu tiên:

1. **Exact Match:** Số câu trả lời đúng theo đối chiếu của BTC — đội có nhiều câu đúng hơn xếp trước. BTC có chuẩn hóa khoảng trắng thừa, dấu không cần thiết, chữ thường và dấu chấm/phẩy thập phân; vẫn phải tuân thủ cụm từ/độ làm tròn mà câu hỏi yêu cầu. Chưa có mã chuẩn hóa chính thức để tái tạo hoàn toàn bộ chấm (giải đáp câu 04).
2. **Thời gian thực thi trung bình / câu hỏi:** Nếu hòa tiêu chí 1, đội có thời gian thấp hơn xếp trước.
3. **Số token LLM trung bình / câu hỏi:** Nếu hòa cả hai tiêu chí trên, đội dùng ít token hơn xếp trước. Giải đáp câu 06 (trang 3) nêu token tính bằng tổng **input + reasoning**; chưa làm rõ output không phải reasoning và cách đo thời gian trung bình. Không đồng nhất tùy tiện `total_tokens` của API với chỉ số xếp hạng này.

---

## 6. Lịch trình

| Thời điểm | Hoạt động |
|---|---|
| **19h00 ngày 13/10** | BTC công bố bộ dữ liệu công khai lần 1; các đội bắt đầu phát triển giải pháp |
| **09h00 ngày 16/10** | BTC công bố bộ dữ liệu công khai lần 2 |
| **12h00 ngày 17/10** | Hạn cuối nộp tệp `.zip` chứa bài dự thi |
| **12h00–17h00 ngày 17/10** | BTC chấm các bài dự thi hợp lệ trên tập kiểm thử ẩn |
| **20h00 ngày 17/10** | Công bố bảng xếp hạng tạm thời |
| **08h00–17h00 ngày 18/10** | Vấn đáp xác minh giải pháp của các đội thi |
| **20h00 ngày 20/10** | Công bố bảng xếp hạng chính thức |

---

## 7. Vấn đáp và xác minh

- Phần vấn đáp nhằm xác minh mức độ **làm chủ giải pháp** của đội thi.
- Theo giải đáp câu 02 (trang 1), BGK vòng khu vực tập trung vào bài toán vòng khu vực; nội dung sản phẩm vòng loại sẽ được hỏi ở vòng chung kết nếu đội vào vòng đó.
- Các đội phải giải thích được **nguyên lý hoạt động**, các **thành phần chính** và **chứng minh khả năng điều chỉnh mã nguồn** theo yêu cầu phù hợp với phạm vi đề thi.
- Đội không đáp ứng yêu cầu xác minh sẽ **bị loại khỏi bảng xếp hạng chính thức**.

---

## 8. Checklist cho agent khi triển khai

Các ô dưới đây là tiêu chí cần xác minh trên bản nộp cuối; không đánh dấu hoàn tất chỉ vì đã có mã xử lý hoặc tài liệu mô tả.

- [ ] Đọc thư mục Excel + `queries.json` từ tham số/config; chạy với đường dẫn mới và khớp template nộp bài của BTC khi nhận được.
- [ ] Hiểu merged cells, tiêu đề phân cấp, nhiều bảng/sheet, nhãn lặp và nhiều ngôn ngữ; truy xuất đủ vùng cần tính thay vì chỉ phần preview.
- [ ] Áp dụng đúng quy ước trung bình “across all…” tại mục 11.1, có ca kiểm tra đối chứng khi câu hỏi loại trừ Total.
- [ ] Xuất `id,answer`, UTF-8, đủ ID, ID số tăng dần; câu không trả lời được có đáp án rỗng.
- [ ] Model cuối đúng AI/LLM BTC cung cấp; khóa API cấu hình từ bên ngoài, không commit khóa.
- [ ] Tổng chi phí ≤ $0.10/câu gồm retry; toàn bộ 20 câu hoàn tất và tạo CSV trong 40 phút. Mốc 2 phút/câu là trung bình, không phải hạn cứng từng câu.
- [ ] Đo riêng RAM ≤ 4 GB, disk ≤ 1 GB và ZIP ≤ 100 MB; đánh giá với mức song song thực tế.
- [ ] Runtime chỉ truy cập mạng cho OpenRouter API; dữ liệu, cấu hình và thư viện cần thiết sẵn sàng sau bước install/build.
- [ ] README/Docker tái tạo được trên môi trường sạch; nêu rõ phần còn chờ template thay vì giả định đã biết môi trường chấm.

## 9. Bộ kiểm thử trong `Test/` (thêm)

At the current update, `Test/README.md` lists **28 suites and 662 questions**; suites 23-27 are compact (about 14,821 physical rows total), and `Test/28_long_multilingual_combined/` combines 150 questions across five workbooks. Each suite has `xlsx_files/`, `queries.json`, `expected_submission.csv`, and a README.

| Suite | Nội dung kiểm tra |
|-------|-------------------|
| `01_smoke_replica` | I/O, merged header `Name`/`Date of`, fiscal `Yes/No` (3 câu) |
| `02_merged_hierarchy` | Ô gộp & tiêu đề 2–3 dòng, flatten `L1 / L2` |
| `03_multisheet_multitable` | Nhiều sheet & nhiều bảng trên 1 sheet |
| `04_robustness` | CSV quoting, ô rỗng, từ chối ID trùng & path traversal |
| `05_truncation_perf` | Lookup trên 500 dòng, vùng vượt preview và hiệu năng |

Nhóm 06–12 kiểm tra lọc, tổng hợp, header ba cấp, join, ngày biên, dữ liệu thiếu/đồng điểm và quét bảng lớn. Nhóm 13–22 bổ sung 300 câu trên workbook mới dựa trên cấu trúc của cả `Public_data_1` và `Public_data_2`, gồm dữ liệu phân cấp, thời kỳ, tài chính và đa ngôn ngữ. Xem `Test/README.md` để biết chi tiết và cách tái tạo; không coi điểm trên bộ đã dùng để chỉnh solver là bằng chứng tổng quát trên tập ẩn.

Chạy: `python main.py --xlsx_dir ./Test/<suite>/xlsx_files --queries ./Test/<suite>/queries.json --output ./outputs/<suite>/submission.csv --mode llm` hoặc chọn dataset trên dashboard → **Chạy mới**. Đánh giá: `python scripts/evaluate.py --prediction ./outputs/<suite>/submission.csv --reference ./Test/<suite>/expected_submission.csv`. Chạy LLM sẽ dùng API và có chi phí; đọc tài liệu không cần chạy API.

`scripts/evaluate.py` hiện so chuỗi chính xác, chưa mô phỏng chuẩn hóa của BTC. Giữ kết quả này dưới tên **strict exact match**; nếu bổ sung phép so gần với BTC thì báo riêng, không ghi đè điểm strict hay tuyên bố khớp bộ chấm chính thức. Các file đáp án/`answer_checks.json` chỉ phục vụ đánh giá, không đưa vào ngữ cảnh solver.

## 10. Dashboard

`dashboard.py` nhận các thư mục `Public_data_*`, `Test/*/queries.json` và dataset ngoài qua `--dataset-dir`; danh mục ở `/api/datasets`. Các thao tác xem workbook/chạy bài tôn trọng `?dataset=` và lưu dataset trong metadata của run. Xem `README.md` để chạy CLI/dashboard.

Pipeline hiện hỗ trợ `--mode llm` và `--mode llm-v2`, đều dùng LLM + Tools; không còn CLI offline/hybrid hay `src/deterministic_qa.py`. Các điểm chính: `src/workbook_index.py` đọc/index workbook, `src/planner.py` lập kế hoạch, `src/tools/executor.py` tính toán, `src/answer_contract.py`/`src/scope_validation.py`/`src/semantic_validation.py` kiểm tra kết quả, `src/usage.py` theo dõi tài nguyên/API. Không phục hồi resolver theo ID/tên workbook để khớp riêng dữ liệu công khai.

## 11. Các giải đáp BTC cần dùng khi thiết kế và sửa lỗi

### 11.1. Trung bình trên các cột phân cấp (câu 01, trang 1)

- Với yêu cầu **average “across all…”** trong một phạm vi dòng/tiêu chí mà không giới hạn cấp phân nhóm, dùng **trung bình cộng không trọng số trên tất cả cột dữ liệu thuộc phạm vi đó**, bao gồm cột Total của các nhóm.
- Ví dụ BTC xác nhận `p4_q007`: dòng **Unemployment rate**, nhóm **Women**, lấy toàn bộ **8 cột dữ liệu**, gồm Total của **Some college or associate degree** và **Bachelor's degree and higher**; đáp án mẫu **3.14**. Đây là ví dụ kiểm chứng quy tắc, không phải đáp án để hard-code vào solver.
- Nếu câu hỏi nêu `subcategories only`, `excluding totals` hoặc chỉ định cấp/nhóm cụ thể, chọn cột theo yêu cầu đó. Xác định phạm vi theo header phân cấp và dữ liệu workbook, không cố định tám cột cho mọi bảng.
- Quy ước này áp dụng cho **mean**; không suy rộng thành cộng Total với các thành phần khi tính **sum**. Tài liệu không quy định cách xử lý missing trong phép mean này; không tự biến ô thiếu thành 0 hoặc áp quy tắc bỏ trống như một quy định BTC.

### 11.2. Đầu vào, định dạng đáp án và chuẩn hóa (câu 04, trang 1–2)

- Tập ẩn theo định dạng công khai, chỉ có workbook **`.xlsx`**, có thể nhiều sheet và nhiều ngôn ngữ. Không giả định câu hỏi/nhãn chỉ bằng tiếng Anh hoặc chỉ dùng sheet đầu tiên.
- ID khi chấm là số tự nhiên; đường dẫn và giao diện chạy sẽ theo template BTC. PDF chưa chốt riêng tên trường `file name` hay `file_name`; `file_name` là giao diện đang dùng trong dự án, cần đối chiếu template sau.
- CSV: **UTF-8, ID tăng dần, không trả lời được thì chuỗi rỗng**. PDF chưa phân biệt UTF-8 có/không BOM; không tự tuyên bố một lựa chọn là bắt buộc.
- BTC bỏ khoảng trắng thừa và một số dấu không cần thiết, chuyển chữ thường, chuẩn hóa dấu thập phân. Câu hỏi sẽ nêu format/cụm từ/độ làm tròn cần thiết. Không có đặc tả đủ để kết luận mọi cặp `11`/`11.0` luôn tương đương.
- Không xóa mù dấu âm, dấu thập phân hoặc ký tự trong mã định danh khỏi **đáp án xuất ra** chỉ vì BTC có bước chuẩn hóa; bảo toàn ý nghĩa và làm theo câu hỏi.

### 11.3. Tài nguyên, thực thi và Internet (câu 03, 05, trang 1–2)

- **Disk ≤ 1 GB; RAM ≤ 4 GB** là hai giới hạn riêng. ZIP ≤ 100 MB và 40 phút/20 câu của đề vẫn áp dụng. Chưa rõ disk có bao gồm image Docker, dữ liệu đầu vào, dependency hay cache; cần đối chiếu hướng dẫn/template nộp bài, không tự loại các phần đó khỏi phép đo.
- Được song song hóa trong tài nguyên được cấp; PDF không đưa ra rate limit cụ thể. Cần retry/backoff và giới hạn concurrency; song song không miễn ngân sách chi phí hay bộ nhớ.
- Build Docker (kể cả tải/cài) không tính vào thời gian chạy chính thức. Không suy rộng thành miễn mọi bước tiền xử lý runtime hoặc tải dữ liệu sau khi bắt đầu chạy.
- Internet chỉ phục vụ **install và OpenRouter API**; không dựa vào web search, API AI khác hoặc dịch vụ dữ liệu ngoài trong bài chạy cuối.

### 11.4. Token, công cụ AI và vấn đáp (câu 02, 06, 07, trang 1–3)

- BTC nêu cách tính token là **input + reasoning**. Nên giữ riêng các trường usage gốc, input, completion và reasoning nếu API trả về; không cộng reasoning hai lần nếu nó đã nằm trong completion. Tách chỉ số theo giải đáp khỏi tổng usage dùng để quản lý chi phí.
- Mọi lượt plan/inspect/repair/review/retry đều phải được theo dõi trong ngân sách. Chưa có giải đáp đầy đủ về output không phải reasoning và cách đo thời gian trung bình.
- Công cụ phát triển không bị giới hạn; AI/LLM trong giải pháp cuối phải do BTC cung cấp. Không tự chuyển sang model khác khi model chấm lỗi hoặc hết ngân sách.
- Chuẩn bị vấn đáp về bài toán Excel QA vòng khu vực: chọn đúng phạm vi dữ liệu, tính toán, định dạng đáp án, kiểm soát tài nguyên và khả năng sửa mã trực tiếp.

### 11.5. Những điểm vẫn cần template/hướng dẫn tiếp theo

Chưa chốt từ PDF này: hệ điều hành/Python máy chấm; tên entrypoint/tham số bắt buộc; tên biến môi trường cấp khóa; tên trường file chính thức; rate limit; BOM; phạm vi tính disk; output token ngoài reasoning; cách đo thời gian trung bình. Đây là thông tin còn thiếu, không phải lý do dừng các việc độc lập đã được người dùng giao. Khi có hướng dẫn mới, đối chiếu và cập nhật tài liệu/config/adapter tương ứng.

## 12. Hướng cải tiến dự án sau giải đáp (đề xuất, chưa triển khai trong lần cập nhật tài liệu)

Các quan sát sau dựa trên mã nguồn tại ngày 16/10/2026; kiểm tra lại trước khi sửa vì dự án đang được phát triển.

| Ưu tiên | Hiện trạng / vấn đề cần xử lý | Hướng sửa và kiểm chứng |
|---|---|---|
| P0 — CSV | `main.py` ghi theo thứ tự `queries.json`; nhánh lỗi dùng ứng viên cuối hoặc `N/A`. `src/pipeline.py` có thể chốt ứng viên chưa qua toàn bộ kiểm tra. | Xuất ID số tăng dần; khi thật sự không có đáp án thì xuất `""`. Quy định rõ trạng thái ứng viên chưa xác thực, tách khỏi đáp án đã xác thực; giữ lỗi/căn cứ trong log. Kiểm tra ID `[10, 2, 1]`, lỗi API và không có kết quả tính. Tiếp tục chạy được bộ public có ID chuỗi. |
| P0 — Tài nguyên | `main.py` còn kiểm tra `memory <= 1024` MB; chưa có kiểm chứng disk trong summary. | Tách kiểm tra RAM 4 GB và disk 1 GB; ghi phạm vi/đơn vị đo, đo tài nguyên của cả cây tiến trình/container khi có tiến trình con, kiểm tra ZIP riêng. Không gắn nhãn “đạt” chỉ dựa trên RAM tiến trình chính. |
| P0 — Phạm vi mean | Prompt có hướng dẫn tránh cộng đôi Total trong sum; phải làm rõ ngoại lệ mean “across all…”. Có logic trung bình theo ngữ nghĩa trong `src/pipeline.py`, nhưng cần kiểm chứng khả năng áp dụng tổng quát. | Đồng bộ planner, answer contract, scope/semantic review với mục 11.1. Kiểm tra ba câu cùng bảng: tất cả cột kể cả Total; chỉ subcategories; loại Total rõ ràng. Thêm workbook đổi vị trí cột/nhãn để phát hiện phụ thuộc dữ liệu mẫu; giữ guard chống cộng đôi cho sum. |
| P1 — Đánh giá | `scripts/evaluate.py` chỉ so chuỗi nguyên văn. | Giữ strict exact match; nếu thêm chuẩn hóa tham khảo thì báo riêng và ghi rõ chưa phải bộ chấm BTC. Không tăng điểm bằng cách loại dấu làm đổi giá trị số/mã. |
| P1 — Usage | `src/llm_client.py`/`src/usage.py` hiện lưu prompt/completion/total; chưa có trường reasoning riêng trong ledger. | Giữ usage gốc, thêm reasoning khi API cung cấp, không coi dữ liệu thiếu là 0 đã xác nhận; tách chỉ số input + reasoning khỏi tổng token/chi phí. Bao gồm toàn bộ lượt gọi lại. |
| P1 — Môi trường | Đã có Dockerfile, config và README; template chấm chưa được đối chiếu trong tài liệu này. | Khi có template, chỉnh adapter I/O/ENV và thử trên môi trường sạch; kiểm tra runtime chỉ truy cập OpenRouter, model đúng cấu hình BTC, không có fallback AI ngoài danh sách được cấp. |
| P2 — Tổng quát | Đã có 22 suite và hai bộ public; các luật sửa theo câu đã thấy có thể khớp riêng mẫu. | Đánh giá bộ chưa dùng để chỉnh solver, đa ngôn ngữ, header phân cấp, nhiều sheet, vùng cuối bảng và biến thể seed. Ghi điểm lần đầu riêng với điểm hồi quy; không đưa đáp án tham chiếu vào solver. |

Phạm vi lần cập nhật này: sửa hướng dẫn và ghi nhận việc cần làm; **chưa sửa solver, chưa đo lại hiệu năng/tài nguyên và chưa chạy API**. Chỉ đánh dấu checklist khi có bằng chứng tương ứng từ bản nộp thực tế.

---

*Nguồn: Đề thi Chủ đề 2 — Hỏi đáp trên bảng tính Excel (trang 1–3); Giải đáp thắc mắc của đội thi — Vòng Khu vực, Bảng C (trang 1–3, câu 01–07), bản sao trong `docs/`. Các mô tả hiện trạng và đề xuất ở mục 8–10, 12 là ghi chú của dự án, không phải phát biểu của BTC.*

## 13. Nhánh thử nghiệm LMMv3

Trên `Bao_LMMv3`, `--mode llm-v3` gọi pipeline riêng `src/lmmv3/`, tên hiển thị LMMv3. Giữ baseline `llm` và `llm-v2`; không merge main nếu chưa được yêu cầu. Thiết kế và giới hạn: `docs/LMMv3.md`. Tám phase ghi đặc tả, coverage, trace và điều phối sửa; grounding tọa độ không chứng minh đúng ngữ nghĩa. Không dùng đáp án mẫu/ID/file-specific resolver. Chỉ có kiểm tra tổng hợp/client giả lập cho v3, chưa có điểm dataset hay chứng nhận tài nguyên. Test dashboard đã được sửa để không gọi CLI thật; không gọi API khi chạy unit tests.


## 14. LMMv3 Lite — lịch sử thử nghiệm

Trên Bao_LMMv3, `--mode llm-v3` hiện dispatch sang `src/lmmv3/lite.py`, version `lmmv3-lite-v1`. Mục 13/mô tả tám phase là lịch sử, không phải luồng mặc định mới. Giữ llm/llm-v2 và các run cũ để so sánh. Baseline Lite: một kế hoạch, executor cơ bản, tối đa một follow-up theo mặc định; không tự khôi phục đặc tả/reviewer/coverage gate. Thêm từng khả năng sau khi có số đo đối chứng, không đưa tất cả cải tiến vào một lượt. `validated` trong Lite chỉ xác nhận thực thi công cụ, không chứng minh đúng ngữ nghĩa; xem docs/LMMv3_LITE.md. Không có kết quả benchmark/API trong lần xây lại này.


## 15. Khôi phục nền LLMv2 — hiện tại

`--mode llm-v3` hiện dùng chung pipeline và cấu hình LLMv2, version `lmmv3-v2-baseline-v1`; không chạy Lite hay tám phase. Đây là mốc khôi phục, chưa có cải tiến mới. Giữ LLMv2 để đối chứng, nâng cấp từng thay đổi sau khi đo baseline. Xem [hướng dẫn baseline](docs/LMMv3_V2_BASELINE.md). Các mô tả Lite/tám phase trước đó là lịch sử. Chưa gọi API để đánh giá trong lần khôi phục.


## 16. LMMv3 hiện tại — chỉ nâng cấp giảm trùng context

Trên nhánh thử nghiệm `codex/llmv3-reliability` mới: cờ `v3_reliability: true` bật version `lmmv3-v2-reliability-v1`, sửa so sánh số text/boolean, báo count boolean, chuẩn hóa lag khai báo rõ, bổ sung section provenance và hướng dẫn cú pháp. Baseline nguyên trạng ở `codex/llmv3-restored-25` commit `e07698f`. Không đổi RAG ranking hoặc tăng ngân sách; chưa benchmark API, không tuyên bố đã sửa hết sáu câu. Xem `docs/LMMv3_RELIABILITY.md`. Mô tả dưới đây áp dụng khi cờ tắt hoặc trên baseline.

Mục 15 là mốc nền; hiện mặc định `--mode llm-v3` dùng version `lmmv3-v2-dedup-v1`, cùng pipeline/cấu hình LLMv2 và chỉ thêm `src/context_dedup.py` tại ranh giới gửi request. Tắt bằng `v3_deduplicate_context: false` để khôi phục `lmmv3-v2-baseline-v1`. Không đổi lựa chọn bảng, kế hoạch, phép tính hay chính sách review trong lần này. Xem docs/LMMv3_CONTEXT_DEDUP.md. Số đo offline là ký tự; chưa chứng minh tiết kiệm token thực hoặc giữ điểm. Tiếp tục phát triển từng thay đổi có đối chứng.
## RAG từ log lỗi — nhánh improve/error-memory-rag

`llm-v3` có thêm `v3_error_memory`, version `lmmv3-v2-error-memory-v1`; `llm`/`llm-v2` giữ baseline. Catalog `src/error_lessons.py` chỉ chứa hướng dẫn tổng quát, snapshot `config/error_memory.json` chỉ chứa lesson ID/support. `scripts/learn_error_memory.py` phân tích offline log, giữ report chứa reference ở outputs, không đưa đáp án/ID câu hỏi/tên file/raw reviewer vào memory. Runtime chỉ đọc snapshot, truy xuất tối đa theo config cho plan/review/repair, ghi hash và bài học đã dùng. Tắt `v3_error_memory` để đối chứng. Chỉ kích hoạt family đã phân tích; lỗi mới cần đọc trace và bổ sung catalog, không tự coi mọi mismatch hay reviewer là nguyên nhân đã xác nhận. Xem [thiết kế và phân tích](docs/ERROR_MEMORY_RAG.md). Kiểm thử offline/client giả không chứng minh điểm API, tiết kiệm token hoặc đạt tài nguyên. Không merge main nếu chưa được yêu cầu.

Bản hiện tại trên nhánh là `lmmv3-v2-error-memory-v2`: thêm bài học complete read scope, record input tường minh, section argmax; preview hiển thị profile mã/năm từ workbook và guard scan thiếu cho đếm mã/annual rows không giới hạn. Record(input) chiếu từng dòng; record không input giữ scalar-only, không gắn ngầm dataset. Giữ nhãn từ ô Excel, không fuzzy match theo đáp án. Bốn câu sai của run v1 đã chạy API riêng đạt 4/4, là kiểm tra hồi quy trên bộ dùng sửa; chưa chứng minh tập ẩn. Xem cập nhật v2 trong tài liệu liên kết.

Kiểm chứng v2: run đầy đủ `20261017-final-rag-v2` 29/30 strict exact match, bốn câu 7/12/17/19 đúng. Sau sửa metadata sheet (record chấp nhận literal trùng chính xác tên sheet thực, nguồn `sheet!_sheet`), câu 23 chạy riêng đúng; bốn câu mục tiêu chạy lại vẫn 4/4. 185 unittest qua; chưa chạy lại đủ 30 sau bản vá cuối, không ghép điểm run con thành 30/30.

Học bổ sung offline từ run `20261017-005400-c32298` (50 câu hai public, strict 48/50): đọc hai câu lỗi cuối và 28 câu phục hồi lỗi, đối chiếu workbook/trace; reviewer có phản đối mâu thuẫn hoặc bỏ sót numeric filter. Snapshot ở mốc đó 19 family, thêm ngưỡng so sánh, header/missing, đối chiếu review với trace và binding output. Không tự coi reviewer là ground truth, không bỏ review gate, không chép reference/ID/file-specific rule vào memory. Xem phần cập nhật mới nhất ở `docs/ERROR_MEMORY_RAG.md`.

Mốc hiện tại: run đầy đủ `20261017-015942-public2goal` đạt **30/30 strict exact match Public_data_2**. Snapshot 21 family; v3 RAG tối đa 8 API/4 repair trong ledger cũ, thêm chuẩn hóa cú pháp predicate/literal, guard nhầm nhãn header với cột số và tách hướng dẫn execution khỏi review. Không có resolver theo ID/file, không đổi review revise thành accept. 100% là kết quả trên bộ public đã dùng sửa, không chứng nhận tập ẩn hay tính ổn định mọi lần chạy. Không merge main nếu chưa được yêu cầu. Chi tiết/hash/cost/artifacts ở tài liệu RAG.

Đánh giá holdout mới đã dừng do bằng chứng overfit: suite 23 26/30 baseline nhưng 22/30 sau học; suite 24 10/30, suite 25 13/30, suite 26 6/30. Bộ gộp 150 câu bị timeout sau 60 câu nên loại khỏi điểm. Không tiếp tục thêm bài học theo từng lỗi; cần thay đổi kiến trúc nếu muốn tăng tổng quát hóa.

## Chạy theo hướng dẫn nộp bài — 17/10/2026

Đã có `docker-build.ps1`, `docker-run.ps1`, `docker-test.ps1` ở gốc. Build Linux amd64, ENTRYPOINT Python nhận đủ sáu tham số BTC; model chính thức `qwen/qwen3.7-flash`, tham số CLI ưu tiên ENV/config. Run script đọc khóa từ ENV hoặc `.env` cục bộ, input mount readonly, output/log riêng, giới hạn 6 CPU/4 GB. Không tạo ZIP theo yêu cầu người dùng. Sau khi CSV đủ ID được ghi, kể cả answer rỗng cho câu lỗi, CLI thoát 0; lỗi input/setup/write vẫn khác 0. ID số sắp tăng dần ở mọi mode. Đã build image thật và kiểm tra CLI/SDK trong container bằng API giả lập local, mạng ngoài tắt; không phải benchmark OpenRouter thật. Xem README mục 8.

README hiện đặt lệnh Docker một dòng ở đầu. `docker-run.ps1 -Concurrency 2` cho phép hai câu song song, mặc định vẫn 1. Đo cùng 6 câu/cùng image: nối tiếp 95,7s đúng 6/6; hai luồng 49,2s đúng 5/6. Không tuyên bố giữ điểm khi tăng concurrency hoặc quy nguyên nhân sai cho concurrency chỉ từ một cặp chạy; báo cáo `outputs/docker-speed-check/comparison.json`. Đã sửa đường dẫn mặc định PowerShell -File bằng cách resolve sau param block; test script kiểm tra cả cách gọi đó và sáu tham số.

Theo yêu cầu làm rõ của người dùng, README hiện chỉ tập trung chạy trực tiếp bằng Docker theo sáu tham số BTC trên terminal: cấu trúc input/output, build, docker run và xem CSV. Không yêu cầu script hỗ trợ hay `.env`, không đặt key/tham số runtime trong Dockerfile. Hướng dẫn phát triển trước đó được giữ tại `docs/DEVELOPMENT_GUIDE.md`; các script cũ chỉ là tiện ích tùy chọn, không phải giao diện bắt buộc khi chấm.

Chuẩn I/O duy nhất hiện tại: `input/queries.json`, `input/xlsx_files/`, `output/submission.csv`, `output/logs/`. main/config không mặc định dataset public; config được tìm tương đối mã nguồn, I/O tương đối cwd. Image đặt cwd `/`, entrypoint `python /app/main.py`, nên mặc định thành `/input/...`, `/output/...` đúng mount BTC. Script tùy chọn cũng dùng input/output này. Workspace đã có bản sao Public_data_1 trong input cho người dùng thử, thư mục này bị gitignore/dockerignore. Khi đổi dataset chỉ thay nội dung input; giữ nguyên đường dẫn trong lệnh Docker. README liệt kê toàn bộ file, sáu tham số và chỗ điền key trên terminal.

## Bản CLI nộp bài sau dọn — thay hướng dẫn log/mode cũ

Theo yêu cầu người dùng, main chỉ xuất CSV tại output; đã bỏ --log-dir và toàn bộ file JSON/JSONL/report/hashes. Chỉ CLI llm-v3 còn được quảng bá/nhận, giữ cùng pipeline và RAG hiện tại. Trace/evidence/ledger chỉ tồn tại trong bộ nhớ khi cần repair/review và kiểm soát chi phí, không lưu file. Các module src dashboard_analysis, diagnostics, run_context, qa_engine, excel_parser và thư mục lmmv3 cũ cùng dashboard/tests lịch sử được dời sang dev_archive, không đưa vào bài nộp. Runtime deps chỉ openpyxl/PyYAML/OpenAI SDK. Docker context dùng allowlist. Người dùng tự ZIP đúng Dockerfile, .dockerignore, README.md, requirements.txt, main.py, config/, src/; không tạo ZIP hay thư mục đóng gói. README là hướng dẫn chạy/nộp hiện tại. Không khôi phục logger/dashboard/mode cũ nếu không được yêu cầu.


## Nâng cấp học từ lỗi và chạy lại hai public — 17/10/2026

Theo yêu cầu mới của người dùng, tiếp tục học từ lỗi public. Bản `lmmv3-v2-error-memory-v3` ưu tiên bài học ánh xạ header khi cả câu hỏi và cấu trúc nhiều cấp phù hợp; loại tín hiệu đếm sai từ lượng chênh lệch “how many hours/more/percent/thousand”. Không thêm đáp án/ID/tên file/tọa độ mẫu vào memory, không tăng giới hạn API/repair/context. Snapshot vẫn 22 family. Lượt trước sửa run02 đạt 20/20 và 29/30; lượt đầy đủ sau sửa `outputs/public-goal/run03/` đạt **20/20 Public_data_1 và 30/30 Public_data_2 strict exact match**, lần lượt 132,5s/$0,017157 và 360,9s/$0,053837. Đã kiểm tra độc lập CSV đủ ID, đúng thứ tự số và khớp nguyên văn; 118 unittest offline qua. Không ghép điểm chạy con, không chứng nhận tập ẩn hay ổn định mọi lần chạy. CLI vẫn chỉ ghi CSV; không khôi phục logger/dashboard/mode cũ. Chi tiết: `docs/ERROR_MEMORY_RAG.md`, mục cập nhật mới nhất. Không merge main hay tạo ZIP.
