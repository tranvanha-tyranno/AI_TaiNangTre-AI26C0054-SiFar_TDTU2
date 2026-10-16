"""Five large, multilingual Excel QA benchmarks; no API calls or solver access.

Build: python scripts/gen_long_multilingual_suites.py
Export each generated spec with scripts/author_long_workbooks.mjs.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.long_benchmark_core import LongSuite

I=" Chỉ trả số nguyên, không dấu phân cách hàng nghìn hay đơn vị."
D=" Chỉ trả số với đúng 2 chữ số thập phân, không đơn vị hay ký hiệu %."
T=" Nếu bằng nhau, chọn mã tăng dần. Chỉ trả mã."
R2={"digits":2,"scale":1}
P2={"digits":2,"scale":100}


def unknown(s,field):
    s.add("vi","unavailable_field",f"Trong workbook này, {field} là gì? Nếu workbook không cung cấp trường đó, trả chuỗi rỗng; không ghi N/A hay lời giải thích.","SELECT NULL",empty=True)


def civic(s):
    records=[]; counts=[]
    cities=["Huế","Cần Thơ","Đà Nẵng","Hà Nội","海港"]
    for i in range(1,12001):
        ward=(i-1)%500+1; month=(i-1)//500%12+1; metric="Đúng hạn" if i<=6000 else "Hài lòng"
        ns=[s.rng.randint(25,900) for _ in range(6)]
        rates=[s.rng.randint(250,980)/10 for _ in range(6)]
        total_a=round(sum(n*r for n,r in zip(ns[:3],rates[:3]))/sum(ns[:3]),1)
        total_b=round(sum(n*r for n,r in zip(ns[3:],rates[3:]))/sum(ns[3:]),1)
        ident=f"DV-{i:05d}"
        records.append([ident,f"P{ward:04d}",cities[ward%5],f"2028-{month:02d}",metric,
                        total_a,*rates[:3],*rates[3:],total_b,sum(ns),"Tạm tính" if i%97==0 else "Đã xác nhận"])
        counts.append([ident,sum(ns[:3]),*ns[:3],*ns[3:],sum(ns[3:])])
    ratekeys=["water_total","basic","advanced","special","residential","commercial","public","waste_total"]
    columns=[("id","Mã khảo sát","TEXT"),("ward","Phường","TEXT"),("city","Tỉnh / thành","TEXT"),("period","Kỳ","TEXT"),("metric","Chỉ tiêu","TEXT")]
    columns += [(key,label,"REAL") for key,label in zip(ratekeys,["Total","Cơ bản","Nâng cao","Đặc biệt","Dân cư","Thương mại","Công cộng","Total"])]
    columns += [("respondents","Tổng mẫu","INTEGER"),("status","Trạng thái","TEXT")]
    headers=[["Mã khảo sát","Phường","Tỉnh / thành","Kỳ","Chỉ tiêu","Cấp nước (%)",None,None,None,"Chất thải (%)",None,None,None,"Tổng mẫu","Trạng thái"],
             [None]*5+["Total","Mức dịch vụ",None,None,"Mức dịch vụ",None,None,"Total",None,None],
             [None]*6+["Cơ bản","Nâng cao","Đặc biệt","Dân cư","Thương mại","Công cộng",None,None,None]]
    s.table("civic","Khảo sát 2028",columns,records,headers,
            ["A1:A3","B1:B3","C1:C3","D1:D3","E1:E3","F1:I1","J1:M1","F2:F3","G2:I2","J2:L2","M2:M3","N1:N3","O1:O3"],{"A":23,"C":25,"E":22,"O":24})
    s.sheets[-1]["formats"]["F4:M12003"]="0.0"
    s.sheets[-1]["previews"] += ["F1:O10","A5999:H6007"]
    s.table("counts","Cỡ mẫu",[("id","Mã khảo sát","TEXT")]+[(key,key,"INTEGER") for key in ratekeys],counts,widths={"A":24})
    archive=[[f"OLD-{i:05d}",r[1],r[2],r[3].replace("2028","2027"),r[4],s.rng.randint(15,45)] for i,r in enumerate(records[:2400],1)]
    s.table("archive","Lưu trữ 2027",[("id","Mã cũ","TEXT"),("ward","Phường","TEXT"),("city","Tỉnh / thành","TEXT"),("period","Kỳ","TEXT"),("metric","Chỉ tiêu","TEXT"),("score","Điểm","INTEGER")],archive)
    allsum="water_total+basic+advanced+special+residential+commercial+public+waste_total"
    leaves="basic+advanced+special+residential+commercial+public"
    s.view(f"CREATE VIEW scores AS SELECT *, ({allsum}) AS all_sum, ({leaves}) AS leaf_sum FROM civic")
    for ident in ["DV-00001","DV-11999"]:
        s.add("vi","mean_all_includes_totals",f"Ở Khảo sát 2028, mã {ident}, trung bình across all nhóm dịch vụ là bao nhiêu? Theo quy ước đề thi, lấy cả 8 cột dữ liệu, gồm hai cột Total; không dùng trọng số."+D,"SELECT all_sum,8 FROM scores WHERE id=?",[ident],ratio=R2)
        s.add("vi","mean_excludes_totals",f"Với {ident}, trung bình chỉ 6 nhóm con (subcategories only, excluding totals) của hai dịch vụ là bao nhiêu?"+D,"SELECT leaf_sum,6 FROM scores WHERE id=?",[ident],ratio=R2)
        s.add("vi","sum_no_double_count",f"Trong Cỡ mẫu, mã {ident}, tổng số người ở 6 nhóm con là bao nhiêu? Không cộng thêm hai cột tổng."+I,"SELECT basic+advanced+special+residential+commercial+public FROM counts WHERE id=?",[ident])
    s.add("vi","weighted_pool","Với DV-11999, tính tỷ lệ gộp có trọng số theo cỡ mẫu của 6 nhóm con: sum(tỷ lệ*cỡ mẫu)/sum(cỡ mẫu). Không dùng hai Total."+D,"SELECT s.basic*c.basic+s.advanced*c.advanced+s.special*c.special+s.residential*c.residential+s.commercial*c.commercial+s.public*c.public,c.basic+c.advanced+c.special+c.residential+c.commercial+c.public FROM civic s JOIN counts c USING(id) WHERE id='DV-11999'",ratio=R2)
    s.add("vi","tail_lookup","Mã DV-12000 thuộc phường nào? Chỉ trả đúng mã phường.","SELECT ward FROM civic WHERE id='DV-12000'",formats=["text"])
    s.add("vi","multi_filter","Có bao nhiêu khảo sát Hài lòng tại Huế có trạng thái Đã xác nhận và tỷ lệ Cơ bản >= 80?"+I,"SELECT count(*) FROM civic WHERE metric='Hài lòng' AND city='Huế' AND status='Đã xác nhận' AND basic>=80")
    s.add("vi","group_rank","Trong tháng 2028-12, chỉ tiêu Hài lòng, phường nào có trung bình 8 cột cao nhất (kể cả Total)?"+T,"SELECT ward FROM scores WHERE period='2028-12' AND metric='Hài lòng' ORDER BY all_sum DESC,ward LIMIT 1",formats=["text"])
    s.add("vi","date_scope","Tổng mẫu của các khảo sát Đúng hạn tại Cần Thơ trong quý 4/2028 là bao nhiêu? Chỉ cộng trường Tổng mẫu mỗi dòng một lần."+I,"SELECT sum(respondents) FROM civic WHERE metric='Đúng hạn' AND city='Cần Thơ' AND period BETWEEN '2028-10' AND '2028-12'")
    s.add("vi","conditional_percentage","Trong tất cả 12000 khảo sát, bao nhiêu phần trăm có trạng thái Tạm tính?"+D,"SELECT sum(status='Tạm tính'),count(*) FROM civic",ratio=P2)
    s.add("vi","paired_metric","Ở phường P0499 tháng 2028-12, trung bình 8 cột của Hài lòng trừ trung bình 8 cột của Đúng hạn là bao nhiêu điểm phần trăm?"+D,"SELECT a.all_sum-b.all_sum,8 FROM scores a JOIN scores b ON a.ward=b.ward AND a.period=b.period WHERE a.ward='P0499' AND a.period='2028-12' AND a.metric='Hài lòng' AND b.metric='Đúng hạn'",ratio=R2)
    s.add("vi","cross_sheet_archive","Trong Lưu trữ 2027, Điểm của OLD-02400 là bao nhiêu? Không lấy giá trị ở Khảo sát 2028."+I,"SELECT score FROM archive WHERE id='OLD-02400'")
    unknown(s,"mã chứng nhận ISO của đơn vị thu thập khảo sát DV-12000")
    s.add("en","all_vs_leaf_gap","For DV-11999, what is the unweighted 8-column mean including both Total columns minus the 6-leaf mean? Return exactly 2 decimals.","SELECT all_sum/8.0-leaf_sum/6.0 FROM scores WHERE id='DV-11999'",formats=[2])
    s.add("en","top_k","Among confirmed Hài lòng records in December 2028, list the top 3 survey IDs by the 6-leaf mean descending, ties by ID ascending. Separate IDs with comma and one space.","SELECT id FROM scores WHERE metric='Hài lòng' AND period='2028-12' AND status='Đã xác nhận' ORDER BY leaf_sum DESC,id LIMIT 3",formats=["text"])
    s.add("en","strict_boundary","How many confirmed Đúng hạn records have the displayed Cấp nước Total strictly above 75.0? Return an integer.","SELECT count(*) FROM civic WHERE metric='Đúng hạn' AND status='Đã xác nhận' AND water_total>75")
    s.add("en","distinct_count","How many distinct wards appear in Khảo sát 2028, across both metrics and all months? Return an integer.","SELECT count(DISTINCT ward) FROM civic")
    s.add("en","minimum_tail","Among DV-11001 through DV-12000 inclusive, which ID has the lowest displayed Chất thải Total? Break ties by ID ascending. Return only the ID.","SELECT id FROM civic WHERE id BETWEEN 'DV-11001' AND 'DV-12000' ORDER BY waste_total,id LIMIT 1",formats=["text"])
    s.add("zh","unicode_filter","在 Khảo sát 2028 中，城市为海港且指标为 Hài lòng 的记录有多少条？只回答整数。","SELECT count(*) FROM civic WHERE city='海港' AND metric='Hài lòng'")
    s.add("zh","weighted_city","在2028年12月的 Hài lòng 记录中，海港的 Cấp nước Total 按每行 Tổng mẫu 加权的平均值是多少？保留两位小数。","SELECT sum(water_total*respondents),sum(respondents) FROM civic WHERE city='海港' AND metric='Hài lòng' AND period='2028-12'",ratio=R2)
    s.add("zh","difference","DV-12000 的 Cấp nước Total 减去 Chất thải Total 是多少个百分点？保留两位小数。","SELECT water_total-waste_total FROM civic WHERE id='DV-12000'",formats=[2])
    s.add("zh","nonempty_zero","有多少条记录的 Tổng mẫu 为0？只回答整数，不要把没有匹配项当作缺失答案。","SELECT count(*) FROM civic WHERE respondents=0")
    s.add("fr","mean_all_scope","Pour DV-06001, quelle est la moyenne non pondérée de toutes les 8 colonnes de taux, y compris les deux Total ? Deux décimales uniquement.","SELECT all_sum,8 FROM scores WHERE id='DV-06001'",ratio=R2)
    s.add("fr","leaf_scope","Pour DV-06001, quelle est la moyenne des six sous-catégories seulement, sans Total ? Deux décimales uniquement.","SELECT leaf_sum,6 FROM scores WHERE id='DV-06001'",ratio=R2)
    s.add("fr","scope_count","Combien de lignes Hài lòng confirmées sont présentes en 2028-12 ? Répondez par un entier.","SELECT count(*) FROM civic WHERE metric='Hài lòng' AND status='Đã xác nhận' AND period='2028-12'")
    s.add("ko","cross_column_max","DV-12000의 6개 하위 항목 중 최대 비율을 소수점 둘째 자리까지 답하십시오. Total은 제외합니다.","SELECT max(basic,advanced,special,residential,commercial,public) FROM civic WHERE id='DV-12000'",formats=[2])
    s.add("ko","sum_tail","DV-11501부터 DV-12000까지의 Tổng mẫu 합계를 정수로 답하십시오. 각 행은 한 번만 더합니다.","SELECT sum(respondents) FROM civic WHERE id BETWEEN 'DV-11501' AND 'DV-12000'")
    s.add("ko","header_position","DV-12000의 Chất thải Total 값은 얼마입니까? 다른 그룹의 Total과 구분하여 소수점 둘째 자리까지 답하십시오.","SELECT waste_total FROM civic WHERE id='DV-12000'",formats=[2])


def procurement(s):
    vendors=[]
    for i in range(1,2401):
        vendors.append([f"NCC-{i:04d}",f'Công ty "Sông Xanh", chi nhánh {i:04d}',["Bắc","Trung","Nam","海外"][i%4],"Ưu tiên" if i%7==0 else "Thường"])
    s.table("vendors","Nhà cung cấp",[("vendor","Mã NCC","TEXT"),("name","Tên NCC","TEXT"),("region","Vùng","TEXT"),("tier","Hạng","TEXT")],vendors,widths={"B":49})
    rates=[]
    for day in range(366):
        d=date(2028,1,1)+timedelta(days=day)
        for c,r in [("VND",1),("USD",24500+day%43*10),("EUR",26800+day%59*10)]: rates.append([d,c,r])
    s.table("fx","Tỷ giá ngày",[("day","Ngày","TEXT"),("currency","Tiền tệ","TEXT"),("rate","VND / 1 đơn vị","INTEGER")],rates)
    contracts=[]
    for vendor,*_ in vendors:
        for q in range(4):
            start=date(2028,1+3*q,1); end=date(2029,1,1) if q==3 else date(2028,4+3*q,1)
            contracts.append([f"{vendor}-Q{q+1}",vendor,start,end,s.rng.randint(2,18),s.rng.randint(20,90)*1000000])
    s.table("contracts","Hợp đồng hiệu lực",[("contract","Hợp đồng","TEXT"),("vendor","Mã NCC","TEXT"),("start","Từ ngày (gồm)","TEXT"),("end","Đến ngày (không gồm)","TEXT"),("rebate","Hoàn tiền (%)","INTEGER"),("cap","Hạn mức VND","INTEGER")],contracts)
    lines=[]
    for i in range(1,16001):
        day=date(2028,1,1)+timedelta(days=s.rng.randrange(366)); currency=["VND","USD","EUR"][i%3]
        amount=100*s.rng.randint(10,9000)
        lines.append([f"CT-{i:05d}",f"HD-{(i+1)//2:05d}",day,f"NCC-{s.rng.randint(1,2400):04d}",currency,amount,s.rng.choice([0,5,10,15]),
                      -1 if i%23==0 else 1,"Đã hủy" if i%31==0 else "Đã duyệt",["Thiết bị","Vật tư","Dịch vụ"][i%3],s.rng.randint(1,50)])
    columns=[("id","Mã dòng","TEXT"),("invoice","Số hóa đơn","TEXT"),("day","Ngày chứng từ","TEXT"),("vendor","Mã NCC","TEXT"),("currency","Tiền tệ","TEXT"),("amount","Giá trị gốc","INTEGER"),("discount","Chiết khấu (%)","INTEGER"),("sign","Dấu (ghi có=-1)","INTEGER"),("status","Trạng thái","TEXT"),("category","Nhóm hàng","TEXT"),("units","Số lượng","INTEGER")]
    s.table("lines","Chi tiết mua sắm",columns,lines,widths={"A":24,"C":25,"D":24,"I":24,"J":24})
    # Move the actual fact sheet away from the first tab; directory is intentionally first.
    s.view("CREATE VIEW spend AS SELECT l.*,v.name,v.region,v.tier,f.rate,c.contract,c.rebate,c.cap, l.amount*f.rate*(100-l.discount)/100*l.sign AS net_vnd FROM lines l JOIN vendors v USING(vendor) JOIN fx f ON l.day=f.day AND l.currency=f.currency JOIN contracts c ON l.vendor=c.vendor AND l.day>=c.start AND l.day<c.end WHERE l.status='Đã duyệt'")
    for region in ["Bắc","Trung","Nam"]:
        s.add("vi","fx_signed_sum",f"Tổng giá trị mua ròng của vùng {region}, chỉ Đã duyệt, quy đổi tỷ giá đúng ngày, trừ chiết khấu và tính âm dòng ghi có, là bao nhiêu VND?"+I,"SELECT sum(net_vnd) FROM spend WHERE region=?",[region])
        s.add("vi","distinct_invoice",f"Có bao nhiêu hóa đơn khác nhau có ít nhất một dòng Đã duyệt của NCC vùng {region}? Không đếm số dòng."+I,"SELECT count(DISTINCT invoice) FROM spend WHERE region=?",[region])
    s.add("vi","asof_contract","Dòng CT-15999 áp dụng mã hợp đồng nào? Dùng ngày bắt đầu có gồm và ngày kết thúc không gồm; không lấy hợp đồng mới nhất toàn bộ. Chỉ trả mã hợp đồng.","SELECT c.contract FROM lines l JOIN contracts c ON l.vendor=c.vendor AND l.day>=c.start AND l.day<c.end WHERE l.id='CT-15999'",formats=["text"])
    s.add("vi","tail_fx","Tỷ giá VND cho 1 đơn vị tiền của dòng CT-16000 tại đúng ngày chứng từ là bao nhiêu?"+I,"SELECT f.rate FROM lines l JOIN fx f ON l.day=f.day AND l.currency=f.currency WHERE id='CT-16000'")
    s.add("vi","rebate_join","Tổng hoàn tiền hợp đồng cho các dòng Đã duyệt, không phải ghi có, trong quý 4/2028 là bao nhiêu VND? Tính net_vnd*rebate/100, cộng trước rồi làm tròn."+D,"SELECT sum(net_vnd*rebate),100 FROM spend WHERE sign=1 AND day>='2028-10-01'",ratio=R2)
    s.add("vi","supplier_rank","NCC nào có giá trị mua ròng VND Đã duyệt cao nhất?"+T,"SELECT vendor FROM spend GROUP BY vendor ORDER BY sum(net_vnd) DESC,vendor LIMIT 1",formats=["text"])
    s.add("vi","quarter_change","Giá trị mua ròng Đã duyệt quý 4 trừ quý 3/2028 là bao nhiêu VND?"+I,"SELECT sum(CASE WHEN day>='2028-10-01' THEN net_vnd ELSE -net_vnd END) FROM spend WHERE day>='2028-07-01'")
    s.add("vi","currency_scope","Có bao nhiêu dòng EUR Đã duyệt có ngày 29/02/2028?"+I,"SELECT count(*) FROM spend WHERE currency='EUR' AND day='2028-02-29'")
    s.add("vi","weighted_discount","Chiết khấu trung bình gia quyền theo Giá trị gốc của các dòng USD Đã duyệt, sign=1, là bao nhiêu phần trăm?"+D,"SELECT sum(amount*discount),sum(amount) FROM spend WHERE currency='USD' AND sign=1",ratio=R2)
    s.add("vi","quoted_unicode_name","Tên NCC của dòng CT-16000 là gì? Giữ nguyên dấu ngoặc kép và dấu phẩy trong tên; chỉ trả tên.","SELECT v.name FROM lines l JOIN vendors v USING(vendor) WHERE id='CT-16000'",formats=["text"])
    unknown(s,"số tài khoản ngân hàng của nhà cung cấp trên dòng CT-16000")
    s.add("en","top_three_concentration","What percent of total approved net VND spend belongs to the three suppliers with largest net spend? Include signed credits, ties by supplier ID. Return exactly 2 decimals without %.","WITH x AS (SELECT vendor,sum(net_vnd) n FROM spend GROUP BY vendor ORDER BY n DESC,vendor LIMIT 3) SELECT (SELECT sum(n) FROM x),(SELECT sum(net_vnd) FROM spend)",ratio=P2)
    s.add("en","reconciliation","For all approved lines, what is gross signed VND before discounts minus approved net VND? Return an integer.","SELECT sum(amount*rate*sign-net_vnd) FROM spend")
    s.add("en","cancelled_fx","What is the signed net VND amount of cancelled line CT-00031, using its daily FX and discount? Include this line despite its cancellation for this question only. Return an integer.","SELECT l.amount*f.rate*(100-discount)/100*sign FROM lines l JOIN fx f ON l.day=f.day AND l.currency=f.currency WHERE id='CT-00031'")
    s.add("en","contract_boundary","Which contract applies to NCC-0001 on 2028-04-01, with start inclusive and end exclusive? Return only the contract ID.","SELECT contract FROM contracts WHERE vendor='NCC-0001' AND start<='2028-04-01' AND end>'2028-04-01'",formats=["text"])
    s.add("en","average_invoice","What is mean approved net VND per distinct invoice with an approved line? Sum all approved lines including credits before dividing by distinct invoice count. Return exactly 2 decimals.","SELECT sum(net_vnd),count(DISTINCT invoice) FROM spend",ratio=R2)
    s.add("zh","overseas_sum","只计已批准（Đã duyệt）的行，海外供应商的净采购总额是多少VND？按当天汇率、折扣及贷项负号计算。只回答整数。","SELECT sum(net_vnd) FROM spend WHERE region='海外'")
    s.add("zh","credit_count","已批准行中有多少个贷项行（sign=-1）？只回答整数。","SELECT count(*) FROM spend WHERE sign=-1")
    s.add("zh","priority_share","已批准的正向行中，Ưu tiên 供应商的净VND金额占多少百分比？保留两位小数，不加%。","SELECT sum(CASE WHEN tier='Ưu tiên' THEN net_vnd ELSE 0 END),sum(net_vnd) FROM spend WHERE sign=1",ratio=P2)
    s.add("zh","tail_contract_rebate","CT-15999 对应生效合同的返利率是多少？只回答整数，不加%。","SELECT c.rebate FROM lines l JOIN contracts c ON l.vendor=c.vendor AND l.day>=c.start AND l.day<c.end WHERE id='CT-15999'")
    s.add("fr","euro_net","Quel est le montant net total en VND des lignes EUR approuvées, crédits négatifs inclus, au taux du jour ? Un entier uniquement.","SELECT sum(net_vnd) FROM spend WHERE currency='EUR'")
    s.add("fr","vendor_cardinality","Combien de fournisseurs distincts ont au moins une ligne approuvée ? Un entier uniquement.","SELECT count(DISTINCT vendor) FROM spend")
    s.add("fr","negative_vendor","Combien de fournisseurs ont un total net approuvé en VND strictement négatif ? Un entier uniquement.","SELECT count(*) FROM (SELECT vendor FROM spend GROUP BY vendor HAVING sum(net_vnd)<0)")
    s.add("ko","rare_date","2028-12-31에 승인된 행의 순 VND 합계를 정수로 답하십시오. 할인과 대변 음수를 포함합니다.","SELECT coalesce(sum(net_vnd),0) FROM spend WHERE day='2028-12-31'")
    s.add("ko","amount_ratio","CT-16000의 원래 Giá trị gốc을 Số lượng로 나눈 값을 소수점 둘째 자리까지 답하십시오. 환산하지 않습니다.","SELECT amount,units FROM lines WHERE id='CT-16000'",ratio=R2)
    s.add("ko","top_list","순 VND 합계가 높은 상위 3개 공급업체 코드를 내림차순으로 답하십시오. 동률이면 코드 오름차순, 쉼표와 공백으로 구분합니다.","SELECT vendor FROM spend GROUP BY vendor ORDER BY sum(net_vnd) DESC,vendor LIMIT 3",formats=["text"])


def energy(s):
    base=datetime(2028,1,20)
    plants=[[f"NM-{i:03d}",["Miền Bắc","Miền Trung","Miền Nam","東部"][i%4],f"Trạm năng lượng {i:03d}",s.rng.randint(200,650)] for i in range(1,41)]
    s.table("plants","Nhà máy",[("plant","Mã nhà máy","TEXT"),("region","Vùng","TEXT"),("name","Tên","TEXT"),("carbon","gCO2 / kWh","INTEGER")],plants,widths={"C":35})
    tariffs=[]
    for p,*_ in plants:
        for block in range(50):
            tariffs.append([p,base+timedelta(hours=block*10),base+timedelta(hours=(block+1)*10),s.rng.randint(1200,3200)])
    s.table("tariffs","Giá theo hiệu lực",[("plant","Mã nhà máy","TEXT"),("start","Từ (UTC, gồm)","TEXT"),("end","Đến (UTC, không gồm)","TEXT"),("tariff","VND/kWh nhập ròng","INTEGER")],tariffs,widths={"B":29,"C":29})
    readings=[]
    for hour in range(500):
        for plant in range(1,41):
            i=hour*40+plant; imp=s.rng.randint(0,850); export=s.rng.randint(0,150)
            readings.append([f"ĐĐ-{i:05d}",f"NM-{plant:03d}",base+timedelta(hours=hour),None if i%211==0 else imp,export,
                             s.rng.randint(0,300),s.rng.randint(0,400),s.rng.randint(0,90),s.rng.randint(0,90),imp+s.rng.randint(0,90),
                             "Ước tính" if i%137==0 else "Đo thật",60])
    cols=[("id","Mã đo","TEXT"),("plant","Nhà máy","TEXT"),("at","Bắt đầu UTC","TEXT"),("import_kwh","Điện nhập kWh","INTEGER"),("export_kwh","Điện xuất kWh","INTEGER"),("solar_kwh","Mặt trời kWh","INTEGER"),("wind_kwh","Gió kWh","INTEGER"),("charge","Nạp pin kWh","INTEGER"),("discharge","Xả pin kWh","INTEGER"),("peak_kw","Công suất đỉnh kW","INTEGER"),("quality","Chất lượng","TEXT"),("minutes","Độ dài phút","INTEGER")]
    headers=[["Mã đo","Nhà máy","Bắt đầu UTC","Trao đổi lưới",None,"Tái tạo",None,"Lưu trữ",None,"Công suất đỉnh kW","Chất lượng","Độ dài phút"],
             [None,None,None,"Nhập kWh","Xuất kWh","Mặt trời kWh","Gió kWh","Nạp kWh","Xả kWh",None,None,None]]
    s.table("readings","Điện năng 1 giờ",cols,readings,headers,["A1:A2","B1:B2","C1:C2","D1:E1","F1:G1","H1:I1","J1:J2","K1:K2","L1:L2"],{"A":24,"C":29,"K":23})
    s.sheets[-1]["previews"] += ["I1:L10","A9989:H9998"]
    events=[]
    for i in range(1,1201):
        start=base+timedelta(hours=s.rng.randrange(495),minutes=s.rng.choice([0,15,30]))
        events.append([f"SC-{i:04d}",f"NM-{s.rng.randint(1,40):03d}",start,start+timedelta(minutes=s.rng.choice([30,60,90,180])),"Đã xác minh" if i%9 else "Chưa xác minh"])
    s.table("outages","Sự cố",[("event","Mã sự cố","TEXT"),("plant","Nhà máy","TEXT"),("start","Bắt đầu UTC","TEXT"),("end","Kết thúc UTC","TEXT"),("status","Trạng thái","TEXT")],events,widths={"C":29,"D":29})
    s.view("CREATE VIEW valid_energy AS SELECT r.*,p.region,p.carbon,t.tariff,import_kwh-export_kwh net_kwh,(import_kwh-export_kwh)*t.tariff net_cost FROM readings r JOIN plants p USING(plant) JOIN tariffs t ON r.plant=t.plant AND r.at>=t.start AND r.at<t.end WHERE r.quality='Đo thật' AND r.import_kwh IS NOT NULL")
    s.view("CREATE VIEW affected AS SELECT r.* FROM readings r WHERE EXISTS (SELECT 1 FROM outages o WHERE o.plant=r.plant AND o.status='Đã xác minh' AND r.at<o.end AND datetime(r.at,'+1 hour')>o.start)")
    for region in ["Miền Bắc","Miền Trung","Miền Nam"]:
        s.add("vi","net_energy",f"Với vùng {region}, tổng điện nhập ròng (nhập-xuất) của các dòng Đo thật và không thiếu điện nhập là bao nhiêu kWh?"+I,"SELECT sum(net_kwh) FROM valid_energy WHERE region=?",[region])
        s.add("vi","asof_tariff_cost",f"Tổng tiền VND của {region} theo net_kWh*giá hiệu lực đúng đầu khoảng là bao nhiêu? Chỉ Đo thật và không thiếu điện nhập; số âm được giữ nguyên."+I,"SELECT sum(net_cost) FROM valid_energy WHERE region=?",[region])
    s.add("vi","weighted_unit_price","Đơn giá bình quân gia quyền theo điện nhập ròng của các dòng hợp lệ có net_kwh>0 là bao nhiêu VND/kWh? Tính sum(net_cost)/sum(net_kwh)."+D,"SELECT sum(net_cost),sum(net_kwh) FROM valid_energy WHERE net_kwh>0",ratio=R2)
    s.add("vi","power_not_energy","Trong toàn bộ bảng Điện năng 1 giờ, công suất đỉnh kW lớn nhất là bao nhiêu? Không cộng điện năng để trả lời."+I,"SELECT max(peak_kw) FROM readings")
    s.add("vi","overlap_distinct","Có bao nhiêu khoảng đo 1 giờ giao với ít nhất một sự cố Đã xác minh? Hai khoảng [bắt đầu,kết thúc) giao nhau khi đầu này nhỏ hơn cuối kia; mỗi mã đo chỉ đếm một lần dù nhiều sự cố."+I,"SELECT count(*) FROM affected")
    s.add("vi","month_boundary","Tổng net_kwh hợp lệ trong tháng 02/2028 là bao nhiêu? Dùng thời điểm bắt đầu UTC, không tính các giờ tháng 01."+I,"SELECT sum(net_kwh) FROM valid_energy WHERE at>='2028-02-01 00:00:00'")
    s.add("vi","tail_lookup","Điện xuất kWh của mã ĐĐ-20000 là bao nhiêu?"+I,"SELECT export_kwh FROM readings WHERE id='ĐĐ-20000'")
    s.add("vi","missing_not_zero","Có bao nhiêu dòng thiếu Điện nhập kWh? Không tính các giá trị 0 là thiếu."+I,"SELECT count(*) FROM readings WHERE import_kwh IS NULL")
    s.add("vi","renewable_share","Trong các dòng hợp lệ, tỷ lệ điện Mặt trời trong tổng Mặt trời+Gió là bao nhiêu phần trăm?"+D,"SELECT sum(solar_kwh),sum(solar_kwh+wind_kwh) FROM valid_energy",ratio=P2)
    s.add("vi","plant_rank","Nhà máy nào có tổng net_cost hợp lệ lớn nhất?"+T,"SELECT plant FROM valid_energy GROUP BY plant ORDER BY sum(net_cost) DESC,plant LIMIT 1",formats=["text"])
    unknown(s,"mã số thuế của đơn vị sở hữu nhà máy NM-040")
    s.add("en","half_open_price","What tariff in VND/kWh applies to NM-040 at exactly 2028-01-20 10:00:00 UTC? Validity is start-inclusive, end-exclusive. Return an integer.","SELECT tariff FROM tariffs WHERE plant='NM-040' AND start<='2028-01-20 10:00:00' AND end>'2028-01-20 10:00:00'")
    s.add("en","estimated_exclusion","How many readings have quality Ước tính? Return an integer.","SELECT count(*) FROM readings WHERE quality='Ước tính'")
    s.add("en","carbon_conversion","For valid readings with positive net_kwh, what is total implied carbon in kgCO2? Use each plant's gCO2/kWh times net_kwh, divide by 1000; exactly 2 decimals.","SELECT sum(net_kwh*carbon),1000 FROM valid_energy WHERE net_kwh>0",ratio=R2)
    s.add("en","storage_balance","Across all valid readings, what is total battery discharge minus charge in kWh? Return an integer.","SELECT sum(discharge-charge) FROM valid_energy")
    s.add("en","tail_region","Which region contains the plant of reading ĐĐ-19999? Return the exact region label.","SELECT p.region FROM readings r JOIN plants p USING(plant) WHERE id='ĐĐ-19999'",formats=["text"])
    s.add("zh","east_region","東部区域的有效记录中，电网净输入总量是多少kWh？有效指Đo thật且输入值不缺失。只回答整数。","SELECT sum(net_kwh) FROM valid_energy WHERE region='東部'")
    s.add("zh","negative_flow","有效记录中，电网净输入严格小于0的记录有多少条？只回答整数。","SELECT count(*) FROM valid_energy WHERE net_kwh<0")
    s.add("zh","zero_distinction","全部记录中，电力输入恰好为0的记录有多少条？不把空白当作0。只回答整数。","SELECT count(*) FROM readings WHERE import_kwh=0")
    s.add("zh","peak_time","NM-040 的最大功率 peak_kw 首次出现于哪个UTC时刻？并列取最早时间。只回答 YYYY-MM-DD HH:MM:SS。","SELECT at FROM readings WHERE plant='NM-040' ORDER BY peak_kw DESC,at LIMIT 1",formats=["text"])
    s.add("fr","sum_tail","Quelle est la somme de net_kwh valide pour les identifiants ĐĐ-19001 à ĐĐ-20000 inclus ? Un entier uniquement.","SELECT sum(net_kwh) FROM valid_energy WHERE id BETWEEN 'ĐĐ-19001' AND 'ĐĐ-20000'")
    s.add("fr","distinct_outage","Combien de centrales distinctes ont au moins un incident Đã xác minh ? Un entier uniquement.","SELECT count(DISTINCT plant) FROM outages WHERE status='Đã xác minh'")
    s.add("fr","average_peak","Quelle est la moyenne simple des puissances peak_kw de NM-040, toutes qualités incluses ? Deux décimales uniquement.","SELECT sum(peak_kw),count(*) FROM readings WHERE plant='NM-040'",ratio=R2)
    s.add("ko","hour_count","NM-040의 전체 측정 구간 수를 정수로 답하십시오. 품질이나 결측으로 제외하지 않습니다.","SELECT count(*) FROM readings WHERE plant='NM-040'")
    s.add("ko","top_three_energy","유효 순전력량 합계가 높은 상위 3개 발전소 코드를 답하십시오. 내림차순, 동률은 코드 오름차순, 쉼표와 공백으로 구분합니다.","SELECT plant FROM valid_energy GROUP BY plant ORDER BY sum(net_kwh) DESC,plant LIMIT 3",formats=["text"])
    s.add("ko","elapsed_outage","검증된 모든 사고의 개별 지속 시간 합계를 분으로 답하십시오. 사고 간 겹침은 이 질문에서는 각각 더합니다.","SELECT sum((strftime('%s',end)-strftime('%s',start))/60) FROM outages WHERE status='Đã xác minh'")


def logistics(s):
    depots=[[f"K-{i:04d}",["Bắc","Trung","Nam","港口"][i%4],f"Kho {i:04d}"] for i in range(1,501)]
    s.table("depots","Danh mục kho",[("depot","Mã kho","TEXT"),("region","Vùng","TEXT"),("name","Tên kho","TEXT")],depots)
    shipments=[]; events=[]
    for i in range(1,8001):
        ident=f"VD-{i:06d}"; created=datetime(2028,2,20)+timedelta(hours=s.rng.randrange(1440))
        service="Nhanh" if i%3==0 else "Chuẩn"; due=created+timedelta(hours=48 if service=="Nhanh" else 72)
        outcome="Đã hủy" if i%19==0 else "Hoàn trả" if i%13==0 else "Đang giao" if i%11==0 else "Đã giao"
        final=created+timedelta(hours=s.rng.randint(13,120)); failed=i%7==0
        shipments.append([ident,f"K-{s.rng.randint(1,500):04d}",service,created,due,s.rng.randint(100,30000),s.rng.randint(100,9000)*1000])
        for step,(stamp,status) in enumerate([(created,"Đã tạo"),(created+timedelta(hours=3),"Đã nhận"),(created+timedelta(hours=10),"Giao thất bại" if failed else "Đang giao"),(final,outcome)],1):
            eid=f"E-{i:06d}-{step}"; old="Đang giao" if i%10==0 and step==4 else status
            events.append([eid,ident,stamp,old,1,stamp+timedelta(minutes=5),"Bản ghi gốc","UTC"])
            if i%10==0 and step==4:
                events.append([eid,ident,stamp,status,2,stamp+timedelta(days=1),"Hiệu chỉnh","UTC"])
    s.table("shipments","Vận đơn",[("shipment","Mã vận đơn","TEXT"),("depot","Mã kho","TEXT"),("service","Dịch vụ","TEXT"),("created","Tạo UTC","TEXT"),("due","Hẹn giao UTC","TEXT"),("grams","Khối lượng g","INTEGER"),("cod","Thu hộ VND","INTEGER")],shipments,widths={"A":25,"D":29,"E":29})
    s.rng.shuffle(events)
    s.table("events","Lịch sử sự kiện",[("event","Mã sự kiện","TEXT"),("shipment","Mã vận đơn","TEXT"),("at","Thời điểm UTC","TEXT"),("status","Trạng thái","TEXT"),("revision","Phiên bản","INTEGER"),("ingested","Ghi nhận UTC","TEXT"),("note","Ghi chú","TEXT"),("timezone","Múi giờ","TEXT")],events,widths={"A":26,"B":25,"C":29,"D":25,"F":29})
    s.sheets[-1]["previews"] += ["A16398:H16406"]
    s.view("CREATE VIEW canonical_events AS SELECT event,shipment,at,status,revision,ingested FROM (SELECT *,row_number() OVER(PARTITION BY event ORDER BY revision DESC,ingested DESC) rn FROM events) WHERE rn=1")
    s.view("CREATE VIEW final_events AS SELECT event,shipment,at,status FROM (SELECT *,row_number() OVER(PARTITION BY shipment ORDER BY at DESC,event DESC) rn FROM canonical_events) WHERE rn=1")
    s.view("CREATE VIEW delivery AS SELECT s.*,d.region,f.status,f.at AS final_at,(strftime('%s',f.at)-strftime('%s',s.created))/3600 AS elapsed_hours,CASE WHEN f.status='Đã giao' AND f.at<=s.due THEN 1 ELSE 0 END AS on_time FROM shipments s JOIN depots d USING(depot) JOIN final_events f USING(shipment)")
    for region in ["Bắc","Trung","Nam"]:
        s.add("vi","deduplicated_final_state",f"Vùng {region} có bao nhiêu vận đơn có trạng thái cuối là Đã giao? Với sự kiện trùng mã, giữ phiên bản lớn nhất rồi thời điểm ghi nhận mới nhất trước khi chọn sự kiện cuối."+I,"SELECT count(*) FROM delivery WHERE region=? AND status='Đã giao'",[region])
        s.add("vi","on_time_rate",f"Tại vùng {region}, tỷ lệ giao đúng hẹn trong các vận đơn có trạng thái cuối Đã giao là bao nhiêu phần trăm? Đúng hẹn gồm thời điểm giao bằng hẹn; khử trùng sự kiện theo phiên bản lớn nhất."+D,"SELECT sum(on_time),count(*) FROM delivery WHERE region=? AND status='Đã giao'",[region],ratio=P2)
    s.add("vi","version_correction","Trạng thái cuối của VD-008000 sau khi giữ phiên bản lớn nhất cho từng mã sự kiện là gì? Chỉ trả đúng nhãn trạng thái.","SELECT status FROM delivery WHERE shipment='VD-008000'",formats=["text"])
    s.add("vi","raw_vs_unique","Số dòng thừa do nhiều phiên bản cùng mã sự kiện là bao nhiêu? Tính số dòng lịch sử trừ số mã sự kiện khác nhau."+I,"SELECT count(*)-count(DISTINCT event) FROM events")
    s.add("vi","transit_mean","Trung bình thời gian từ Tạo UTC đến sự kiện giao cuối của các vận đơn Nhanh đã giao là bao nhiêu giờ? Dùng giờ thực trôi qua, không dùng ngày lịch."+D,"SELECT sum(elapsed_hours),count(*) FROM delivery WHERE service='Nhanh' AND status='Đã giao'",ratio=R2)
    s.add("vi","failed_first_attempt","Có bao nhiêu vận đơn đã giao thành công nhưng có sự kiện Giao thất bại trước đó, sau khử trùng phiên bản? Mỗi vận đơn chỉ đếm một lần."+I,"SELECT count(*) FROM delivery d WHERE status='Đã giao' AND EXISTS (SELECT 1 FROM canonical_events e WHERE e.shipment=d.shipment AND e.status='Giao thất bại' AND e.at<d.final_at)")
    s.add("vi","cod_sum","Tổng Thu hộ VND của các vận đơn có trạng thái cuối Hoàn trả là bao nhiêu? Không cộng nhiều lần theo lịch sử sự kiện."+I,"SELECT sum(cod) FROM delivery WHERE status='Hoàn trả'")
    s.add("vi","weight_conversion","Tổng khối lượng các vận đơn Đã giao đúng hẹn là bao nhiêu kg? Khối lượng g phải chia 1000."+D,"SELECT sum(grams),1000 FROM delivery WHERE on_time=1",ratio=R2)
    s.add("vi","late_rank","Vận đơn Đã giao nào trễ hẹn nhiều giờ nhất? So thời điểm cuối trừ hẹn UTC."+T,"SELECT shipment FROM delivery WHERE status='Đã giao' ORDER BY strftime('%s',final_at)-strftime('%s',due) DESC,shipment LIMIT 1",formats=["text"])
    s.add("vi","cross_month","Có bao nhiêu vận đơn được tạo trong tháng 02/2028 nhưng sự kiện cuối nằm trong tháng 03/2028? Dùng UTC và sự kiện đã khử trùng."+I,"SELECT count(*) FROM delivery WHERE created<'2028-03-01 00:00:00' AND final_at>='2028-03-01 00:00:00' AND final_at<'2028-04-01 00:00:00'")
    unknown(s,"số điện thoại người nhận của vận đơn VD-008000")
    s.add("en","latest_not_last_row","For event E-008000-4, what is the retained revision under largest revision then latest ingestion time? Return an integer, regardless of physical row order.","SELECT revision FROM canonical_events WHERE event='E-008000-4'")
    s.add("en","cancelled_state","How many shipments have final status Đã hủy after event deduplication? Return an integer.","SELECT count(*) FROM delivery WHERE status='Đã hủy'")
    s.add("en","p95_nearest_rank","Among delivered shipments, what is the 95th percentile of elapsed_hours using nearest-rank: sort ascending, select position ceil(0.95*N), 1-based? Return an integer.","WITH x AS (SELECT elapsed_hours,row_number() OVER(ORDER BY elapsed_hours,shipment) rn,count(*) OVER() n FROM delivery WHERE status='Đã giao') SELECT elapsed_hours FROM x WHERE rn=(95*n+99)/100")
    s.add("en","count_equal_deadline","How many delivered shipments arrived at exactly the promised UTC time? Count equality as on-time. Return an integer.","SELECT count(*) FROM delivery WHERE status='Đã giao' AND final_at=due")
    s.add("en","tail_pending","Among VD-007501 through VD-008000 inclusive, how many have final status Đang giao? Return an integer.","SELECT count(*) FROM delivery WHERE shipment BETWEEN 'VD-007501' AND 'VD-008000' AND status='Đang giao'")
    s.add("zh","port_scope","港口区域最终状态为Đã giao的运单有多少个？先对相同事件编号保留最高版本。只回答整数。","SELECT count(*) FROM delivery WHERE region='港口' AND status='Đã giao'")
    s.add("zh","return_percentage","在港口区域所有运单中，最终状态为Hoàn trả的运单占多少百分比？保留两位小数，不加%。","SELECT sum(status='Hoàn trả'),count(*) FROM delivery WHERE region='港口'",ratio=P2)
    s.add("zh","gram_tail","VD-008000 的重量是多少克？只回答整数。","SELECT grams FROM shipments WHERE shipment='VD-008000'")
    s.add("zh","service_scope","已成功交付的Nhanh运单中，迟于约定时间的有多少个？等于约定时间不算迟到。只回答整数。","SELECT count(*) FROM delivery WHERE service='Nhanh' AND status='Đã giao' AND final_at>due")
    s.add("fr","event_count","Après conservation de la plus grande version par code événement, combien d'événements uniques restent-ils ? Un entier uniquement.","SELECT count(*) FROM canonical_events")
    s.add("fr","mean_lateness","Parmi les livraisons Đã giao strictement en retard, quel est le retard moyen en heures ? Deux décimales uniquement.","SELECT sum((strftime('%s',final_at)-strftime('%s',due))/3600),count(*) FROM delivery WHERE status='Đã giao' AND final_at>due",ratio=R2)
    s.add("fr","depot_rank","Quel dépôt a le plus de livraisons finales Đã giao ? En cas d'égalité, code dépôt croissant. Répondez uniquement par le code.","SELECT depot FROM delivery WHERE status='Đã giao' GROUP BY depot ORDER BY count(*) DESC,depot LIMIT 1",formats=["text"])
    s.add("ko","tail_final_date","VD-008000의 최종 이벤트 UTC 시각을 YYYY-MM-DD HH:MM:SS 형식으로 답하십시오. 최고 버전으로 중복을 제거합니다.","SELECT final_at FROM delivery WHERE shipment='VD-008000'",formats=["text"])
    s.add("ko","top_late_list","지연된 배송 완료 운송장 중 지연 시간이 큰 상위 3개 코드를 답하십시오. 동률은 코드 오름차순, 쉼표와 공백으로 구분합니다.","SELECT shipment FROM delivery WHERE status='Đã giao' AND final_at>due ORDER BY strftime('%s',final_at)-strftime('%s',due) DESC,shipment LIMIT 3",formats=["text"])
    s.add("ko","distinct_created_date","전체 운송장의 생성 UTC 날짜는 몇 종류입니까? 시각 부분은 제외하고 정수로 답하십시오.","SELECT count(DISTINCT date(created)) FROM shipments")


def laboratory(s):
    sites=[[f"QT-{i:04d}",["Sông","Nước ngầm","Hồ","河口"][i%4],f"Điểm quan trắc {i:04d}"] for i in range(1,1501)]
    s.table("sites","Điểm quan trắc",[("site","Mã điểm","TEXT"),("matrix","Nền mẫu","TEXT"),("name","Tên điểm","TEXT")],sites,widths={"C":35})
    limits=[[a,m,l] for a,l in [("Chì",50),("Đồng",2000),("Nitrat",10000)] for m in ["Sông","Nước ngầm","Hồ","河口"]]
    s.table("limits","Ngưỡng nội bộ",[("analyte","Chất","TEXT"),("matrix","Nền mẫu","TEXT"),("limit_ug","Ngưỡng µg/L","INTEGER")],limits)
    records=[]
    for i in range(1,30001):
        sample=(i-1)//3+1; a=["Chì","Đồng","Nitrat"][(i-1)%3]; unit="mg/L" if i%2 else "µg/L"
        ug=s.rng.randint(0,150 if a=="Chì" else 5000 if a=="Đồng" else 20000)
        lod=10 if a=="Chì" else 100; qualifier="<" if i%17==0 else "="
        result=f"<{lod/1000:.3f}" if qualifier=="<" and unit=="mg/L" else f"<{lod}" if qualifier=="<" else ug/1000 if unit=="mg/L" else ug
        if i%251==0: result=None; qualifier="Thiếu"
        records.append([f"KQ-{i:05d}",f"M-{sample:05d}",f"QT-{(sample-1)%1500+1:04d}",date(2028,3,1)+timedelta(days=(sample-1)%180),a,unit,result,qualifier,
                        "Rejeté" if i%29==0 else "Valide",s.rng.randint(10,100)*10,f"L-{(i-1)//250+1:03d}",f"Máy-{i%12+1:02d}",
                        s.rng.randint(180,280)/10,s.rng.randint(30,80),s.rng.randint(10,90),s.rng.randint(1000,90000),s.rng.randint(0,30),
                        s.rng.randint(90,110)/100,s.rng.randint(10,200),"ICP" if a!="Nitrat" else "UV",lod,1+i%5,f"NV-{i%80+1:03d}",
                        "A" if i%3 else "B",s.rng.randint(990,1010)/10,s.rng.randint(0,500)/100,s.rng.randint(800,1200)/10])
    keys=[("id","Mã kết quả","TEXT"),("sample","Mã mẫu","TEXT"),("site","Mã điểm","TEXT"),("day","Ngày lấy mẫu","TEXT"),("analyte","Chất","TEXT"),("unit","Đơn vị","TEXT"),("result","Kết quả",""),("qualifier","Định lượng","TEXT"),("quality","Duyệt","TEXT"),("volume","Thể tích mL","INTEGER"),("batch","Lô","TEXT"),("instrument","Thiết bị","TEXT"),("temperature","Nhiệt độ °C","REAL"),("humidity","Độ ẩm %","INTEGER"),("runtime","Phút chạy","INTEGER"),("signal","Tín hiệu thô","INTEGER"),("blank","Mẫu trắng","INTEGER"),("calibration","Hệ số chuẩn","REAL"),("pressure","Áp suất kPa","INTEGER"),("method","Phương pháp","TEXT"),("lod_ug","LOD µg/L","INTEGER"),("dilution","Pha loãng","INTEGER"),("operator","Kỹ thuật viên","TEXT"),("channel","Kênh","TEXT"),("reference","Chuẩn thu hồi %","REAL"),("uncertainty","Độ không đảm bảo","REAL"),("recovery","Thu hồi %","REAL")]
    s.table("results","Résultats dài",keys,records,widths={"A":24,"B":24,"C":24,"D":25,"I":24,"W":25,"Y":28,"Z":28,"AA":24},repeats=1000)
    s.sheets[-1]["previews"] += ["V1:AA10","A1000:I1008","V30024:AA30030"]
    s.view("CREATE VIEW quantified AS SELECT r.*,s.matrix,l.limit_ug,CASE WHEN r.unit='mg/L' THEN cast(round(cast(r.result AS REAL)*1000) AS INTEGER) ELSE cast(r.result AS INTEGER) END AS ug FROM results r JOIN sites s USING(site) JOIN limits l ON r.analyte=l.analyte AND s.matrix=l.matrix WHERE r.quality='Valide' AND r.qualifier='=' AND r.result IS NOT NULL")
    for analyte in ["Chì","Đồng","Nitrat"]:
        s.add("vi","unit_harmonized_mean",f"Nồng độ trung bình cộng của {analyte}, chỉ kết quả Valide và định lượng '=', là bao nhiêu µg/L? Đổi mg/L sang µg/L nhân 1000, bỏ '<' và ô thiếu."+D,"SELECT sum(ug),count(*) FROM quantified WHERE analyte=?",[analyte],ratio=R2)
        s.add("vi","limit_exceedance",f"Có bao nhiêu kết quả {analyte} Valide, định lượng '=', vượt nghiêm ngặt Ngưỡng nội bộ theo đúng nền mẫu? Không coi bằng ngưỡng là vượt; không tính kết quả '<'."+I,"SELECT count(*) FROM quantified WHERE analyte=? AND ug>limit_ug",[analyte])
    s.add("vi","volume_weighted","Nồng độ Chì trung bình gia quyền theo Thể tích mL trong các kết quả định lượng hợp lệ là bao nhiêu µg/L? Tính sum(ug*volume)/sum(volume)."+D,"SELECT sum(ug*volume),sum(volume) FROM quantified WHERE analyte='Chì'",ratio=R2)
    s.add("vi","censored_not_zero","Có bao nhiêu kết quả được ghi dưới giới hạn phát hiện bằng dấu '<', bất kể trạng thái duyệt? Không coi '<' là số 0."+I,"SELECT count(*) FROM results WHERE qualifier='<'")
    s.add("vi","missing_vs_censored","Có bao nhiêu dòng thật sự thiếu Kết quả? Không tính các chuỗi bắt đầu '<' là ô thiếu."+I,"SELECT count(*) FROM results WHERE result IS NULL")
    s.add("vi","wide_tail_lookup","Giá trị Thu hồi % ở cột AA của KQ-30000 là bao nhiêu?"+D,"SELECT recovery FROM results WHERE id='KQ-30000'",formats=[2])
    s.add("vi","nearest_rank_p95","Phân vị 95% nồng độ Đồng (µg/L) trong các kết quả định lượng hợp lệ là bao nhiêu? Dùng nearest-rank: vị trí ceil(0.95*N) sau khi sắp tăng dần, 1-based; không nội suy."+I,"WITH x AS (SELECT ug,row_number() OVER(ORDER BY ug,id) rn,count(*) OVER() n FROM quantified WHERE analyte='Đồng') SELECT ug FROM x WHERE rn=(95*n+99)/100")
    s.add("vi","median_even","Trung vị nồng độ Nitrat (µg/L) trong kết quả định lượng hợp lệ là bao nhiêu? Nếu N chẵn, lấy trung bình hai phần tử giữa."+D,"WITH x AS (SELECT ug,row_number() OVER(ORDER BY ug,id) rn,count(*) OVER() n FROM quantified WHERE analyte='Nitrat') SELECT avg(ug) FROM x WHERE rn IN ((n+1)/2,(n+2)/2)",formats=[2])
    s.add("vi","distinct_sample","Có bao nhiêu mã mẫu khác nhau có ít nhất một kết quả định lượng hợp lệ vượt Ngưỡng nội bộ? Mỗi mẫu chỉ đếm một lần dù nhiều chất vượt."+I,"SELECT count(DISTINCT sample) FROM quantified WHERE ug>limit_ug")
    s.add("vi","repeat_header_exclusion","Bảng Résultats dài có bao nhiêu bản ghi kết quả thật? Không tính tiêu đề đầu hoặc các dòng tiêu đề lặp giữa bảng."+I,"SELECT count(*) FROM results")
    unknown(s,"tọa độ GPS của điểm quan trắc QT-1500")
    s.add("en","matrix_top_site","Among valid quantified Chì results in matrix Sông, which site has the highest mean concentration in µg/L? Break ties by site code ascending. Return only the site code.","SELECT site FROM quantified WHERE analyte='Chì' AND matrix='Sông' GROUP BY site ORDER BY avg(ug) DESC,site LIMIT 1",formats=["text"])
    s.add("en","zero_is_quantified","How many valid quantified results have concentration exactly zero after unit conversion? Exclude censored and missing results. Return an integer.","SELECT count(*) FROM quantified WHERE ug=0")
    s.add("en","tail_quantified_sum","What is the sum of quantified valid concentrations in µg/L for KQ-29001 through KQ-30000 inclusive? This is a requested diagnostic sum, not a concentration of a pooled sample. Return an integer.","SELECT sum(ug) FROM quantified WHERE id BETWEEN 'KQ-29001' AND 'KQ-30000'")
    s.add("en","sample_all_analytes","How many sample IDs have all three analytes valid, quantified and strictly below their respective internal limits? Samples missing any eligible analyte do not qualify. Return an integer.","SELECT count(*) FROM (SELECT sample FROM quantified GROUP BY sample HAVING count(*)=3 AND sum(ug<limit_ug)=3)")
    s.add("en","unit_diagnostic","What percent of all real result records use mg/L, including censored and rejected records? Ignore repeated header rows. Return exactly 2 decimals without %.","SELECT sum(unit='mg/L'),count(*) FROM results",ratio=P2)
    s.add("zh","estuary_scope","河口基质中，有多少个已批准且定量的结果严格超过内部阈值？先统一为µg/L，不包括小于检出限及缺失值。只回答整数。","SELECT count(*) FROM quantified WHERE matrix='河口' AND ug>limit_ug")
    s.add("zh","recovery_tail","KQ-29999 在AA列的回收率是多少？保留两位小数，不加%。","SELECT recovery FROM results WHERE id='KQ-29999'",formats=[2])
    s.add("zh","rejected_count","真实结果记录中，Duyệt 为 Rejeté 的有多少条？不要计入重复表头。只回答整数。","SELECT count(*) FROM results WHERE quality='Rejeté'")
    s.add("zh","max_id","已批准且定量的Chì结果中，哪个结果编号的µg/L浓度最高？相同则编号升序，回答编号。","SELECT id FROM quantified WHERE analyte='Chì' ORDER BY ug DESC,id LIMIT 1",formats=["text"])
    s.add("fr","lake_mean","Quelle est la moyenne simple du Nitrat quantifié et Valide dans la matrice Hồ, en µg/L après conversion ? Deux décimales uniquement.","SELECT sum(ug),count(*) FROM quantified WHERE analyte='Nitrat' AND matrix='Hồ'",ratio=R2)
    s.add("fr","censor_ratio","Quel pourcentage des résultats Valide de Chì porte le qualificatif '<' ? Inclure les résultats manquants dans le dénominateur Valide. Deux décimales sans %.","SELECT sum(qualifier='<'),count(*) FROM results WHERE analyte='Chì' AND quality='Valide'",ratio=P2)
    s.add("fr","maximum_batch","Quel lot contient le plus de résultats quantifiés Valide dépassant leur seuil interne ? Égalité : code lot croissant. Répondez uniquement par le code.","SELECT batch FROM quantified WHERE ug>limit_ug GROUP BY batch ORDER BY count(*) DESC,batch LIMIT 1",formats=["text"])
    s.add("ko","lower_bound_exclusion","유효 정량 Đồng 결과 중 내부 기준과 정확히 같은 농도의 수를 정수로 답하십시오. '<' 결과는 제외합니다.","SELECT count(*) FROM quantified WHERE analyte='Đồng' AND ug=limit_ug")
    s.add("ko","middle_lookup","KQ-15000의 Thiết bị 값을 표에 나온 그대로 답하십시오.","SELECT instrument FROM results WHERE id='KQ-15000'",formats=["text"])
    s.add("ko","top_three_sites","유효 정량 결과의 기준 초과 건수가 많은 상위 3개 지점 코드를 답하십시오. 동률은 코드 오름차순, 쉼표와 공백으로 구분합니다.","SELECT site FROM quantified WHERE ug>limit_ug GROUP BY site ORDER BY count(*) DESC,site LIMIT 3",formats=["text"])


DEFINITIONS=[
    ("23_civic_service_long",civic,12000,"Khảo sát dịch vụ đô thị: header 3 cấp, Total đổi vị trí, mean across all và mean loại Total, tỷ lệ có trọng số, lưu trữ gây nhiễu."),
    ("24_procurement_temporal_long",procurement,16000,"Mua sắm 16000 dòng: tỷ giá đúng ngày, hợp đồng hiệu lực [từ,đến), nhiều dòng một hóa đơn, ghi có, hoàn tiền, tập trung nhà cung cấp."),
    ("25_energy_intervals_long",energy,20000,"20000 khoảng điện 1 giờ: kWh khác kW, giá hiệu lực, giao khoảng nửa mở, sự cố chồng nhau, CO2, pin và dữ liệu ước tính/thiếu."),
    ("26_logistics_event_versions",logistics,32800,"32800 dòng lịch sử cho 8000 vận đơn: sửa phiên bản, thứ tự vật lý xáo trộn, trạng thái cuối, giao đúng hẹn, phân vị thời gian và ngày UTC."),
    ("27_lab_units_censoring_long",laboratory,30000,"30000 phép kiểm nghiệm, 27 cột tới AA: đổi mg/L–µg/L, kiểm duyệt '<', ô thiếu, tiêu đề lặp, trung vị, phân vị, điều kiện đủ cả ba chất."),
]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--test-root",type=Path,default=ROOT/"Test")
    p.add_argument("--spec-root",type=Path,default=ROOT/"outputs/long-multilingual/specs")
    p.add_argument("--seed",type=int,default=261017)
    args=p.parse_args(); summary=[]
    for name,fn,count,description in DEFINITIONS:
        s=LongSuite(name,description,count,args.seed); fn(s)
        summary.append(s.save(args.test_root,args.spec_root))
        print(f"Prepared {name}: 30 questions, {count} main records",flush=True)
        del s
    args.test_root.mkdir(parents=True,exist_ok=True)
    (args.test_root/"long_multilingual_manifest.json").write_text(json.dumps({
        "seed":args.seed,"suite_count":5,"questions":150,"language_counts":{"vi":75,"en":25,"zh":20,"fr":15,"ko":15},
        "ag_instruction_sha256":hashlib.sha256((ROOT/"AGENTS.md").read_bytes()).hexdigest(),"suites":summary,
        "reference_notes":"New fictional domains; I/O and mean semantics follow AGENTS.md. Audit SQL is evaluation-only."},ensure_ascii=False,indent=2),encoding="utf-8")


if __name__=="__main__": main()
