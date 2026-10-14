#!/usr/bin/env python3
"""Tạo Test/ với 5 suite riêng dựa trên Public_data_1."""
import json, datetime
from pathlib import Path
import openpyxl
from openpyxl.styles import Alignment, Font

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "Test"
TEST.mkdir(exist_ok=True)

def write(p, wb): wb.save(p)

# 01 smoke replica
def build_01():
    base = TEST / "01_smoke_replica"
    (base / "xlsx_files").mkdir(parents=True, exist_ok=True)
    p = base / "xlsx_files" / "mini_people.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "People"
    ws["B1"]="Name"; ws["E1"]="Date of"; ws["G1"]="Score"
    for c,v in enumerate(["No","First","Middle","Last","Birth","Admission",""],1):
        ws.cell(2,c).value = v if v else ("Score" if c==7 else "")
    ws.merge_cells("B1:D1"); ws.merge_cells("E1:F1"); ws.merge_cells("G1:G2")
    data=[
        [1,"Ha","Minh","Dang", datetime.date(2005,1,3), datetime.date(2025,2,12), 92],
        [2,"An","Gia","Pham", datetime.date(1995,2,14), datetime.date(2024,2,8), 60],
        [3,"Linh","Thi","Ngo", datetime.date(2003,6,20), datetime.date(2024,6,1), 83],
        [4,"Binh","Van","Tran", datetime.date(1998,11,2), datetime.date(2023,9,15), 77],
        [5,"Mai","Thu","Le", datetime.date(2006,3,18), datetime.date(2025,1,10), 99],
    ]
    for i,row in enumerate(data,3):
        for c,v in enumerate(row,1): ws.cell(i,c).value=v
    wb.save(p)
    p2 = base / "xlsx_files" / "mini_fiscal.xlsx"
    wb2 = openpyxl.Workbook(); ws2=wb2.active; ws2.title="Fiscal"
    ws2["A1"]="Category"; ws2["B1"]="Fiscal year-to-date 2023"; ws2["C1"]="Fiscal year-to-date 2024"
    ws2["A2"]="Agricultural exports"; ws2["B2"]=1200; ws2["C2"]=1350
    ws2["A3"]="Industrial exports"; ws2["B3"]=800; ws2["C3"]=750
    wb2.save(p2)
    queries=[
        {"id":"smoke_q001","file_name":"mini_people.xlsx","query":"Who was the second-youngest person on their admission date? Answer with only the last name."},
        {"id":"smoke_q002","file_name":"mini_people.xlsx","query":"Among the ten youngest people, what was the highest score? Answer with only the integer score."},
        {"id":"smoke_q003","file_name":"mini_fiscal.xlsx","query":"Is the agricultural export value for the fiscal year-to-date 2024 greater than that for the fiscal year-to-date 2023? Answer with only Yes or No."},
    ]
    (base/"queries.json").write_text(json.dumps(queries,ensure_ascii=False,indent=2),encoding="utf-8")
    (base/"expected_submission.csv").write_text("id,answer\nsmoke_q001,Pham\nsmoke_q002,99\nsmoke_q003,Yes\n",encoding="utf-8")
    (base/"README.md").write_text("# 01_smoke_replica — Smoke nhanh (3 cau)\n\nKiem tra I/O, merged header Name/Date of, va nhanh fiscal Yes/No ma khong can LLM.\n\n```powershell\n./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/01_smoke_replica/xlsx_files --queries ./Test/01_smoke_replica/queries.json --output ./Test/01_smoke_replica/submission.csv\n./.venv/Scripts/python.exe scripts/evaluate.py --prediction ./Test/01_smoke_replica/submission.csv --reference ./Test/01_smoke_replica/expected_submission.csv\n```\n\nDashboard: chon dataset `01_smoke_replica` o dropdown.\n",encoding="utf-8")

def build_02():
    base = TEST / "02_merged_hierarchy"
    (base / "xlsx_files").mkdir(parents=True, exist_ok=True)
    p = base / "xlsx_files" / "hierarchy.xlsx"
    wb = openpyxl.Workbook(); ws=wb.active; ws.title="HOUSEHOLD DATA"
    ws["A1"]="HOUSEHOLD DATA - Numbers in thousands"
    ws.merge_cells("A1:E1")
    ws.merge_cells("B2:C2"); ws.merge_cells("D2:E2")
    ws["A2"]="Category"; ws["B2"]="2023"; ws["D2"]="2024"
    ws["A3"]="Category"; ws["B3"]="Total"; ws["C3"]="Percent"; ws["D3"]="Total"; ws["E3"]="Percent"
    for i,r in enumerate([[ "All items",1000,10,1100,11],[ "Airline fares",200,5,260,8],[ "Rent",500,20,510,19]],4):
        for c,v in enumerate(r,1): ws.cell(i,c).value=v
    ws["A8"]="Note: Percent is unadjusted percent change Sep-Oct"
    wb.save(p)
    p2 = base / "xlsx_files" / "industry_hours.xlsx"
    wb2=openpyxl.Workbook(); ws2=wb2.active; ws2.title="Industry"
    ws2.merge_cells("A1:A2"); ws2["A1"]="Industry"
    ws2.merge_cells("B1:D1"); ws2["B1"]="Employed (thousands)"
    ws2["B2"]="Construction"; ws2["C2"]="Manufacturing"; ws2["D2"]="Agriculture"
    for i, (ind,a,b,c) in enumerate([["Agriculture",10,20,30],["Manufacturing",100,200,5],["Construction",80,150,12]],3):
        ws2.cell(i,1).value=ind; ws2.cell(i,2).value=a; ws2.cell(i,3).value=b; ws2.cell(i,4).value=c
    wb2.save(p2)
    queries=[
        {"id":"hier_q001","file_name":"hierarchy.xlsx","query":"What is the total for All items in 2024? Answer with only the integer."},
        {"id":"hier_q002","file_name":"industry_hours.xlsx","query":"Rank the following sectors by the number of employees in 'Manufacturing': Agriculture, Manufacturing, and Construction. Answer with the three sector names in descending order, separated by a comma and one space, without numbering."},
    ]
    (base/"queries.json").write_text(json.dumps(queries,ensure_ascii=False,indent=2),encoding="utf-8")
    (base/"expected_submission.csv").write_text("id,answer\nhier_q001,1100\nhier_q002,\"Manufacturing, Construction, Agriculture\"\n",encoding="utf-8")
    (base/"README.md").write_text("# 02_merged_hierarchy — O gop & tieu de phan cap\n\nKiem tra _expand_merged, _header_depth, flatten L1 / L2.\n\n```powershell\n./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/02_merged_hierarchy/xlsx_files --queries ./Test/02_merged_hierarchy/queries.json --output ./Test/02_merged_hierarchy/submission.csv\n```\n",encoding="utf-8")

def build_03():
    base = TEST / "03_multisheet_multitable"
    (base / "xlsx_files").mkdir(parents=True, exist_ok=True)
    p = base / "xlsx_files" / "multi.xlsx"
    wb=openpyxl.Workbook()
    ws1=wb.active; ws1.title="Summary"
    ws1["A1"]="Category"; ws1["B1"]="Value 2023"; ws1["C1"]="Value 2024"
    ws1["A2"]="Total"; ws1["B2"]=500; ws1["C2"]=600
    ws2=wb.create_sheet("Details")
    ws2["A1"]="Industry"; ws2["B1"]="Employees 2023"
    ws2["A2"]="Manufacturing"; ws2["B2"]=1200
    ws2["A3"]="Construction"; ws2["B3"]=800
    ws2["D1"]="Industry"; ws2["E1"]="Hours"
    ws2["D2"]="Agriculture"; ws2["E2"]=35
    wb.save(p)
    queries=[
        {"id":"multi_q001","file_name":"multi.xlsx","query":"What is the absolute difference in the total number of people working in Manufacturing and Construction industries in 2023? Answer with only the integer, without commas or units."},
        {"id":"multi_q002","file_name":"multi.xlsx","query":"What is the total value for 2024 in Summary sheet? Answer with only the integer."},
    ]
    (base/"queries.json").write_text(json.dumps(queries,ensure_ascii=False,indent=2),encoding="utf-8")
    (base/"expected_submission.csv").write_text("id,answer\nmulti_q001,400\nmulti_q002,600\n",encoding="utf-8")
    (base/"README.md").write_text("# 03_multisheet_multitable — Nhieu sheet & nhieu bang\n\nKiem tra parse_excel doc du sheet, giu toa do, dashboard hien sheet selector.\n\n```powershell\n./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/03_multisheet_multitable/xlsx_files --queries ./Test/03_multisheet_multitable/queries.json --output ./Test/03_multisheet_multitable/submission.csv\n```\n",encoding="utf-8")

def build_04():
    base = TEST / "04_robustness"
    (base / "xlsx_files").mkdir(parents=True, exist_ok=True)
    p = base / "xlsx_files" / "edge.xlsx"
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="Edge"
    ws["A1"]="ID"; ws["B1"]="Name, with comma"; ws["C1"]="Score %"
    ws["A2"]=1; ws["B2"]="O'Neil, Jr."; ws["C2"]="  42.00 "
    ws["A3"]=2; ws["B3"]=""; ws["C3"]=None
    ws["A4"]=3; ws["B4"]="An, Test"; ws["C4"]=100
    wb.save(p)
    queries=[{"id":"edge_q001","file_name":"edge.xlsx","query":"What is the score for ID 1? Answer with only the integer."}]
    (base/"queries.json").write_text(json.dumps(queries,ensure_ascii=False,indent=2),encoding="utf-8")
    (base/"expected_submission.csv").write_text("id,answer\nedge_q001,42\n",encoding="utf-8")
    (base/"queries_duplicate.json").write_text(json.dumps([queries[0],queries[0]],ensure_ascii=False,indent=2),encoding="utf-8")
    (base/"queries_bad_path.json").write_text(json.dumps([{"id":"bad_q001","file_name":"../Public_data_1/sample_submission.csv","query":"test"} ],ensure_ascii=False,indent=2),encoding="utf-8")
    (base/"README.md").write_text("# 04_robustness — Bien & bao mat\n\n- Dau phay, nhay don, khoang trang trong o/cau tra loi (CSV quoting)\n- O rong / None\n- Tu choi ID trung, duong dan traversal\n\n```powershell\n./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/04_robustness/xlsx_files --queries ./Test/04_robustness/queries.json --output ./Test/04_robustness/submission.csv\n./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/04_robustness/xlsx_files --queries ./Test/04_robustness/queries_duplicate.json --output ./Test/04_robustness/out.csv; echo $LASTEXITCODE\n```\n",encoding="utf-8")

def build_05():
    base = TEST / "05_truncation_perf"
    (base / "xlsx_files").mkdir(parents=True, exist_ok=True)
    p = base / "xlsx_files" / "large.xlsx"
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="Big"
    ws["A1"]="ID"; ws["B1"]="Value"
    for i in range(2,502):
        ws.cell(i,1).value=i-1
        ws.cell(i,2).value=(i*7)%100
    wb.save(p)
    queries=[{"id":f"big_q{i:03d}","file_name":"large.xlsx","query":f"What is the value for ID {i}? Answer with only the integer."} for i in [1,100,250,500]]
    (base/"queries.json").write_text(json.dumps(queries,ensure_ascii=False,indent=2),encoding="utf-8")
    vals={q["id"]: (int(q["id"].split("q")[1])+1)*7%100 for q in queries}
    lines=["id,answer"]+[f"{q['id']},{vals[q['id']]}" for q in queries]
    (base/"expected_submission.csv").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (base/"README.md").write_text("# 05_truncation_perf — Cat ngan & hieu nang\n\n500 dong de kiem tra serialize_for_llm(max_chars=14000) cat 60/40 va dashboard hien 200x30.\n\n```powershell\n./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/05_truncation_perf/xlsx_files --queries ./Test/05_truncation_perf/queries.json --output ./Test/05_truncation_perf/submission.csv\n```\n",encoding="utf-8")

for fn in [build_01, build_02, build_03, build_04, build_05]:
    fn()
print("done")
