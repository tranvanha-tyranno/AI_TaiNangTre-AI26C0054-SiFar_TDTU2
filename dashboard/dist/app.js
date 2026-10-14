const $ = id => document.getElementById(id);
let state = null, selected = '', dataset = 'public', detailRow = null, activeView = 'overview', polling = false;
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const duration = value => value >= 60 ? `${Math.floor(value / 60)}m ${Math.floor(value % 60)}s` : `${Number(value || 0).toFixed(1)}s`;
const modes = {llm:'LLM · OpenRouter', offline:'Offline · Không gọi AI', hybrid:'Hybrid · Cục bộ + LLM', unknown:'Chưa có dữ liệu'};
function notice(message) { $('notice').textContent = message; $('notice').classList.toggle('hidden', !message); }
async function getJSON(url, options) {
  const response = await fetch(url, options); const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Không kết nối được dashboard');
  return data;
}
function view(name) {
  activeView = name; document.querySelectorAll('.view').forEach(el => el.classList.toggle('hidden', el.id !== name));
  document.querySelectorAll('.nav').forEach(el => el.classList.toggle('active', el.dataset.view === name));
  if(name === 'data') loadWorkbook();
}
async function refresh() {
  if(polling) return; polling = true;
  try {
    const qs = new URLSearchParams();
    if(selected) qs.set('run', selected);
    if(dataset) qs.set('dataset', dataset);
    state = await getJSON('/api/state' + (qs.toString() ? '?' + qs.toString() : ''));
    selected = state.selected || '';
    // keep dataset in sync with what server resolved (run's dataset wins)
    if(state.dataset) dataset = state.dataset;
    render(); $('connection').textContent = '● Đã kết nối';
  } catch (error) { $('connection').textContent = 'Mất kết nối'; notice(error.message); }
  finally { polling = false; }
}
function render() {
  const sum = state.summary;
  // dataset dropdowns
  const dsList = state.datasets || [{id:'public',label:'Public_data_1'}];
  const dsOptions = dsList.map(d => `<option value="${escapeHTML(d.id)}">${escapeHTML(d.label)}</option>`).join('');
  ['datasetSelect','datasetDialog'].forEach(id => {
    const el = $(id); if(!el) return;
    el.innerHTML = dsOptions;
    el.value = dataset;
  });
  $('runSelect').innerHTML = state.runs.length ? state.runs.map(run => `<option value="${escapeHTML(run.id)}">${escapeHTML(run.label)} · ${escapeHTML(run.mode)}${run.dataset ? ' · ' + escapeHTML(run.dataset) : ''}</option>`).join('') : '<option>Chưa có lần chạy</option>';
  $('runSelect').value = selected;
  const toolPipeline = sum.pipeline_version === 'tools-v1';
  $('modeBadge').textContent = toolPipeline ? 'LLM + Tools · OpenRouter' : (modes[sum.mode] || sum.mode);
  $('modeBadge').className = 'badge ' + (sum.mode === 'offline' ? 'gray' : '');
  $('runStatus').textContent = state.running ? '● Đang xử lý…' : `${sum.completed} / ${sum.questions} câu đã xử lý`;
  $('answered').innerHTML = `${sum.answered}<span class="denom"> / ${sum.questions}</span>`;
  $('completionText').textContent = `${sum.completed} câu đã xử lý · ${sum.questions - sum.completed} câu đang chờ`;
  $('progressBar').style.width = (100 * sum.completed / Math.max(1,sum.questions)) + '%';
  $('matched').innerHTML = `${sum.matched}<span class="denom"> / ${sum.compared}</span>`;
  $('elapsed').textContent = duration(sum.elapsed_seconds);
  $('average').textContent = sum.completed ? `${(sum.elapsed_seconds / sum.completed).toFixed(2)}s / câu đã xử lý${state.running ? ' · tạm tính' : ''}` : 'Chưa có thời gian';
  $('contextText').textContent = toolPipeline ? 'RAG chọn vùng bảng → LLM gọi công cụ bằng kế hoạch JSON → Python tính trên đủ dữ liệu → kiểm tra và xuất đáp án. Chọn câu để xem từng bước.' : sum.mode === 'offline' ? 'Lần chạy cũ dùng quy tắc Python để đọc và tính dữ liệu. Không có lời gọi LLM.' : 'Nhật ký cũ: LLM trả lời trực tiếp, chưa dùng công cụ. Lần chạy mới dùng pipeline LLM + Tools.';
  const usage=sum.usage;
  if(usage && (usage.api_calls || (sum.mode === 'offline' && usage.cost_complete))) {
    $('costValue').textContent = '$'+usage.actual_cost_usd.toFixed(6)+(usage.cost_complete ? '' : '+');
    $('tokenValue').textContent = `${usage.total_tokens.toLocaleString('vi-VN')} token${usage.tokens_complete ? '' : ' đã ghi nhận'} · ${usage.api_calls} lượt API`;
    $('usageNote').textContent = usage.cost_complete ? 'Chi phí API báo · Đã cộng lượt sửa / retry' : `Chi phí đã xác nhận; ${usage.unknown_cost_calls} lượt chưa rõ phí. Ước tính theo bảng giá: $${usage.estimated_cost_usd.toFixed(6)}`;
  } else {
    $('costValue').textContent='Chưa đo'; $('tokenValue').textContent='Nhật ký cũ không có số liệu API'; $('usageNote').textContent='Không thể coi chi phí chưa ghi nhận là $0.';
  }
  $('openRun').disabled = state.job.running;
  $('openRun').textContent = state.job.running ? 'Đang chạy…' : '＋ Chạy mới';
  const dl = new URLSearchParams(); if(selected) dl.set('run', selected); if(dataset) dl.set('dataset', dataset);
  $('download').href = '/api/download' + (dl.toString() ? '?' + dl.toString() : '');
  $('modelText').textContent = state.config.model;
  $('keyText').textContent = state.config.key_configured ? '● Đã cấu hình khóa API · Không hiển thị khóa trên giao diện' : 'Chưa cấu hình khóa API trong .env';
  const currentFile = $('fileSelect').value;
  $('fileSelect').innerHTML = state.files.map(file => `<option>${escapeHTML(file)}</option>`).join('');
  if(state.files.includes(currentFile)) $('fileSelect').value = currentFile;
  const currentQuestion = $('questionSelect').value;
  const catalog = state.catalog || state.rows;
  $('questionSelect').innerHTML = catalog.map(row => `<option value="${escapeHTML(row.id)}">${escapeHTML(row.id)} · ${escapeHTML(row.query.slice(0,85))}</option>`).join('');
  if(catalog.some(row => String(row.id) === currentQuestion)) $('questionSelect').value = currentQuestion;
  renderRows(); renderPipeline(); renderTestSuites();
}
function statusBadge(row) {
  if(row.status === 'pending') return '<span class="badge gray">Đang chờ</span>';
  if(row.status !== 'ok') return '<span class="badge amber">'+(row.status === 'error' ? 'Lỗi xử lý' : 'Chưa trả lời')+'</span>';
  if(row.match === null) return '<span class="badge gray">Chưa đối chiếu</span>';
  return row.match ? '<span class="badge green">✓ Khớp mẫu</span>' : '<span class="badge red">≠ Khác mẫu</span>';
}
function renderRows() {
  if(!state) return;
  const search = $('search').value.toLowerCase(), filter = $('filter').value;
  const rows = state.rows.filter(row => `${row.id} ${row.file_name} ${row.query} ${row.answer}`.toLowerCase().includes(search))
    .filter(row => filter === 'all' || (filter === 'match' && row.match === true) || (filter === 'mismatch' && row.match === false) || (filter === 'error' && ['error','unanswered'].includes(row.status)));
  $('rowCount').textContent = rows.length;
  $('answerRows').innerHTML = rows.map(row => `<tr data-id="${escapeHTML(row.id)}" tabindex="0" role="button" aria-label="Xem câu ${escapeHTML(row.id)}"><td class="qid">${escapeHTML(row.id)}</td><td class="query-cell"><div class="question">${escapeHTML(row.query)}</div><div class="filename">▤ ${escapeHTML(row.file_name)}</div></td><td class="answer-value">${escapeHTML(row.answer || '—')}</td><td>${statusBadge(row)}</td><td class="duration">${row.elapsed_seconds != null ? duration(row.elapsed_seconds) : '—'}</td><td class="arrow">↗</td></tr>`).join('');
  $('empty').classList.toggle('hidden', !!rows.length);
}
function renderPipeline() {
  if(state.summary.pipeline_version === 'tools-v1') {
    const steps=[['Đọc và chuẩn hóa','Giữ sheet, ô gộp, tọa độ và vùng dữ liệu.'],['RAG tìm bảng','Xếp hạng theo sheet, tiêu đề, cột và nội dung; có vùng toàn sheet.'],['LLM lập kế hoạch','Gọi execute_spreadsheet_plan với JSON theo schema công cụ.'],['Công cụ Python','Lọc, tính tuổi, đếm, tổng, nhóm, ghép và sắp xếp trên đủ dữ liệu.'],['Kiểm tra & sửa','Kiểm tra cột, phạm vi, kiểu dữ liệu và kết quả; tối đa hai lượt sửa kế hoạch.'],['Xuất & ghi nhận','Chuẩn hóa đáp án; lưu ô căn cứ, token và chi phí mọi lượt gọi.']];
    $('pipelineSteps').innerHTML=steps.map((step,index)=>`<div class="step"><div class="step-number">0${index+1}</div><h3>${step[0]}</h3><p>${step[1]}</p></div>`).join('');
    document.querySelector('.future').innerHTML='<span class="badge green">ĐANG SỬ DỤNG</span><h3>LLM chọn thao tác, chương trình thực hiện</h3><p>Kế hoạch được kiểm tra về cấu trúc và khả năng thực thi. Điều này chưa bảo đảm LLM hiểu đúng mọi câu hỏi; đối chiếu dữ liệu và file mẫu để đánh giá độ chính xác.</p>';
    return;
  }
  document.querySelector('.future').innerHTML='<span class="badge amber">NHẬT KÝ CŨ</span><h3>Lần chạy này chưa dùng pipeline công cụ</h3><p>Chạy mới ở chế độ LLM để dùng RAG, kế hoạch JSON, công cụ Python và theo dõi token/chi phí.</p>';
  const mode = state.summary.mode;
  const middle = mode === 'offline' ? ['Quy tắc cục bộ','Nhận diện dạng câu hỏi trong bộ giải hiện có.'] : mode === 'hybrid' ? ['Cục bộ → LLM','Nếu quy tắc chưa trả lời được, gọi LLM trực tiếp.'] : ['LLM trực tiếp','Gửi văn bản Excel và câu hỏi tới OpenRouter.'];
  const last = mode === 'offline' ? ['Tính toán','Python tra cứu hoặc thực hiện phép tính theo quy tắc.'] : ['Chuẩn hóa đáp án','Làm sạch văn bản trả về; chưa có kiểm chứng tính toán tự động.'];
  const steps = [['Đọc đầu vào','Lấy câu hỏi và file Excel được chỉ định.'],['Đọc Excel','Đọc ô, ô gộp và tiêu đề; LLM nhận văn bản có giới hạn độ dài.'],middle,last];
  $('pipelineSteps').innerHTML = steps.map((step,index) => `<div class="step"><div class="step-number">0${index+1}</div><h3>${step[0]}</h3><p>${step[1]}</p></div>`).join('');
}
function renderTestSuites() {
  const el = $('testSuites'); if(!el || !state.datasets) return;
  const suites = state.datasets.filter(d => d.kind === 'test');
  if(!suites.length) { el.innerHTML = '<p class="tiny-note" style="grid-column:1/-1">Chưa có suite nào trong Test/. Chạy <code>python scripts/gen_test_suites.py</code></p>'; return; }
  const blurbs = {
    '01_smoke_replica':'Smoke 3 câu · merged header + fiscal Yes/No · kiểm tra I/O',
    '02_merged_hierarchy':'Ô gộp & tiêu đề 2-3 dòng · flatten header',
    '03_multisheet_multitable':'Nhiều sheet & nhiều bảng trên 1 sheet',
    '04_robustness':'CSV quoting, ô rỗng, ID trùng, traversal',
    '05_truncation_perf':'500 dòng · cắt 60/40 · hiệu năng',
  };
  el.innerHTML = suites.map(s => `<div class="step" style="cursor:pointer" data-dataset="${escapeHTML(s.id)}"><div class="step-number">▦</div><h3>${escapeHTML(s.id)}</h3><p>${escapeHTML(blurbs[s.id] || s.label)}</p><p style="margin-top:8px"><span class="badge gray">${escapeHTML(s.id)}</span> <span style="font-size:10px;color:#7a8392">${escapeHTML(s.xlsx_dir.split('/').slice(-2).join('/'))}</span></p></div>`).join('');
  el.querySelectorAll('[data-dataset]').forEach(card => card.onclick = () => { dataset = card.dataset.dataset; selected=''; refresh(); });
}
function detail(id) {
  detailRow = state.rows.find(row => String(row.id) === id); if(!detailRow) return;
  $('detailId').textContent = `${detailRow.id} / ${detailRow.file_name}`;
  $('detailQuestion').textContent = detailRow.query;
  $('detailAnswer').textContent = detailRow.answer || 'Chưa có đáp án';
  $('detailReference').textContent = detailRow.reference ?? 'Không có';
  const stage = {llm_direct:'Gọi LLM trực tiếp (cũ)', deterministic:'Bộ quy tắc Python (cũ)',parse:'Đọc Excel',retrieve:'Tìm bảng',plan:'LLM lập kế hoạch',execute:'Thực hiện công cụ',validated:'Đã kiểm tra kế hoạch và thực hiện công cụ'}[detailRow.stage] || 'Chưa xử lý';
  $('detailMeta').innerHTML = `${statusBadge(detailRow)}<br>Nhánh xử lý: ${escapeHTML(stage)}<br>Thời gian: ${duration(detailRow.elapsed_seconds)}${detailRow.error_type ? '<br>Loại lỗi: '+escapeHTML(detailRow.error_type) : ''}`;
  const usage=detailRow.usage;
  if(usage) $('detailMeta').innerHTML += `<br>Token vào / ra: ${usage.prompt_tokens} / ${usage.completion_tokens} · ${usage.api_calls} lượt API<br>Chi phí API báo: $${usage.actual_cost_usd.toFixed(6)}${usage.cost_complete ? '' : ' (chưa đủ)'} · Ước tính bảng giá: $${usage.estimated_cost_usd.toFixed(6)}`;
  const operations={read:'Đọc vùng bảng',cell:'Lấy giá trị ô',concat:'Nối các vùng',collect:'Gom đáp án',unpivot:'Chuyển cột thành dòng',filter:'Lọc dòng',derive:'Tính cột mới',sort:'Sắp xếp',take:'Lấy vị trí',select:'Chọn cột',aggregate:'Tính tổng hợp',group:'Nhóm dữ liệu',join:'Ghép bảng',calculate:'Tính kết quả'};
  let html='';
  if(detailRow.retrieval) html += '<h3 class="detail-section">Vùng dữ liệu đã tìm</h3><div class="evidence">'+detailRow.retrieval.filter(r=>r.selected).map(r=>`<span>${escapeHTML(r.sheet)}!${escapeHTML(r.range)}</span>`).join('')+'</div>';
  if(detailRow.tool_trace) html += '<h3 class="detail-section">Công cụ đã thực hiện</h3><div class="tool-trace">'+detailRow.tool_trace.map((step,index)=>`<div><b>${index+1}. ${operations[step.op] || escapeHTML(step.op)}</b><span>${step.row_count != null ? step.row_count+' dòng' : escapeHTML(step.scalar)} · ${duration(step.elapsed_seconds)}</span></div>`).join('')+'</div>';
  if(detailRow.timings) html += '<div class="detail-meta">Thời gian: '+Object.entries(detailRow.timings).map(([key,val])=>`${escapeHTML(key)} ${duration(val)}`).join(' · ')+'</div>';
  if(detailRow.evidence) html += '<h3 class="detail-section">Ô dùng làm căn cứ ('+detailRow.evidence_count+')</h3><div class="evidence">'+detailRow.evidence.slice(0,20).map(cell=>`<span>${escapeHTML(cell)}</span>`).join('')+'</div>';
  if(usage?.calls.length) html += '<h3 class="detail-section">Các lượt gọi API</h3><div class="tool-trace">'+usage.calls.map(call=>`<div><b>#${call.attempt} · ${call.purpose === 'repair' ? 'Sửa kế hoạch' : 'Lập kế hoạch'} · ${escapeHTML(call.status)}</b><span>${call.total_tokens ?? '?'} token · ${call.actual_cost_usd != null ? '$'+call.actual_cost_usd.toFixed(6) : 'Chưa rõ phí'}</span></div>`).join('')+'</div>';
  if(detailRow.validation_errors) html+='<h3 class="detail-section">Lỗi kiểm tra kế hoạch</h3><p class="detail-note">'+detailRow.validation_errors.map(escapeHTML).join('<br>')+'</p>';
  if(detailRow.plan || detailRow.plans) html += '<details class="plan"><summary>Xem kế hoạch JSON</summary><pre>'+escapeHTML(JSON.stringify(detailRow.plan || detailRow.plans,null,2))+'</pre></details>';
  $('toolDetails').innerHTML=html;
  $('detailNote').textContent=detailRow.pipeline_version === 'tools-v1' ? 'Công cụ xử lý toàn bộ vùng được chọn, kể cả dòng không có trong bản xem trước. Kiểm tra kế hoạch hợp lệ chưa bảo đảm chọn đúng ý nghĩa của câu hỏi. File mẫu chưa được xác minh độc lập là đáp án chuẩn.' : 'Nhật ký cũ chưa có kế hoạch công cụ và số liệu sử dụng đầy đủ. Chạy lại với pipeline mới để xem căn cứ tính toán.';
  $('detailDialog').showModal();
}
async function loadWorkbook(sheet) {
  const file = $('fileSelect').value; if(!file) return;
  $('sheetInfo').textContent = 'Đang đọc file Excel…';
  try {
    const qs = new URLSearchParams({file}); if(sheet) qs.set('sheet', sheet); if(dataset) qs.set('dataset', dataset);
    const data = await getJSON('/api/workbook?'+qs.toString());
    $('sheetSelect').innerHTML = data.sheets.map(value => `<option>${escapeHTML(value)}</option>`).join(''); $('sheetSelect').value = data.sheet;
    $('sheetInfo').textContent = `${data.filename} / ${data.sheet} · ${data.total_rows} dòng × ${data.total_columns} cột · ${data.merged.length} vùng ô gộp` + (data.merged.length ? ' · '+data.merged.slice(0,8).join(', ') : '');
    $('workbookTable').innerHTML = '<thead><tr><th>#</th>'+data.columns.map(col => `<th>${col}</th>`).join('')+'</tr></thead><tbody>'+data.rows.map((row,index) => `<tr><td class="row-num">${index+1}</td>${row.map(value => `<td>${escapeHTML(value)}</td>`).join('')}</tr>`).join('')+'</tbody>';
  } catch(error) { $('sheetInfo').textContent = error.message; $('workbookTable').innerHTML = ''; }
}
document.querySelectorAll('.nav').forEach(button => button.onclick = () => view(button.dataset.view));
$('viewPipeline').onclick = () => view('pipeline');
$('refresh').onclick = refresh;
$('datasetSelect').onchange = () => { dataset = $('datasetSelect').value; selected=''; refresh(); };
$('runSelect').onchange = () => { selected = $('runSelect').value; refresh(); };
$('search').oninput = renderRows; $('filter').onchange = renderRows;
$('answerRows').onclick = event => { const row=event.target.closest('tr'); if(row) detail(row.dataset.id); };
$('answerRows').onkeydown = event => {if(event.key === 'Enter') { const row=event.target.closest('tr'); if(row) detail(row.dataset.id); }};
$('closeDetail').onclick = () => $('detailDialog').close();
$('detailData').onclick = () => { $('detailDialog').close(); $('fileSelect').value = detailRow.file_name; view('data'); };
$('fileSelect').onchange = () => loadWorkbook(); $('sheetSelect').onchange = () => loadWorkbook($('sheetSelect').value);
$('openRun').onclick = () => {
  const dsList = state.datasets || []; const sel = $('datasetDialog');
  if(sel) { sel.innerHTML = dsList.map(d => `<option value="${escapeHTML(d.id)}">${escapeHTML(d.label)}</option>`).join(''); sel.value = dataset; }
  $('runDialog').showModal();
};
$('closeRun').onclick = $('cancelRun').onclick = () => $('runDialog').close();
$('datasetDialog').onchange = () => { /* keep preview in sync */ };
$('scope').onchange = () => $('questionSelect').classList.toggle('hidden', $('scope').value === 'all');
$('mode').onchange = () => { $('apiNote').textContent = $('mode').value === 'offline' ? 'Chế độ cũ dùng quy tắc cục bộ, không gọi API. Đây không phải kết quả pipeline LLM.' : 'LLM lập kế hoạch và gọi công cụ. Ghi nhận token/chi phí gồm retry; kiểm tra ngân sách trước mỗi lượt gọi. Tối đa $0.10/câu.'; };
$('runForm').onsubmit = async event => {
  event.preventDefault(); $('submitRun').disabled = true;
  try {
    const chosenDataset = $('datasetDialog').value || dataset;
    const data = await getJSON('/api/run', {method:'POST', headers:{'Content-Type':'application/json','X-Dashboard-Token':state.csrf}, body:JSON.stringify({mode:$('mode').value, dataset: chosenDataset, ids:$('scope').value === 'all' ? null : [$('questionSelect').value]})});
    selected = data.run_id; dataset = chosenDataset; $('runDialog').close(); notice('Đã bắt đầu lần chạy mới. Kết quả sẽ tự cập nhật; dữ liệu các lần trước được giữ lại.'); view('overview'); await refresh();
  } catch(error) { notice(error.message); $('runDialog').close(); }
  finally { $('submitRun').disabled = false; }
};
refresh(); setInterval(refresh,2000);
