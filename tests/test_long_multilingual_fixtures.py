"""No LLM: saved-XLSX SQL replay plus independent Python business controls."""
from collections import Counter, defaultdict
import csv
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import unittest

from scripts.long_benchmark_core import rebuild_database, present, number_text, LongSuite

ROOT=Path(__file__).resolve().parents[1]


class LongMultilingualFixturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loaded={}
        root=json.loads((ROOT/"Test/long_multilingual_manifest.json").read_text(encoding="utf-8"))
        for entry in root["suites"]:
            folder=ROOT/"Test"/entry["name"]
            cls.loaded[int(entry["name"][:2])]=(folder,*rebuild_database(folder))

    @classmethod
    def tearDownClass(cls):
        for _,db,_,_ in cls.loaded.values(): db.close()

    def records(self,index,table):
        db=self.loaded[index][1]
        names=[r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
        return [dict(zip(names,row)) for row in db.execute(f'SELECT * FROM "{table}"')]

    def expect(self,index,question,value,digits=None):
        checks=self.loaded[index][3]["checks"]
        expected=next(c["answer"] for c in checks if c["id"]==index*1000+question)
        actual=value if isinstance(value,str) else number_text(value,digits)
        self.assertEqual(actual,expected,f"{index*1000+question}: independent Python")

    def test_150_answers_recomputed_from_saved_xlsx_and_io_contract(self):
        ids=set()
        for index,(folder,db,manifest,audit) in self.loaded.items():
            with self.subTest(suite=folder.name):
                queries=json.loads((folder/"queries.json").read_text(encoding="utf-8"))
                self.assertEqual(len(queries),30)
                self.assertTrue(all(type(q["id"]) is int and q["id"]>0 for q in queries))
                qids=[q["id"] for q in queries]
                self.assertNotEqual(qids,sorted(qids))
                self.assertEqual(len({q["query"] for q in queries}),30)
                self.assertEqual(len(set(qids)-ids),30); ids.update(qids)
                self.assertEqual(Counter(c["language"] for c in audit["checks"]),{"vi":15,"en":5,"zh":4,"fr":3,"ko":3})
                with (folder/"expected_submission.csv").open(encoding="utf-8",newline="") as f:
                    reader=csv.DictReader(f); self.assertEqual(reader.fieldnames,["id","answer"]); gold=list(reader)
                self.assertEqual([int(r["id"]) for r in gold],sorted(qids))
                self.assertEqual(sum(r["answer"]=="" for r in gold),1)
                for check,row in zip(audit["checks"],gold):
                    actual=present(db.execute(check["sql"],check["params"]).fetchall(),check["presentation"])
                    self.assertEqual(actual,check["answer"],check["id"])
                    self.assertEqual(actual,row["answer"],check["id"])
                for table in manifest["tables"]:
                    count=db.execute(f'SELECT count(*) FROM "{table["table"]}"').fetchone()[0]
                    self.assertEqual(count,table["record_count"])
                with (folder/"sample_submission.csv").open(encoding="utf-8",newline="") as f:
                    sample=list(csv.DictReader(f))
                self.assertEqual([r["id"] for r in sample],[r["id"] for r in gold])
                self.assertTrue(all(r["answer"]=="" for r in sample))
        self.assertEqual(len(ids),150)

    def test_civic_total_semantics_and_independent_controls(self):
        records=self.records(23,"civic"); by={r["id"]:r for r in records}
        counts={r["id"]:r for r in self.records(23,"counts")}
        allcols=["water_total","basic","advanced","special","residential","commercial","public","waste_total"]
        leaves=allcols[1:-1]
        D=lambda x:Decimal(str(x))
        for j,ident in enumerate(["DV-00001","DV-11999"]):
            r=by[ident]
            a=sum(D(r[c]) for c in allcols)/8; b=sum(D(r[c]) for c in leaves)/6
            self.expect(23,1+j*3,a,2); self.expect(23,2+j*3,b,2)
            self.assertNotEqual(number_text(a,2),number_text(b,2),"Fixture must distinguish including Total")
            self.expect(23,3+j*3,sum(counts[ident][c] for c in leaves))
        r=by["DV-11999"]; ns=counts[r["id"]]
        self.expect(23,7,sum(D(r[c])*ns[c] for c in leaves)/sum(ns[c] for c in leaves),2)
        self.expect(23,8,by["DV-12000"]["ward"])
        self.expect(23,9,sum(r["metric"]=="Hài lòng" and r["city"]=="Huế" and r["status"]=="Đã xác nhận" and r["basic"]>=80 for r in records))
        sub=[r for r in records if r["period"]=="2028-12" and r["metric"]=="Hài lòng"]
        self.expect(23,10,sorted(sub,key=lambda r:(-sum(D(r[c]) for c in allcols),r["ward"]))[0]["ward"])
        self.expect(23,11,sum(r["respondents"] for r in records if r["metric"]=="Đúng hạn" and r["city"]=="Cần Thơ" and r["period"]>="2028-10"))
        self.expect(23,12,100*D(sum(r["status"]=="Tạm tính" for r in records))/len(records),2)
        pair={r["metric"]:r for r in records if r["ward"]=="P0499" and r["period"]=="2028-12"}
        self.expect(23,13,sum(D(pair["Hài lòng"][c])-D(pair["Đúng hạn"][c]) for c in allcols)/8,2)
        old=self.records(23,"archive"); self.expect(23,14,next(r["score"] for r in old if r["id"]=="OLD-02400"))
        self.assertEqual(len(records),12000)
        for r in records:
            n=counts[r["id"]]
            self.assertEqual(n["water_total"],sum(n[c] for c in leaves[:3]))
            self.assertEqual(n["waste_total"],sum(n[c] for c in leaves[3:]))
            self.assertEqual(r["respondents"],sum(n[c] for c in leaves))

    def test_procurement_independent_temporal_and_money_controls(self):
        lines=self.records(24,"lines"); vendors={r["vendor"]:r for r in self.records(24,"vendors")}
        fx={(r["day"],r["currency"]):r["rate"] for r in self.records(24,"fx")}
        contracts=defaultdict(list)
        for r in self.records(24,"contracts"): contracts[r["vendor"]].append(r)
        eligible=[]; every={}
        for raw in lines:
            matches=[c for c in contracts[raw["vendor"]] if c["start"]<=raw["day"]<c["end"]]
            self.assertEqual(len(matches),1)
            r={**raw,**vendors[raw["vendor"]],"contract_info":matches[0],"rate":fx[raw["day"],raw["currency"]]}
            r["net"]=r["amount"]*r["rate"]*(100-r["discount"])*r["sign"]//100
            every[r["id"]]=r
            if r["status"]=="Đã duyệt": eligible.append(r)
        for j,region in enumerate(["Bắc","Trung","Nam"]):
            sub=[r for r in eligible if r["region"]==region]
            self.expect(24,1+j*2,sum(r["net"] for r in sub)); self.expect(24,2+j*2,len({r["invoice"] for r in sub}))
        self.expect(24,7,every["CT-15999"]["contract_info"]["contract"])
        self.expect(24,8,every["CT-16000"]["rate"])
        self.expect(24,9,Decimal(sum(r["net"]*r["contract_info"]["rebate"] for r in eligible if r["sign"]==1 and r["day"]>="2028-10-01"))/100,2)
        totals=defaultdict(int)
        for r in eligible: totals[r["vendor"]]+=r["net"]
        self.expect(24,10,sorted(totals,key=lambda x:(-totals[x],x))[0])
        self.expect(24,11,sum(r["net"]*(1 if r["day"]>="2028-10-01" else -1) for r in eligible if r["day"]>="2028-07-01"))
        self.expect(24,12,sum(r["currency"]=="EUR" and r["day"]=="2028-02-29" for r in eligible))
        usd=[r for r in eligible if r["currency"]=="USD" and r["sign"]==1]
        self.expect(24,13,Decimal(sum(r["amount"]*r["discount"] for r in usd))/sum(r["amount"] for r in usd),2)
        self.expect(24,14,every["CT-16000"]["name"])
        self.expect(24,19,"NCC-0001-Q2")

    def test_energy_independent_interval_and_unit_controls(self):
        rows=self.records(25,"readings"); plants={r["plant"]:r for r in self.records(25,"plants")}
        tariffs=defaultdict(list); outages=defaultdict(list)
        for r in self.records(25,"tariffs"): tariffs[r["plant"]].append(r)
        for r in self.records(25,"outages"):
            if r["status"]=="Đã xác minh": outages[r["plant"]].append(r)
        eligible=[]; affected=0
        for r in rows:
            start=datetime.fromisoformat(r["at"])
            from datetime import timedelta
            end=start+timedelta(hours=1)
            if any(start<datetime.fromisoformat(o["end"]) and end>datetime.fromisoformat(o["start"]) for o in outages[r["plant"]]): affected+=1
            if r["quality"]!="Đo thật" or r["import_kwh"] is None: continue
            matched=[t for t in tariffs[r["plant"]] if t["start"]<=r["at"]<t["end"]]
            self.assertEqual(len(matched),1)
            eligible.append({**r,**plants[r["plant"]],"net":r["import_kwh"]-r["export_kwh"],"price":matched[0]["tariff"]})
        for j,region in enumerate(["Miền Bắc","Miền Trung","Miền Nam"]):
            sub=[r for r in eligible if r["region"]==region]
            self.expect(25,1+2*j,sum(r["net"] for r in sub)); self.expect(25,2+2*j,sum(r["net"]*r["price"] for r in sub))
        pos=[r for r in eligible if r["net"]>0]
        self.expect(25,7,Decimal(sum(r["net"]*r["price"] for r in pos))/sum(r["net"] for r in pos),2)
        self.expect(25,8,max(r["peak_kw"] for r in rows)); self.expect(25,9,affected)
        self.expect(25,10,sum(r["net"] for r in eligible if r["at"]>="2028-02-01 00:00:00"))
        self.expect(25,11,next(r["export_kwh"] for r in rows if r["id"]=="ĐĐ-20000"))
        self.expect(25,12,sum(r["import_kwh"] is None for r in rows))
        self.expect(25,13,100*Decimal(sum(r["solar_kwh"] for r in eligible))/sum(r["solar_kwh"]+r["wind_kwh"] for r in eligible),2)
        money=defaultdict(int)
        for r in eligible: money[r["plant"]]+=r["net"]*r["price"]
        self.expect(25,14,sorted(money,key=lambda p:(-money[p],p))[0])

    def test_logistics_independent_revision_and_state_controls(self):
        raw=self.records(26,"events"); retained={}
        for r in raw:
            previous=retained.get(r["event"])
            if previous is None or (r["revision"],r["ingested"])>(previous["revision"],previous["ingested"]): retained[r["event"]]=r
        latest={}; failures=set()
        for r in retained.values():
            previous=latest.get(r["shipment"])
            if previous is None or (r["at"],r["event"])>(previous["at"],previous["event"]): latest[r["shipment"]]=r
            if r["status"]=="Giao thất bại": failures.add(r["shipment"])
        depots={r["depot"]:r for r in self.records(26,"depots")}; records=[]
        for r in self.records(26,"shipments"):
            event=latest[r["shipment"]]
            records.append({**r,"region":depots[r["depot"]]["region"],"status":event["status"],"final":event["at"],
                            "hours":int((datetime.fromisoformat(event["at"])-datetime.fromisoformat(r["created"])).total_seconds()/3600)})
        for j,region in enumerate(["Bắc","Trung","Nam"]):
            sub=[r for r in records if r["region"]==region and r["status"]=="Đã giao"]
            self.expect(26,1+j*2,len(sub)); self.expect(26,2+j*2,100*Decimal(sum(r["final"]<=r["due"] for r in sub))/len(sub),2)
        self.expect(26,7,latest["VD-008000"]["status"]); self.expect(26,8,len(raw)-len(retained))
        fast=[r for r in records if r["service"]=="Nhanh" and r["status"]=="Đã giao"]
        self.expect(26,9,Decimal(sum(r["hours"] for r in fast))/len(fast),2)
        self.expect(26,10,sum(r["status"]=="Đã giao" and r["shipment"] in failures for r in records))
        self.expect(26,11,sum(r["cod"] for r in records if r["status"]=="Hoàn trả"))
        self.expect(26,12,Decimal(sum(r["grams"] for r in records if r["status"]=="Đã giao" and r["final"]<=r["due"]))/1000,2)
        late=sorted([r for r in records if r["status"]=="Đã giao"],key=lambda r:(-(datetime.fromisoformat(r["final"])-datetime.fromisoformat(r["due"])).total_seconds(),r["shipment"]))
        self.expect(26,13,late[0]["shipment"])
        self.expect(26,14,sum(r["created"]<'2028-03-01 00:00:00' and '2028-03-01 00:00:00'<=r["final"]<'2028-04-01 00:00:00' for r in records))
        delivered=sorted(r["hours"] for r in records if r["status"]=="Đã giao")
        self.expect(26,18,delivered[(95*len(delivered)+99)//100-1])
        self.assertEqual(len(retained),32000); self.assertEqual(len(raw),32800)

    def test_lab_independent_units_censoring_and_quantiles(self):
        rows=self.records(27,"results"); sites={r["site"]:r for r in self.records(27,"sites")}
        limits={(r["analyte"],r["matrix"]):r["limit_ug"] for r in self.records(27,"limits")}; eligible=[]
        for r in rows:
            if r["quality"]!="Valide" or r["qualifier"]!="=" or r["result"] is None: continue
            ug=Decimal(str(r["result"]))* (1000 if r["unit"]=="mg/L" else 1)
            self.assertEqual(ug,int(ug))
            matrix=sites[r["site"]]["matrix"]
            eligible.append({**r,"ug":int(ug),"limit":limits[r["analyte"],matrix],"matrix":matrix})
        for j,a in enumerate(["Chì","Đồng","Nitrat"]):
            sub=[r for r in eligible if r["analyte"]==a]
            self.expect(27,1+j*2,Decimal(sum(r["ug"] for r in sub))/len(sub),2)
            self.expect(27,2+j*2,sum(r["ug"]>r["limit"] for r in sub))
        lead=[r for r in eligible if r["analyte"]=="Chì"]
        self.expect(27,7,Decimal(sum(r["ug"]*r["volume"] for r in lead))/sum(r["volume"] for r in lead),2)
        self.expect(27,8,sum(r["qualifier"]=="<" for r in rows)); self.expect(27,9,sum(r["result"] is None for r in rows))
        self.expect(27,10,next(r["recovery"] for r in rows if r["id"]=="KQ-30000"),2)
        copper=sorted(r["ug"] for r in eligible if r["analyte"]=="Đồng")
        self.expect(27,11,copper[(95*len(copper)+99)//100-1])
        nitrate=sorted(r["ug"] for r in eligible if r["analyte"]=="Nitrat"); count=len(nitrate)
        self.expect(27,12,Decimal(nitrate[(count-1)//2]+nitrate[count//2])/2,2)
        self.expect(27,13,len({r["sample"] for r in eligible if r["ug"]>r["limit"]})); self.expect(27,14,len(rows))
        self.assertEqual(len(rows),30000)
        self.assertEqual(len(self.loaded[27][2]["tables"][-1]["skip_rows"]),29)


class LongSeedReproductionTest(unittest.TestCase):
    def test_seed_reproducibility_and_fresh_answers(self):
        from scripts.gen_long_multilingual_suites import DEFINITIONS
        for name,fn,count,description in DEFINITIONS:
            snapshots=[]; answers=[]
            for seed in [261017,261017,261099]:
                s=LongSuite(name,description,count,seed); fn(s)
                snapshots.append(hashlib.sha256(json.dumps(s.sheets,ensure_ascii=False).encode()).hexdigest())
                answers.append([c["answer"] for c in s.checks]); s.db.close(); del s
            with self.subTest(suite=name):
                self.assertEqual(snapshots[0],snapshots[1]); self.assertNotEqual(snapshots[0],snapshots[2])
                self.assertEqual(answers[0],answers[1]); self.assertGreater(sum(a!=b for a,b in zip(answers[0],answers[2])),8)


if __name__=="__main__": unittest.main()
