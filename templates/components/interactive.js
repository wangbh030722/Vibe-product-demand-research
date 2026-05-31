/* ============================================================
   Category Research Interactive Layer · v1
   Inline this script in each report HTML. Reads inline JSON
   from <script type="application/json" id="report-data">.

   Provides 4 components:
     A. Process Bar (sticky top, scroll-driven active)
     B. Knowledge Graph (force-directed SVG, vanilla)
     C. Filter Bar (chips + search for .drow tables)
     D. What-If panel collapse handlers

   No CDN. No external deps. Self-contained.
   ============================================================ */

(function(){
  'use strict';
  const DATA = JSON.parse(document.getElementById('report-data').textContent);

  /* ============= A. PROCESS BAR =============
     Expects:
       <nav class="process-bar"><div class="pb-inner">
         <a class="pb-step" data-target="#sec-meta">...</a>
         ...5 steps
       </div></nav>
     Each section in body has matching id="sec-meta" / sec-collect / sec-clean / sec-analyze / sec-verdict.
  ============================================= */
  const pbSteps = document.querySelectorAll('.process-bar .pb-step');
  const pbTargets = Array.from(pbSteps).map(s => document.querySelector(s.dataset.target)).filter(Boolean);
  function updatePB() {
    const y = window.scrollY + 100;
    let idx = 0;
    pbTargets.forEach((el, i) => { if (el && el.offsetTop <= y) idx = i; });
    pbSteps.forEach((s, i) => s.classList.toggle('active', i === idx));
  }
  window.addEventListener('scroll', updatePB, { passive: true });
  updatePB();

  /* ============= B. KNOWLEDGE GRAPH =============
     Expects:
       <svg id="kgSvg" viewBox="0 0 760 520"></svg>
       <aside id="kgSide">initial empty state</aside>
     Reads DATA.players, DATA.themes, DATA.voices, DATA.opportunity, DATA.edges.
  ============================================= */
  const svg = document.getElementById('kgSvg');
  if (svg) buildGraph();

  function buildGraph() {
    const W = 760, H = 520;
    const nodes = [];
    DATA.players.forEach(p => nodes.push({...p, kind: 'player'}));
    DATA.themes.forEach(t => nodes.push({...t, kind: 'theme', name: t.label}));
    DATA.voices.forEach(v => nodes.push({
      ...v, name: v.title,
      color: v.sentiment === 'pos' ? '#14532d' : '#c2410c',
      size: 6 + Math.min(8, Math.log10((v.score || 1) + 1) * 2),
      kind: 'voice'
    }));
    if (DATA.opportunity) nodes.push({...DATA.opportunity, kind: 'oppor'});

    nodes.forEach(n => {
      n.px = 60 + n.x * (W - 120);
      n.py = 40 + n.y * (H - 80);
      n.vx = 0; n.vy = 0;
    });

    const edges = DATA.edges
      .map(e => ({source: nodes.find(n => n.id === e.from), target: nodes.find(n => n.id === e.to), weight: e.w}))
      .filter(e => e.source && e.target);

    // Force-directed: 90 iterations
    const REPEL = 1200, SPRING = 0.035, CENTER = 0.008, DAMP = 0.78;
    for (let iter = 0; iter < 90; iter++) {
      // Repulsion (n²)
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = a.px - b.px, dy = a.py - b.py;
          const d2 = dx * dx + dy * dy + 50;
          const d = Math.sqrt(d2);
          const f = REPEL / d2;
          const fx = (dx / d) * f, fy = (dy / d) * f;
          a.vx += fx; a.vy += fy;
          b.vx -= fx; b.vy -= fy;
        }
      }
      // Spring edges
      edges.forEach(e => {
        const dx = e.target.px - e.source.px, dy = e.target.py - e.source.py;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const restLen = 90 / e.weight;
        const f = (d - restLen) * SPRING;
        const fx = (dx / d) * f, fy = (dy / d) * f;
        e.source.vx += fx; e.source.vy += fy;
        e.target.vx -= fx; e.target.vy -= fy;
      });
      // Center pull
      nodes.forEach(n => {
        n.vx += (W / 2 - n.px) * CENTER;
        n.vy += (H / 2 - n.py) * CENTER;
        n.px += n.vx; n.py += n.vy;
        n.vx *= DAMP; n.vy *= DAMP;
        n.px = Math.max(40, Math.min(W - 40, n.px));
        n.py = Math.max(30, Math.min(H - 30, n.py));
      });
    }

    // Render SVG
    const NS = 'http://www.w3.org/2000/svg';
    edges.forEach(e => {
      const l = document.createElementNS(NS, 'line');
      l.setAttribute('x1', e.source.px); l.setAttribute('y1', e.source.py);
      l.setAttribute('x2', e.target.px); l.setAttribute('y2', e.target.py);
      l.setAttribute('class', 'kg-edge');
      l.setAttribute('stroke-width', Math.max(0.6, e.weight * 0.6));
      svg.appendChild(l);
    });

    const nodeMap = new Map();
    nodes.forEach(n => {
      const g = document.createElementNS(NS, 'g');
      g.setAttribute('class', 'kg-node');
      g.setAttribute('transform', `translate(${n.px},${n.py})`);
      const c = document.createElementNS(NS, 'circle');
      c.setAttribute('r', n.size);
      c.setAttribute('fill', n.kind === 'oppor' ? 'transparent' : n.color);
      c.setAttribute('stroke', n.kind === 'oppor' ? '#14532d' : '#fff');
      c.setAttribute('stroke-width', n.kind === 'oppor' ? 2 : 1.5);
      if (n.kind === 'oppor') c.setAttribute('stroke-dasharray', '4 3');
      if (n.kind === 'voice') c.setAttribute('fill-opacity', 0.85);
      g.appendChild(c);
      if (n.kind !== 'voice') {
        const t = document.createElementNS(NS, 'text');
        t.setAttribute('y', n.size + 12);
        t.setAttribute('text-anchor', 'middle');
        t.setAttribute('font-size', n.kind === 'player' ? 11 : 10);
        t.setAttribute('fill', n.kind === 'player' ? '#14171c' : '#5a606a');
        t.textContent = n.name || n.label;
        g.appendChild(t);
      }
      svg.appendChild(g);
      nodeMap.set(n.id, { g, data: n });

      g.addEventListener('mouseenter', () => highlight(n.id));
      g.addEventListener('mouseleave', () => unhighlight());
      g.addEventListener('click', () => showDetail(n));
    });

    function adjacent(id) {
      const adj = new Set([id]);
      edges.forEach(e => {
        if (e.source.id === id) adj.add(e.target.id);
        if (e.target.id === id) adj.add(e.source.id);
      });
      return adj;
    }
    function highlight(id) {
      const adj = adjacent(id);
      nodeMap.forEach((v, k) => {
        v.g.classList.toggle('kg-faded', !adj.has(k));
        v.g.classList.toggle('kg-active', k === id);
      });
      edges.forEach((e, i) => {
        const l = svg.querySelectorAll('.kg-edge')[i];
        const involved = e.source.id === id || e.target.id === id;
        l.classList.toggle('kg-active', involved);
        l.classList.toggle('kg-faded', !involved && !(adj.has(e.source.id) && adj.has(e.target.id)));
      });
    }
    function unhighlight() {
      nodeMap.forEach(v => v.g.classList.remove('kg-faded', 'kg-active'));
      svg.querySelectorAll('.kg-edge').forEach(l => l.classList.remove('kg-faded', 'kg-active'));
    }
    window.kgHighlight = highlight;
    window.kgUnhighlight = unhighlight;
    window._kgNodes = nodes;
  }

  /* ============= Side detail panel =============
     Click handler — renders different templates per kind.
  ============================================= */
  const side = document.getElementById('kgSide');
  function showDetail(n) {
    if (!side) return;
    const tc = n.kind === 'voice' ? 'voice'
              : n.kind === 'theme' ? 'theme'
              : n.kind === 'oppor' ? 'oppor' : 'player';
    const tl = n.kind === 'voice' ? '顶帖 / 评测'
              : n.kind === 'theme' ? ('主题 · ' + (n.polarity === 'win' ? '正面' : n.polarity === 'pain' ? '负面' : '中性'))
              : n.kind === 'oppor' ? '空白机会区'
              : ('玩家 · ' + (n.status || '在售'));
    let html = `<span class="kg-tag ${tc}">${tl}</span><h5>${n.name || n.label}</h5>`;

    if (n.kind === 'voice') {
      const scoreLabel = n.score > 0 ? '▲ ' + n.score.toLocaleString() : '评测/报道';
      html += `<div class="kg-meta">${n.player.toUpperCase()} · ${scoreLabel} · <a href="${n.url}" target="_blank" rel="noopener" style="color:var(--muted);border-bottom:1px solid var(--line);text-decoration:none;">来源 ↗</a></div>`;
      html += `<p style="font-size:13px;color:var(--muted);">在 §2 voice 表查看完整双语原文 + 关键启示。</p>`;
    } else if (n.kind === 'player') {
      html += `<p style="font-size:13px;color:var(--muted);">${n.summary || ''}</p>`;
      const linkedThemes = DATA.themes.filter(t => DATA.edges.find(e => (e.from === n.id && e.to === t.id) || (e.to === n.id && e.from === t.id)));
      const linkedVoices = DATA.voices.filter(v => v.player === n.id);
      if (linkedThemes.length) {
        html += `<div class="kg-related"><div class="kg-related-lbl">关联主题</div>`;
        linkedThemes.forEach(t => { html += `<a href="#" data-jump-node="${t.id}">→ ${t.label}</a>`; });
        html += `</div>`;
      }
      if (linkedVoices.length) {
        html += `<div class="kg-related"><div class="kg-related-lbl">该玩家 ${linkedVoices.length} 条 voice</div>`;
        linkedVoices.forEach(v => {
          const sc = v.score > 0 ? '▲' + v.score.toLocaleString() + ' · ' : '';
          html += `<a href="#" data-jump-node="${v.id}">${sc}${v.title}</a>`;
        });
        html += `</div>`;
      }
    } else if (n.kind === 'theme') {
      html += `<p style="font-size:13px;color:var(--muted);">${n.summary || ''}</p>`;
      const lv = DATA.voices.filter(v => v.themes && v.themes.includes(n.id));
      const lp = DATA.players.filter(p => DATA.edges.find(e => (e.from === p.id && e.to === n.id) || (e.to === p.id && e.from === n.id)));
      if (lp.length) {
        html += `<div class="kg-related"><div class="kg-related-lbl">涉及玩家</div>`;
        lp.forEach(p => { html += `<a href="#" data-jump-node="${p.id}">→ ${p.name}</a>`; });
        html += `</div>`;
      }
      if (lv.length) {
        html += `<div class="kg-related"><div class="kg-related-lbl">证据 (${lv.length})</div>`;
        lv.sort((a, b) => (b.score || 0) - (a.score || 0)).forEach(v => {
          html += `<a href="#" data-jump-node="${v.id}">${v.title}</a>`;
        });
        html += `</div>`;
      }
    } else if (n.kind === 'oppor') {
      html += `<p style="font-size:13px;color:var(--muted);">${n.summary || ''}</p>`;
      html += `<p style="font-size:12px;color:var(--good);margin-top:10px;"><strong>本报告核心战略推荐位置 · 见 §4.2。</strong></p>`;
    }

    side.innerHTML = html;
    side.querySelectorAll('[data-jump-node]').forEach(a => {
      a.addEventListener('click', ev => {
        ev.preventDefault();
        const id = a.dataset.jumpNode;
        const target = window._kgNodes.find(x => x.id === id);
        if (target) { window.kgHighlight(id); showDetail(target); }
      });
    });
  }

  /* ============= C. FILTER BAR =============
     Expects:
       <div class="filter-bar" data-filter-target=".voice-table">
         <button class="filter-chip" data-filter-group="player" data-filter-value="Oura">...</button>
         <input class="filter-search" data-filter-search>
         <span class="filter-count" data-filter-count>N / N</span>
       </div>
       Each .drow has a .sent-dot whose textContent is the player name
       and class includes pos|neg|acq|dead for sentiment.
  ============================================= */
  document.querySelectorAll('.filter-bar').forEach(bar => {
    const target = document.querySelector(bar.dataset.filterTarget);
    if (!target) return;
    const rows = Array.from(target.querySelectorAll('details.drow'));
    const state = { player: 'all', sent: 'all', search: '' };
    const countEl = bar.querySelector('[data-filter-count]');
    const total = rows.length;
    const searchEl = bar.querySelector('[data-filter-search]');

    function apply() {
      let visible = 0;
      const q = state.search.toLowerCase().trim();
      rows.forEach(r => {
        const dot = r.querySelector('.sent-dot');
        const player = dot ? dot.textContent.trim() : '';
        const sc = dot ? Array.from(dot.classList).find(c => ['pos','neg','acq','dead'].includes(c)) : '';
        const sentMatch = state.sent === 'all'
                        || (state.sent === 'pos' && sc === 'pos')
                        || (state.sent === 'neg' && (sc === 'neg' || sc === 'dead' || sc === 'acq'));
        const playerMatch = state.player === 'all' || player.toLowerCase().includes(state.player.toLowerCase());
        const text = r.textContent.toLowerCase();
        const searchMatch = !q || text.includes(q);
        const v = playerMatch && sentMatch && searchMatch;
        r.classList.toggle('fb-hidden', !v);
        r.classList.toggle('fb-match-search', !!q && v);
        if (v) visible++;
      });
      if (countEl) countEl.textContent = visible + ' / ' + total;
    }

    bar.querySelectorAll('.filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const group = chip.dataset.filterGroup;
        bar.querySelectorAll(`.filter-chip[data-filter-group="${group}"]`).forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state[group] = chip.dataset.filterValue;
        apply();
      });
    });
    if (searchEl) {
      searchEl.addEventListener('input', () => { state.search = searchEl.value; apply(); });
    }
  });

  /* ============= D. WHAT-IF PANEL TOGGLE =============
     <button class="whatif-toggle" onclick="this.closest('.whatif-panel').classList.toggle('wi-collapsed')">
     CSS: .whatif-panel.wi-collapsed .whatif-body { display: none; }
     Handler is inline in HTML (above); this block reserves the global hook if needed.
  ============================================= */

  /* ============= KG reset button ============= */
  const resetBtn = document.getElementById('kgReset');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (window.kgUnhighlight) window.kgUnhighlight();
      if (side && side.dataset.original) side.innerHTML = side.dataset.original;
    });
  }
  if (side) side.dataset.original = side.innerHTML;
})();
