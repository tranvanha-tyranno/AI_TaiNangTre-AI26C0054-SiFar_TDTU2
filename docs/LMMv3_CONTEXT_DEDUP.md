# LMMv3 — bước 1: giảm dữ liệu trùng

Phiên bản `lmmv3-v2-dedup-v1`, nhánh `Bao_LMMv3`. Chỉ thay biểu diễn dữ liệu trong request trên nền LLMv2. Không đổi retrieval, bảng được chọn, giới hạn gọi, prompt lập kế hoạch gốc, công cụ, kiểm tra kết quả hoặc chính sách review. Có thêm hướng dẫn ngắn giải thích cách đọc tham chiếu ô.

## Cơ chế

`src/context_dedup.py` tìm ô trùng theo sheet + dòng + cột + giá trị JSON giống hệt. Bản đầu được giữ; bản sau tham chiếu tới view trước trong cùng request. Không gộp hai ô khác sheet hoặc khác giá trị, không bỏ table ID, bounds, header, merged ranges hay metadata của bảng.

`view_id` định danh preview trong request. `cells_from` tham chiếu các cột tại cùng dòng; `row_refs` gom những dòng trùng hoàn toàn theo view nguồn và cột; `row_order` giữ thứ tự gốc. Không có cache liên request hoặc phụ thuộc lượt gọi trước. Mọi nguồn tham chiếu đều có giá trị thực ở cùng message. Preview và workbook gốc trong log/executor không bị sửa.

Áp dụng cho cả plan/repair (previews + inspection_results) và review (previews). Chỉ dùng nếu tổng ký tự request sau nén, kể cả hướng dẫn tham chiếu, nhỏ hơn bản gốc; nếu không thì giữ request ban đầu nguyên vẹn. Correction/row_samples không nằm trong phạm vi thay đổi lần này.

## Bật/tắt để đối chứng

```yaml
v3_deduplicate_context: true
```

- true + `--mode llm-v3`: phiên bản `lmmv3-v2-dedup-v1`.
- false + `--mode llm-v3`: khôi phục đầu vào LLMv2 nguyên bản, version `lmmv3-v2-baseline-v1`.
- `--mode llm-v2` và `--mode llm` không dùng cơ chế này dù config đặt true.

Dashboard chọn **LMMv3 · LLMv2 + giảm dữ liệu trùng**. Các run cũ vẫn giữ nguyên version. Chi tiết câu có mục **Giảm dữ liệu trùng (đo ký tự)**; log `context_dedup` ghi từng request có áp dụng hay không, số ô và ký tự trước/sau.

## Kiểm chứng

Kiểm tra tổng hợp chứng minh khôi phục được toàn bộ payload gốc, giữ khác biệt giá trị tại cùng tọa độ, không gộp qua sheet, không thay đầu vào, tham chiếu không rò sang request khác và có fallback khi nén không có lợi. Kiểm tra pipeline xác nhận không thêm lượt gọi, kết quả công cụ không đổi với client giả lập và tắt tính năng khôi phục request LLMv2 nguyên bản.

Kiểm tra offline ngữ cảnh 10 câu từ run 20261016-134755-c9959d bằng parser/retrieval LLMv2 hiện tại: 502.867 xuống 436.840 ký tự message (-13,13%), bỏ 3.491 lần xuất hiện ô trùng; cả 10 payload khôi phục khớp bản gốc. Không gọi API, không sinh đáp án mới, không dùng reference trong solver. Tool schema không đổi và nằm ngoài số ký tự message này.

Đây không phải phép đo token/chi phí thực hoặc bằng chứng độ chính xác không giảm: LLM có thể đọc tham chiếu khác bảng số trực tiếp. Cần A/B trên cùng câu hỏi, model và cấu hình trước khi kết luận giữ cải tiến. Chưa tối ưu thêm các phase khác.
