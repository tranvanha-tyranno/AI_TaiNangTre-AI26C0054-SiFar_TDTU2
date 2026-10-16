# Bộ kiểm thử Excel QA

**27 bộ, 662 câu** với file Excel và đáp án mẫu. Các bộ 06–12 có 200 câu; bộ 13–22 có 300 câu dựa theo hai bộ công khai; **5 bộ mới 23–27 có 150 câu và bảng chính 12.000–32.800 bản ghi**, áp dụng thêm quy ước trong `AGENTS.md` cập nhật 16/10/2026.

| Bộ | Số câu | Nội dung |
|---|---:|---|
| 01_smoke_replica | 3 | Tên, tuổi tại nhập học, so sánh năm |
| 02_merged_hierarchy | 2 | Ô gộp, tiêu đề phân cấp |
| 03_multisheet_multitable | 2 | Nhiều bảng và sheet |
| 04_robustness | 1 | Ô trống, quoting, đầu vào không hợp lệ riêng |
| 05_truncation_perf | 4 | Lookup trên 500 dòng |
| 06_people_filters | 30 | Ô gộp, lọc nhiều điều kiện, tuổi, xếp hạng |
| 07_sales_aggregation | 30 | Nhóm, tổng, trung bình có trọng số, trả hàng âm |
| 08_three_level_headers | 25 | Tiêu đề 3 cấp, tỷ lệ, đơn vị nghìn |
| 09_multisheet_join | 30 | Ghép khóa giữa sheet, bảng cạnh nhau, tránh cộng đôi TOTAL |
| 10_dates_boundaries | 25 | Năm nhuận, ngày biên, tuổi tròn, khoảng ngày |
| 11_missing_ties_unicode | 25 | Ô trống khác 0, số âm, đồng điểm, Unicode, mã `001` |
| 12_large_full_scan | 35 | 2.500 dòng, cuối bảng, nhóm hiếm, cột AI |
| [13_admission_transfer](13_admission_transfer/README.md) | 30 | 64 người mới, tuổi theo ngày, ngày nhuận, đồng điểm, top-k |
| [14_trade_periods](14_trade_periods/README.md) | 30 | 6 mặt hàng mới, fiscal/calendar/year-to-date, số âm, tăng trưởng |
| [15_cpi_hierarchy](15_cpi_hierarchy/README.md) | 30 | CPI, con trực tiếp khác cháu, điều chỉnh mùa vụ, chênh lệch điểm % |
| [16_demographic_blocks](16_demographic_blocks/README.md) | 30 | Nam/nữ với nhãn lặp, học vấn, trung bình đơn khác tỷ lệ gộp |
| [17_industry_hours](17_industry_hours/README.md) | 30 | Ngành/nghề, tuổi, giờ làm, TOTAL, phép tính chéo sheet |
| [18_time_use_blocks](18_time_use_blocks/README.md) | 30 | 3 nhóm trẻ, mẹ/cha, việc làm, giờ khác tỷ lệ tham gia |
| [19_safety_naics](19_safety_naics/README.md) | 30 | 1.100 ngành, NAICS 3/6 chữ số, ngưỡng 5.0, dữ liệu thiếu, quartile |
| [20_productivity_periods](20_productivity_periods/README.md) | 30 | 20 năm xen 80 quý, bảng level riêng, giảm liên năm |
| [21_finance_multisheet](21_finance_multisheet/README.md) | 30 | 5 sheet, số chuỗi `$`, dấu phẩy, ngoặc âm, cuối kỳ/bình quân |
| [22_multilingual_social](22_multilingual_social/README.md) | 30 | Việt/Pháp/Hàn/Trung; chăm sóc, thu nhập, tòa án, lao động, sức khỏe |
| [23_civic_service_long](23_civic_service_long/README.md) | 30 | 12.000 khảo sát + 12.000 cỡ mẫu; mean có/không Total, header 3 cấp |
| [24_procurement_temporal_long](24_procurement_temporal_long/README.md) | 30 | 16.000 dòng, 9.600 hợp đồng; tỷ giá ngày, hiệu lực nửa mở, ghi có |
| [25_energy_intervals_long](25_energy_intervals_long/README.md) | 30 | 20.000 khoảng đo; kWh/kW, giao khoảng, giá theo giờ, bảng cạnh nhau |
| [26_logistics_event_versions](26_logistics_event_versions/README.md) | 30 | 32.800 dòng sự kiện / 8.000 vận đơn; phiên bản, UTC, đúng hẹn, P95 |
| [27_lab_units_censoring_long](27_lab_units_censoring_long/README.md) | 30 | 30.000 kết quả / 27 cột; µg/L–mg/L, '<', tiêu đề lặp, median/P95 |

Trong dashboard, tải lại trang để thấy các bộ tự được nhận diện. Chọn một hoặc nhiều bộ rồi **Chạy mới**. Nên bắt đầu bằng một bộ hoặc một câu ở chế độ **LLM + Tools**. Chọn tất cả sẽ gọi API cho nhiều câu và có thể phát sinh phí.

Mỗi bộ có `xlsx_files/`, `queries.json`, `expected_submission.csv` và README. Bộ 06–22 có thêm `answer_checks.json`: phép tính tham chiếu từ địa chỉ ô, được kiểm lại trên file Excel đã lưu. File này và đáp án mẫu chỉ phục vụ đánh giá, không là đầu vào của bộ giải. Các câu ghi rõ cách làm tròn, thứ tự phá hòa và xử lý ô trống.

Chưa chạy LLM để đo exact match trên 300 câu mới của bộ 13–22. Kiểm tra đáp án chuẩn không chứng minh mô hình trả lời đúng. Dữ liệu được tạo để kiểm tra nhiều cấu trúc và phép tính; không thay thế tập ẩn của BTC.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_extended_fixtures.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_public_transfer_fixtures.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_long_multilingual_fixtures.py -v
.\.venv\Scripts\python.exe -m unittest discover -s Test -v
```

Tái tạo câu hỏi và đặc tả workbook bằng `python scripts/gen_extended_test_suites.py`. Export Excel bằng `scripts/author_test_workbooks.mjs` với `@oai/artifact-tool` trong môi trường authoring; đây không phải phụ thuộc khi chạy bài thi. Copy builder Node vào thư mục có `node_modules/@oai/artifact-tool`, rồi chạy bản copy và truyền đường dẫn tới `outputs/test-expansion/workbooks.json`. Không chạy generator khi một lần đánh giá đang dùng bộ dữ liệu.

Đáp án `smoke_q001` đã sửa thành `Dang`: phải xếp theo tuổi thực tế tại ngày nhập học, không theo ngày sinh hay thứ tự nhập học.

## 10 bộ mới dựa trên cả hai bộ công khai (13–22)

Mỗi bộ có một `data.xlsx` mới và đúng 30 câu trong `queries.json`. Một workbook có thể có nhiều sheet. Cả 25 workbook nguồn được ghi nhận trong `public_transfer_manifest.json`, kèm SHA-256, kích thước, merged ranges và ID câu hỏi gốc liên quan. `provenance.json` trong từng bộ ghi rõ nguồn cấu trúc và seed; dữ liệu không phải bản sao các bản ghi công khai, cũng không phải số liệu thống kê thực tế.

Ngoài các file chung, mỗi bộ có `sample_submission.csv` với 30 đáp án rỗng. Khi đánh giá, dùng **`expected_submission.csv`**, không dùng file mẫu rỗng. Chỉ truyền `xlsx_files/` và `queries.json` vào mô hình; giữ đáp án và biểu thức kiểm tra ngoài ngữ cảnh mô hình.

Hai lớp kiểm chứng: `test_extended_fixtures.py` tính lại biểu thức tham chiếu từ XLSX đã lưu; `test_public_transfer_fixtures.py` tính riêng toàn bộ **300 đáp án** bằng thao tác dòng/cột, không gọi bộ giải hay bộ thông dịch biểu thức tham chiếu. Test cũng kiểm tra seed cố định tái tạo được dữ liệu, seed khác thay đổi dữ liệu và đáp án, và câu hỏi không trùng nguyên văn câu công khai. Các sheet đã được render để kiểm tra bố cục.

Chạy một bộ và chấm Exact Match:

```powershell
python main.py --mode llm --xlsx_dir Test/19_safety_naics/xlsx_files --queries Test/19_safety_naics/queries.json --output outputs/19_safety_naics.csv --log-dir outputs/19_safety_naics-logs
python scripts/evaluate.py --prediction outputs/19_safety_naics.csv --reference Test/19_safety_naics/expected_submission.csv --report outputs/19_safety_naics-evaluation.json
```

Tái tạo bộ 13–22 gồm hai bước: sinh đặc tả/câu hỏi/đáp án bằng Python, sau đó export XLSX bằng builder Node. `@oai/artifact-tool` chỉ cần trong môi trường tạo dữ liệu, không cần khi mô hình đọc các XLSX đã có:

```powershell
python scripts/gen_public_transfer_suites.py --seed 261016
# Chạy bản copy builder trong thư mục authoring có node_modules/@oai/artifact-tool:
node <authoring-dir>/author_public_transfer_workbooks.mjs outputs/public-transfer/workbooks.json
```

Builder gốc ở `scripts/author_public_transfer_workbooks.mjs`. Để sinh biến thể đánh giá mới, dùng seed khác và thư mục riêng, ví dụ `python scripts/gen_public_transfer_suites.py --seed 271017 --test-root TestHoldout --spec outputs/holdout/workbooks.json`, rồi export spec đó. Giữ seed mặc định của bộ đã commit để kết quả hiện tại có thể so sánh và kiểm lại bằng test độc lập. Không chạy generator khi một lần đánh giá đang dùng dữ liệu.
