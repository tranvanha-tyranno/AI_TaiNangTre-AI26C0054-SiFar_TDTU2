# Bộ kiểm thử Excel QA

**12 bộ, 212 câu** với file Excel và đáp án mẫu. Các bộ 06–12 thêm 200 câu từ dữ liệu tổng hợp cố định.

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

Trong dashboard, tải lại trang để thấy các bộ tự được nhận diện. Chọn một hoặc nhiều bộ rồi **Chạy mới**. Nên bắt đầu bằng một bộ hoặc một câu ở chế độ **LLM + Tools**. Chọn tất cả sẽ gọi API cho nhiều câu và có thể phát sinh phí.

Mỗi bộ có `xlsx_files/`, `queries.json`, `expected_submission.csv` và README. Bộ 06–12 có thêm `answer_checks.json`: phép tính tham chiếu từ địa chỉ ô, được kiểm lại trên file Excel đã lưu. File này và đáp án mẫu chỉ phục vụ đánh giá, không là đầu vào của bộ giải. Các câu ghi rõ cách làm tròn, thứ tự phá hòa và xử lý ô trống.

Chưa chạy LLM để đo exact match của 200 câu mới. Kiểm tra offline xác nhận I/O, không chứng minh bộ giải trả lời đúng. Dữ liệu được tạo để kiểm tra nhiều cấu trúc và phép tính; không thay thế tập ẩn của BTC.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_extended_fixtures.py -v
.\.venv\Scripts\python.exe -m unittest discover -s Test -v
```

Tái tạo câu hỏi và đặc tả workbook bằng `python scripts/gen_extended_test_suites.py`. Export Excel bằng `scripts/author_test_workbooks.mjs` với `@oai/artifact-tool` trong môi trường authoring; đây không phải phụ thuộc khi chạy bài thi. Copy builder Node vào thư mục có `node_modules/@oai/artifact-tool`, rồi chạy bản copy và truyền đường dẫn tới `outputs/test-expansion/workbooks.json`. Không chạy generator khi một lần đánh giá đang dùng bộ dữ liệu.

Đáp án `smoke_q001` đã sửa thành `Dang`: phải xếp theo tuổi thực tế tại ngày nhập học, không theo ngày sinh hay thứ tự nhập học.
