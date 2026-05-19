// 真需求研判 App — single-page UI.
// State machine: input → running → result. SSE for progress.

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ---------- health ----------
fetch('/api/health').then(r => r.json()).then(j => {
  const el = $('#health');
  if (j.anthropic_key) {
    el.innerHTML = '<span class="badge-ok">● Anthropic key 已配置</span>';
  } else {
    el.innerHTML = '<span class="badge-warn">● 未设 ANTHROPIC_API_KEY — LLM 面板将跳过</span>';
  }
});

// ---------- view switching ----------
function showView(id) {
  $$('.view').forEach(v => v.classList.remove('active'));
  $(`#${id}`).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---------- form submit ----------
$('#form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const idea = $('#idea').value.trim();
  const locale = $('#locale').value;
  const mode = $('#mode').value || null;
  if (!idea) return;

  $('#running-idea').textContent = idea;
  $('#running-title').textContent = `${locale} · ${mode || 'auto'}`;
  $('#phases').innerHTML = '';
  showView('view-running');

  const resp = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idea, locale, mode })
  });
  const { job_id, stream } = await resp.json();
  subscribeStream(stream, job_id);
});

// ---------- SSE ----------
function subscribeStream(streamUrl, jobId) {
  const es = new EventSource(streamUrl);
  const phaseRows = new Map();

  es.addEventListener('status', (ev) => {
    const data = JSON.parse(ev.data);
    addPhase('init', '启动', data.msg || '', 'done', null);
  });

  es.addEventListener('phase', (ev) => {
    const data = JSON.parse(ev.data);
    upsertPhase(data, phaseRows);
  });

  es.addEventListener('done', async (ev) => {
    es.close();
    const res = await fetch(`/api/result/${jobId}`);
    const result = await res.json();
    renderResult(result);
  });

  es.addEventListener('error', (ev) => {
    try {
      const data = JSON.parse(ev.data || '{}');
      addPhase('error', 'error', data.message || '未知错误', 'failed', null);
    } catch {
      addPhase('error', 'error', '连接中断', 'failed', null);
    }
  });

  es.onerror = () => {/* normal close */};
}

function upsertPhase(data, rows) {
  const key = data.phase;
  let li = rows.get(key);
  if (!li) {
    li = document.createElement('li');
    li.dataset.phase = key;
    li.innerHTML = `
      <span class="marker"></span>
      <span><span class="phase-name">${key}</span> · <span class="phase-detail"></span></span>
      <span class="phase-time"></span>
      <span class="phase-extra"></span>
    `;
    $('#phases').appendChild(li);
    rows.set(key, li);
  }
  const marker = li.querySelector('.marker');
  const detail = li.querySelector('.phase-detail');
  const time = li.querySelector('.phase-time');
  const extra = li.querySelector('.phase-extra');

  marker.className = 'marker ' + (data.status || '');
  detail.textContent = describePhase(data);
  if (data.elapsed != null) {
    time.textContent = `${data.elapsed.toFixed(1)}s`;
  }
  if (data.failed_subs && data.failed_subs.length) {
    extra.textContent = `failed: ${data.failed_subs.join(', ')}`;
    extra.style.color = 'var(--warn)';
  }
}

function describePhase(data) {
  const p = data.phase;
  if (data.status === 'running') return '运行中…';
  if (p === 'detect' && data.decision) {
    return `mode=${data.decision.mode} (${data.decision.via}${data.decision.rationale ? ' · ' + data.decision.rationale : ''})`;
  }
  if (p === 'collect_reddit') return `posts=${data.posts || 0} comments=${data.comments || 0}`;
  if (p === 'collect_hn')     return `stories=${data.stories || 0} comments=${data.comments || 0}`;
  if (p === 'clean')          return `raw_voice=${data.raw_voice_count || 0} · ${Object.entries(data.by_source || {}).map(([k, v]) => `${k}:${v}`).join(' ')}`;
  if (data.via)               return `via=${data.via}`;
  return '完成';
}

function addPhase(key, label, detail, status, time) {
  const li = document.createElement('li');
  li.innerHTML = `
    <span class="marker ${status}"></span>
    <span><span class="phase-name">${label}</span> · <span class="phase-detail">${escapeHtml(detail || '')}</span></span>
    <span class="phase-time">${time || ''}</span>
    <span></span>`;
  $('#phases').appendChild(li);
}

// ---------- result rendering ----------
function renderResult(r) {
  const v = r.verdict || {};
  const counts = v.evidence_counts || {};
  $('#verdict-eyebrow').textContent = `${r.mode} · ${r.locale} · idea: ${r.idea}`;
  $('#verdict-headline').textContent = v.one_line || '(无 verdict)';
  $('#verdict-oneline').textContent = v.missing_layers && v.missing_layers.length
    ? `缺失层: ${v.missing_layers.join(' · ')}`
    : '所有关键层均已采集。';

  const pills = $('#verdict-pills');
  pills.innerHTML = '';
  pills.appendChild(statusPill(v.status));
  for (const [k, n] of Object.entries(counts)) {
    if (k === 'by_source' || k === 'by_category') continue;
    pills.appendChild(metaPill(`${k}: ${n}`));
  }
  for (const pv of (v.panel_verdicts || [])) {
    if (pv.verdict) pills.appendChild(metaPill(`${pv.panel}: ${pv.verdict}`));
  }

  // Render VOC if existing or hybrid
  if (r.voc) {
    renderVoc(r.voc);
    $('#panel-voc').hidden = false;
  } else {
    $('#panel-voc').hidden = true;
  }

  // Render non-stock columns if applicable
  if (r.framework || r.counter || r.qualitative) {
    renderNonStock(r.framework, r.counter, r.qualitative);
    $('#panel-nonstock').hidden = false;
  } else {
    $('#panel-nonstock').hidden = true;
  }

  // Method note
  $('#method-note').innerHTML = buildMethodNote(r);

  // Raw pack
  $('#raw-pack').textContent = JSON.stringify(r.evidence_pack, null, 2);

  showView('view-result');
}

function statusPill(status) {
  const tone = {
    'supported': 'ok',
    'partially_supported': 'partial',
    'weakly_supported': 'weak',
    'insufficient': 'none',
  }[status] || 'none';
  const label = {
    'supported': '真需求',
    'partially_supported': '需求存在 / 证据不全',
    'weakly_supported': '信号矛盾',
    'insufficient': '证据不足',
  }[status] || status;
  const el = document.createElement('span');
  el.className = 'status-pill';
  el.dataset.tone = tone;
  el.textContent = label;
  return el;
}

function metaPill(text) {
  const el = document.createElement('span');
  el.className = 'meta-pill';
  el.textContent = text;
  return el;
}

function renderVoc(voc) {
  $('#voc-thesis').textContent = voc.thesis || '(无 thesis)';
  fillVocCol('voc-pain', voc.top_pain || []);
  fillVocCol('voc-positive', voc.top_positive || []);
  fillVocCol('voc-counter', voc.counter_evidence || []);
}

function fillVocCol(id, rows) {
  const wrap = $(`#${id}`);
  wrap.innerHTML = '';
  if (!rows.length) {
    wrap.innerHTML = '<div class="voc-card"><p class="insight skipped">(无数据)</p></div>';
    return;
  }
  for (const r of rows) {
    const card = document.createElement('div');
    card.className = 'voc-card';
    card.innerHTML = `
      <div class="theme">${escapeHtml(r.theme || '')}</div>
      <blockquote class="quote">${escapeHtml(r.quote_en || '')}</blockquote>
      <p class="insight">${escapeHtml(r.insight || '')}</p>
      <div class="cite">${r.url ? `<a href="${r.url}" target="_blank" rel="noopener">${shortUrl(r.url)}</a>` : ''}${r.score != null ? ` · ${r.score}` : ''}</div>
    `;
    wrap.appendChild(card);
  }
}

function renderNonStock(framework, counter, qualitative) {
  // Framework column
  const fwBody = $('#ns-framework .ns-body');
  fwBody.innerHTML = '';
  if (framework && framework.dimensions && framework.dimensions.length) {
    for (const d of framework.dimensions) {
      const row = document.createElement('div');
      row.className = 'dim-row';
      row.innerHTML = `
        <div class="dim-label">${escapeHtml(d.label || d.key)}</div>
        <div class="dim-score">${d.score != null ? d.score : '—'}/3</div>
        <div class="dim-reasoning">${escapeHtml(d.reasoning || '')}</div>
      `;
      fwBody.appendChild(row);
    }
    const overall = document.createElement('div');
    overall.className = 'overall';
    overall.textContent = `总分 ${framework.overall ?? '—'}/15 · ${framework.verdict || ''}`;
    fwBody.appendChild(overall);
  } else if (framework && framework.via === 'no-llm') {
    fwBody.innerHTML = '<p class="skipped">LLM 未启用,跳过此列。</p>';
  } else {
    fwBody.innerHTML = '<p class="skipped">(无数据)</p>';
  }

  // Counter column
  const cBody = $('#ns-counter .ns-body');
  cBody.innerHTML = '';
  if (counter && counter.items && counter.items.length) {
    for (const item of counter.items) {
      const div = document.createElement('div');
      div.className = 'item';
      div.innerHTML = `
        <div><span class="case-name">${escapeHtml(item.case)}</span><span class="case-year">${escapeHtml(item.year || '')}</span></div>
        <div class="case-detail">${escapeHtml(item.why_failed || '')}</div>
        ${item.shared_premise_with_idea ? `<span class="case-flag">重蹈前提</span><div class="case-detail">${escapeHtml(item.premise_detail || '')}</div>` : ''}
      `;
      cBody.appendChild(div);
    }
    if (counter.premise_repeat_summary) {
      const p = document.createElement('p');
      p.className = 'verdict-line';
      p.textContent = counter.premise_repeat_summary;
      cBody.appendChild(p);
    }
    if (counter.verdict) {
      const v = document.createElement('p');
      v.className = 'verdict-line';
      v.textContent = `结论:${counter.verdict}`;
      cBody.appendChild(v);
    }
  } else if (counter && counter.via === 'no-llm') {
    cBody.innerHTML = '<p class="skipped">LLM 未启用,跳过此列。</p>';
  } else {
    cBody.innerHTML = '<p class="skipped">(无数据)</p>';
  }

  // Qualitative column
  const qBody = $('#ns-qual .ns-body');
  qBody.innerHTML = '';
  if (qualitative && qualitative.strengths && qualitative.strengths.length) {
    qBody.appendChild(listGroup('优势', qualitative.strengths));
    qBody.appendChild(listGroup('劣势', qualitative.weaknesses || []));
    qBody.appendChild(listGroup('创始人话术陷阱', qualitative.founder_pitch_red_flags || []));
    if (qualitative.what_would_change_your_mind) {
      const p = document.createElement('p');
      p.className = 'verdict-line';
      p.textContent = `什么会让我改变看法:${qualitative.what_would_change_your_mind}`;
      qBody.appendChild(p);
    }
    if (qualitative.verdict) {
      const v = document.createElement('p');
      v.className = 'verdict-line';
      v.textContent = `结论:${qualitative.verdict}`;
      qBody.appendChild(v);
    }
    if (qualitative.subjective_disclaimer) {
      const d = document.createElement('p');
      d.className = 'disclaimer';
      d.textContent = qualitative.subjective_disclaimer;
      qBody.appendChild(d);
    }
  } else if (qualitative && qualitative.via === 'no-llm') {
    qBody.innerHTML = '<p class="skipped">LLM 未启用,跳过此列。</p>';
  } else {
    qBody.innerHTML = '<p class="skipped">(无数据)</p>';
  }
}

function listGroup(label, items) {
  const g = document.createElement('div');
  g.className = 'list-group';
  const h = document.createElement('div'); h.className = 'list-h'; h.textContent = label;
  g.appendChild(h);
  const ul = document.createElement('ul');
  for (const it of items) {
    const li = document.createElement('li');
    li.textContent = it;
    ul.appendChild(li);
  }
  g.appendChild(ul);
  return g;
}

function buildMethodNote(r) {
  const v = r.verdict || {};
  const c = v.evidence_counts || {};
  const sources = Object.entries(c.by_source || {}).map(([k, n]) => `${k}:${n}`).join(' · ') || '0';
  const cats = Object.entries(c.by_category || {}).map(([k, n]) => `${k}:${n}`).join(' · ') || '—';
  return `<strong>Method</strong> · target_market = ${r.locale} · mode = ${r.mode}` +
    ` · 来源 ${sources}` +
    ` · 分类 ${cats}` +
    ` · 缺失层 ${(v.missing_layers || []).join(', ') || '无'}`;
}

function shortUrl(url) {
  try {
    const u = new URL(url);
    let path = u.pathname.length > 38 ? u.pathname.slice(0, 35) + '…' : u.pathname;
    return `${u.host}${path}`;
  } catch { return url; }
}

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

$('#new-run').addEventListener('click', () => showView('view-input'));
