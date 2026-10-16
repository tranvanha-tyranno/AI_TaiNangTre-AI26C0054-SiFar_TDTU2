# 5 bộ dài, đa ngôn ngữ và nghiệp vụ mới (23–27)

Mỗi bộ có **30 câu**, gồm **15 Việt, 5 Anh, 4 Trung, 3 Pháp, 3 Hàn**. Tổng cộng 150 câu trên **110.800 bản ghi ở các bảng chính**, cộng các bảng phụ có quan hệ nghiệp vụ. Tất cả bản ghi là hư cấu được sinh mới với seed `261017`; không trình bày chúng như số liệu thống kê hay tiêu chuẩn môi trường thực tế.

| Bộ | Bảng chính | Dạng bài mới |
|---|---:|---|
| [Dịch vụ đô thị](23_civic_service_long/README.md) | 12.000 bản ghi, header 3 cấp | Mean qua mọi cột gồm Total; mean chỉ nhóm con; tỷ lệ có trọng số; Total đổi vị trí; bảng lưu trữ gây nhiễu |
| [Mua sắm](24_procurement_temporal_long/README.md) | 16.000 dòng chứng từ | Ghép tỷ giá theo đúng ngày; ghép hợp đồng theo hiệu lực; ghi có âm; đếm hóa đơn khác đếm dòng; top-3 concentration |
| [Điện năng](25_energy_intervals_long/README.md) | 20.000 khoảng đo 1 giờ | Giá theo giờ; giao khoảng nửa mở; nhiều sự cố không đếm đôi; kWh khác kW; CO2 và đổi đơn vị; bảng nằm cạnh nhau |
| [Vận chuyển](26_logistics_event_versions/README.md) | 32.800 dòng sự kiện | Giữ bản sửa mới nhất trước khi tìm trạng thái cuối; thứ tự vật lý xáo trộn; đúng hẹn gồm dấu bằng; giờ UTC; nearest-rank P95 |
| [Kiểm nghiệm](27_lab_units_censoring_long/README.md) | 30.000 kết quả, 30.030 dòng vật lý, tới cột AA | Chuỗi '<' khác số 0 và ô thiếu; mg/L–µg/L; loại kết quả bị từ chối; header lặp; trung vị/P95; mẫu đủ ba chất; truy xuất cột xa/cuối bảng |

Các bảng phụ có hàng nghìn dòng thực, như 12.000 dòng cỡ mẫu, 9.600 hợp đồng, 8.000 vận đơn và 2.000 khoảng giá. Workbook có 3–4 sheet; dữ liệu chính có thể nằm sau sheet danh mục. Các câu hỏi yêu cầu tính trên toàn bảng và truy xuất phần giữa/cuối, không chỉ tăng số dòng đệm.

## Áp dụng AGENTS.md mới

- `queries.json` dùng ID số tự nhiên, cố ý xáo trộn để phát hiện xuất CSV theo thứ tự đầu vào. `expected_submission.csv` dùng UTF-8 và ID số tăng dần. Mã như `VD-008000` là mã nghiệp vụ trong Excel, cần giữ số 0 đầu.
- Mỗi bộ có một câu hỏi yêu cầu trường không tồn tại; đáp án đúng là chuỗi rỗng. Không thay bằng `N/A`, `None` hay thông báo lỗi. Những câu có phép đếm không tìm thấy vẫn trả `0`.
- Bộ 23 có các cặp câu đối chứng theo §11.1: mean “across all…” trên 8 cột, gồm hai Total; mean chỉ 6 nhóm con; sum cỡ mẫu không cộng lại Total. Các cặp được kiểm tra để bảo đảm kết quả có/không Total thật sự khác nhau.
- Câu hỏi ghi rõ cách xử lý thiếu, phạm vi, đơn vị, biên thời gian, phá hòa và số chữ số thập phân. Quy ước bỏ thiếu trong các câu này được nêu riêng, không gán thành một quy định chung của BTC.
- Điểm của `scripts/evaluate.py` là **strict exact match**; không tuyên bố mô phỏng đầy đủ chuẩn hóa của BTC.

## Kiểm chứng và tính ổn định

```powershell
python -m unittest tests.test_long_multilingual_fixtures -v
```

Bộ kiểm tra đọc lại **XLSX đã lưu**, dựng bảng SQLite từ đúng vùng vật lý, rồi tính lại cả 150 đáp án bằng SQL ngoài solver. Các phép đối chứng Python riêng kiểm tra hơn 70 đáp án quan trọng: cột Total, trọng số, biên hợp đồng, tỷ giá, giao khoảng, khử trùng sự kiện, thời gian thực, median/P95 và đổi đơn vị. Có kiểm tra số bản ghi, định dạng UTF-8/ID, đáp án rỗng, seed lặp lại và seed mới làm thay đổi dữ liệu/đáp án. Mỗi sheet có preview đầu/cuối; bảng rộng còn được xem ở vùng cột xa.

Các file `answer_audit.json`, `dataset_manifest.json` và `expected_submission.csv` dành riêng cho đánh giá. **Chỉ đưa `xlsx_files/` và `queries.json` cho mô hình**, không đưa SQL, manifest hay đáp án vào ngữ cảnh. Đã tạo dữ liệu chưa đồng nghĩa mô hình giải đúng; chưa có điểm LLM trên 150 câu này.

## Chạy một bộ

```powershell
python main.py --mode llm --xlsx_dir Test/26_logistics_event_versions/xlsx_files --queries Test/26_logistics_event_versions/queries.json --output outputs/logistics.csv --log-dir outputs/logistics-logs
python scripts/evaluate.py --prediction outputs/logistics.csv --reference Test/26_logistics_event_versions/expected_submission.csv --report outputs/logistics-strict.json
```

Dashboard tự phát hiện các bộ mới khi làm mới danh sách dataset. Chọn bộ 23–27 tương ứng. Việc gọi LLM dùng API và cần đo chi phí/thời gian thực tế; không suy ra đạt giới hạn 40 phút/20 câu, RAM ≤ 4 GB hay disk ≤ 1 GB chỉ từ kích thước workbook.

## Tái tạo và sinh đề mới

```powershell
python scripts/gen_long_multilingual_suites.py --seed 261017
# Chạy bản copy builder cạnh node_modules/@oai/artifact-tool, mỗi spec một tiến trình:
node --max-old-space-size=6000 <authoring-dir>/author_long_workbooks.mjs outputs/long-multilingual/specs/23_civic_service_long.json
```

Lặp lệnh export cho spec 24–27. Builder ở `scripts/author_long_workbooks.mjs`; `@oai/artifact-tool` chỉ cần để tạo file, không phải dependency của solver. Ngân sách bộ nhớ của môi trường **authoring** riêng không phải bằng chứng về giới hạn RAM bài chạy cuối. Thời điểm Excel được ghi dưới dạng serial số với format ngày/giờ để giữ chính xác mốc UTC, tránh biến đổi qua múi giờ của môi trường tạo file.

Để tạo biến thể chưa dùng chỉnh mô hình, giữ riêng thư mục mới:

```powershell
python scripts/gen_long_multilingual_suites.py --seed 261099 --test-root TestHoldoutLong --spec-root outputs/long-holdout/specs
```

Sau đó export các spec mới; `expected_submission.csv` được tính lại theo dữ liệu seed mới. Không ghi đè bộ chuẩn hoặc tái sinh trong lúc mô hình đang chạy đánh giá. Bộ test đối chứng mặc định dùng seed chuẩn đã commit.
