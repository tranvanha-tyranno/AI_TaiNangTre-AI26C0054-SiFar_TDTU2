"""Generate independent, reproducible workbook shapes for a first model pass.

This is a regression probe for known failure classes, not a hidden-set score.
The solver receives only xlsx_files/ and queries.json, never the reference CSV.
"""
import argparse
import csv
import json
import random
from pathlib import Path
from openpyxl import Workbook


def generate(root, seed):
    root=Path(root); folder=root/'xlsx_files';folder.mkdir(parents=True,exist_ok=True)
    rng=random.Random(seed); queries=[]; answers=[]
    def save(name, rows, question, answer):
        wb=Workbook(); ws=wb.active;ws.title='Observations'
        for row in rows: ws.append(row)
        wb.save(folder/name);wb.close()
        ident=len(queries)+1
        queries.append({'id':ident,'file_name':name,'query':question})
        answers.append((ident,str(answer)))
    a=rng.randrange(4000,9000);b=rng.randrange(100,900)
    save('cash.xlsx',[['Product','Revenue'],['Orchid',f'${a:,}'],['Cedar',f'(${b:,})']],
         'What is the combined revenue of Orchid and Cedar? Answer with only the integer, without commas or units.',a-b)
    high=rng.randrange(800,1200);drop=rng.randrange(100,300)
    save('annual.xlsx',[['Year','Workers'],[2032,high-drop],[2030,high-50],[2031,high]],
         'In which year did Workers fall the most compared with the previous year? Answer as `year, decrease`, with both values as integers.',f'2032, {drop}')
    low=rng.randrange(5,15)/10;high=low+2
    save('sections.xlsx',[['Activity','Average hours'],['North laboratory'],['  Calibration',low],
                          ['  Inspection',4],['South laboratory'],['  Calibration',high],['  Inspection',3]],
         'Across North laboratory and South laboratory, which laboratory has the highest average hours for Calibration? Answer with only the laboratory name exactly as it appears in the table.','South laboratory')
    save('pair.xlsx',[['Group','Score'],['Maple',29],['Aspen',46]],
         'Which group has the highest Score, and by how much does it exceed the other group? Answer as `group, difference`, with the difference using exactly one decimal place.','Aspen, 17.0')
    save('codes.xlsx',[['Industry','Code','Rate'],['A','001234',6],['B','123456',7],['C','1234567',9],
                       ['D','12345',8],['E','654321',5],['F','234567','..']],
         'How many industries have a 6-digit Code and a Rate strictly above 5.0? Answer with only the integer.',2)
    save('decline.xlsx',[['Year','Total cases'],['2030/2031','8,700'],['2031/2032','6,090']],
         '2030/2031년 대비 2031/2032년에 총 사건(total cases) 수는 몇 퍼센트 감소했습니까? 소수점 둘째 자리까지, % 기호 없이 숫자만 답하십시오.','30.00')
    (root/'queries.json').write_text(json.dumps(queries,ensure_ascii=False,indent=2),encoding='utf-8')
    with (root/'expected_submission.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['id','answer']);writer.writerows(answers)
    (root/'probe_metadata.json').write_text(json.dumps({'seed':seed,'kind':'synthetic_regression_probe','questions':len(queries)}),encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',required=True,type=Path);ap.add_argument('--seed',type=int,default=7319)
    args=ap.parse_args();generate(args.output,args.seed)
