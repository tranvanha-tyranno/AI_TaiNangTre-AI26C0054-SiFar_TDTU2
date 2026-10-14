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
function datasetList() { return (dataset || 'public').split(',').map(s=>s.trim()).filter(Boolean); }
function datasetLabel(id) {
  const d = (state && state.datasets || []).find(x=>x.id===id);
  return d ? d.label : id;
}
function setDataset(ids) {
  let arr = [...new Set(ids.map(s=>String(s).trim()).filter(Boolean))];
  if(!arr.length) arr = ['public'];
  dataset = arr.join(',');
  selected = '';
  refresh();
}
async function refresh() {
  if(polling) return; polling = true;
  try {
    const qs = new URLSearchParams();
    if(selected) qs.set('run', selected);
    if(dataset) qs.set('dataset', dataset);
    state = await getJSON('/api/state' + (qs.toString() ? '?' + qs.toString() : ''));
    selected = state.selected || '';
    if(state.dataset) dataset = state.dataset;
    render(); $('connection').textContent = '● Đã kết nối';
  } catch (error) { $('connection').textContent = 'Mất kết nối'; notice(error.message); }
  finally { polling = false; }
}
function render() {
  const sum = state.summary;
  const dsList = state.datasets || [{id:'public',label:'Public_data_1'}];
  const chosen = new Set(datasetList());
  // multi picker menu
  const menu = $('datasetMenu');
  if(menu) {
    menu.innerHTML = dsList.map(d => `<label class="multi-option"><input type="checkbox" value="${escapeHTML(d.id)}" ${chosen.has(d.id)?'checked':''}> <span>${escapeHTML(d.label)}</span> <small>${escapeHTML(d.kind||'')}</small></label>`).join('');
    menu.querySelectorAll('input').forEach(cb => cb.onchange = () => {
      const ids = [...menu.querySelectorAll('input:checked')].map(i=>i.value);
      setDataset(ids);
    });
  }
  const btn = $('datasetButton');
  if(btn) {
    const ids = datasetList();
    btn.textContent = ids.length===1 ? datasetLabel(ids[0]) : `${ids.length} dataset · ${ids.join(', ')}`;
  }
  const chips = $('datasetChips');
  if(chips) {
    chips.innerHTML = datasetList().map(id => `<span class="chip">${escapeHTML(id)} <button data-rm="${escapeHTML(id)}" aria-label="Bỏ ${escapeHTML(id)}">×</button></span>`).join('');
    chips.querySelectorAll('[data-rm]').forEach(b=> b.onclick = () => { const ids = datasetList().filter(x=>x!==b.dataset.rm); setDataset(ids); });
  }
  // dialog checks
  const dlg = $('datasetDialog');
  if(dlg) {
    dlg.innerHTML = dsList.map(d => `<label class="multi-option"><input type="checkbox" value="${escapeHTML(d.id)}" ${chosen.has(d.id)?'checked':''}> ${escapeHTML(d.label)}</label>`).join('');
  }
  $('runSelect').innerHTML = state.runs.length ? state.runs.map(run => `<option value="${escapeHTML(run.id)}">${escapeHTML(run.label)} · ${escapeHTML(run.mode)}${run.dataset ? ' · ' + escapeHTML(run.dataset) : ''}</option>`).join('') : '<option>Chưa có lần chạy</option>';
  $('runSelect').value = selected;
  $('modeBadge').textContent = modes[sum.mode] || sum.mode;
  $('modeBadge').className = 'badge ' + (sum.mode === 'offline' ? 'gray' : '');
  $('runStatus').textContent = state.running ? '● Đang xử lý…' : `${sum.completed} / ${sum.questions} câu đã xử lý`;
  $('answered').innerHTML = `${sum.answered}<span class="denom"> / ${sum.questions}</span>`;
  $('completionText').textContent = `${sum.completed} câu đã xử lý · ${sum.questions - sum.completed} câu đang chờ`;
  $('progressBar').style.width = (100 * sum.completed / Math.max(1,sum.questions)) + '%';
  $('matched').innerHTML = `${sum.matched}<span class="denom"> / ${sum.compared}</span>`;
  $('elapsed').textContent = duration(sum.elapsed_seconds);
  $('average').textContent = sum.completed ? `${(sum.elapsed_seconds / sum.completed).toFixed(2)}s / câu đã xử lý${state.running ? ' · tạm tính' : ''}` : 'Chưa có thời gian';
  $('contextText').textContent = sum.mode === 'offline' ? 'Lần chạy này dùng quy tắc Python để đọc và tính dữ liệu. Không có lời gọi LLM.' : sum.mode === 'hybrid' ? 'Hybrid thử quy tắc cục bộ trước. Chỉ câu chưa giải được mới gọi LLM; xem chi tiết từng câu.' : 'Lần chạy này gọi LLM trực tiếp. RAG và kế hoạch JSON chưa được triển khai; đáp án cần đối chiếu.';
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
  const chosen = new Set(datasetList());
  el.innerHTML = suites.map(s => `<div class="step ${chosen.has(s.id)?'active':''}" style="cursor:pointer" data-dataset="${escapeHTML(s.id)}"><div class="step-number">${chosen.has(s.id)?'✓':'▦'}</div><h3>${escapeHTML(s.id)}</h3><p>${escapeHTML(blurbs[s.id] || s.label)}</p><p style="margin-top:8px"><span class="badge ${chosen.has(s.id)?'green':'gray'}">${chosen.has(s.id)?'Đang chọn':'Chưa chọn'}</span></p></div>`).join('');
  el.querySelectorAll('[data-dataset]').forEach(card => card.onclick = () => {
    const id = card.dataset.dataset;
    const ids = datasetList();
    if(ids.includes(id)) setDataset(ids.filter(x=>x!==id));
    else setDataset([...ids, id]);
  });
}
function detail(id) {
  detailRow = state.rows.find(row => String(row.id) === id); if(!detailRow) return;
  $('detailId').textContent = `${detailRow.id} / ${detailRow.file_name}`;
  $('detailQuestion').textContent = detailRow.query;
  $('detailAnswer').textContent = detailRow.answer || 'Chưa có đáp án';
  $('detailReference').textContent = detailRow.reference ?? 'Không có';
  const stage = {llm_direct:'Gọi LLM trực tiếp', deterministic:'Bộ quy tắc Python'}[detailRow.stage] || 'Chưa xử lý';
  $('detailMeta').innerHTML = `${statusBadge(detailRow)}<br>Nhánh xử lý: ${escapeHTML(stage)}<br>Thời gian: ${duration(detailRow.elapsed_seconds)}${detailRow.error_type ? '<br>Loại lỗi: '+escapeHTML(detailRow.error_type) : ''}`;
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
$('runSelect').onchange = () => { selected = $('runSelect').value; refresh(); };
$('search').oninput = renderRows; $('filter').onchange = renderRows;
$('answerRows').onclick = event => { const row=event.target.closest('tr'); if(row) detail(row.dataset.id); };
$('answerRows').onkeydown = event => {if(event.key === 'Enter') { const row=event.target.closest('tr'); if(row) detail(row.dataset.id); }};
$('closeDetail').onclick = () => $('detailDialog').close();
$('detailData').onclick = () => { $('detailDialog').close(); $('fileSelect').value = detailRow.file_name; view('data'); };
$('fileSelect').onchange = () => loadWorkbook(); $('sheetSelect').onchange = () => loadWorkbook($('sheetSelect').value);
$('datasetButton').onclick = () => { const m=$('datasetMenu'); const open=m.classList.contains('hidden'); m.classList.toggle('hidden', !open); $('datasetButton').setAttribute('aria-expanded', open?'false':'true'); };
document.addEventListener('click', e=>{ const picker=$('datasetPicker'); if(picker && !picker.contains(e.target)) { $('datasetMenu').classList.add('hidden'); $('datasetButton').setAttribute('aria-expanded','false'); }});
$('clearDatasets').onclick = () => setDataset(['public']);
$('openRun').onclick = () => {
  // sync dialog checks with current selection
  const chosen = new Set(datasetList());
  const dlg = $('datasetDialog'); if(dlg) dlg.querySelectorAll('input').forEach(cb=> cb.checked = chosen.has(cb.value));
  $('runDialog').showModal();
};
$('closeRun').onclick = $('cancelRun').onclick = () => $('runDialog').close();
$('scope').onchange = () => $('questionSelect').classList.toggle('hidden', $('scope').value === 'all');
$('mode').onchange = () => { $('apiNote').textContent = $('mode').value === 'offline' ? 'Chế độ này dùng quy tắc cục bộ và không gọi API. Đây không phải kết quả LLM.' : 'Chạy LLM có thể phát sinh phí API. Chưa có bộ giới hạn chi phí tự động. Mỗi lần chạy được lưu riêng.'; };
$('runForm').onsubmit = async event => {
  event.preventDefault(); $('submitRun').disabled = true;
  try {
    const chosenDataset = [...$('datasetDialog').querySelectorAll('input:checked')].map(i=>i.value).join(',') || dataset;
    const data = await getJSON('/api/run', {method:'POST', headers:{'Content-Type':'application/json','X-Dashboard-Token':state.csrf}, body:JSON.stringify({mode:$('mode').value, dataset: chosenDataset, ids:$('scope').value === 'all' ? null : [$('questionSelect').value]})});
    selected = data.run_id; dataset = chosenDataset; $('runDialog').close(); notice('Đã bắt đầu lần chạy mới. Kết quả sẽ tự cập nhật; dữ liệu các lần trước được giữ lại.'); view('overview'); await refresh();
  } catch(error) { notice(error.message); $('runDialog').close(); }
  finally { $('submitRun').disabled = false; }
};
refresh(); setInterval(refresh,2000);
