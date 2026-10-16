# LLMv4 — nâng cấp từng phần trên nền LMMv3

Nhánh `Bao_LLMv4`, chế độ `--mode llm-v4`, version hiện tại `llmv4-typed-comparison-v3`.
Đây là phiên bản pipeline dùng cùng model OpenRouter cấu hình hiện có, không phải huấn luyện model mới.

## Phạm vi đã làm

- Đặc tả đầu ra: yêu cầu trả năm/nhãn không bị ép sum/mean do tên chỉ tiêu trong điều kiện; template Việt/Anh xác định tuple và số thành phần. Kiểm tra thập phân từng thành phần số, không ép nhãn thành số.
- Boolean: nhận diện một số cặp trả lời Việt, Anh, Pháp, Trung, Nhật, Hàn. Executor vẫn tính boolean như cũ; chỉ đổi `Yes/No` sang cặp ngôn ngữ được hỏi sau kiểm chứng. Không dịch tên riêng hoặc thay số bằng boolean.
- Metadata Excel riêng v4: nhận diện nhãn nhóm ở ô gộp bằng anchor, tách nhãn nhóm đầu khỏi header khi có bằng chứng nhiều khối. `_section` giữ nguồn ô nhãn. Bổ sung `document_context` chứa tiêu đề/đơn vị đã bị loại khỏi column headers.
- Retry: cùng kế hoạch hoặc phản hồi lỗi, cùng lỗi và cùng bằng chứng lặp hai lần thì dừng với log `retry_stop_reason`; không xuất ứng viên đã bị từ chối. Giới hạn tổng API, retry, thời gian và ngân sách không tăng.
- CLI/dashboard có lựa chọn riêng, log ghi version, contract, metadata, định dạng boolean và lý do dừng retry. Giữ v3 để đối chứng.

## Nâng cấp structured-plan-v2

- Một đặc tả thống nhất: thay contract cũ trong payload planner/reviewer bằng contract v4; ghi `question_spec` với thành phần đầu ra, đề cập kỳ, đơn vị và nhãn được trích dẫn. Đây là ứng viên cần grounding, không phải khẳng định đã hiểu mọi điều kiện.
- RAG bổ sung điểm theo cấu trúc: sheet, header, nhóm và cụm từ được hỏi; vẫn truy xuất cục bộ, không dùng model embedding hay API mới. Catalog lưu cả điểm gốc và phần điểm cấu trúc.
- Mỗi preview có `structure` chứa đường dẫn header, nhóm và đơn vị kèm địa chỉ nguồn. Không trộn kW với kWh, không tự biến mọi số trong sheet thành tiền.
- Kiểm tra phụ thuộc trước thực thi: bước phải tồn tại trước khi được tham chiếu; `ref` cần scalar, thao tác dòng cần bảng; output phải trỏ bước thật và chọn cột nếu là bảng. Schema thao tác/biểu thức chi tiết tiếp tục do executor hữu hạn hiện tại kiểm tra.
- Kiểm tra phạm vi ở mức cảnh báo: đọc thiếu phần cuối khi đề nói toàn bộ, count trên boolean, hoặc nguồn/đích khác thang tiền tệ. Không tự sửa hay chặn chỉ vì cảnh báo; không có cảnh báo cũng không đồng nghĩa đã đủ dữ liệu.
- Audit thực thi ghi input/output row count, loại kết quả và giá trị scalar. Reviewer nhận audit và cảnh báo trong lượt review đã có; sửa kế hoạch nhận audit trước đó. Không thêm lượt LLM cho phase mới.
- Review dài được chuẩn hóa về verdict/issues và giới hạn feedback, giữ log nội dung gốc có giới hạn. `revise` không có bằng chứng cụ thể được ghi unavailable thay vì kích hoạt vòng sửa vô nghĩa. Phản hồi không có verdict hợp lệ vẫn không được suy đoán thành accept.
- Dashboard có chi tiết đặc tả, kiểm tra kiểu, audit phạm vi, chuẩn hóa review và lý do dừng retry.

Tham khảo ý tưởng từ [SpreadsheetLLM](https://www.microsoft.com/en-us/research/publication/encoding-spreadsheets-for-large-language-models/), [Program of Thoughts](https://arxiv.org/abs/2211.12588), [Chain-of-Table](https://github.com/google-research/chain-of-table), [PICARD](https://aclanthology.org/2021.emnlp-main.779/), [CHESS](https://arxiv.org/abs/2405.16755). Đây là áp dụng ý tưởng vào DSL hiện có, không sao chép nguyên kiến trúc, không phải constrained decoding tại provider hoặc triển khai nhiều agent.

Test biến thể có đổi thứ tự dòng và thêm bảng nhiễu cho phép tính xác định. Các test này kiểm tra tính nhất quán của tool/metadata, chưa chứng minh LLM bất biến với các biến đổi và chưa tái tạo benchmark RobuT.

## Sửa lỗi sau đối chiếu run v3/v4

Đối chiếu các log Public_data_2: baseline v3 `20261016-142856-ebdfbc` khớp 25/30, v4 structured-plan-v2 `20261016-220904-eb2c27` khớp 23/30. V4 sửa được hai câu nhưng hồi quy bốn câu; không được suy ra mọi hồi quy đều do typed validator.

- Boolean `eq/ne`: v4 thực thi so sánh hai boolean trực tiếp, không đi vào nhánh số do Python coi bool là subclass của int. Boolean không được trộn với số hoặc dùng làm thứ tự.
- Thứ tự của hai chuỗi số: v4 nhận diện cú pháp số rõ ràng và so số bằng Decimal, thay vì so từ điển. Không đổi raw cells, không ép equality mã số, không ép chuỗi có số 0 dẫn đầu. Dấu phân cách mơ hồ yêu cầu `parse_number` khai báo locale; không tự đoán.
- Dùng ContextVar giới hạn semantics mới vào lời gọi execute của v4, reset bằng finally; không đổi mặc định hoặc làm rò cấu hình giữa luồng/câu hỏi/v3.
- Chuẩn hóa một quan hệ lag rõ ràng: derive ngay sau lag, cùng input gốc, đang dùng đúng cột mới của lag thì nối lại input tới lag. Chỉ đổi ref thành col khi tên step và cột lag trùng nhau; các quan hệ mơ hồ giữ nguyên để báo lỗi. Không thêm phép tính, bộ lọc hoặc dữ liệu đầu vào.
- Nếu output.decimals là danh sách toàn cùng một số nguyên hợp lệ, đổi thành scalar tương đương; không đoán định dạng khi các thành phần khác nhau.
- Với steps bị encode thành string, chỉ chuẩn hóa escape whitespace bên ngoài chuỗi JSON rồi dùng parser cũ. Không thêm key, số, toán tử, dấu phẩy hoặc sửa giá trị literal; cấu trúc còn sai vẫn bị từ chối.

Các test mới dùng dữ liệu tổng hợp và phản ví dụ. Không có resolver theo ID, không thực thi lại dataset bằng API và không có điểm benchmark mới. Các vấn đề chọn sai phạm vi, thiếu điều kiện và kế hoạch thiếu phép tính vẫn cần đánh giá/sửa riêng. Không tăng retry để che lỗi.

## Chạy

```powershell
.\.venv\Scripts\python.exe main.py --mode llm-v4 --xlsx_dir <dataset>/xlsx_files --queries <dataset>/queries.json --output outputs/v4/submission.csv --log-dir outputs/v4/logs
```

Dashboard: chọn **LLMv4 · Excel có cấu trúc và kiểm chứng kế hoạch**. Cần restart server để nạp backend mới, sau đó F5. Không tự chạy dataset khi mở dashboard.

## Những giới hạn cần giữ rõ

Chưa benchmark API; chưa có bằng chứng tăng điểm hay tiết kiệm token thực tế. Test giả lập kiểm tra các cơ chế, không chứng nhận độ chính xác trên tập ẩn. Giữ giới hạn 200.000 ô và giới hạn giải nén hiện tại.

Nhận diện ý định/ngôn ngữ vẫn là bộ luật hữu hạn. RAG vẫn lexical; review vẫn dùng cùng model, chưa kiểm chứng tự động mọi trường hợp đơn vị. Metadata và cảnh báo được đưa cho planner/reviewer, không đoán hệ số hoặc tự sửa đáp án dựa trên mẫu. Cần đánh giá riêng các điều kiện thiếu dữ liệu, nhóm lồng sâu, sai cột và đơn vị mơ hồ.

Không dùng ID, tên workbook hoặc tham chiếu để chọn đáp án. Không sửa các reference sai đơn vị để làm tăng điểm, không đưa reference vào prompt. Chưa merge main.
