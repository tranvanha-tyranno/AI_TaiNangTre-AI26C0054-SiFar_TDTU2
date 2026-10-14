// DOM regression checks against the local dashboard API. No browser control,
// and no LLM calls: POST /api/run is intercepted and inspected in memory.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const {JSDOM}=require(require.resolve('jsdom',{paths:[path.join(root,'outputs/dashboard-ui-test')]}));
const base=process.env.DASHBOARD_TEST_URL||'http://127.0.0.1:8504';
// Self-contained fixtures make this test runnable on a fresh checkout.
const runsRoot=path.join(root,'outputs/runs');fs.mkdirSync(runsRoot,{recursive:true});
const resolvedRunsRoot=fs.realpathSync(runsRoot),resolvedWorkspace=fs.realpathSync(root);
assert.ok(resolvedRunsRoot.startsWith(resolvedWorkspace+path.sep));
const fixtureDirs=[];
function fixture(correct){
  const folder=fs.mkdtempSync(path.join(runsRoot,'20000101-000000-dom'));
  fixtureDirs.push(folder);
  const queries=JSON.parse(fs.readFileSync(path.join(root,'Test/06_people_filters/queries.json'),'utf8')).map(q=>({...q,dataset:'06_people_filters',original_id:q.id,source_file:q.file_name}));
  const expected=Object.fromEntries(JSON.parse(fs.readFileSync(path.join(root,'Test/06_people_filters/answer_checks.json'),'utf8')).map(c=>[c.id,c.answer]));
  const wrong={'06_q011':'62, 86, 98, 54, 66, 90, 46, 58','06_q019':Array.from({length:40},(_,i)=>'P'+String(i+1).padStart(3,'0')).join(', '),'06_q021':Array.from({length:40},(_,i)=>'P'+String(i+1).padStart(3,'0')).join(', '),'06_q023':'P001, P002, P003, P004'};
  const records=queries.map((q,i)=>({...q,answer:!correct&&wrong[q.id]?wrong[q.id]:expected[q.id],status:'ok',mode:'fixture',pipeline_version:'tools-v1',elapsed_seconds:1+i/10,
    evidence:['People!F3'],evidence_count:1,plans:[{attempt:1,plan:{steps:[{id:'r',op:'read',table:'t1'}],output:{step:'r',columns:['F']}}}],
    tool_trace:[{id:'r',op:'read',row_count:40,elapsed_seconds:.01},{id:'f',op:'filter',row_count:8,elapsed_seconds:.01}],
    usage:{api_calls:1,prompt_tokens:900,completion_tokens:100,total_tokens:1000,actual_cost_usd:.0001+i*.000001,estimated_cost_usd:.0001,cost_complete:true,tokens_complete:true,unknown_cost_calls:0,calls:[]}}));
  fs.writeFileSync(path.join(folder,'metadata.json'),JSON.stringify({dataset:'06_people_filters',mode:'fixture',label:'DOM QA '+(correct?'after':'before'),finished:true,catalog:queries,ids:queries.map(q=>q.id),reference:expected}));
  fs.writeFileSync(path.join(folder,'queries.json'),JSON.stringify(queries));
  fs.writeFileSync(path.join(folder,'questions.jsonl'),records.map(r=>JSON.stringify(r)).join('\n'));
  fs.writeFileSync(path.join(folder,'summary.json'),JSON.stringify({questions:30,mode:'fixture',pipeline_version:'tools-v1',elapsed_seconds:60}));
  return path.basename(folder);
}
const baseline=fixture(false),improved=fixture(true);
const dom=new JSDOM(fs.readFileSync(path.join(root,'dashboard/dist/index.html'),'utf8'),
  {url:base,runScripts:'outside-only',pretendToBeVisual:true});
const w=dom.window;
const errors=[];let posted=null;
w.addEventListener('error',event=>errors.push(event.error||event.message));
w.HTMLElement.prototype.scrollIntoView=function(){};
w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
w.HTMLDialogElement.prototype.close=function(){this.open=false;};
w.setInterval=()=>0;
w.localStorage.setItem('sifar.dataset','06_people_filters');
w.localStorage.setItem('sifar.run',baseline);
w.fetch=async(url,options)=>{
  if(url==='/api/run'){
    posted=JSON.parse(options.body);
    assert.equal(posted.mode,'offline');
    return {ok:true,json:async()=>({run_id:baseline})};
  }
  return fetch(new URL(url,base),options);
};
const $=id=>w.document.getElementById(id);
function change(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event('change',{bubbles:true}));}
async function until(predicate,label){
  const deadline=Date.now()+15000;
  while(!predicate()){
    if(Date.now()>deadline)throw new Error('Timed out: '+label+'; errors: '+errors.join(', '));
    await new Promise(resolve=>setTimeout(resolve,25));
  }
}
async function main(){
  console.log('Starting DOM checks');
  w.eval(fs.readFileSync(path.join(root,'dashboard/dist/chart-math.js'),'utf8'));
  w.eval(fs.readFileSync(path.join(root,'dashboard/dist/app.js'),'utf8'));
  await until(()=>$('connection').textContent.includes('Đã kết nối'),'initial render');
  console.log('Initial render OK');
  assert.match($('matched').textContent,/26.*30/);
  assert.equal(w.document.querySelectorAll('#answerRows tr').length,20);
  assert.equal(w.document.querySelectorAll('#outcomeChart button').length,2);
  assert.equal(w.document.querySelectorAll('#questionMap .map-cell').length,30);
  assert.equal(w.document.querySelectorAll('#resultDonut .donut-slice').length,2);
  assert.equal(w.document.querySelectorAll('#scatterPlot .scatter-point').length,30);
  assert.equal(w.document.querySelectorAll('#latencyHistogram .histogram-bin').length,6);
  change('mapMetric','cost');
  assert.equal(w.document.querySelectorAll('#questionMap [class*="map-tone-"]').length,30);
  change('mapMetric','status');
  const math=w.SifarCharts;
  const initialState=await fetch(base+'/api/state?run='+baseline).then(r=>r.json());
  const nonemptyBin=math.distribution(initialState.rows).bins.findIndex(b=>b.ids.length>0);
  w.document.querySelector(`#latencyHistogram [data-bin="${nonemptyBin}"]`).dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
  assert.equal(Number($('rowCount').textContent),math.distribution(initialState.rows).bins[nonemptyBin].ids.length);
  assert.equal($('visualFilter').classList.contains('hidden'),false);
  $('clearVisualFilter').click();
  w.document.querySelector('#questionMap [data-question="06_q011"]').click();
  assert.equal($('detailDialog').open,true);
  assert.ok($('toolDetails').querySelector('.tool-flow'));
  $('closeDetail').click();
  change('scatterMetric','tokens');
  assert.equal(w.document.querySelectorAll('#scatterPlot .scatter-point').length,30);
  change('filter','mismatch');
  assert.equal(w.document.querySelectorAll('#answerRows tr').length,4);
  $('selectVisible').click();assert.match($('selectionCount').textContent,/4 câu/);
  $('rerunFailed').click();
  await until(()=>$('runDialog').open&&$('dialogSelection').querySelectorAll('input:checked').length===4,'failed selection');
  assert.match($('runEstimate').textContent,/4 câu/);
  change('mode','offline');
  $('runForm').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
  await until(()=>posted&&!$('runDialog').open,'mock offline submit');
  assert.deepEqual(posted.ids.sort(),['06_q011','06_q019','06_q021','06_q023']);
  assert.equal(posted.dataset,'06_people_filters');
  console.log('Selection and mocked offline submit OK');
  await until(()=>$('connection').textContent.includes('Đã kết nối'),'submit refresh');
  change('filter','all');$('nextPage').click();
  assert.equal(w.document.querySelectorAll('#answerRows tr').length,10);
  change('filter','mismatch');
  w.document.querySelector('#answerRows tr[data-id="06_q019"]').click();
  assert.equal($('detailDialog').open,true);
  assert.equal($('detailAnswer').textContent.split(', ').length,40);
  assert.ok($('toolDetails').textContent.includes('Yêu cầu đáp án')||$('toolDetails').textContent.includes('Luồng công cụ'));
  const evidence=w.document.querySelector('#toolDetails [data-cell]');
  assert.ok(evidence);const address=evidence.dataset.cell.split('!').at(-1);
  evidence.click();
  await until(()=>w.document.querySelector('.cell-highlight')?.dataset.coordinate===address,'evidence jump');
  console.log('Evidence navigation OK');
  w.document.querySelector('.nav[data-view="history"]').click();
  assert.equal(w.document.querySelectorAll('#historyTrend .history-point').length,2);
  assert.ok($('historyTrend').querySelector('.history-line').getAttribute('d').includes('L'));
  change('historyMetric','cost');
  assert.equal(w.document.querySelectorAll('#historyTrend .history-point').length,2);
  $('datasetButton').click();
  w.document.querySelector('#datasetMenu input[value="12_large_full_scan"]').click();
  await until(()=>w.document.querySelector('#datasetChips [data-remove="12_large_full_scan"]'),'add large dataset');
  w.document.querySelector('#datasetChips [data-remove="06_people_filters"]').click();
  await until(()=>$('datasetButton').textContent.includes('12_large_full_scan')&&!w.document.querySelector('#datasetChips [data-remove="06_people_filters"]'),'large dataset only');
  w.document.querySelector('.nav[data-view="data"]').click();
  await until(()=>$('sheetInfo').textContent.includes('Big'),'load large workbook');
  $('cellJump').value='AI2501';$('cellJumpForm').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
  await until(()=>w.document.querySelector('.cell-highlight')?.dataset.coordinate==='AI2501','wide tail jump');
  assert.equal(w.document.querySelector('.cell-highlight').textContent,'32507');
  assert.match($('workbookWindow').textContent,/2401.*2501/);
  w.document.querySelector('.nav[data-view="history"]').click();
  change('compareBefore',baseline);change('compareAfter',improved);$('compareButton').click();
  await until(()=>$('comparisonResult').querySelector('.compare-stats'),'comparison');
  const stats=$('comparisonResult').querySelectorAll('.compare-stat strong');
  assert.equal(stats[0].textContent,'4');assert.equal(stats[1].textContent,'0');
  assert.equal($('comparisonResult').querySelectorAll('.compare-result-row').length,4);
  assert.equal($('comparisonResult').querySelectorAll('.comparison-map .map-cell').length,30);
  assert.equal($('comparisonResult').querySelectorAll('.change-improved').length,4);
  assert.ok($('downloadReport').href.includes('/api/report?'));
  assert.equal(errors.length,0,errors.join(', '));
  console.log('DOM checks passed: donut, question map, scatter, histogram filtering, tool flow, pagination, rerun, evidence navigation, AI2501, comparisons. No LLM requests.');
}
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>{
  w.close();
  for(const folder of fixtureDirs){
    const resolved=fs.realpathSync(folder);
    assert.equal(path.dirname(resolved),resolvedRunsRoot);
    assert.match(path.basename(resolved),/^20000101-000000-dom[a-zA-Z0-9]+$/);
    fs.rmSync(resolved,{recursive:true,force:true});
  }
});
