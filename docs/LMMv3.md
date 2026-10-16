# LMMv3 — pipeline 8 phase

Nhánh `Bao_LMMv3`, nền main `6fbc527` + chẩn đoán Bao (`a979892`). Đây là phiên bản pipeline quanh Qwen cấu hình qua OpenRouter, không phải model fine-tune. Chưa merge main.

## Chạy và so sánh

- `--mode llm`: baseline hiện có.
- `--mode llm-v2`: deep hiện có.
- `--mode llm-v3`: tên hiển thị **LMMv3**, code riêng ở `src/lmmv3/`.

PowerShell (chỉ chạy khi bắt đầu test có phí):

```powershell
.\.venv\Scripts\python.exe main.py --mode llm-v3 --xlsx_dir ./Public_data_2/xlsx_files --queries ./Public_data_2/queries.json --output ./outputs/lmmv3/submission.csv --log-dir ./outputs/lmmv3/logs
```

Dashboard: `.\.venv\Scripts\python.exe dashboard.py --port 8503`, mở `http://127.0.0.1:8503`. Khởi động lại dashboard cũ để thấy lựa chọn **LMMv3 · 8 phase có bằng chứng**. Mỗi run lưu mode/fingerprint; chi tiết câu hiển thị phase, đặc tả, readiness và lịch sử đọc thêm/sửa. API key/model/base URL dùng ENV như trước.

## Các phase

| Phase | Thực hiện | Đầu ra / cải tiến |
|---|---|---|
| 1 | Python | Vùng dữ liệu giữ tọa độ, giá trị gốc/giá trị đọc, ô gộp, kiểu, number format, cảnh báo formula/cache. Header/section chỉ là gợi ý. |
| 2 | LLM + Python | Đặc tả đa ngôn ngữ có ID yêu cầu, trích dẫn nguyên văn, phạm vi, phép tính, layout trường, số lượng và decimals từng trường. |
| 3 | LLM gọi tool | Catalog/preview Unicode, đọc bảng/sheet/ô/vùng/schema/profile; ghi vùng thực sự đã quan sát. |
| 4 | Python + LLM | Mỗi yêu cầu phải có chứng cứ tại tọa độ đã đọc; kiểm tra bounds/bao phủ, yêu cầu đọc thêm hoặc sửa đặc tả nếu thiếu/mơ hồ. |
| 5 | LLM + preflight | Kiểm tra schema, ID duy nhất, tham chiếu trước đó, kiểu rows/scalar, bảng có bằng chứng. |
| 6 | Python | Chạy đúng kế hoạch khai báo; lưu compiled plan, trace, mẫu giá trị trung gian và nguồn ô. Không exec mã do LLM sinh. |
| 7 | Python + review chọn lọc | Kiểm tra layout/kiểu đầu ra, legacy semantic guards là cảnh báo; review khi có nhãn/đơn vị/logic rủi ro, dừng sau accept. |
| 8 | Python | Định dạng từng trường, giữ mã 001; CSV UTF-8, ID số tăng dần; ứng viên bị bác bỏ không được dùng làm submission. |

Phase 3 trả kế hoạch và coverage cùng lượt API, nhưng readiness và preflight vẫn kiểm tra riêng. Coverage chứng minh tọa độ đã quan sát, **không chứng minh hiểu đúng ý nghĩa hay phạm vi**. Scope còn phụ thuộc đặc tả, kế hoạch và review. Executor xử lý toàn phạm vi khai báo, không chỉ preview.

## Tool và tính toán

Tools đọc: `list_sheets`, `inspect_table`, `table_schema`, `search_cells`, `read_range` (tối đa 600 ô), `read_cell` (kèm vùng lân cận), `profile`. Đọc vùng trả cả ô trống và giá trị gốc; tìm kiếm báo truncation. Profile không được coi là đã quan sát toàn bộ giá trị.

Tái sử dụng Decimal, filter/group/join có cardinality audit, lag/fill_down/record, unpivot, sort/take, ngày/tuổi và provenance.

Bổ sung v3:

- `weighted_mean(input,value:expr,weight:expr)`: biên dịch thành tích, tổng tử/mẫu, chia; thiếu dữ liệu/mẫu 0 là lỗi.
- `percent_change(old:expr,new:expr)`: (new-old)/old*100, không đồng nhất với điểm phần trăm.
- `aggregate/group metric=median`: trung vị bằng Decimal.
- `parse_number:[expr,{value:decimal_comma|decimal_dot}]`: locale tường minh, từ chối dấu không hợp lệ.
- `parse_date:[expr,{value:format}]`: format ngày tường minh, tránh đoán tháng/ngày.

Các giao thức cũ giữ nguyên; executor chỉ được bổ sung thao tác. Mean across all tuân thủ giải đáp BTC (gồm Total trong phạm vi nếu không loại trừ); sum vẫn chống cộng đôi Total/detail.

## Sửa lỗi và giới hạn

Inspect phải nêu ID yêu cầu thiếu. Revise_spec giữ trích dẫn câu hỏi và lưu lịch sử. Feedback chỉ rõ phase, lỗi, kế hoạch trước và số lần lặp. Kế hoạch đã bị bác bỏ lặp nguyên dạng bị chặn; lỗi lặp 3 lần hoặc hết ngân sách thì dừng. Reviewer sai schema được thử lại tối đa một lần; tiếp tục không khả dụng thì không xuất ứng viên như đã xác minh.

Config riêng: `v3_max_api_calls=8`, `v3_max_repairs=3`, `v3_max_inspections=3`. Đây là trần, không phải số lượt bắt buộc. Một ledger cho spec/inspect/plan/review/repair và transport retry; giữ giới hạn $0.10/câu, timeout câu và tổng runtime. Mốc 115 giây/câu là chính sách dự án, không phải quy định BTC từng câu.

Usage gốc được giữ; input + reasoning chỉ có số khi API cung cấp đủ, nếu thiếu là null. Không cộng reasoning hai lần vào completion/total. Summary ghi rõ RAM là peak tiến trình chính; chưa xác minh disk hoặc đầy đủ cây tiến trình/container, không tuyên bố đã đạt mọi giới hạn nộp bài.

## Kiểm chứng và giới hạn hiện tại

Kiểm tra mới dùng workbook tổng hợp/client giả lập. Không chạy dataset đánh giá qua LMMv3 trong lần triển khai. Một test dashboard cũ có thể tự gọi CLI thật đã được đổi sang subprocess giả lập để tránh API trong kiểm tra tiếp theo.

Chưa khẳng định chính xác hơn baseline/v2. Sau triển khai cần test bộ chưa dùng chỉnh solver, cùng model/cấu hình, nhiều lần chạy; báo strict exact match, thời gian, phí và lỗi từng phase. Không đưa reference/answer_checks vào solver.

Header/table segmentation còn suy đoán; không tự tính lại công thức thiếu cache; ô preview có giới hạn; tìm kiếm chưa có embedding đa ngôn ngữ; đặc tả và reviewer có thể cùng hiểu sai. Không hỗ trợ mọi bài toán và không bảo đảm đúng trên mọi dataset. Các giới hạn workbook/executor vẫn áp dụng.


## Sửa giao thức sau run lỗi — lmmv3-8phase-v2

- Chuẩn hóa output_count/decimals từ số thực nguyên, chuỗi số nguyên và chuỗi null sang kiểu JSON chuẩn, ghi từng thay đổi. Không đoán từ ngữ như one/several, không chấp nhận boolean hoặc số lẻ làm count. Validator chấp nhận số thực nguyên theo ý nghĩa JSON Schema integer.
- ID yêu cầu là chuỗi định danh, có thể đa ngôn ngữ; vẫn kiểm tra không trùng và không tự đổi ID. Schema gửi provider cho từng lượt plan/inspect chứa enum các requirement/table ID thật. Không ánh xạ theo kiểu fuzzy hoặc tự cắt bounds sai.
- Log model_responses lưu raw phản hồi spec/plan/review (giới hạn 24.000 ký tự mỗi lượt, kèm độ dài/hash/truncated) để xác định giá trị và kiểu thực tế gây lỗi. Retry spec có phản hồi trước, lỗi kèm kiểu và hướng dẫn cụ thể.
- Thiếu ngữ cảnh workbook trong ambiguities được giải quyết bằng inspect rồi ambiguity_resolutions: index, requirement có coverage, giải thích. Readiness kiểm tra đủ từng index; reviewer phải xem giải thích. Không được bỏ qua mơ hồ còn tồn tại.
- Feedback coverage chỉ rõ danh sách ID hợp lệ và bounds bảng; giữ kiểm tra vùng đã quan sát. Không tự sửa tọa độ để làm cho một kế hoạch sai vượt kiểm tra.
- Chỉ kiểm chứng bằng client giả lập; chưa chạy lại dataset hoặc gọi API. Kiểm thử này không chứng minh Qwen sẽ luôn tuân thủ schema hay LMMv3 sẽ đạt điểm cao hơn.
