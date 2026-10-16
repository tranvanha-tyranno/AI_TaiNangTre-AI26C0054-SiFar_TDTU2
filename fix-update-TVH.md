# Fix update TVH

Ngày ghi nhận: 16/10/2026.

Tài liệu theo dõi các giải pháp sửa lỗi để xử lý lần lượt. Hiện ghi nhận **giải pháp 1 cho câu 2**; đây là đề xuất triển khai, chưa phải xác nhận solver đã được sửa.

## Giải pháp 1 — Câu 2: chọn tên nhóm bằng điều kiện từ dữ liệu Excel

**Trạng thái:** Đã phân tích log, chưa sửa mã nguồn, chưa chạy lại API.

### 1. Log và yêu cầu đầu ra

- Run: `outputs/runs/20261016-121430-10f888/` — Public_data_2, bắt đầu lúc 12:14:30 ngày 16/10/2026.
- Bản ghi: câu có `id = 2` trong `questions.jsonl`.
- Workbook: `p2_t01.xlsx`, sheet `Table A-6`.
- Yêu cầu: so sánh thời gian làm việc nhà của hai nhóm, trả về `group, difference`; chênh lệch có đúng hai chữ số thập phân.

Dữ liệu trong lần chạy này:

| Nhóm | Ô | Giá trị (giờ/ngày) |
|---|---|---:|
| Full-time employed mothers | B67 | 0.84 |
| Not-employed fathers | F67 | 0.56 |

Kết quả đối chiếu: `full-time employed mothers, 0.28`.

### 2. Vì sao bị lỗi?

| Lượt | Xử lý | Kết quả |
|---|---|---|
| 1 | Đọc hai ô, khai báo xuất `diff_calc` nhưng chưa tạo bước này. | `Final step does not exist`. |
| 2 | Bổ sung phép trừ và tính được `0.28`, chỉ xuất một số. | Thiếu tên nhóm; answer contract yêu cầu hai thành phần. |
| 3 | Ghép tên nhóm cố định với kết quả phép trừ bằng `record`. | Trường tên nhóm không phụ thuộc dữ liệu Excel nên executor từ chối. |

Thông báo ở lượt cuối:

```text
record fields must depend on spreadsheet scalars; labels can be cells or conditionals on cells
```

Trong lượt 3, tên nhóm được khai báo trực tiếp:

```json
"group": {"value": "full-time employed mothers"}
```

Biểu thức này không có nguồn ô Excel (`sources` rỗng), nên bị chặn tại `src/tools/executor.py`, trong nhánh xử lý `record`. Sau khi hết hai lượt sửa, pipeline không có đáp án vượt qua kiểm tra và xuất chuỗi rỗng.

**Kết luận:** Hai ô đầu vào và phép trừ đã đúng. Lỗi nằm ở kế hoạch ghép đầu ra, cụ thể là cách chọn tên nhóm.

### 3. Cách sửa

Chọn tên nhóm bằng `if` dựa trên phép so sánh hai giá trị đã đọc. Tính độ chênh lệch bằng `abs(sub(...))`, rồi ghép hai thành phần trong một `record`.

Kế hoạch minh họa cho đúng workbook của log này:

```json
{
  "steps": [
    {
      "id": "mothers_full_time",
      "op": "cell",
      "table": "t1",
      "row": 67,
      "column": "B"
    },
    {
      "id": "fathers_not_employed",
      "op": "cell",
      "table": "t1",
      "row": 67,
      "column": "F"
    },
    {
      "id": "difference",
      "op": "calculate",
      "expr": {
        "abs": [
          {
            "sub": [
              {"ref": "mothers_full_time"},
              {"ref": "fathers_not_employed"}
            ]
          }
        ]
      }
    },
    {
      "id": "result",
      "op": "record",
      "fields": {
        "group": {
          "if": [
            {
              "gt": [
                {"ref": "mothers_full_time"},
                {"ref": "fathers_not_employed"}
              ]
            },
            {"value": "full-time employed mothers"},
            {"value": "not-employed fathers"}
          ]
        },
        "difference": {"ref": "difference"}
      }
    }
  ],
  "output": {
    "step": "result",
    "columns": ["group", "difference"],
    "separator": ", ",
    "decimals": 2
  },
  "answer_spec": {
    "answer_type": "text",
    "answer_field": "group",
    "operation": "other",
    "metric": "difference in average hours of Housework",
    "unit": "hours"
  }
}
```

Nhánh `if` nhận nguồn từ điều kiện so sánh, nên tên nhóm được chọn có căn cứ từ hai ô Excel. Trường `difference` nhận nguồn từ phép tính. Cả hai trường đáp ứng yêu cầu truy vết của `record`.

`t1`, dòng 67 và cột B/F chỉ minh họa dữ liệu trong log. Khi triển khai, planner phải xác định vị trí từ workbook và câu hỏi; không gắn quy tắc với ID câu hỏi, tên workbook hoặc tọa độ cố định. Hai tên nhóm trong nhánh `if` là các lựa chọn đầu ra do câu hỏi yêu cầu.

### 4. Phạm vi triển khai giải pháp 1

- Hướng dẫn planner tạo điều kiện so sánh dữ liệu khi đầu ra gồm tên nhóm thắng và mức chênh lệch.
- Dùng `record` để xuất đúng hai thành phần, theo thứ tự câu hỏi yêu cầu.
- Giữ kiểm tra nguồn dữ liệu của executor; tên nhóm phải phụ thuộc phép so sánh.
- Với trường hợp hai giá trị bằng nhau, xử lý theo yêu cầu câu hỏi; mẫu hai nhánh trên chỉ áp dụng khi có một nhóm lớn hơn rõ ràng.

### 5. Kiểm chứng trước khi đánh dấu hoàn tất

| Ca kiểm tra | Kết quả cần có |
|---|---|
| Dữ liệu gốc: mẹ 0.84, cha 0.56. | `full-time employed mothers, 0.28` |
| Dữ liệu biến thể: mẹ 0.56, cha 0.84. | `not-employed fathers, 0.28` |
| Đổi vị trí hai cột cùng tiêu đề tương ứng. | Planner tìm đúng cột và giữ kết quả đúng theo dữ liệu. |

Có thể kiểm chứng kế hoạch với executor cục bộ trước. Việc planner tự tạo được kế hoạch đúng cần được kiểm tra riêng bằng một lần chạy API sau khi cập nhật hướng dẫn.

- [ ] Kế hoạch có đủ bước đọc, so sánh, tính chênh lệch và ghép đầu ra.
- [ ] Tên nhóm và chênh lệch đều truy vết được về dữ liệu Excel.
- [ ] Đầu ra đúng hai thành phần, chênh lệch không âm và có hai chữ số thập phân.
- [ ] Các ca biến thể xác nhận kết quả không phụ thuộc ID hoặc vị trí cột cố định.
- [ ] Log chạy lại xác nhận câu trả lời cuối vượt qua các lớp kiểm tra.
