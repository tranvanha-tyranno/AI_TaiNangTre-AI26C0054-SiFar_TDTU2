"""Deterministic Excel QA fixtures. Answers are computed from cell references.

Run this script, then author_test_workbooks.mjs to export the workbook specs.
The solver never reads answer_checks.json; it is only for fixture verification.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.test_fixture_oracle import evaluate, format_answer


class Suite:
    def __init__(self, name, description):
        self.name, self.description = name, description
        self.sheets, self.queries, self.checks = [], [], []
        self.cells = {}

    def sheet(self, name, rows, start="A1", merges=(), formats=None):
        from openpyxl.utils.cell import coordinate_to_tuple, get_column_letter
        row0, col0 = coordinate_to_tuple(start)
        serialized = [[v.isoformat() if isinstance(v, date) else v for v in row] for row in rows]
        self.sheets.append({"name": name, "start": start, "rows": serialized,
                            "merges": list(merges), "formats": formats or {}})
        for r, row in enumerate(rows, row0):
            for c, value in enumerate(row, col0):
                self.cells[f"{name}!{get_column_letter(c)}{r}"] = value

    def add(self, category, question, expression, decimals=None):
        ident = f"{self.name[:2]}_q{len(self.queries)+1:03d}"
        answer = format_answer(evaluate(expression, self.cells), decimals)
        if not answer:
            raise ValueError(f"Empty oracle answer: {ident}")
        self.queries.append({"id": ident, "file_name": "data.xlsx", "query": question})
        self.checks.append({"id": ident, "category": category, "expression": expression,
                            "decimals": decimals, "answer": answer})

    def save(self, target):
        folder = target / self.name
        (folder / "xlsx_files").mkdir(parents=True, exist_ok=True)
        for filename, payload in [("queries.json", self.queries), ("answer_checks.json", self.checks)]:
            (folder / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with (folder / "expected_submission.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["id", "answer"])
            writer.writerows((q["id"], check["answer"]) for q, check in zip(self.queries, self.checks))
        categories = sorted({c["category"] for c in self.checks})
        (folder / "README.md").write_text(
            f"# {self.name}\n\n{self.description}\n\n"
            f"{len(self.queries)} câu. Nhóm: {', '.join(categories)}. Dữ liệu tổng hợp cố định, không có thông tin cá nhân thật.\n\n"
            "Chọn bộ này trong Dashboard → Chạy mới → LLM + Tools. Đáp án mẫu được tính bằng Python từ ô nguồn; "
            "`answer_checks.json` lưu phép tính và địa chỉ ô để kiểm chứng, không được đưa vào đầu vào của bộ giải. "
            "Không có đáp án hay công thức kiểm thử trong Excel.\n\n"
            f"```powershell\n.\\.venv\\Scripts\\python.exe main.py --mode llm --xlsx_dir Test/{self.name}/xlsx_files "
            f"--queries Test/{self.name}/queries.json --output outputs/{self.name}.csv --log-dir outputs/{self.name}-logs\n"
            f".\\.venv\\Scripts\\python.exe scripts/evaluate.py --prediction outputs/{self.name}.csv "
            f"--reference Test/{self.name}/expected_submission.csv\n```\n\n"
            "Offline chỉ kiểm tra I/O; có thể trả chưa trả lời. Chạy online có phí theo số câu. "
            "Câu hỏi quy định thứ tự, cách xử lý thiếu dữ liệu và số chữ số thập phân khi cần.\n",
            encoding="utf-8")
        return {"suite": self.name, "file": str(folder / "xlsx_files" / "data.xlsx"), "sheets": self.sheets}


def cell(sheet, col, row): return {"cell": f"{sheet}!{col}{row}"}
def cells(sheet, col, first, last): return {"range": {"sheet":sheet,"column":col,"first":first,"last":last}}
def op(name, *args): return {name: list(args)}
def table(sheet, columns, first, last):
    return {"table": {"sheet":sheet,"columns":columns,"first":first,"last":last}}
def filt(data, **conditions): return {"filter": {"data": data, "conditions": conditions}}
def column(data, name): return {"column": {"data": data, "name": name}}
def agg(name, data, col=None): return {name: column(data, col) if col else data}
def ranked(data, by, columns, offset=0, limit=1):
    return {"rank": {"data": data, "by": by, "columns": columns, "offset": offset, "limit": limit}}


def people():
    s = Suite("06_people_filters", "40 người, tiêu đề tên/ngày/điểm có ô gộp. Lọc nhiều điều kiện, tuổi tròn tại ngày nhập học, xếp hạng và phá hòa.")
    rows = [["ID", "Identity", None, "Dates", None, "Results", None, "City", "Status"],
            [None, "Name", "Department", "Birth", "Admission", "Score", "Attendance", None, None]]
    depts = ["Engineering", "Business", "Design", "Science"]
    cities = ["Ha Noi", "Da Nang", "Ho Chi Minh City"]
    for i in range(1,41):
        rows.append([f"P{i:03d}", f"Person {i:02d}", depts[(i-1)%4], date(1990+i%15,1+i%12,1+i%27),
                     date(2024+i%2,1+(i*3)%12,1+(i*5)%27), 45+(i*17)%56, .7+(i%7)*.05,
                     cities[i%3], "Active" if i%5 else "Inactive"])
    s.sheet("People", rows, merges=["A1:A2","B1:C1","D1:E1","F1:G1","H1:H2","I1:I2"],
            formats={"D3:E42":"yyyy-mm-dd", "G3:G42":"0%"})
    t=table("People",dict(id="A",name="B",dept="C",birth="D",admission="E",score="F",attendance="G",city="H",status="I"),3,42)
    for i in [1,7,13,24,40]:
        s.add("lookup",f"In People, what is the score of P{i:03d}? Answer only the integer.",cell("People","F",i+2))
    for threshold in [60,70,80,90,100]:
        s.add("count",f"How many people have Score strictly greater than {threshold}? Answer only the integer.",agg("count",filt(t,score={"gt":threshold})))
    for dept in depts:
        s.add("conditional_sum",f"Tổng Score của những người thuộc Department {dept} và Status Active là bao nhiêu? Chỉ trả số nguyên.",agg("sum",filt(t,dept=dept,status="Active"),"score"))
    for dept in depts:
        s.add("average",f"What is the average Score for Department {dept}? Include all statuses. Answer to exactly 2 decimal places.",agg("mean",filt(t,dept=dept),"score"),2)
    for k in [1,2,3,5]:
        s.add("ranking",f"Sort all people by Score descending, breaking ties by ID ascending. What is the ID at position {k} (1-based)? Answer only the ID.",ranked(t,[["score","desc"],["id","asc"]],["id"],k-1))
    s.add("top_k","List the IDs of the top 3 Active people by Score descending, ties by ID ascending. Separate IDs with comma and one space.",ranked(filt(t,status="Active"),[["score","desc"],["id","asc"]],["id"],limit=3))
    for city in cities:
        s.add("multi_filter",f"How many people in {city} have Score >= 80 and Status Active? Answer only the integer.",agg("count",filt(t,city=city,score={"ge":80},status="Active")))
    for ident in ["P001","P007"]:
        s.add("age",f"What was {ident}'s age in completed years on their Admission date? Use Birth and Admission, not the current date. Answer only the integer.",{"age": [cell("People","D",int(ident[1:])+2),cell("People","E",int(ident[1:])+2)]})
    s.add("percentage","What percentage of all 40 people are Active? Answer with exactly 2 decimal places, without the percent sign.",op("mul",op("div",agg("count",filt(t,status="Active")),40),100),2)
    s.add("empty_filter","How many people have Score greater than 100? Answer only the integer, including 0 if none.",agg("count",filt(t,score={"gt":100})))
    return s


def sales():
    s=Suite("07_sales_aggregation", "96 giao dịch: tổng có điều kiện, nhóm, nhiều phép tính, giá trị âm của trả hàng và tỷ lệ có trọng số.")
    rows=[["Order ID","Region","Product","Month","Units","Unit Price","Revenue","Cost","Status"]]
    for i in range(1,97):
        units=-(1+i%4) if i%11==0 else 1+i%9
        price=20+(i%5)*15
        rows.append([f"O{i:03d}",["North","Central","South"][i%3],["Laptop","Phone","Tablet","Monitor"][i%4],
                     1+(i//4)%6,units,price,units*price,units*(price-8),"Returned" if units<0 else "Completed"])
    s.sheet("Sales",rows,formats={"F2:H97":"0.00"})
    t=table("Sales",dict(id="A",region="B",product="C",month="D",units="E",price="F",revenue="G",cost="H",status="I"),2,97)
    for region in ["North","Central","South"]:
        for metric,col in [("Revenue","revenue"),("Units","units"),("Cost","cost")]:
            s.add("group_sum",f"What is total {metric} in Region {region}, including negative returned transactions? Answer only the integer.",agg("sum",filt(t,region=region),col))
    for product in ["Laptop","Phone","Tablet","Monitor"]:
        s.add("filter_sum",f"What is total Revenue for Product {product} with Status Completed? Answer only the integer.",agg("sum",filt(t,product=product,status="Completed"),"revenue"))
    for month in range(1,7):
        s.add("period_sum",f"Tổng Revenue trong Month {month}, bao gồm trả hàng âm, là bao nhiêu? Chỉ trả số nguyên.",agg("sum",filt(t,month=month),"revenue"))
    for region in ["North","Central","South"]:
        f=filt(t,region=region)
        s.add("profit",f"What is profit (total Revenue minus total Cost) for Region {region}, including returns? Answer only the integer.",op("sub",agg("sum",f,"revenue"),agg("sum",f,"cost")))
    s.add("weighted_average","Among Completed sales, what is the unit-weighted average Unit Price (sum Revenue / sum Units)? Answer exactly 2 decimal places.",op("div",agg("sum",filt(t,status="Completed"),"revenue"),agg("sum",filt(t,status="Completed"),"units")),2)
    s.add("negative","How many orders have negative Units? Answer only the integer.",agg("count",filt(t,units={"lt":0})))
    s.add("total","What is total net Revenue over every Sales data row, including returns? Answer only the integer.",agg("sum",t,"revenue"))
    s.add("ranking","Which Order ID has the highest Revenue? Break ties by Order ID ascending. Answer only the ID.",ranked(t,[["revenue","desc"],["id","asc"]],["id"]))
    s.add("top_k","List the 3 Order IDs with lowest Revenue, breaking ties by Order ID ascending. Separate with comma and one space.",ranked(t,[["revenue","asc"],["id","asc"]],["id"],limit=3))
    s.add("range_filter","How many Completed orders have Revenue from 100 to 300 inclusive? Answer only the integer.",agg("count",filt(t,status="Completed",revenue={"ge":100,"le":300})))
    s.add("percentage","What percent of all orders have Status Returned? Answer exactly 2 decimal places without %.",op("mul",op("div",agg("count",filt(t,status="Returned")),agg("count",t)),100),2)
    s.add("comparison","Is total Revenue for South greater than total Revenue for North, including returns? Answer only Yes or No.",op("gt",agg("sum",filt(t,region="South"),"revenue"),agg("sum",filt(t,region="North"),"revenue")))
    return s


def hierarchy():
    s=Suite("08_three_level_headers", "Tiêu đề 3 cấp Year / Quarter / Metric, hai chỉ tiêu lặp tên dưới từng quý và ghi chú cuối bảng không phải dữ liệu.")
    rows=[["Sector", "2023",None,None,None,"2024",None,None,None],
          [None,"Q1",None,"Q2",None,"Q1",None,"Q2",None],
          [None,"Count","Rate","Count","Rate","Count","Rate","Count","Rate"]]
    labels=["Agriculture","Manufacturing","Construction","Transport","Education","Retail","Health","Technology"]
    for i,label in enumerate(labels,1):
        rows.append([label,100+i*13,.05+i*.01,110+i*17,.04+i*.01,140+i*11,.06+i*.01,130+i*19,.05+i*.01])
    rows += [[None]*9,["Note: Count is in thousands. Rate is stored as a fraction. This note is not a data row."]+[None]*8]
    s.sheet("Indicators",rows,merges=["A1:A3","B1:E1","F1:I1","B2:C2","D2:E2","F2:G2","H2:I2"],
            formats={f"{c}4:{c}11":"0%" for c in "CEGI"})
    for i,label in enumerate(labels[:5],4):
        s.add("header_lookup",f"For {label}, what is Count in 2024 Q2 (not Rate)? Answer only the integer in the table's thousands unit.",cell("Indicators","H",i))
        s.add("header_lookup",f"For {label}, what is Count in 2023 Q1? Answer only the integer in the table's thousands unit.",cell("Indicators","B",i))
    for i,label in enumerate(labels[:4],4):
        s.add("percentage_format",f"For {label}, what is Rate in 2024 Q1 as percentage points (multiply stored fraction by 100)? Answer exactly 2 decimal places, without %.",op("mul",cell("Indicators","G",i),100),2)
    for col,period in [("B","2023 Q1"),("D","2023 Q2"),("F","2024 Q1"),("H","2024 Q2")]:
        s.add("sum","What is the sum of Count across the 8 sectors in "+period+"? Ignore the note. Answer only the integer in thousands.",{"sum":cells("Indicators",col,4,11)})
    for i,label in enumerate(labels[:3],4):
        s.add("difference",f"For {label}, how much did Count change from 2023 Q2 to 2024 Q2 (2024 minus 2023)? Answer only the integer in thousands.",op("sub",cell("Indicators","H",i),cell("Indicators","D",i)))
    t=table("Indicators",dict(sector="A",count="H",rate="I"),4,11)
    s.add("ranking","Rank all sectors by 2024 Q2 Count descending, ties alphabetically. Return sector names separated by comma and one space.",ranked(t,[["count","desc"],["sector","asc"]],["sector"],limit=8))
    s.add("comparison","Is Education's 2024 Q1 Count greater than Education's 2023 Q1 Count? Answer Yes or No.",op("gt",cell("Indicators","F",8),cell("Indicators","B",8)))
    s.add("units","Convert the total 2024 Q2 Count across all sectors from thousands into individual people. Answer only the integer, no commas.",op("mul",{"sum":cells("Indicators","H",4,11)},1000))
    s.add("ratio","What is Technology's 2024 Q2 Count divided by its 2023 Q2 Count? Answer exactly 2 decimal places.",op("div",cell("Indicators","H",11),cell("Indicators","D",11)),2)
    return s


def multisheet():
    s=Suite("09_multisheet_join", "Ba sheet, hai bảng cùng sheet, tên cột lặp và hàng TOTAL dễ gây cộng đôi. Ghép Orders với Products theo Product ID.")
    products=[["Product ID","Name","Category","Unit Cost"]]+[[f"K{i:02d}",f"Item {i:02d}","Hardware" if i%2 else "Accessory",10+i*3] for i in range(1,9)]
    orders=[["Order ID","Product ID","Units","Revenue"]]
    for i in range(1,33): orders.append([f"R{i:03d}",f"K{1+i%8:02d}",1+i%6,(1+i%6)*(30+(i%8)*7)])
    s.sheet("Products",products)
    s.sheet("Orders",orders)
    rows=[[None]*7 for _ in range(8)]
    rows[0]=["Warehouse","Stock",None,None,"Warehouse","Returns",None]
    for i,name in enumerate(["North","Central","South"],1): rows[i]=[name,100+i*40,None,None,name,i*3,None]
    rows[6]=["Metric","Value",None,None,None,None,None]
    rows[7]=["TOTAL",sum(r[3] for r in orders[1:]),None,None,None,None,None]
    s.sheet("Summary",rows)
    t=table("Orders",dict(id="A",product="B",units="C",revenue="D"),2,33)
    p=table("Products",dict(product="A",name="B",category="C",cost="D"),2,9)
    j={"join":{"left":t,"right":p,"key":"product"}}
    for i in range(1,9):
        data=filt(j,product=f"K{i:02d}")
        s.add("join_sum",f"What is total Units ordered for product Item {i:02d}? Join Orders.Product ID to Products.Product ID. Answer only the integer.",agg("sum",data,"units"))
        s.add("join_calculation",f"For Item {i:02d}, what is total cost of ordered units (sum Orders.Units times Products.Unit Cost)? Answer only the integer.",op("mul",agg("sum",data,"units"),cell("Products","D",i+1)))
    for category in ["Hardware","Accessory"]:
        s.add("join_filter",f"What is total Revenue from Orders for Products in Category {category}? Do not add Summary.TOTAL. Answer only the integer.",agg("sum",filt(j,category=category),"revenue"))
    for i,name in enumerate(["North","Central","South"],2):
        s.add("side_by_side",f"In Summary, what is Stock minus Returns for warehouse {name}? Use the two side-by-side tables. Answer only the integer.",op("sub",cell("Summary","B",i),cell("Summary","F",i)))
    s.add("deduplicate_total","What is total Revenue across Orders only? Summary.TOTAL repeats it and must not be added. Answer only the integer.",agg("sum",t,"revenue"))
    s.add("reconcile","Does Summary.TOTAL equal the sum of Orders.Revenue? Answer only Yes or No.",op("eq",cell("Summary","B",8),agg("sum",t,"revenue")))
    s.add("table_sum","Tổng Stock của ba kho trong bảng bên trái sheet Summary là bao nhiêu? Chỉ trả số nguyên.",{"sum":cells("Summary","B",2,4)})
    s.add("table_sum","What is total Returns in the right-hand Summary table? Answer only the integer.",{"sum":cells("Summary","F",2,4)})
    s.add("join_count","How many Orders rows refer to Category Hardware? Answer only the integer.",agg("count",filt(j,category="Hardware")))
    s.add("join_count","How many distinct Product IDs exist in Orders? Answer only the integer.",{"distinct_count":column(t,"product")})
    s.add("ranking","Which Order ID has the largest Revenue? Break ties by Order ID ascending. Answer only the ID.",ranked(t,[["revenue","desc"],["id","asc"]],["id"]))
    s.add("join_lookup","What is the product Name for order R017? Join by Product ID and answer only the Name.",ranked(filt(j,id="R017"),[["id","asc"]],["name"]))
    s.add("multi_step","What is total Revenue divided by total Units in Orders? Answer exactly 2 decimal places.",op("div",agg("sum",t,"revenue"),agg("sum",t,"units")),2)
    return s


def dates():
    s=Suite("10_dates_boundaries", "Ngày tháng kiểu Excel, năm nhuận, lọc khoảng đóng/mở, sinh nhật và độ dài dự án. Mốc thời gian cố định.")
    records=[
        ["D01",date(2000,2,29),date(2024,2,28),date(2024,3,1),100],
        ["D02",date(2001,3,1),date(2024,2,29),date(2024,3,10),110],
        ["D03",date(1999,12,31),date(2024,12,31),date(2025,1,1),120],
        ["D04",date(2000,1,1),date(2024,1,1),date(2024,1,31),130],
        ["D05",date(2000,6,15),date(2024,6,14),date(2024,6,15),140],
        ["D06",date(2000,6,15),date(2024,6,15),date(2024,7,1),150],
    ]
    for i in range(7,21):
        start=date(2024,1,1)+timedelta(days=i*17)
        records.append([f"D{i:02d}",date(1995+i%9,1+i%12,1+i%27),start,start+timedelta(days=i*3),90+i*10])
    s.sheet("Projects",[["ID","Birth","Start","End","Budget"]]+records,formats={"B2:D21":"yyyy-mm-dd"})
    t=table("Projects",dict(id="A",birth="B",start="C",end="D",budget="E"),2,21)
    for i in range(1,7):
        s.add("age",f"What is D{i:02d}'s age in completed years on Start? For a Feb 29 birthday in a non-leap year, treat Mar 1 as the birthday. Answer only the integer.",{"age":[cell("Projects","B",i+1),cell("Projects","C",i+1)]})
    for i in range(1,7):
        s.add("date_diff",f"How many elapsed calendar days are between Start and End for D{i:02d}? Compute End minus Start, do not add 1. Answer only the integer.",{"days":[cell("Projects","C",i+1),cell("Projects","D",i+1)]})
    for month in [1,2,3,6]:
        lower=date(2024,month,1); upper=date(2024,month+1,1)
        s.add("date_filter",f"How many projects start in {lower:%Y-%m}? Include the month's first and last calendar day. Answer only the integer.",agg("count",filt(t,start={"ge":lower.isoformat(),"lt":upper.isoformat()})))
    s.add("date_filter","What is total Budget for projects starting on or after 2024-01-01 and before 2024-07-01? Answer only the integer.",agg("sum",filt(t,start={"ge":"2024-01-01","lt":"2024-07-01"}),"budget"))
    s.add("date_filter","How many projects have Start strictly before 2024-03-01? Answer only the integer.",agg("count",filt(t,start={"lt":"2024-03-01"})))
    s.add("date_filter","How many projects start exactly on 2024-02-29? Answer only the integer.",agg("count",filt(t,start="2024-02-29")))
    s.add("date_filter","How many projects have End in 2025? Answer only the integer.",agg("count",filt(t,end={"ge":"2025-01-01","lt":"2026-01-01"})))
    s.add("ranking","Which project has the earliest Start? Break ties by ID ascending. Answer only its ID.",ranked(t,[["start","asc"],["id","asc"]],["id"]))
    s.add("ranking","Which project has the latest End? Break ties by ID ascending. Answer only its ID.",ranked(t,[["end","desc"],["id","asc"]],["id"]))
    s.add("date_lookup","What is the End date for D03? Answer only YYYY-MM-DD.",cell("Projects","D",4))
    s.add("date_lookup","Ngày Start của D02 là ngày nào? Chỉ trả YYYY-MM-DD.",cell("Projects","C",3))
    s.add("comparison","Does D05 start before its 24th birthday? Answer only Yes or No.",op("lt",cell("Projects","C",6),"2024-06-15"))
    return s


def edges():
    s=Suite("11_missing_ties_unicode", "Ô trống khác số 0, số âm, trùng tên, đồng điểm, Unicode tiếng Việt, dấu phẩy/nháy và mã có số 0 đầu.")
    rows=[["Code","Name","Group","Value","Score","Remark"],
          ["001","Nguyễn An","A",0,90,"zero is present"],
          ["002","Trần Bình","A",None,90,"missing"],
          ["003","O'Neil, Jr.","B",-5,80,"comma and apostrophe"],
          ["004",'Công ty "Ánh Dương"',"B",10,80,"quoted name"],
          ["005","Lê Mai","C",20,100,"top tie"],
          ["006","Lê Mai","C",30,100,"duplicate name, unique code"],
          ["007","Đỗ Hà","A",-10,70,None],
          ["008","Bùi Vân","B",None,60,None],
          ["009","Phạm Quang","C",40,50,"normal"],
          ["010","Vũ Linh","A",0,40,"zero is present"],
          ["011","Hồ Tú","B",5,30,"normal"],
          ["012","Dương Hòa","C",None,20,"missing"]]
    s.sheet("Records",rows,formats={"A2:A13":"@"})
    t=table("Records",dict(code="A",name="B",group="C",value="D",score="E",remark="F"),2,13)
    for i in [1,3,4,5,12]:
        s.add("text_lookup",f"What is the exact Name for Code {i:03d}? Preserve spelling, accents and punctuation. Answer only the name.",cell("Records","B",i+1))
    for group in "ABC":
        f=filt(t,group=group)
        s.add("missing_sum",f"What is the sum of Value for Group {group}? Ignore blank Values, include zero and negatives. Answer only the integer.",agg("sum",f,"value"))
        s.add("missing_average",f"What is the average Value for Group {group}? Ignore blank Values but include zero and negatives. Answer exactly 2 decimal places.",agg("mean",f,"value"),2)
    s.add("missing_count","How many Records have a blank Value? Do not count numeric zero as blank. Answer only the integer.",agg("count",filt(t,value=None)))
    s.add("zero_count","How many Records have numeric Value equal to 0? Ignore blanks. Answer only the integer.",agg("count",filt(t,value=0)))
    s.add("negative_count","How many Records have Value below 0? Ignore blanks. Answer only the integer.",agg("count",filt(t,value={"lt":0})))
    s.add("nonblank_count","How many Records have a nonblank Value, including zero? Answer only the integer.",agg("count",filt(t,value={"not_blank":True})))
    s.add("ties","Which Code has the highest Score? Break the tie by Code ascending. Preserve leading zeros. Answer only the Code.",ranked(t,[["score","desc"],["code","asc"]],["code"]))
    s.add("ties","List the Codes with the top 3 Scores, ties by Code ascending. Preserve leading zeros. Separate with comma and one space.",ranked(t,[["score","desc"],["code","asc"]],["code"],limit=3))
    s.add("duplicate_name","How many rows have Name exactly Lê Mai? Count rows, not distinct names. Answer only the integer.",agg("count",filt(t,name="Lê Mai")))
    s.add("duplicate_name","Tổng Value của các dòng có Name Lê Mai là bao nhiêu? Chỉ trả số nguyên.",agg("sum",filt(t,name="Lê Mai"),"value"))
    s.add("distinct","How many distinct Name values are in Records? Answer only the integer.",{"distinct_count":column(t,"name")})
    s.add("min","What is the minimum nonblank Value? Answer only the integer, including the minus sign.",agg("min",t,"value"))
    s.add("max","What is the maximum nonblank Value? Answer only the integer.",agg("max",t,"value"))
    s.add("missing_count","How many rows have blank Remark? Answer only the integer.",agg("count",filt(t,remark=None)))
    s.add("empty_filter","How many rows have Score strictly greater than 100? Answer only the integer.",agg("count",filt(t,score={"gt":100})))
    s.add("sum","What is total Value across all Records? Ignore blank Values. Answer only the integer.",agg("sum",t,"value"))
    return s


def large():
    s=Suite("12_large_full_scan", "2.500 dòng trên sheet lớn; câu hỏi ở giữa/cuối dữ liệu, tổng toàn bảng, lọc hiếm và cột ở ngoài 30 cột xem trước của dashboard.")
    rows=[["ID","Group","Value","Flag"]+[f"Aux {i}" for i in range(5,35)]+["Secret Value"]]
    for i in range(1,2501):
        rows.append([i,f"G{i%5}",(i*37)%1000-100,"Rare" if i%499==0 else "Normal"]+[None]*30+[i*13+7])
    s.sheet("Big",rows,formats={"AI2:AI2501":"0"})
    t=table("Big",dict(id="A",group="B",value="C",flag="D",secret="AI"),2,2501)
    for i in [1,100,501,999,1250,1703,1996,2000,2499,2500]:
        s.add("long_lookup",f"In Big, what is Value for ID {i}? Answer only the integer.",cell("Big","C",i+1))
    for group in [f"G{i}" for i in range(5)]:
        s.add("full_scan_sum",f"What is the sum of Value for Group {group} across all 2500 data rows, including negatives? Answer only the integer.",agg("sum",filt(t,group=group),"value"))
        s.add("full_scan_count",f"How many rows in Group {group} have Value > 800? Scan the full table. Answer only the integer.",agg("count",filt(t,group=group,value={"gt":800})))
    for i in [501,1250,2000,2500]:
        s.add("wide_lookup",f"What is Secret Value in column AI for ID {i}? Answer only the integer.",cell("Big","AI",i+1))
    s.add("full_scan_sum","What is the total Value across all 2500 data rows? Include negative values. Answer only the integer.",agg("sum",t,"value"))
    s.add("full_scan_average","What is average Value across all 2500 rows? Answer exactly 2 decimal places.",agg("mean",t,"value"),2)
    s.add("rare_filter","How many rows have Flag Rare? Answer only the integer.",agg("count",filt(t,flag="Rare")))
    s.add("rare_filter","What is total Value for Flag Rare? Answer only the integer.",agg("sum",filt(t,flag="Rare"),"value"))
    s.add("rare_filter","List all IDs with Flag Rare in ID ascending order, separated by comma and one space.",ranked(filt(t,flag="Rare"),[["id","asc"]],["id"],limit=2500))
    s.add("ranking","Which ID has the highest Value? Break ties by numeric ID ascending. Answer only the integer ID.",ranked(t,[["value","desc"],["id","asc"]],["id"]))
    s.add("ranking","List the 3 IDs with lowest Value, breaking ties by numeric ID ascending. Separate with comma and one space.",ranked(t,[["value","asc"],["id","asc"]],["id"],limit=3))
    s.add("late_range","What is total Value for IDs 2001 through 2500 inclusive? Answer only the integer.",agg("sum",filt(t,id={"ge":2001,"le":2500}),"value"))
    s.add("late_range","How many IDs from 1001 through 2000 inclusive have Value below 0? Answer only the integer.",agg("count",filt(t,id={"ge":1001,"le":2000},value={"lt":0})))
    s.add("empty_filter","How many rows have Value > 1000? Answer only the integer, including 0.",agg("count",filt(t,value={"gt":1000})))
    s.add("wide_sum","What is total Secret Value in column AI over all 2500 data rows? Answer only the integer.",agg("sum",t,"secret"))
    return s


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-root",type=Path,default=ROOT/"Test")
    parser.add_argument("--spec",type=Path,default=ROOT/"outputs/test-expansion/workbooks.json")
    args=parser.parse_args()
    suites=[fn() for fn in [people,sales,hierarchy,multisheet,dates,edges,large]]
    counts=[len(s.queries) for s in suites]
    assert counts==[30,30,25,30,25,25,35],counts
    specs=[s.save(args.test_root) for s in suites]
    args.spec.parent.mkdir(parents=True,exist_ok=True)
    args.spec.write_text(json.dumps(specs,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Prepared {len(suites)} suites, {sum(counts)} questions. Workbook spec: {args.spec}")


if __name__=="__main__": main()
