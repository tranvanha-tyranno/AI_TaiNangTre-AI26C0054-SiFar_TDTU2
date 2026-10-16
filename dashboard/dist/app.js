'use strict';
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const escapeHTML=esc;
const duration=value=>Number(value||0)>=60?`${Math.floor(value/60)}m ${Math.floor(value%60)}s`:`${Number(value||0).toFixed(1)}s`;
const number=value=>Number(value||0).toLocaleString('vi-VN');
const outcomes={match:['Khớp','green'],mismatch:['Đáp án khác','red'],api_error:['Lỗi API','amber'],error:['Lỗi xử lý','red'],unanswered:['Chưa trả lời','amber'],pending:['Đang chờ','gray'],uncompared:['Chưa đối chiếu','gray']};
const ops={read:'Đọc vùng',cell:'Lấy ô',sum_columns:'Cộng ngang',concat:'Nối vùng',collect:'Gom đáp án',unpivot:'Chuyển cột thành dòng',filter:'Lọc',derive:'Tính cột',sort:'Sắp xếp',take:'Lấy vị trí',select:'Chọn cột',aggregate:'Tính tổng hợp',group:'Nhóm',join:'Ghép bảng',calculate:'Tính kết quả'};
const changes={improved:'Cải thiện',regressed:'Bị lỗi lại',still_wrong:'Vẫn sai',api_error:'Lỗi API',api_recovered:'API phục hồi',unchanged:'Không đổi',pending:'Đang chờ'};
const charts=globalThis.SifarCharts;
const descriptions={'01':'Tên, tuổi tại nhập học, ô gộp','02':'Tiêu đề phân cấp, xếp hạng','03':'Nhiều sheet và nhiều bảng','04':'Ô trống, dấu phẩy, đầu vào biên','05':'Lookup trên 500 dòng','06':'Lọc nhiều điều kiện, tuổi, xếp hạng','07':'Tổng theo nhóm, số âm, trung bình có trọng số','08':'Tiêu đề 3 cấp, phần trăm, đơn vị nghìn','09':'Ghép sheet, bảng cạnh nhau, tránh cộng đôi','10':'Năm nhuận, ngày biên, tuổi tròn','11':'Ô trống và 0, Unicode, đồng điểm, mã 001','12':'2.500 dòng, dữ liệu cuối bảng, cột AI'};
let state=null,selected='',dataset='public',activeView='overview',detailRow=null,polling=false,page=0;
let selectedIds=new Set(),visibleRows=[],dialogCatalog=[],dialogRevision=0,comparison=null,comparisonFilter='changed';
let workbookData=null,windowRow=1,windowCol=1,highlightCell='',workbookRevision=0;
let visualFilter=null;
try{dataset=localStorage.getItem('sifar.dataset')||'public';selected=localStorage.getItem('sifar.run')||'';}catch{}
const initialParams=new URLSearchParams(location.search);
if(initialParams.has('dataset')){dataset=initialParams.get('dataset')||'public';selected='';}
if(initialParams.has('run'))selected=initialParams.get('run')||'';
function remember(){try{localStorage.setItem('sifar.dataset',dataset);localStorage.setItem('sifar.run',selected);}catch{}}
function notice(message){$('notice').textContent=message;$('notice').classList.toggle('hidden',!message);}
async function getJSON(url,options){const response=await fetch(url,options);const data=await response.json();if(!response.ok)throw new Error(data.error||'Không đọc được dashboard');return data;}
function sameDatasets(a,b){return String(a).split(',').sort().join(',')===String(b).split(',').sort().join(',');}
function datasetList(){return dataset.split(',').filter(Boolean);}
function label(id){return state?.datasets.find(d=>d.id===id)?.label||id;}
function cost(usage){if(!usage)return 'Chưa đo';if(usage.cost_complete)return '$'+Number(usage.actual_cost_usd||0).toFixed(6);return usage.actual_cost_usd>0?'$'+usage.actual_cost_usd.toFixed(6)+'+':'Chưa xác nhận';}
function badge(row){const [text,color]=outcomes[row.outcome]||outcomes.uncompared;return `<span class="badge ${color}">${esc(text)}${row.finalized_with_warning?(row.llm_variant==='llm-v3'?' · Tính được, chưa qua review':' · Đã chốt đáp án'):''}${row.api_statuses?.length?' · '+row.api_statuses.join(', '):''}</span>`;}
function setDataset(ids){dataset=[...new Set(ids)].join(',')||'public';selected='';selectedIds.clear();page=0;remember();refresh();}
function view(name){activeView=name;document.querySelectorAll('.view').forEach(el=>el.classList.toggle('hidden',el.id!==name));document.querySelectorAll('.nav').forEach(el=>el.classList.toggle('active',el.dataset.view===name));if(name==='data')loadWorkbook();if(name==='history')renderHistory();}
function openRun(id){selected=id;selectedIds.clear();page=0;remember();refresh();view('overview');}
async function refresh(){
  if(polling)return;polling=true;
  const requested={dataset,selected};
  try{
    const params=new URLSearchParams({dataset});if(selected)params.set('run',selected);
    const next=await getJSON('/api/state?'+params);
    if(dataset!==requested.dataset||selected!==requested.selected)return;
    const changed=!state||state.selected!==next.selected||state.dataset!==next.dataset;
    state=next;selected=state.selected||'';dataset=state.dataset;
    if(changed){selectedIds.clear();page=0;windowRow=1;windowCol=1;highlightCell='';workbookData=null;comparison=null;visualFilter=null;
      $('compareBefore').innerHTML='';$('compareAfter').innerHTML='';
      $('comparisonResult').innerHTML='<p class="subtle">Chọn hai lần chạy để so sánh.</p>';}
    remember();render();$('connection').textContent='● Đã kết nối';
    if(changed&&activeView==='data')loadWorkbook();
  }catch(error){
    $('connection').textContent='Mất kết nối';notice(error.message);
    if(error.message.includes('Không tìm thấy lần chạy'))selected='';
  }finally{polling=false;if(dataset!==requested.dataset||selected!==requested.selected)refresh();}
}
function render(){
  renderDiagnostics();
  const sum=state.summary,a=state.analysis,chosen=new Set(datasetList());
  $('datasetMenu').innerHTML=state.datasets.map(d=>`<label class="multi-option"><input type="checkbox" value="${esc(d.id)}" ${chosen.has(d.id)?'checked':''}><span>${esc(d.label)}</span><small>${d.question_count} câu</small></label>`).join('');
  $('datasetButton').textContent=chosen.size===1?label([...chosen][0]):`${chosen.size} bộ dữ liệu`;
  $('datasetChips').innerHTML=datasetList().map(id=>`<span class="chip">${esc(id)}<button data-remove="${esc(id)}" aria-label="Bỏ ${esc(id)}">×</button></span>`).join('');
  const compatible=state.runs.filter(r=>sameDatasets(r.dataset,dataset));
  $('runSelect').innerHTML='<option value="">Chưa chạy bộ đang chọn</option>'+compatible.map(r=>`<option value="${esc(r.id)}">${esc(r.label)} · ${r.matched}/${r.compared} khớp${r.api_errors?' · '+r.api_errors+' lỗi API':''}</option>`).join('');
  $('runSelect').value=selected;
  const context=state.context||{};
  $('runProvenance').textContent=context.source_fingerprint?`Mã nguồn ${context.source_fingerprint} · ${context.model||sum.model||''}`:(sum.model||'Chưa có thông tin phiên bản');
  $('modeBadge').textContent=sum.mode==='llm-v3'?(String(sum.pipeline_version||'').startsWith('lmmv3-lite')?'LMMv3 Lite':'LMMv3 · 8 phase'):sum.mode==='llm-v2'?'LLMv2 + Tools':'LLM + Tools';
  $('modeBadge').className='badge';
  $('projectVersion').textContent=`Project v${state.config.app_version||'2.0.0'} · ${sum.mode==='llm-v3'?(String(sum.pipeline_version||'').startsWith('lmmv3-lite')?'LMMv3 Lite':'LMMv3 · 8 phase'):sum.mode==='llm-v2'?'LLMv2 + Tools':'LLM + Tools'} · ${sum.pipeline_version||'tools-v2'}`;
  $('runStatus').textContent=state.running?'● Đang xử lý…':`${sum.completed}/${sum.questions} câu hoàn thành`;
  $('answered').innerHTML=`${sum.answered}<span class="denom"> / ${sum.questions}</span>`;
  $('completionText').textContent=`${sum.completed} câu đã xử lý · ${sum.questions-sum.completed} câu đang chờ`;
  $('progressBar').style.width=(100*sum.completed/Math.max(1,sum.questions))+'%';
  $('matched').innerHTML=`${sum.matched}<span class="denom"> / ${sum.compared}</span>`;
  $('matchRate').textContent=a.exact_match==null?'Chưa có câu để đối chiếu':`${(a.exact_match*100).toFixed(1)}% khớp · ${a.api_errors} lỗi API`;
  $('elapsed').textContent=duration(sum.elapsed_seconds);
  $('average').textContent=sum.completed?`${(sum.elapsed_seconds/sum.completed).toFixed(2)}s / câu${state.running?' · tạm tính':''}`:'Chưa có thời gian';
  $('repairText').textContent=`${a.repaired_questions} câu đã sửa kế hoạch · ${a.repair_attempts} lượt sửa`;
  $('costValue').textContent=sum.completed?cost(sum.usage):(state.running?'Đang xử lý':'Chưa chạy');
  $('tokenValue').textContent=sum.usage?.api_calls?`${number(sum.usage.total_tokens)} token${sum.usage.tokens_complete?'':' ghi nhận'} · ${sum.usage.api_calls} lượt API`:'Chưa ghi nhận lượt API';
  $('usageNote').textContent=!sum.completed?'Chi phí xuất hiện sau khi có kết quả API.':sum.usage?.cost_complete?'Phí API xác nhận, gồm các lượt sửa/retry':`${sum.usage?.unknown_cost_calls||0} lượt chưa rõ phí · Không coi là $0`;
  $('contextText').textContent='Đọc Excel → chọn vùng → LLM lập kế hoạch → công cụ tính → kiểm tra đáp án. Mở chi tiết để xem từng bước.';
  $('openRun').disabled=state.job.running;$('openRun').textContent=state.job.running?'Đang chạy…':'＋ Chạy mới';
  const params=new URLSearchParams({dataset});if(selected)params.set('run',selected);
  $('download').href='/api/download?'+params;$('downloadReport').href='/api/report?'+params;
  $('modelText').textContent=state.config.model;$('keyText').textContent=state.config.key_configured?'Đã cấu hình API key trong môi trường':'Chưa cấu hình API key';
  const currentFile=$('fileSelect').value;$('fileSelect').innerHTML=state.files.map(f=>`<option>${esc(f)}</option>`).join('');if(state.files.includes(currentFile))$('fileSelect').value=currentFile;
  const has402=state.rows.some(r=>r.api_statuses?.includes(402));
  $('apiBanner').classList.toggle('hidden',!a.api_errors);
  $('apiBanner').innerHTML=a.api_errors?`<div><strong>${a.api_errors} câu gặp lỗi API trong lần chạy này${has402?' · HTTP 402':''}</strong><p>${has402?'Kiểm tra credit và hạn mức key trên OpenRouter trước khi chạy lại.':'Mở chi tiết câu hỏi để xem mã lỗi API.'} Đây là thông tin từ log, không phải kiểm tra số dư hiện tại.</p></div>${has402?'<a class="api-link" href="https://openrouter.ai/settings/credits" target="_blank" rel="noreferrer">Mở OpenRouter ↗</a>':''}`:'';
  renderCharts();renderVisuals();renderRows();renderDatasets();renderHistory();renderPipeline();
}
function outcomeFilter(key){return key==='error'?'processing_error':key;}
function axisLabel(value,metric){return metric==='cost'?'$'+value.toFixed(value<.001?5:value<.01?4:2):metric==='tokens'?number(Math.round(value)):metric==='match'?value.toFixed(0)+'%':value.toFixed(1)+'s';}
function plotSVG(content,label,width=800,height=260){return `<svg viewBox="0 0 ${width} ${height}" role="group" aria-label="${esc(label)}" class="data-plot">${content}</svg>`;}
function renderVisuals(){
  const count=state.rows.length,counts=state.analysis.outcomes;let offset=0;
  const slices=Object.entries(outcomes).filter(([key])=>counts[key]>0).map(([key,[text,color]])=>{
    const share=100*counts[key]/Math.max(1,count);const slice=`<circle cx="100" cy="100" r="70" pathLength="100" fill="none" stroke-width="23" stroke-dasharray="${share} ${100-share}" stroke-dashoffset="${-offset}" class="stroke-${color} donut-slice" tabindex="0" role="button" data-filter="${outcomeFilter(key)}" aria-label="${esc(text)}: ${counts[key]} câu"><title>${esc(text)}: ${counts[key]} câu</title></circle>`;offset+=share;return slice;
  }).join('');
  const rate=state.summary.compared?(counts.match||0)/Math.max(1,count):null;
  $('resultDonut').innerHTML=`<svg viewBox="0 0 200 200" class="result-donut" role="group" aria-label="Kết quả của ${count} câu hỏi"><g transform="rotate(-90 100 100)">${slices}</g><text x="100" y="94" class="donut-value">${rate==null?'—':(rate*100).toFixed(0)+'%'}</text><text x="100" y="116" class="donut-subtitle">khớp / toàn bộ câu</text><text x="100" y="137" class="donut-total">${state.summary.completed}/${count} đã xử lý</text></svg>`;
  $('resultLegend').innerHTML=Object.entries(outcomes).filter(([key])=>counts[key]>0).map(([key,[text,color]])=>`<button data-filter="${outcomeFilter(key)}"><i class="legend-dot bg-${color}"></i><span>${text}</span><strong>${counts[key]}</strong></button>`).join('');
  renderQuestionMap();renderScatter();renderDistribution();
}
function renderQuestionMap(){
  const metric=$('mapMetric').value;const values=state.rows.map(r=>charts.measured(r,metric)).filter(v=>v!==null);const max=Math.max(...values,0);
  const groups=new Map();state.rows.forEach((r,i)=>{const key=r.dataset||dataset;if(!groups.has(key))groups.set(key,[]);groups.get(key).push({row:r,index:i+1});});
  $('questionMap').innerHTML=[...groups].map(([key,items])=>`<div class="map-group"><div class="map-group-heading"><span>${esc(label(key))}</span><small>${items.length} câu</small></div><div class="map-grid">${items.map(({row:r,index})=>{
    const value=charts.measured(r,metric);const tone=metric==='status'?'outcome-'+r.outcome:value===null?'map-unknown':'map-tone-'+Math.min(4,Math.floor(4*value/Math.max(.000001,max)));
    const title=`${r.id} · ${outcomes[r.outcome]?.[0]||r.outcome}\n${r.query}\n${metric==='status'?duration(r.elapsed_seconds):value==null?'Chưa có số liệu':axisLabel(value,metric)}`;
    return `<button class="map-cell ${tone}" data-question="${esc(r.id)}" title="${esc(title)}" aria-label="${esc(title)}"><span>${index}</span>${r.repairs?'<i class="repair-mark" aria-label="Có sửa kế hoạch"></i>':''}</button>`;
  }).join('')}</div></div>`).join('');
  $('mapLegend').innerHTML=metric==='status'?'<span><i class="legend-dot bg-green"></i>Khớp</span><span><i class="legend-dot bg-red"></i>Khác / lỗi xử lý</span><span><i class="legend-dot bg-amber"></i>Lỗi API / chưa trả lời</span><span><i class="legend-dot bg-gray"></i>Chờ / chưa đối chiếu</span><span class="subtle">• Chấm ở góc: đã sửa kế hoạch</span>':values.length?`<span>${metric==='time'?'Thời gian':'Chi phí'} thấp</span><span class="tone-scale">${[0,1,2,3,4].map(i=>`<i class="map-tone-${i}"></i>`).join('')}</span><span>${axisLabel(max,metric)}</span><span class="subtle">Ô xám: chưa có số liệu</span>`:'<span class="subtle">Chưa có số liệu được xác nhận. Các ô hiển thị màu xám.</span>';
}
function inspectQuestion(id,target){
  const r=state.rows.find(row=>String(row.id)===String(id));if(!r)return;
  $(target).innerHTML=`<strong>${esc(r.id)}</strong> ${badge(r)}<span class="inspector-question">${esc(r.query)}</span><span class="inspector-metrics">${duration(r.elapsed_seconds)} · ${cost(r.usage)} · ${number(r.usage?.total_tokens)} token ghi nhận${r.repairs?' · '+r.repairs+' lượt sửa':''}</span>`;
}
function renderScatter(){
  const metric=$('scatterMetric').value,data=charts.scatter(state.rows,metric);
  if(!data.points.length){$('scatterPlot').innerHTML=`<div class="plot-empty"><p>Chưa có câu đủ số liệu ${metric==='cost'?'chi phí xác nhận':'token'} và thời gian.</p></div>`;$('scatterInspector').textContent=`${data.excluded} câu thiếu số liệu; không vẽ thành điểm $0.`;return;}
  const width=780,height=260,left=75,right=22,top=25,bottom=48;
  const maxX=Math.max(1,...data.points.map(p=>p.x))*1.06,maxY=Math.max(metric==='cost'?.0001:1,...data.points.map(p=>p.y))*1.08;
  const x=v=>left+v/maxX*(width-left-right),y=v=>height-bottom-v/maxY*(height-top-bottom);
  let svg='';
  for(let i=0;i<=4;i++){
    svg+=`<line x1="${left}" x2="${width-right}" y1="${y(i*maxY/4)}" y2="${y(i*maxY/4)}" class="plot-grid"/><text x="${left-10}" y="${y(i*maxY/4)+4}" text-anchor="end" class="axis-text">${axisLabel(i*maxY/4,metric)}</text><text x="${x(i*maxX/4)}" y="${height-bottom+21}" text-anchor="middle" class="axis-text">${(i*maxX/4).toFixed(1)}</text>`;
  }
  svg+=`<text x="${width/2}" y="${height-6}" text-anchor="middle" class="axis-title">Thời gian mỗi câu (giây)</text>`;
  svg+=data.points.map(p=>`<circle cx="${x(p.x)}" cy="${y(p.y)}" r="${p.repairs?7:5}" class="scatter-point fill-${outcomes[p.outcome]?.[1]||'gray'} ${p.repairs?'point-repaired':''}" role="button" tabindex="0" data-question="${esc(p.id)}" aria-label="Mở ${esc(p.id)}, ${p.x.toFixed(2)} giây, ${axisLabel(p.y,metric)}"><title>${esc(p.id)} · ${p.x.toFixed(2)}s · ${axisLabel(p.y,metric)}</title></circle>`).join('');
  $('scatterPlot').innerHTML=plotSVG(svg,'Thời gian mỗi câu và '+(metric==='cost'?'chi phí API':'token'),width,height)+`<p class="plot-caption">${data.points.length} câu có đủ số liệu · ${data.excluded} câu không vẽ vì thiếu số liệu. Màu thể hiện trạng thái kết quả.</p>`;
}
function renderDistribution(){
  const d=charts.distribution(state.rows);
  if(!d.count){$('latencyHistogram').innerHTML='<div class="plot-empty"><p>Chưa có thời gian từng câu.</p></div>';$('latencyStats').innerHTML='';return;}
  const width=430,height=260,left=38,top=25,bottom=48,plotWidth=width-left-20,plotHeight=height-top-bottom,maxCount=Math.max(...d.bins.map(b=>b.ids.length),1);
  let svg='';
  for(let i=0;i<=2;i++){const yy=height-bottom-i/2*plotHeight;svg+=`<line x1="${left}" x2="${width-20}" y1="${yy}" y2="${yy}" class="plot-grid"/><text x="${left-8}" y="${yy+4}" text-anchor="end" class="axis-text">${Math.round(i/2*maxCount)}</text>`;}
  svg+=d.bins.map((b,i)=>{const x=left+i*plotWidth/6+5,h=b.ids.length/maxCount*plotHeight;return `<g class="histogram-bin" tabindex="0" role="button" data-bin="${i}" aria-label="${b.ids.length} câu từ ${b.lower.toFixed(1)} đến ${b.upper.toFixed(1)} giây"><rect x="${x}" y="${height-bottom-h}" width="${plotWidth/6-10}" height="${Math.max(h,2)}" rx="5" class="fill-blue"/><text x="${x+(plotWidth/6-10)/2}" y="${height-bottom-h-7}" text-anchor="middle" class="bin-value">${b.ids.length}</text><text x="${x+(plotWidth/6-10)/2}" y="${height-bottom+20}" text-anchor="middle" class="axis-text">${b.lower.toFixed(1)}</text><title>${b.lower.toFixed(2)}–${b.upper.toFixed(2)}s: ${b.ids.length} câu</title></g>`;}).join('');
  svg+=`<text x="${width/2}" y="${height-6}" text-anchor="middle" class="axis-title">Thời gian (giây) · khoảng bằng nhau</text>`;
  $('latencyHistogram').innerHTML=plotSVG(svg,'Phân bố thời gian của '+d.count+' câu',width,height);
  $('latencyStats').innerHTML=[['Trung vị',d.median],['P90',d.p90],['Chậm nhất',d.max]].map(([name,v])=>`<div><strong>${v.toFixed(2)}s</strong><span>${name}</span></div>`).join('');
}
function chart(target,items,format=value=>String(value)){
  const max=Math.max(1,...items.map(i=>i.value));
  $(target).innerHTML=items.length?items.map(i=>`<${i.filter?'button':'div'} class="chart-row" ${i.filter?'data-filter="'+esc(i.filter)+'" type="button"':''}><span class="chart-label">${esc(i.label)}</span><svg viewBox="0 0 100 8" preserveAspectRatio="none" aria-hidden="true"><rect width="100" height="8" rx="4" class="bar-track"/><rect width="${100*i.value/max}" height="8" rx="4" class="fill-${i.color||'blue'}"/></svg><strong>${esc(format(i.value))}</strong></${i.filter?'button':'div'}>`).join(''):'<div class="chart-empty"><p>Chưa có dữ liệu trong log.</p></div>';
}
function renderCharts(){
  chart('outcomeChart',Object.entries(outcomes).filter(([key])=>state.analysis.outcomes[key]>0).map(([key,[text,color]])=>({label:text,color,value:state.analysis.outcomes[key],filter:key==='error'?'processing_error':key})));
  const phases={parse:'Đọc Excel',retrieve:'Chọn vùng',plan:'LLM lập kế hoạch',execute:'Tính & kiểm tra'};
  chart('phaseChart',Object.entries(state.analysis.phases).map(([key,value])=>({label:phases[key]||key,value})),duration);
  const issues={answer_shape:'Dạng đáp án',double_count:'Cộng trùng tổng',scope:'Thiếu phạm vi',missing_data:'Thiếu dữ liệu',invalid_plan:'Kế hoạch không hợp lệ',api:'Lỗi API'};
  chart('issueChart',Object.entries(state.analysis.issues).map(([key,value])=>({label:issues[key]||key,value,color:key==='api'?'amber':'purple',filter:key==='api'?'api_error':'validation'})));
}
function filteredRows(){
  const query=$('search').value.toLowerCase(),filter=$('filter').value,sort=$('sortRows').value;
  const rows=state.rows.filter(r=>!$("phaseFilter")||$("phaseFilter").value==="all"||r.diagnostics?.issues.some(issue=>issue.phase===$("phaseFilter").value&&!issue.recovered)).filter(r=>`${r.id} ${r.query} ${r.file_name} ${r.answer}`.toLowerCase().includes(query)).filter(r=>filter==='all'||(filter==='error'&&['error','api_error','unanswered'].includes(r.outcome))||(filter==='processing_error'&&r.outcome==='error')||(filter==='validation'&&r.had_validation_errors)||(filter==='repaired'&&r.repairs>0)||r.outcome===filter).filter(r=>!visualFilter||(charts.finite(r.elapsed_seconds)&&r.elapsed_seconds>=visualFilter.lower&&(visualFilter.last?r.elapsed_seconds<=visualFilter.upper:r.elapsed_seconds<visualFilter.upper)));
  if(sort==='slow')rows.sort((a,b)=>(b.elapsed_seconds||0)-(a.elapsed_seconds||0));
  if(sort==='cost')rows.sort((a,b)=>(b.usage?.actual_cost_usd??-1)-(a.usage?.actual_cost_usd??-1));
  if(sort==='repairs')rows.sort((a,b)=>b.repairs-a.repairs);
  return rows;
}
function renderRows(){
  if(!state)return;
  const rows=filteredRows();page=Math.min(page,Math.max(0,Math.ceil(rows.length/20)-1));visibleRows=rows.slice(page*20,page*20+20);
  $('rowCount').textContent=rows.length;
  $('visualFilter').classList.toggle('hidden',!visualFilter);
  $('visualFilter').innerHTML=visualFilter?`<span>Đang lọc: ${visualFilter.lower.toFixed(2)}–${visualFilter.upper.toFixed(2)} giây</span><button id="clearVisualFilter" class="text-button">Bỏ lọc biểu đồ ×</button>`:'';
  $('answerRows').innerHTML=visibleRows.map(r=>`<tr data-id="${esc(r.id)}" tabindex="0"><td class="row-check"><input type="checkbox" data-pick="${esc(r.id)}" aria-label="Chọn ${esc(r.id)}" ${selectedIds.has(String(r.id))?'checked':''}></td><td class="qid">${esc(r.id)}${r.repairs?'<div class="answer-length">'+r.repairs+' lượt sửa</div>':''}</td><td class="query-cell"><div class="question">${esc(r.query)}</div><div class="filename">${esc(r.file_name)}</div></td><td class="answer-value"><div class="answer-clip">${esc(r.answer||'—')}</div>${r.answer?.length>80?'<div class="answer-length">'+r.answer.length+' ký tự · mở chi tiết</div>':''}</td><td>${badge(r)}</td><td class="duration">${r.elapsed_seconds!=null?duration(r.elapsed_seconds):'—'}</td><td class="duration">${cost(r.usage)}</td><td class="arrow">↗</td></tr>`).join('');
  $('empty').classList.toggle('hidden',rows.length>0);
  $('pageInfo').textContent=rows.length?`${page*20+1}–${Math.min(rows.length,page*20+20)} / ${rows.length} câu`:'0 câu';
  $('previousPage').disabled=page===0;$('nextPage').disabled=(page+1)*20>=rows.length;
  updateSelection();
}
function updateSelection(){
  $('selectionCount').textContent=selectedIds.size+' câu đã chọn';
  $('selectVisible').checked=visibleRows.length>0&&visibleRows.every(r=>selectedIds.has(String(r.id)));
  $('selectVisible').indeterminate=visibleRows.some(r=>selectedIds.has(String(r.id)))&&!$('selectVisible').checked;
  $('rerunSelected').disabled=!selectedIds.size||state.job.running;
  $('rerunFailed').disabled=!failedIds().length||state.job.running;
}
function failedIds(){return state.rows.filter(r=>r.match===false||['error','api_error','unanswered'].includes(r.outcome)).map(r=>String(r.id));}
function renderDatasets(){
  const chosen=new Set(datasetList());
  $('testSuites').innerHTML=state.datasets.filter(d=>d.kind==='test').map(d=>`<button class="step ${chosen.has(d.id)?'active':''}" data-dataset="${esc(d.id)}" aria-pressed="${chosen.has(d.id)}"><div class="step-number">${chosen.has(d.id)?'✓':'▦'}</div><h3>${esc(d.id)}</h3><p>${d.question_count} câu · ${esc(descriptions[d.id.slice(0,2)]||d.label)}</p></button>`).join('');
}
function renderHistory(){
  if(!state)return;
  const runs=state.runs.filter(r=>!$('historyDatasetOnly').checked||sameDatasets(r.dataset,dataset));
  const comparable=runs.filter(r=>!$('sameCohort').checked||(r.cohort&&r.cohort===state.analysis.cohort&&r.mode===state.summary.mode));
  renderHistoryPlot(comparable.slice(0,16).reverse());
  $('historyRows').innerHTML=runs.map(r=>`<tr class="${r.id===selected?'history-row-active':''}"><td><button class="history-open" data-run="${esc(r.id)}">${esc(r.label)}<small>${esc(r.mode)} · ${esc(r.context?.source_fingerprint||'Chưa có fingerprint')}</small></button></td><td class="filename">${esc(r.dataset)}</td><td>${r.matched}/${r.compared}${r.finished?'':' · đang chạy'}</td><td>${duration(r.elapsed_seconds)}</td><td>${cost(r.usage)}</td><td>${r.api_errors||'—'}</td><td><button class="text-button" data-compare-run="${esc(r.id)}">So sánh ↗</button></td></tr>`).join('');
  for(const id of ['compareBefore','compareAfter']){
    const previous=$(id).value;
    $(id).innerHTML=state.runs.map(r=>`<option value="${esc(r.id)}">${esc(r.label)} · ${esc(r.dataset)} · ${r.matched}/${r.compared}</option>`).join('');
    if(state.runs.some(r=>r.id===previous))$(id).value=previous;
    else if(id==='compareAfter'&&selected)$(id).value=selected;
    else if(id==='compareBefore')$(id).value=state.runs.find(r=>r.id!==selected&&sameDatasets(r.dataset,dataset))?.id||state.runs[0]?.id||'';
  }
}
function renderHistoryPlot(runs){
  const metric=$('historyMetric').value;
  if(!runs.length){$('historyTrend').innerHTML='<div class="plot-empty"><p>Chưa có lần chạy cùng phạm vi. Bỏ chọn “Cùng câu hỏi, tham chiếu và chế độ” để xem các lần khác.</p></div>';return;}
  const points=runs.map((run,index)=>({run,index,value:charts.historyValue(run,metric)}));
  const maxY=metric==='match'?100:Math.max(metric==='cost'?.001:1,...points.map(p=>p.value||0))*1.1;
  const width=980,height=260,left=70,right=35,top=22,bottom=55;
  const x=p=>left+(points.length===1?.5:p.index/(points.length-1))*(width-left-right);
  const y=p=>height-bottom-(p.value||0)/maxY*(height-top-bottom);
  let svg='';
  for(let i=0;i<=4;i++){const value=i*maxY/4,yy=height-bottom-value/maxY*(height-top-bottom);svg+=`<line x1="${left}" x2="${width-right}" y1="${yy}" y2="${yy}" class="plot-grid"/><text x="${left-12}" y="${yy+4}" text-anchor="end" class="axis-text">${axisLabel(value,metric)}</text>`;}
  svg+=`<path d="${charts.segments(points,x,y)}" class="history-line"/>`;
  svg+=points.map(p=>`<circle cx="${x(p)}" cy="${p.value===null?height-bottom:y(p)}" r="7" class="history-point ${p.value===null?'point-unknown':p.run.id===selected?'point-current':''}" tabindex="0" role="button" data-run="${esc(p.run.id)}" aria-label="Mở ${esc(p.run.label)}, ${p.value===null?'thiếu số liệu hoặc lỗi API':axisLabel(p.value,metric)}"><title>${esc(p.run.label)} · ${p.value===null?'Không vẽ giá trị thiếu/lỗi API':axisLabel(p.value,metric)}</title></circle>${p.index%Math.max(1,Math.ceil(points.length/8))===0||p.index===points.length-1?`<text x="${x(p)}" y="${height-bottom+23}" text-anchor="middle" class="axis-text">${esc(p.run.label.split(' ').at(-1).slice(0,5))}</text>`:''}`).join('');
  $('historyTrend').innerHTML=plotSVG(svg,'Lịch sử '+{match:'tỷ lệ khớp',time:'thời gian',cost:'chi phí'}[metric],width,height)+`<p class="plot-caption">${runs.length} lần chạy · ${$('sameCohort').checked?'cùng câu hỏi, tham chiếu và chế độ':'các phạm vi có thể khác nhau'} · Điểm rỗng: thiếu số liệu/chưa xong/lỗi API. Đường không nối qua điểm thiếu dữ liệu.</p>`;
}
async function compareRuns(){
  const before=$('compareBefore').value,after=$('compareAfter').value;
  if(!before||!after||before===after){$('comparisonResult').innerHTML='<p class="subtle">Chọn hai lần chạy khác nhau.</p>';return;}
  $('compareButton').disabled=true;
  try{comparison=await getJSON('/api/compare?'+new URLSearchParams({before,after}));comparisonFilter='changed';renderComparison();}
  catch(error){$('comparisonResult').textContent=error.message;}
  finally{$('compareButton').disabled=false;}
}
function renderComparison(){
  if(!comparison)return;const c=comparison.counts;
  const rows=comparison.rows.filter(r=>comparisonFilter==='all'||(comparisonFilter==='changed'&&r.change!=='unchanged')||r.change===comparisonFilter);
  $('comparisonResult').innerHTML=`<div class="compare-stats"><div class="compare-stat green"><strong>${c.improved||0}</strong><span>Câu cải thiện</span></div><div class="compare-stat red"><strong>${c.regressed||0}</strong><span>Câu bị lỗi lại</span></div><div class="compare-stat amber"><strong>${c.api_error||0}</strong><span>Câu lỗi API</span></div><div class="compare-stat"><strong>${comparison.comparable}</strong><span>Câu có thể so sánh</span></div></div><p class="subtle">${comparison.excluded_changed_reference_or_question} câu loại vì đổi câu hỏi/tham chiếu · ${comparison.only_before} chỉ có ở lần trước · ${comparison.only_after} chỉ có ở lần sau. API phục hồi được ghi riêng.</p><div class="compare-tabs">${[['changed','Có thay đổi'],['improved','Cải thiện'],['regressed','Bị lỗi lại'],['still_wrong','Vẫn sai'],['api_error','Lỗi API'],['all','Tất cả']].map(([key,text])=>`<button data-change="${key}" class="${key===comparisonFilter?'active':''}">${text}</button>`).join('')}</div>${rows.length?rows.map(r=>`<article class="compare-result-row"><span class="badge ${r.change==='improved'?'green':r.change==='regressed'?'red':'gray'}">${changes[r.change]}</span> <span class="qid">${esc(r.id)}</span><p>${esc(r.query)}</p><div class="compare-answers"><div><small>TRƯỚC</small>${esc(r.before||'—')}</div><div><small>SAU</small>${esc(r.after||'—')}</div></div><p class="subtle">Tham chiếu: ${esc(r.reference)}</p><button class="text-button" data-open-after="${esc(r.id)}">Mở câu ở lần sau ↗</button></article>`).join(''):'<div class="chart-empty"><p>Không có câu trong nhóm này.</p></div>'}`;
  const board=document.createElement('div');board.className='comparison-map';board.innerHTML='<div class="map-group-heading"><span>Thay đổi theo từng câu</span><small>Bấm ô để mở câu ở lần sau.</small></div><div class="map-grid">'+comparison.rows.map((r,i)=>`<button class="map-cell change-${r.change}" data-open-after="${esc(r.id)}" title="${esc(r.id)} · ${changes[r.change]}" aria-label="${esc(r.id)} · ${changes[r.change]}">${i+1}</button>`).join('')+'</div>';
  $('comparisonResult').querySelector('.compare-tabs').before(board);
}
function renderPipeline(){
  const modern=String(state.summary.pipeline_version||'').startsWith('tools-')||state.summary.mode==='llm-v3';
  const steps=String(state.summary.pipeline_version||'').startsWith('lmmv3-lite')?[['Đọc dữ liệu gọn','Giữ tọa độ, tiêu đề và tránh gửi vùng trùng.'],['Lập kế hoạch','Một lượt LLM; tối đa một lượt sửa hoặc đọc thêm.'],['Python tính toán','Chỉ thực thi công cụ cho phép, giữ nguồn ô.'],['Xuất đáp án','Định dạng từ kế hoạch; chưa có review ngữ nghĩa.']]:state.summary.mode==='llm-v3'?[['Đọc workbook','Giá trị gốc, ô gộp, tiêu đề, kiểu dữ liệu.'],['Đặc tả câu hỏi','Yêu cầu đa ngôn ngữ, phạm vi và định dạng.'],['Khám phá dữ liệu','Đọc sheet, bảng, ô, vùng và thống kê cột.'],['Đủ bằng chứng?','Đối chiếu từng yêu cầu với ô đã quan sát.'],['Lập kế hoạch','Kiểm tra cấu trúc, kiểu và tham chiếu.'],['Thực thi','Python tính theo kế hoạch, giữ nguồn ô.'],['Kiểm chứng và sửa','Review có chọn lọc, ghi lỗi và giới hạn retry.'],['Xuất đáp án','Định dạng theo đặc tả và lưu log.']]:[['Đọc Excel','Giữ tọa độ, ô gộp và tiêu đề.'],['Chọn vùng','Tìm sheet/bảng liên quan.'],['Lập kế hoạch','LLM chọn thao tác tính.'],['Tính bằng công cụ','Lọc, nhóm, tổng, xếp hạng.'],['Kiểm tra đáp án','Kiểm tra phạm vi và dạng đáp án.'],['Xuất kết quả','CSV, căn cứ, log và chi phí.']];
  $('pipelineSteps').innerHTML=steps.map(([title,text],i)=>`<div class="step"><div class="step-number">0${i+1}</div><h3>${title}</h3><p>${text}</p></div>`).join('');
  document.querySelector('.future').innerHTML=`<span class="badge ${modern?'green':'gray'}">${modern?'LLM + TOOLS':'LOG CŨ'}</span><h3>${modern?'Kế hoạch hợp lệ chưa đồng nghĩa đáp án đúng':'Chỉ có các thông tin được ghi ở phiên bản cũ'}</h3><p>${modern?'Dùng đối chiếu tham chiếu và ô căn cứ để đánh giá. Câu sai vẫn có thể xuất phát từ cách hiểu câu hỏi hoặc lựa chọn dữ liệu.':'Không suy ngược token/chi phí từ đáp án. Chạy phiên bản mới để có log chi tiết hơn.'}</p>`;
}
function detail(id){
  detailRow=state.rows.find(r=>String(r.id)===String(id));if(!detailRow)return;
  const r=detailRow,u=r.usage;
  $('detailId').textContent=`${r.id} / ${r.file_name}`;$('detailQuestion').textContent=r.query;
  $('detailAnswer').textContent=r.answer||'Chưa có đáp án';$('detailReference').textContent=r.reference??'Không có tham chiếu';
  $('detailMeta').innerHTML=`${badge(r)}<br>${duration(r.elapsed_seconds)} · ${r.repairs} lượt sửa kế hoạch${u?'<br>'+number(u.total_tokens)+' token · '+u.api_calls+' lượt API · '+cost(u):''}${r.error_type?'<br>Loại lỗi: '+esc(r.error_type):''}${r.finalized_reason?'<br>Chốt cuối: '+esc(r.finalized_reason):''}`;
  let html='';
  if(r.answer_contract){const c=r.answer_contract;html+=`<div class="contract-card"><strong>Yêu cầu đáp án</strong><br>${c.count==null?'Danh sách / số phần tử chưa cố định':c.count+' giá trị'}${c.reduction?' · phép '+esc({sum:'tổng',mean:'trung bình',count:'đếm'}[c.reduction]||c.reduction):''}${c.rank_offset!=null?' · bắt đầu ở vị trí '+(c.rank_offset+1):''}${c.decimals!=null?' · '+c.decimals+' chữ số thập phân':''}</div>`;}
  if(r.tool_trace?.length)html+='<h3 class="detail-section">Dữ liệu đi qua các công cụ</h3><div class="tool-flow">'+r.tool_trace.map((s,i)=>`<div class="flow-node"><span class="flow-index">${i+1}</span><strong>${esc(ops[s.op]||s.op)}</strong><div class="flow-result">${s.row_count==null?esc(s.scalar):number(s.row_count)+' dòng'}</div><small>${duration(s.elapsed_seconds)}</small></div>`).join('')+'</div>';
  if(r.timings)html+='<h3 class="detail-section">Thời gian từng bước</h3><div class="tool-trace">'+Object.entries(r.timings).map(([key,value])=>`<div><b>${esc(key)}</b><span>${duration(value)}</span></div>`).join('')+'</div>';
  if(r.tool_trace)html+='<h3 class="detail-section">Luồng công cụ</h3><div class="tool-trace">'+r.tool_trace.map((s,i)=>`<div><b>${i+1}. ${esc(ops[s.op]||s.op)}</b><span>${s.row_count==null?esc(s.scalar):s.row_count+' dòng'} · ${duration(s.elapsed_seconds)}</span></div>`).join('')+'</div>';
  if(r.evidence?.length)html+='<h3 class="detail-section">Ô căn cứ · '+r.evidence_count+' ô (hiển thị tối đa 40)</h3><div class="evidence">'+r.evidence.slice(0,40).map(cell=>`<button data-cell="${esc(cell)}">${esc(cell)} ↗</button>`).join('')+'</div>';
  if(u?.calls?.length)html+='<h3 class="detail-section">Lượt API</h3><div class="tool-trace">'+u.calls.map(call=>`<div><b>#${call.attempt} · ${call.purpose==='repair'?'Sửa kế hoạch':'Lập kế hoạch'} · ${esc(call.status)}${call.http_status?' · HTTP '+call.http_status:''}</b><span>${call.total_tokens??'?'} token · ${call.actual_cost_usd==null?'Chưa xác nhận phí':'$'+call.actual_cost_usd.toFixed(6)}</span></div>`).join('')+'</div>';
  if(r.validation_errors?.length)html+='<h3 class="detail-section">Lỗi kiểm tra đã gặp</h3><p class="detail-note">'+r.validation_errors.map(esc).join('<br>')+'</p>';
  if(r.plans?.length)html+='<h3 class="detail-section">Các lần lập kế hoạch</h3>'+r.plans.map(p=>`<details class="plan"><summary>Lần ${p.attempt}${p.validation_error?' · có lỗi kiểm tra':''}</summary>${p.validation_error?'<p class="detail-note">'+esc(p.validation_error)+'</p>':''}<pre>${esc(JSON.stringify(p.plan,null,2))}</pre></details>`).join('');
  if(r.retrieval)html+='<details class="plan"><summary>Vùng dữ liệu được chọn</summary><pre>'+esc(JSON.stringify(r.retrieval.filter(t=>t.selected),null,2))+'</pre></details>';
  if(r.previews)html+='<details class="plan"><summary>Excel đã đưa vào prompt</summary><pre>'+esc(JSON.stringify(r.previews,null,2))+'</pre></details>';
  if(r.phases)html+='<h3 class="detail-section">LMMv3 · Lịch sử 8 phase</h3><div class="tool-trace">'+r.phases.map(p=>`<div><b>${p.phase}. ${esc(p.name)} · ${esc(p.status)}</b><span>${duration(p.elapsed_seconds)}${p.message?' · '+esc(p.message):''}</span></div>`).join('')+'</div>';
  for(const [key,title] of [['verification_level','Mức kiểm chứng'],['finalized_reason','Lý do giữ kết quả kèm cảnh báo'],['unanswerable_reason','Lý do chưa có đáp án'],['specification_warnings','Cảnh báo đặc tả'],['model_responses','Phản hồi LLM gốc'],['candidate_answer','Ứng viên tính toán (xem trạng thái kiểm chứng)'],['question_spec','Đặc tả câu hỏi'],['readiness','Đối chiếu yêu cầu và bằng chứng'],['verification_warnings','Cảnh báo cần kiểm chứng'],['interactions','Đọc thêm và điều phối sửa lỗi']])if(r[key])html+=`<details class="plan"><summary>${title}</summary><pre>${esc(JSON.stringify(r[key],null,2))}</pre></details>`;
  $('toolDetails').innerHTML=html;
  $('toolDetails').insertAdjacentHTML('afterbegin','<h3 class="detail-section">Chẩn đoán theo phase</h3>'+renderIssueList(r.diagnostics?.issues||[])+'<p class="detail-note">Phase là nơi quan sát lỗi; nguyên nhân gốc chưa xác nhận.</p><div id="diagnosticHistory">Đang đọc lịch sử phiên…</div>');
  loadDiagnosticHistory(String(r.id));
$('detailNote').textContent=r.verification_level==='tool_execution_only'?'LMMv3 Lite: Python đã thực thi kế hoạch; chưa có bước review ý nghĩa hoặc xác nhận đáp án đúng.':'Căn cứ và kiểm tra kế hoạch giúp truy lỗi. Mức khớp tham chiếu không bảo đảm khả năng trả lời trên tập ẩn.';
  $('detailRerun').disabled=state.job.running;$('detailDialog').showModal();
}
async function loadWorkbook(sheet){
  const file=$('fileSelect').value;if(!file)return;const revision=++workbookRevision;
  $('sheetInfo').textContent='Đang đọc Excel…';
  try{
    const params=new URLSearchParams({file,dataset,row:windowRow,col:windowCol});if(sheet)params.set('sheet',sheet);
    const data=await getJSON('/api/workbook?'+params);if(revision!==workbookRevision)return;workbookData=data;
    windowRow=data.start_row;windowCol=data.start_col;
    $('sheetSelect').innerHTML=data.sheets.map(s=>`<option>${esc(s)}</option>`).join('');$('sheetSelect').value=data.sheet;
    $('sheetInfo').textContent=`${data.filename} / ${data.sheet} · ${number(data.total_rows)} dòng × ${data.total_columns} cột · ${data.merged.length} vùng ô gộp`;
    $('workbookWindow').textContent=`Dòng ${data.start_row}–${data.end_row} · Cột ${data.columns[0]}–${data.columns.at(-1)}`;
    $('workbookTable').innerHTML='<thead><tr><th>#</th>'+data.columns.map(c=>`<th>${c}</th>`).join('')+'</tr></thead><tbody>'+data.rows.map((row,i)=>`<tr><td class="row-num">${data.start_row+i}</td>${row.map((value,j)=>{const cell=data.columns[j]+(data.start_row+i);return `<td data-coordinate="${cell}" class="${cell===highlightCell?'cell-highlight':''}">${esc(value)}</td>`;}).join('')}</tr>`).join('')+'</tbody>';
    $('rowBack').disabled=windowRow<=1;$('rowForward').disabled=data.end_row>=data.total_rows;$('colBack').disabled=windowCol<=1;$('colForward').disabled=data.end_col>=data.total_columns;
    if(highlightCell)document.querySelector('.cell-highlight')?.scrollIntoView({block:'center',inline:'center'});
  }catch(error){if(revision!==workbookRevision)return;$('sheetInfo').textContent=error.message;$('workbookTable').innerHTML='';}
}
function parseCell(text){const match=String(text).trim().toUpperCase().match(/^([A-Z]{1,3})([1-9]\d*)$/);if(!match)throw new Error('Nhập địa chỉ ô như A1 hoặc AI2501.');let col=0;for(const c of match[1])col=col*26+c.charCodeAt(0)-64;return {col,row:Number(match[2]),cell:match[0]};}
async function jumpTo(text,sheet){try{const cell=parseCell(text);const targetSheet=sheet||$('sheetSelect').value;
  if(workbookData?.filename===$('fileSelect').value&&workbookData.sheet===targetSheet&&(cell.row>workbookData.total_rows||cell.col>workbookData.total_columns))throw new Error('Ô nằm ngoài vùng dữ liệu của sheet.');
  windowRow=Math.floor((cell.row-1)/200)*200+1;windowCol=Math.floor((cell.col-1)/30)*30+1;highlightCell=cell.cell;$('cellJump').value=cell.cell;await loadWorkbook(targetSheet);}catch(error){notice(error.message);}}
async function openEvidence(text){const index=text.lastIndexOf('!');if(index<0)return;const sheet=text.slice(0,index).replace(/^'|'$/g,'');const cell=text.slice(index+1);$('detailDialog').close();$('fileSelect').value=detailRow.file_name;activeView='data';document.querySelectorAll('.view').forEach(el=>el.classList.toggle('hidden',el.id!=='data'));document.querySelectorAll('.nav').forEach(el=>el.classList.toggle('active',el.dataset.view==='data'));await jumpTo(cell,sheet);}
async function openRunDialog(scope='one',seed=[]){
  if(!state||state.job.running)return;
  const chosen=new Set(datasetList());
  $('datasetDialog').innerHTML=state.datasets.map(d=>`<label class="multi-option"><input type="checkbox" value="${esc(d.id)}" ${chosen.has(d.id)?'checked':''}><span>${esc(d.label)}</span><small>${d.question_count} câu</small></label>`).join('');
  $('scope').value=scope;$('runDialog').showModal();await loadDialogCatalog(seed);updateRunEstimate();
}
async function loadDialogCatalog(seed=[]){
  const revision=++dialogRevision;const datasets=[...$('datasetDialog').querySelectorAll('input:checked')].map(el=>el.value);
  $('submitRun').disabled=true;dialogCatalog=[];$('questionSelect').innerHTML='';$('dialogSelection').innerHTML='';
  if(!datasets.length){updateRunEstimate();return;}
  try{
    const data=await getJSON('/api/catalog?'+new URLSearchParams({dataset:datasets.join(',')}));if(revision!==dialogRevision)return;
    dialogCatalog=data.catalog;$('questionSelect').innerHTML=dialogCatalog.map(q=>`<option value="${esc(q.id)}">${esc(q.id)} · ${esc(q.query.slice(0,90))}</option>`).join('');
    const wanted=new Set(seed.length?seed:$('scope').value==='failed'?failedIds():[...selectedIds]);
    $('dialogSelection').innerHTML=dialogCatalog.map(q=>`<label class="question-check"><input type="checkbox" value="${esc(q.id)}" ${wanted.has(String(q.id))?'checked':''}><span><small>${esc(q.id)}</small>${esc(q.query)}</span></label>`).join('');
    if(seed.length)$('questionSelect').value=seed[0];updateRunEstimate();
  }catch(error){notice(error.message);}
}
function runIds(){if($('scope').value==='all')return null;if($('scope').value==='one')return $('questionSelect').value?[$('questionSelect').value]:[];return [...$('dialogSelection').querySelectorAll('input:checked')].map(el=>el.value);}
function updateRunEstimate(){
  const scope=$('scope').value;
  $('questionSelect').classList.toggle('hidden',scope!=='one');$('dialogSelection').classList.toggle('hidden',!['selected','failed'].includes(scope));
  const ids=runIds(),count=ids===null?dialogCatalog.length:ids.length;
  $('runEstimate').textContent=`${count} câu · Giới hạn ngân sách tối đa $${(count*.10).toFixed(2)} cho lần chạy ($0.10/câu). Phí thực tế phụ thuộc token.`;
  $('apiNote').textContent='LLM dùng API key đã cấu hình. Kiểm tra credit trước khi chạy.';
  $('submitRun').disabled=!count||state.job.running;
}
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>view(b.dataset.view));
for(const id of ['resultDonut','resultLegend'])$(id).onclick=e=>{const target=e.target.closest('[data-filter]');if(!target)return;$('filter').value=target.dataset.filter;page=0;renderRows();document.querySelector('.answers-panel').scrollIntoView({behavior:'smooth',block:'start'});};
$('mapMetric').onchange=renderQuestionMap;$('scatterMetric').onchange=renderScatter;
for(const [container,inspector] of [['questionMap','mapInspector'],['scatterPlot','scatterInspector']]){
  $(container).onclick=e=>{const target=e.target.closest('[data-question]');if(target)detail(target.dataset.question);};
  for(const event of ['pointerover','focusin'])$(container).addEventListener(event,e=>{const target=e.target.closest('[data-question]');if(target)inspectQuestion(target.dataset.question,inspector);});
}
$('latencyHistogram').onclick=e=>{const target=e.target.closest('[data-bin]');if(!target)return;const d=charts.distribution(state.rows),index=Number(target.dataset.bin),bin=d.bins[index];visualFilter={lower:bin.lower,upper:bin.upper,last:index===d.bins.length-1};page=0;renderRows();document.querySelector('.answers-panel').scrollIntoView({behavior:'smooth',block:'start'});};
$('visualFilter').onclick=e=>{if(e.target.closest('#clearVisualFilter')){visualFilter=null;page=0;renderRows();}};
for(const id of ['sameCohort','historyMetric'])$(id).onchange=renderHistory;
for(const event of ['pointerover','focusin'])$('historyTrend').addEventListener(event,e=>{const target=e.target.closest('[data-run]');if(!target)return;const run=state.runs.find(r=>r.id===target.dataset.run);if(run)$('historyInspector').textContent=`${run.label} · ${run.questions} câu · ${run.matched}/${run.compared} khớp · ${duration(run.elapsed_seconds)} · ${cost(run.usage)}${run.api_errors?' · '+run.api_errors+' lỗi API':''}`;});
for(const id of ['resultDonut','scatterPlot','latencyHistogram','historyTrend'])$(id).addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)&&e.target.matches('[role="button"]')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
$('viewPipeline').onclick=()=>view('pipeline');$('refresh').onclick=refresh;
$('datasetButton').onclick=()=>{const open=$('datasetMenu').classList.contains('hidden');$('datasetMenu').classList.toggle('hidden',!open);$('datasetButton').setAttribute('aria-expanded',String(open));};
$('datasetMenu').onchange=()=>setDataset([...$('datasetMenu').querySelectorAll('input:checked')].map(el=>el.value));
$('datasetChips').onclick=e=>{const b=e.target.closest('[data-remove]');if(b)setDataset(datasetList().filter(id=>id!==b.dataset.remove));};
document.addEventListener('click',e=>{if(!$('datasetPicker').contains(e.target)){$('datasetMenu').classList.add('hidden');$('datasetButton').setAttribute('aria-expanded','false');}});
$('runSelect').onchange=()=>openRun($('runSelect').value);$('clearDatasets').onclick=()=>setDataset(['public']);
$('testSuites').onclick=e=>{const b=e.target.closest('[data-dataset]');if(!b)return;const ids=datasetList();setDataset(ids.includes(b.dataset.dataset)?ids.filter(id=>id!==b.dataset.dataset):[...ids,b.dataset.dataset]);};
for(const id of ['search','filter','sortRows'])$(id).addEventListener(id==='search'?'input':'change',()=>{page=0;renderRows();});
$('previousPage').onclick=()=>{page--;renderRows();};$('nextPage').onclick=()=>{page++;renderRows();};
$('answerRows').onclick=e=>{const input=e.target.closest('[data-pick]');if(input){if(input.checked)selectedIds.add(input.dataset.pick);else selectedIds.delete(input.dataset.pick);updateSelection();return;}const row=e.target.closest('tr');if(row)detail(row.dataset.id);};
$('answerRows').onkeydown=e=>{if(e.key==='Enter'&&!e.target.matches('input')){const row=e.target.closest('tr');if(row)detail(row.dataset.id);}};
$('selectVisible').onchange=()=>{visibleRows.forEach(r=>$('selectVisible').checked?selectedIds.add(String(r.id)):selectedIds.delete(String(r.id)));renderRows();};
$('clearSelection').onclick=()=>{selectedIds.clear();renderRows();};
$('rerunSelected').onclick=()=>openRunDialog('selected');$('rerunFailed').onclick=()=>openRunDialog('failed');
for(const id of ['outcomeChart','issueChart'])$(id).onclick=e=>{const b=e.target.closest('[data-filter]');if(!b)return;$('filter').value=b.dataset.filter;page=0;renderRows();document.querySelector('.answers-panel').scrollIntoView({behavior:'smooth',block:'start'});};
$('historyDatasetOnly').onchange=renderHistory;
for(const id of ['historyRows','historyTrend'])$(id).onclick=e=>{const b=e.target.closest('[data-run]');if(b){openRun(b.dataset.run);return;}const c=e.target.closest('[data-compare-run]');if(c){$('compareBefore').value=c.dataset.compareRun;$('compareAfter').value=selected;compareRuns();}};
$('compareButton').onclick=compareRuns;
$('comparisonResult').onclick=async e=>{const b=e.target.closest('[data-change]');if(b){comparisonFilter=b.dataset.change;renderComparison();return;}const target=e.target.closest('[data-open-after]');if(target&&comparison){selected=comparison.after;await refresh();view('overview');detail(target.dataset.openAfter);}};
$('closeDetail').onclick=()=>$('detailDialog').close();$('detailData').onclick=()=>{$('detailDialog').close();$('fileSelect').value=detailRow.file_name;windowRow=windowCol=1;highlightCell='';view('data');};
$('toolDetails').onclick=e=>{const b=e.target.closest('[data-cell]');if(b)openEvidence(b.dataset.cell);};
$('detailRerun').onclick=()=>{const id=String(detailRow.id);$('detailDialog').close();openRunDialog('one',[id]);};
$('fileSelect').onchange=()=>{windowRow=windowCol=1;highlightCell='';loadWorkbook();};$('sheetSelect').onchange=()=>{windowRow=windowCol=1;highlightCell='';loadWorkbook($('sheetSelect').value);};
$('cellJumpForm').onsubmit=e=>{e.preventDefault();jumpTo($('cellJump').value);};
for(const [id,axis,delta] of [['rowBack','row',-200],['rowForward','row',200],['colBack','col',-30],['colForward','col',30]])$(id).onclick=()=>{if(axis==='row')windowRow=Math.max(1,windowRow+delta);else windowCol=Math.max(1,windowCol+delta);highlightCell='';loadWorkbook($('sheetSelect').value);};
$('openRun').onclick=()=>openRunDialog();$('datasetDialog').onchange=()=>loadDialogCatalog();
$('closeRun').onclick=$('cancelRun').onclick=()=>$('runDialog').close();
$('scope').onchange=()=>{if($('scope').value==='failed'){const ids=new Set(failedIds());$('dialogSelection').querySelectorAll('input').forEach(input=>input.checked=ids.has(input.value));}updateRunEstimate();};
for(const id of ['mode','questionSelect','dialogSelection'])$(id).onchange=updateRunEstimate;
$('runForm').onsubmit=async e=>{
  e.preventDefault();$('submitRun').disabled=true;
  try{
    const chosen=[...$('datasetDialog').querySelectorAll('input:checked')].map(input=>input.value).join(',');const ids=runIds();
    if(!chosen||ids?.length===0)throw new Error('Chọn bộ dữ liệu và ít nhất một câu hỏi.');
    const result=await getJSON('/api/run',{method:'POST',headers:{'Content-Type':'application/json','X-Dashboard-Token':state.csrf},body:JSON.stringify({mode:$('mode').value,dataset:chosen,ids})});
    selected=result.run_id;dataset=chosen;selectedIds.clear();page=0;$('runDialog').close();notice('Đã bắt đầu lần chạy mới. Kết quả tự cập nhật và được lưu riêng.');await refresh();view('overview');
  }catch(error){notice(error.message);}
  finally{updateRunEstimate();}
};
refresh();setInterval(()=>{if($('autoRefresh').checked)refresh();},3000);
