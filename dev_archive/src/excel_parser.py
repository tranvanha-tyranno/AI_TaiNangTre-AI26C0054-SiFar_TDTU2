"""
excel_parser.py — Chuẩn hoá Excel phức tạp thành text cho LLM / code-gen.

Xử lý:
- Merged cells  -> expand giá trị ra toàn vùng
- Tiêu đề phân cấp (2-3 dòng header) -> flatten thành "L1 | L2 | L3"
- Nhiều bảng / sheet trên cùng file
- Giữ nguyên số, ngày, indent level để LLM suy luận

Output: dict {sheet_name: {"markdown": str, "csv": str, "meta": {...}}}
và hàm serialize_for_llm() trả về chuỗi text gọn để nhét vào prompt.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Tuple

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet


def _expand_merged(ws: Worksheet):
    """Copy giá trị ô gốc ra toàn bộ vùng merged. Phải làm trước khi đọc."""
    for mr in list(ws.merged_cells.ranges):
        val = ws.cell(mr.min_row, mr.min_col).value
        # unmerge rồi fill
        ws.unmerge_cells(str(mr))
        for r in range(mr.min_row, mr.max_row + 1):
            for c in range(mr.min_col, mr.max_col + 1):
                if ws.cell(r, c).value is None:
                    ws.cell(r, c).value = val


def _clean(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        # giữ nguyên dạng số, LLM cần chính xác
        return str(int(v))
    s = str(v).strip()
    # gộp whitespace / newline trong header
    s = re.sub(r"\s+", " ", s)
    return s


def _detect_data_start(ws: Worksheet, max_scan: int = 12) -> int:
    """Heuristic: dòng đầu có >=2 ô non-empty liên tiếp là header."""
    for r in range(1, min(max_scan, ws.max_row) + 1):
        vals = [_clean(ws.cell(r, c).value) for c in range(1, min(8, ws.max_column + 1))]
        non_empty = sum(1 for v in vals if v)
        if non_empty >= 3:
            return r
    return 1


def _header_depth(ws: Worksheet, start_row: int) -> int:
    """Đếm số dòng header liên tiếp trước khi gặp dòng dữ liệu số/nhãn rõ ràng."""
    depth = 1
    for r in range(start_row, min(start_row + 3, ws.max_row)):
        nxt = r + 1
        if nxt > ws.max_row:
            break
        cur_vals = [_clean(ws.cell(r, c).value) for c in range(1, ws.max_column + 1)]
        nxt_vals = [_clean(ws.cell(nxt, c).value) for c in range(1, ws.max_column + 1)]
        # Nếu dòng tiếp theo có cột đầu là số nguyên (như cột No=1,2,3...) -> đó là data, dừng
        first = nxt_vals[0] if nxt_vals else ""
        if re.fullmatch(r"\d+", first):
            break
        nxt_text_ratio = sum(1 for v in nxt_vals if v and re.search(r"[A-Za-z%]", v)) / max(1, sum(1 for v in nxt_vals if v))
        cur_text_ratio = sum(1 for v in cur_vals if v and re.search(r"[A-Za-z%]", v)) / max(1, sum(1 for v in cur_vals if v))
        if nxt_text_ratio > 0.3 and "20" not in " ".join(nxt_vals[:3]):
            header_keywords = ["year", "total", "percent", "index", "level", "category", "age", "industry", "hours", "education", "bachelor"]
            joined = " ".join(nxt_vals).lower()
            if any(k in joined for k in header_keywords) or cur_text_ratio > 0.4:
                depth += 1
            else:
                break
        else:
            break
        if depth >= 3:
            break
    return min(depth, 3)


def _flatten_headers(ws: Worksheet, start_row: int, depth: int) -> List[str]:
    headers: List[str] = []
    for c in range(1, ws.max_column + 1):
        parts = []
        for r in range(start_row, start_row + depth):
            v = _clean(ws.cell(r, c).value)
            if v and v not in parts:
                parts.append(v)
        # loại bỏ duplicate do expand merged
        # nếu cột đầu tiên rỗng ở dòng dưới thì lấy từ trên
        h = " / ".join(parts) if parts else f"col_{c}"
        headers.append(h)
    # trim trailing empty cols
    while headers and headers[-1].startswith("col_"):
        headers.pop()
    return headers


def _rows_as_records(ws: Worksheet, start_row: int, depth: int, headers: List[str]) -> List[List[str]]:
    records = []
    for r in range(start_row + depth, ws.max_row + 1):
        vals = [_clean(ws.cell(r, c).value) for c in range(1, len(headers) + 1)]
        if not any(vals):
            continue
        # skip dòng footnote / note (thường chứa *, -, --, Footnote)
        joined = " ".join(vals).lower()
        if joined.startswith("note") or joined.startswith("footnote") or joined.startswith("source"):
            continue
        records.append(vals)
    return records


def parse_excel(path: str | Path) -> Dict[str, Dict]:
    """Parse một file .xlsx, trả về dict theo sheet."""
    wb = openpyxl.load_workbook(path, data_only=True)
    result: Dict[str, Dict] = {}
    for ws in wb.worksheets:
        _expand_merged(ws)
        # bỏ qua sheet rỗng
        if ws.max_row < 2 or ws.max_column < 2:
            continue
        # phát hiện vùng dữ liệu thực
        # tìm dòng đầu có nội dung
        start_row = 1
        for r in range(1, ws.max_row + 1):
            vals = [_clean(ws.cell(r, c).value) for c in range(1, min(6, ws.max_column + 1))]
            if sum(1 for v in vals if v) >= 2:
                start_row = r
                break
        # với các file HOUSEHOLD DATA có title ở trên, header thực sự ở dòng 4-6
        # heuristic: nếu dòng start chứa HOUSEHOLD / Numbers -> nhảy xuống
        probe = " ".join(_clean(ws.cell(start_row, c).value) for c in range(1, 4)).lower()
        if "household" in probe or "numbers in thousands" in probe or "in thousands" in probe:
            # tìm dòng có "2023" hoặc "Less than" hoặc "Industry"
            for r in range(start_row, min(start_row + 8, ws.max_row + 1)):
                row_txt = " ".join(_clean(ws.cell(r, c).value) for c in range(1, 5)).lower()
                if "2023" in row_txt or "less than" in row_txt or "industry" in row_txt or "age and" in row_txt or "characteristic" in row_txt:
                    start_row = r
                    break

        depth = _header_depth(ws, start_row)
        # clamp: với HOUSEHOLD DATA header thường 2 dòng, với p4_t03 là 3 dòng
        headers = _flatten_headers(ws, start_row, depth)
        records = _rows_as_records(ws, start_row, depth, headers)

        # build markdown
        md_lines = [f"### Sheet: {ws.title}  (header_depth={depth}, rows={len(records)})"]
        # ghi chú đơn vị nếu có
        for r in range(1, start_row):
            note = " ".join(_clean(ws.cell(r, c).value) for c in range(1, ws.max_column + 1) if _clean(ws.cell(r, c).value))
            if note and ("thousands" in note.lower() or "billion" in note.lower() or "numbers" in note.lower()):
                md_lines.append(f"> Unit note: {note}")
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for rec in records:
            # escape |
            rec_esc = [v.replace("|", "/") for v in rec]
            md_lines.append("| " + " | ".join(rec_esc) + " |")

        # csv
        csv_lines = [",".join(f'"{h}"' if "," in h else h for h in headers)]
        for rec in records:
            csv_lines.append(",".join(f'"{v}"' if "," in v else v for v in rec))

        result[ws.title] = {
            "headers": headers,
            "records": records,
            "markdown": "\n".join(md_lines),
            "csv": "\n".join(csv_lines),
            "meta": {"header_depth": depth, "start_row": start_row, "nrows": len(records), "ncols": len(headers)},
        }
    return result


def serialize_for_llm(parsed: Dict[str, Dict], max_chars: int = 14000) -> str:
    """Gộp các sheet thành một chuỗi text nhét vào prompt, cắt ngắn nếu quá dài."""
    parts = []
    for sheet, data in parsed.items():
        parts.append(data["markdown"])
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        # cắt theo dòng, ưu tiên giữ header
        lines = text.splitlines()
        # giữ 60% đầu + 40% cuối nếu quá dài
        keep_head = int(max_chars * 0.6)
        head = "\n".join(lines)[:keep_head]
        tail = "\n".join(lines)[-int(max_chars * 0.35):]
        text = head + "\n\n...[TRUNCATED]...\n\n" + tail
    return text


def parse_and_serialize(path: str | Path) -> Tuple[Dict[str, Dict], str]:
    parsed = parse_excel(path)
    text = serialize_for_llm(parsed)
    return parsed, text
