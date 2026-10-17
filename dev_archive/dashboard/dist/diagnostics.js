/* Diagnostics only; no API generation requests. */
const diagnosticCertainty={confirmed:'Đã xác định dấu hiệu',suspected:'Nghi ngờ',unknown:'Chưa xác định'};
const diagnosticTransitions={first_observation:'Ghi nhận đầu tiên',improved:'Đã cải thiện',regressed:'Tái xuất hiện',still_failing:'Còn lặp lại',still_matches:'Tiếp tục khớp',not_comparable:'Chưa đủ dữ liệu so sánh'};
function renderIssueList(issues){
  if(!issues.length) return '<p class="detail-note">Chưa ghi nhận lỗi từ nhật ký. Điều này không chứng minh đáp án đúng.</p>';
  return issues.map(issue=>`<div class="diagnostic-issue"><strong>${escapeHTML(issue.phase_label)} · ${escapeHTML(issue.title)}</strong><p>${escapeHTML(issue.evidence)}</p><span class="badge ${issue.recovered?'green':'amber'}">${issue.recovered?'Đã sửa trong phiên':'Còn tồn tại'}</span> <span class="badge gray">${diagnosticCertainty[issue.certainty]}</span>${issue.candidate_phases.length?'<p>Phase cần kiểm tra thêm: '+issue.candidate_phases.map(escapeHTML).join(', ')+'</p>':''}</div>`).join('');
}
function diagnosticBuckets(buckets){
  if(!buckets?.length) return '<p class="detail-note">Chưa ghi nhận lỗi trong phạm vi này.</p>';
  return '<div class="tool-trace">'+buckets.map(bucket=>`<div><b>${escapeHTML(bucket.phase_label)} · ${escapeHTML(bucket.title)}<br><small>${diagnosticCertainty[bucket.certainty]} · ${bucket.recovered?'Đã sửa trong phiên':'Còn tồn tại'}</small></b><span>${bucket.questions} lần ghi nhận · ${bucket.datasets.length} dataset</span></div>`).join('')+'</div>';
}
function renderDiagnostics(){
  if(!$('phaseFilter')){
    const filter=document.createElement('select');filter.id='phaseFilter';filter.setAttribute('aria-label','Lọc phase lỗi');
    filter.innerHTML='<option value="all">Tất cả phase lỗi</option>'+Object.entries({parse:'Đọc Excel',rag:'RAG',llm:'LLM',tool:'TOOL',format:'Định dạng',api:'API / tài nguyên',unknown:'Chưa xác định'}).map(([key,label])=>`<option value="${key}">${label}</option>`).join('');
    $('filter').parentElement.appendChild(filter);filter.onchange=renderRows;
  }
  let panel=$('diagnosticsPanel');
  if(!panel){
    panel=document.createElement('section'); panel.id='diagnosticsPanel'; panel.className='panel';
    panel.innerHTML='<div class="panel-heading"><div><h2>Khoanh vùng lỗi theo phase</h2><p>Lỗi quan sát được, mức xác nhận và lỗi đã sửa trong phiên.</p></div><button id="diagnosticAllRuns" class="button secondary">Thống kê lịch sử các dataset</button></div><div id="diagnosticBuckets" class="diagnostic-content"></div><div class="sheet-foot">Một câu có thể có nhiều dấu hiệu lỗi. Không cộng các phase để suy ra số câu sai; chưa xác nhận quan hệ lỗi gốc / dây chuyền.</div>';
    document.querySelector('.context-strip').insertAdjacentElement('afterend',panel);
    $('diagnosticAllRuns').onclick=async()=>{
      const button=$('diagnosticAllRuns');button.disabled=true;
      try{const result=await getJSON(diagnosticURL()); $('diagnosticBuckets').innerHTML='<p class="detail-note">Lịch sử '+result.runs_scanned+' phiên gần nhất (tối đa '+result.limit_runs+'). Đếm lần ghi nhận, không phải số câu độc lập.</p>'+diagnosticBuckets(result.summary_all_runs);}
      catch(error){notice(error.message);}finally{button.disabled=false;}
    };
  }
  // Do not overwrite a historical report during polling the same run.
  if(panel.dataset.run!==String(state.selected)||!$('diagnosticBuckets').innerHTML){
    panel.dataset.run=String(state.selected);$('diagnosticBuckets').innerHTML=diagnosticBuckets(state.diagnostics_summary);
  }
}
function diagnosticURL(){const params=new URLSearchParams();if(selected)params.set('run',selected);if(dataset)params.set('dataset',dataset);return '/api/diagnostics?'+params.toString();}
async function loadDiagnosticHistory(id){
  try{
    const result=await getJSON(diagnosticURL());
    if(String(detailRow?.id)!==id)return;
    const entries=result.question_history[id]||[];
    $('diagnosticHistory').innerHTML='<h3 class="detail-section">Lịch sử cùng câu / dataset / tham chiếu</h3>'+(entries.length?'<div class="tool-trace">'+entries.map(entry=>`<div><b>${escapeHTML(entry.run)}<br><small>${escapeHTML(entry.pipeline_version||'Phiên bản chưa lưu')} · ${escapeHTML(entry.model||'Model chưa lưu')} · ${escapeHTML(entry.code_fingerprint?.slice(0,8)||'Chưa lưu mã phiên bản')}<br>${entry.reference_basis==='snapshot'?'Tham chiếu lưu theo phiên':'So lại bằng tham chiếu hiện tại'}</small></b><span>${diagnosticTransitions[entry.transition]}</span></div>`).join('')+'</div><p class="detail-note">Lịch sử phản ánh mức khớp; chưa chứng minh thay đổi code là nguyên nhân cải thiện. Nhật ký cũ có thể thiếu phiên bản và snapshot dữ liệu.</p>':'<p class="detail-note">Chưa có phiên tương thích để so sánh.</p>');
  }catch(error){if(String(detailRow?.id)===id)$('diagnosticHistory').textContent=error.message;}
}
