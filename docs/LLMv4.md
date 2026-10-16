# LLMv4 — nâng cấp từng phần trên nền LMMv3

Nhánh `Bao_LLMv4`, chế độ `--mode llm-v4`, version `llmv4-contract-context-v1`.
Đây là phiên bản pipeline dùng cùng model OpenRouter cấu hình hiện có, không phải huấn luyện model mới.

## Phạm vi đã làm

- Đặc tả đầu ra: yêu cầu trả năm/nhãn không bị ép sum/mean do tên chỉ tiêu trong điều kiện; template Việt/Anh xác định tuple và số thành phần. Kiểm tra thập phân từng thành phần số, không ép nhãn thành số.
- Boolean: nhận diện một số cặp trả lời Việt, Anh, Pháp, Trung, Nhật, Hàn. Executor vẫn tính boolean như cũ; chỉ đổi `Yes/No` sang cặp ngôn ngữ được hỏi sau kiểm chứng. Không dịch tên riêng hoặc thay số bằng boolean.
- Metadata Excel riêng v4: nhận diện nhãn nhóm ở ô gộp bằng anchor, tách nhãn nhóm đầu khỏi header khi có bằng chứng nhiều khối. `_section` giữ nguồn ô nhãn. Bổ sung `document_context` chứa tiêu đề/đơn vị đã bị loại khỏi column headers.
- Retry: cùng kế hoạch hoặc phản hồi lỗi, cùng lỗi và cùng bằng chứng lặp hai lần thì dừng với log `retry_stop_reason`; không xuất ứng viên đã bị từ chối. Giới hạn tổng API, retry, thời gian và ngân sách không tăng.
- CLI/dashboard có lựa chọn riêng, log ghi version, contract, metadata, định dạng boolean và lý do dừng retry. Giữ v3 để đối chứng.

## Chạy

```powershell
.\.venv\Scripts\python.exe main.py --mode llm-v4 --xlsx_dir <dataset>/xlsx_files --queries <dataset>/queries.json --output outputs/v4/submission.csv --log-dir outputs/v4/logs
```

Dashboard: chọn **LLMv4 · Đầu ra đa ngôn ngữ và nhãn nhóm**. Cần restart server để nạp backend mới, sau đó F5. Không tự chạy dataset khi mở dashboard.

## Những giới hạn cần giữ rõ

Chưa benchmark API; chưa có bằng chứng tăng điểm hay tiết kiệm token thực tế. Test giả lập kiểm tra các cơ chế, không chứng nhận độ chính xác trên tập ẩn. Giữ giới hạn 200.000 ô và giới hạn giải nén hiện tại.

Nhận diện ý định/ngôn ngữ vẫn là bộ luật hữu hạn. V4 chưa thay RAG, chưa thiết kế lại review và chưa kiểm chứng tự động mọi trường hợp đơn vị. Metadata đơn vị được đưa cho planner, không đoán hệ số hoặc tự sửa đáp án dựa trên mẫu. Cần đánh giá riêng các điều kiện thiếu dữ liệu, nhóm lồng sâu và đơn vị mơ hồ.

Không dùng ID, tên workbook hoặc tham chiếu để chọn đáp án. Không sửa các reference sai đơn vị để làm tăng điểm, không đưa reference vào prompt. Chưa merge main.
