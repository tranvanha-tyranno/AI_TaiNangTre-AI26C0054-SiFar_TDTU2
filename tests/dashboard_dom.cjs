// DOM regression checks against the local dashboard API. No browser control,
// and no LLM calls: POST /api/run is intercepted and inspected in memory.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const {JSDOM}=require(require.resolve('jsdom',{paths:[path.join(root,'outputs/dashboard-ui-test')]}));
const base=process.env.DASHBOARD_TEST_URL||'http://127.0.0.1:8504';
const baseline='20261014-170251-4f423d';
const improved='20261014-171811-d116aa';
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
  w.eval(fs.readFileSync(path.join(root,'dashboard/dist/app.js'),'utf8'));
  await until(()=>$('connection').textContent.includes('Đã kết nối'),'initial render');
  console.log('Initial render OK');
  assert.match($('matched').textContent,/26.*30/);
  assert.equal(w.document.querySelectorAll('#answerRows tr').length,20);
  assert.equal(w.document.querySelectorAll('#outcomeChart button').length,2);
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
  assert.ok($('downloadReport').href.includes('/api/report?'));
  assert.equal(errors.length,0,errors.join(', '));
  console.log('DOM checks passed: charts, filtering, pagination, multi-question rerun, details, evidence navigation, AI2501, comparisons. No LLM requests.');
}
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>w.close());
