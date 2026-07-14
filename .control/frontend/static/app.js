'use strict';

/* ================= API ================= */
const API = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error((await r.json()).error || r.statusText);
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) throw new Error((await r.json()).error || r.statusText);
    return r.json();
  },
};

/* ================= estado global ================= */
const STATE = {
  data: null,
  currentFlowId: null,       // null = raiz del canvas de flujos
  flowBreadcrumb: [],        // pila de {id, nombre}
};

/* ================= mini markdown -> html (solo lo que nosotros generamos) ================= */
function renderMarkdown(md) {
  if (!md) return '<p class="empty-hint">(vacío)</p>';
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  html = html.replace(/^### (.*)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.*)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.*)$/gm, '<h1>$1</h1>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/^- \[[xX]\] (.*)$/gm, '<li style="text-decoration:line-through;color:var(--ink-faint);">$1</li>');
  html = html.replace(/^- \[ \] (.*)$/gm, '<li>$1</li>');
  html = html.replace(/^\d+\. (.*)$/gm, '<li>$1</li>');
  html = html.replace(/^- (.*)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  html = html.split(/\n{2,}/).map(block => {
    if (/^<(h1|h2|h3|ul)/.test(block.trim())) return block;
    if (!block.trim()) return '';
    return `<p>${block.trim()}</p>`;
  }).join('\n');
  return html;
}

function codeRefPills(text) {
  return (text || '').replace(/`([\w./-]+:\d+(?:-\d+)?)`/g, '<span class="code-ref">$1</span>');
}

/* ================= mermaid (carga perezosa) ================= */
let mermaidReady = null;
function ensureMermaid() {
  if (mermaidReady) return mermaidReady;
  mermaidReady = new Promise((resolve) => {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js';
    s.onload = () => { window.mermaid.initialize({ startOnLoad: false, theme: 'neutral' }); resolve(true); };
    s.onerror = () => resolve(false);
    document.head.appendChild(s);
    setTimeout(() => resolve(false), 4000);
  });
  return mermaidReady;
}
async function renderMermaidInto(container, mmdText, id) {
  const ok = await ensureMermaid();
  if (!ok) { container.innerHTML = `<pre style="white-space:pre-wrap;font-size:11px;">${mmdText}</pre>`; return; }
  try {
    const { svg } = await window.mermaid.render(id, mmdText);
    container.innerHTML = svg;
  } catch (e) {
    container.innerHTML = `<pre style="white-space:pre-wrap;font-size:11px;">${mmdText}</pre>`;
  }
}

/* ================= navegación ================= */
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => switchView(el.dataset.view));
});
function switchView(name) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.view === name));
  document.querySelectorAll('.view').forEach(el => el.classList.toggle('active', el.id === 'view-' + name));
  if (name === 'arquitectura') renderArchitectureCanvas();
  if (name === 'flujos') renderFlowsCanvas();
  if (name === 'sesiones') renderSessions();
  if (name === 'decisiones') renderDecisions();
  if (name === 'skills') renderSkills();
  if (name === 'grafo') renderGrafo();
  if (name === 'contexto') renderContexto();
}

/* ================= drawer genérico ================= */
const drawer = document.getElementById('drawer');
const drawerBackdrop = document.getElementById('drawer-backdrop');
function openDrawer({ id, title, bodyHtml, footButtons }) {
  document.getElementById('drawer-id').textContent = id || '';
  document.getElementById('drawer-title').textContent = title || '';
  document.getElementById('drawer-body').innerHTML = bodyHtml || '';
  const foot = document.getElementById('drawer-foot');
  foot.innerHTML = '';
  (footButtons || []).forEach(b => {
    const btn = document.createElement('button');
    btn.className = 'btn ' + (b.cls || 'ghost');
    btn.textContent = b.label;
    btn.onclick = b.onClick;
    foot.appendChild(btn);
  });
  drawer.classList.add('open');
  drawerBackdrop.classList.add('open');
}
function closeDrawer() {
  drawer.classList.remove('open');
  drawerBackdrop.classList.remove('open');
}
document.getElementById('drawer-close').onclick = closeDrawer;
drawerBackdrop.onclick = closeDrawer;

/* ================= modal genérico ================= */
const modalBackdrop = document.getElementById('modal-backdrop');
const modalEl = document.getElementById('modal');
function openModal(html) { modalEl.innerHTML = html; modalBackdrop.classList.add('open'); }
function closeModal() { modalBackdrop.classList.remove('open'); modalEl.innerHTML = ''; }
modalBackdrop.addEventListener('click', (e) => { if (e.target === modalBackdrop) closeModal(); });

/* ================= carga inicial ================= */
API.bootstrap = () => API.get('/api/bootstrap');

async function loadAll() {
  STATE.data = await API.bootstrap();
  renderTopbar();
  renderKanban();
}

function renderTopbar() {
  const d = STATE.data;
  document.getElementById('project-name').textContent =
    (d.meta.project.match(/^#\s*(.+)$/m) || [null, 'Proyecto sin título'])[1];
  const counts = { backlog: 0, in_progress: 0, blocked: 0, done: 0 };
  d.tasks.forEach(t => { counts[t.estado] = (counts[t.estado] || 0) + 1; });
  document.getElementById('pill-backlog').textContent = `backlog ${counts.backlog}`;
  document.getElementById('pill-progress').textContent = `en curso ${counts.in_progress}`;
  document.getElementById('pill-done').textContent = `completas ${counts.done}`;
  const blockedPill = document.getElementById('pill-blocked');
  if (counts.blocked > 0) { blockedPill.style.display = ''; blockedPill.textContent = `bloqueadas ${counts.blocked}`; }
  else blockedPill.style.display = 'none';

  document.getElementById('nav-count-tablero').textContent = d.tasks.length;
  document.getElementById('nav-count-arquitectura').textContent = Object.keys(d.domains).length;
  document.getElementById('nav-count-flujos').textContent = d.flows.length;
  document.getElementById('nav-count-sesiones').textContent = d.sessions.length;
  document.getElementById('nav-count-decisiones').textContent = d.decisions.length;
  const proposedSkills = d.skills.filter(s => s.estado === 'propuesta').length;
  document.getElementById('nav-count-skills').textContent = proposedSkills ? `${proposedSkills} nuevas` : '';
}

document.getElementById('btn-reindex').onclick = async () => {
  await API.post('/api/reindex');
  await loadAll();
};
document.getElementById('btn-validate').onclick = async () => {
  const r = await API.get('/api/validate');
  if (!r.errores.length) { alert('Sin errores.'); return; }
  alert('Errores encontrados:\n\n' + r.errores.join('\n'));
};

/* ================================================================
   TABLERO (kanban)
   ================================================================ */
const KANBAN_COLS = [
  { key: 'backlog', label: 'Backlog' },
  { key: 'in_progress', label: 'En curso' },
  { key: 'blocked', label: 'Bloqueada' },
  { key: 'done', label: 'Completadas' },
];

function renderKanban() {
  const root = document.getElementById('view-tablero');
  root.innerHTML = '';
  KANBAN_COLS.forEach(col => {
    const wrap = document.createElement('div');
    wrap.className = 'kanban-col';
    const tasksInCol = STATE.data.tasks.filter(t => t.estado === col.key)
      .sort((a, b) => prioRank(a.prioridad) - prioRank(b.prioridad));
    wrap.innerHTML = `<div class="ruler"></div><h3>${col.label} <span>${tasksInCol.length}</span></h3>`;
    const drop = document.createElement('div');
    drop.className = 'kanban-drop';
    drop.dataset.estado = col.key;
    tasksInCol.forEach(t => drop.appendChild(taskCard(t)));
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('dragover'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
    drop.addEventListener('drop', async (e) => {
      e.preventDefault(); drop.classList.remove('dragover');
      const tid = e.dataTransfer.getData('text/plain');
      await tryMoveTask(tid, col.key);
    });
    wrap.appendChild(drop);
    if (col.key === 'backlog') {
      const addBtn = document.createElement('div');
      addBtn.className = 'add-card-btn'; addBtn.textContent = '+ nueva tarea';
      addBtn.onclick = openNewTaskModal;
      wrap.appendChild(addBtn);
    }
    root.appendChild(wrap);
  });
}
function prioRank(p) { return { critica: 0, alta: 1, media: 2, baja: 3 }[p] ?? 9; }

function taskCard(t) {
  const card = document.createElement('div');
  card.className = 'task-card';
  card.draggable = true;
  card.innerHTML = `
    <div class="id">${t.id}</div>
    <div class="titulo">${escapeHtml(t.titulo)}</div>
    <div class="badges">
      <span class="badge prio-${t.prioridad}">${t.prioridad}</span>
      <span class="badge">${t.tipo}</span>
      ${t.estado === 'blocked' ? '<span class="badge estado-blocked">bloqueada</span>' : ''}
    </div>`;
  card.addEventListener('dragstart', (e) => e.dataTransfer.setData('text/plain', t.id));
  card.addEventListener('click', () => openTaskDrawer(t.id));
  return card;
}

async function tryMoveTask(tid, nuevoEstado) {
  try {
    let motivo = null, force = null;
    if (nuevoEstado === 'blocked') {
      motivo = prompt('¿Por qué se bloquea esta tarea?');
      if (!motivo) return;
    }
    await API.post(`/api/tasks/${tid}/move`, { estado: nuevoEstado, motivo, force });
    await loadAll();
  } catch (e) {
    if (nuevoEstado === 'done' && /criterios de aceptacion sin marcar/.test(e.message)) {
      if (confirm('Hay criterios de aceptación sin marcar. ¿Forzar de todas formas?')) {
        const motivo = prompt('Motivo del --force:') || 'sin motivo detallado';
        await API.post(`/api/tasks/${tid}/move`, { estado: nuevoEstado, force: motivo });
        await loadAll();
      }
      return;
    }
    alert('No se pudo mover: ' + e.message);
  }
}

async function openTaskDrawer(tid) {
  const full = await API.get(`/api/tasks/${tid}`);
  const d = full.data;
  const criteriosHtml = full.criterios.map((c, i) => `
    <label class="checklist-item">
      <input type="checkbox" data-idx="${i}" ${c.checked ? 'checked' : ''}>
      <span>${escapeHtml(c.texto)}</span>
    </label>`).join('') || '<div class="empty-hint">sin criterios definidos</div>';

  const bodyHtml = `
    <div class="section-label">Estado</div>
    <div class="badges">
      <span class="badge estado-${d.estado}">${d.estado}</span>
      <span class="badge prio-${d.prioridad}">${d.prioridad}</span>
      <span class="badge">${d.tipo}</span>
    </div>
    ${d.bloqueado_por ? `<div class="section-label">Motivo de bloqueo</div><div>${escapeHtml(d.bloqueado_por)}</div>` : ''}
    <div class="section-label">Contexto</div>
    <textarea class="field" id="edit-contexto">${escapeHtml(full.contexto)}</textarea>
    <div class="section-label">Criterios de aceptación</div>
    <div id="edit-criterios">${criteriosHtml}</div>
    <div class="section-label">Notas del agente</div>
    <textarea class="field" id="edit-notas">${escapeHtml(full.notas)}</textarea>
    <div class="section-label">Metadatos</div>
    <div style="font-family:var(--mono);font-size:11px;color:var(--ink-soft);">
      creada ${d.creado} · actualizada ${d.actualizado} · por ${d.creado_por} · asignada a ${d.asignado_a}
    </div>`;

  const moveOptions = { backlog: ['in_progress'], in_progress: ['blocked', 'done', 'backlog'], blocked: ['in_progress'], done: ['in_progress'] };
  const buttons = (moveOptions[d.estado] || []).map(target => ({
    label: `→ ${target}`, cls: target === 'done' ? 'primary' : 'ghost',
    onClick: async () => { await tryMoveTask(tid, target); closeDrawer(); },
  }));
  buttons.push({
    label: 'Guardar cambios', cls: 'primary',
    onClick: async () => {
      const criterios = full.criterios.map((c, i) => ({
        checked: document.querySelector(`#edit-criterios input[data-idx="${i}"]`).checked,
        texto: c.texto,
      }));
      await API.post(`/api/tasks/${tid}/body`, {
        contexto: document.getElementById('edit-contexto').value,
        notas: document.getElementById('edit-notas').value,
        criterios,
      });
      closeDrawer(); await loadAll();
    },
  });

  openDrawer({ id: d.id, title: d.titulo, bodyHtml, footButtons: buttons });
}

function openNewTaskModal() {
  openModal(`
    <h3>Nueva tarea</h3>
    <div class="field-group"><label>Título</label><input class="field" id="m-titulo"></div>
    <div class="field-group"><label>Prioridad</label>
      <select class="field" id="m-prioridad">
        <option value="media" selected>media</option><option value="baja">baja</option>
        <option value="alta">alta</option><option value="critica">critica</option>
      </select></div>
    <div class="field-group"><label>Tipo</label>
      <select class="field" id="m-tipo">
        <option value="feature" selected>feature</option><option value="bug">bug</option>
        <option value="refactor">refactor</option><option value="investigacion">investigacion</option>
        <option value="chore">chore</option>
      </select></div>
    <div class="field-group"><label>Dominio (opcional, para monorepo)</label><input class="field" id="m-dominio" placeholder="ej: productos"></div>
    <div class="actions">
      <button class="btn ghost" id="m-cancel">Cancelar</button>
      <button class="btn primary" id="m-save">Crear</button>
    </div>`);
  document.getElementById('m-cancel').onclick = closeModal;
  document.getElementById('m-save').onclick = async () => {
    const titulo = document.getElementById('m-titulo').value.trim();
    if (!titulo) return;
    await API.post('/api/tasks', {
      titulo,
      prioridad: document.getElementById('m-prioridad').value,
      tipo: document.getElementById('m-tipo').value,
      dominio: document.getElementById('m-dominio').value.trim() || null,
      creado_por: 'usuario',
    });
    closeModal(); await loadAll();
  };
}

function escapeHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/* ================================================================
   MOTOR DE CANVAS INFINITO (reusado por Arquitectura y Flujos)
   ================================================================ */
function createInfiniteCanvas(container) {
  container.innerHTML = '';
  const world = document.createElement('div');
  world.className = 'canvas-world';
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'canvas-svg');
  svg.setAttribute('width', '4000'); svg.setAttribute('height', '4000');
  world.appendChild(svg);
  container.appendChild(world);

  const toolbar = document.createElement('div');
  toolbar.className = 'canvas-toolbar';
  toolbar.innerHTML = `<button class="btn ghost" data-a="zoom-out">−</button>
    <span style="font-family:var(--mono);font-size:11px;" id="zoom-label">100%</span>
    <button class="btn ghost" data-a="zoom-in">+</button>
    <button class="btn ghost" data-a="reset">centrar</button>`;
  container.appendChild(toolbar);

  const cam = { x: 40, y: 40, scale: 1 };
  function applyCam() {
    world.style.transform = `translate(${cam.x}px, ${cam.y}px) scale(${cam.scale})`;
    toolbar.querySelector('#zoom-label').textContent = Math.round(cam.scale * 100) + '%';
  }
  applyCam();

  let panning = false, panStart = null;
  container.addEventListener('mousedown', (e) => {
    if (e.target !== container && e.target !== world && e.target !== svg) return;
    panning = true; panStart = { x: e.clientX - cam.x, y: e.clientY - cam.y };
  });
  window.addEventListener('mousemove', (e) => {
    if (panning) { cam.x = e.clientX - panStart.x; cam.y = e.clientY - panStart.y; applyCam(); redrawEdges(); }
  });
  window.addEventListener('mouseup', () => panning = false);
  container.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.08 : 0.08;
    cam.scale = Math.min(2.2, Math.max(0.35, cam.scale + delta));
    applyCam(); redrawEdges();
  }, { passive: false });

  toolbar.querySelector('[data-a="zoom-in"]').onclick = () => { cam.scale = Math.min(2.2, cam.scale + 0.15); applyCam(); redrawEdges(); };
  toolbar.querySelector('[data-a="zoom-out"]').onclick = () => { cam.scale = Math.max(0.35, cam.scale - 0.15); applyCam(); redrawEdges(); };
  toolbar.querySelector('[data-a="reset"]').onclick = () => { cam.x = 40; cam.y = 40; cam.scale = 1; applyCam(); redrawEdges(); };

  const nodeEls = {};
  const edgeDefs = [];

  function addNode({ id, x, y, html, cls, onDrag, draggable = true }) {
    const el = document.createElement('div');
    el.className = 'node-card ' + (cls || '');
    el.style.left = x + 'px'; el.style.top = y + 'px';
    el.innerHTML = html;
    world.appendChild(el);
    nodeEls[id] = { el, x, y };

    if (draggable) {
      let dragging = false, start = null;
      el.addEventListener('mousedown', (e) => {
        e.stopPropagation();
        dragging = true;
        start = { mx: e.clientX, my: e.clientY, ox: nodeEls[id].x, oy: nodeEls[id].y };
      });
      window.addEventListener('mousemove', (e) => {
        if (!dragging) return;
        const dx = (e.clientX - start.mx) / cam.scale;
        const dy = (e.clientY - start.my) / cam.scale;
        nodeEls[id].x = start.ox + dx; nodeEls[id].y = start.oy + dy;
        el.style.left = nodeEls[id].x + 'px'; el.style.top = nodeEls[id].y + 'px';
        redrawEdges();
      });
      window.addEventListener('mouseup', () => {
        if (dragging && onDrag) onDrag(nodeEls[id].x, nodeEls[id].y);
        dragging = false;
      });
    }
    return el;
  }

  function addEdge(fromId, toId, cls) { edgeDefs.push({ fromId, toId, cls }); redrawEdges(); }

  function redrawEdges() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    edgeDefs.forEach(({ fromId, toId, cls }) => {
      const a = nodeEls[fromId], b = nodeEls[toId];
      if (!a || !b) return;
      const ax = a.x + 110, ay = a.y + 30, bx = b.x + 110, by = b.y + 30;
      const midX = (ax + bx) / 2;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M ${ax} ${ay} C ${midX} ${ay}, ${midX} ${by}, ${bx} ${by}`);
      if (cls) path.setAttribute('class', cls);
      svg.appendChild(path);
    });
  }

  return { addNode, addEdge, redrawEdges, nodeEls };
}

/* ================================================================
   ARQUITECTURA
   ================================================================ */
async function renderArchitectureCanvas() {
  const container = document.getElementById('canvas-arquitectura');
  const canvas = createInfiniteCanvas(container);
  const domains = STATE.data.domains;
  const positions = STATE.data.positions.architecture || {};
  const names = Object.keys(domains);
  if (!names.length) {
    container.innerHTML += '<div class="empty-hint" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);">Todavía no hay dominios documentados. Aparecen acá cuando el agente trabaja en ellos.</div>';
    return;
  }
  names.forEach((name, i) => {
    const pos = positions[name] || { x: 60 + (i % 4) * 260, y: 60 + Math.floor(i / 4) * 160 };
    const r = domains[name];
    const html = `
      <div class="node-id">DOMINIO</div>
      <div class="node-title">${escapeHtml(name)}</div>
      <div class="node-meta">estado: ${r.estado} · ${r.actualizado || '—'}</div>
      <div class="node-actions">
        <button data-a="expand">desplegar</button>
      </div>`;
    const el = canvas.addNode({
      id: name, x: pos.x, y: pos.y, html, cls: 'dominio',
      onDrag: (x, y) => API.post('/api/positions', { seccion: 'architecture', id: name, x, y }),
    });
    el.querySelector('[data-a="expand"]').addEventListener('mousedown', (e) => e.stopPropagation());
    el.querySelector('[data-a="expand"]').addEventListener('click', () => openDomainDrawer(name));
  });
}

async function openDomainDrawer(name) {
  const r = await API.get(`/api/architecture/${name}`);
  let bodyHtml = `<div class="rendered-md">${renderMarkdown(codeRefPills(r.body))}</div>`;
  const mmdMatch = (r.body || '').match(/diagrams\/[\w./-]+\.mmd/);
  bodyHtml += `<div class="section-label">Diagrama</div><div id="domain-diagram">${mmdMatch ? 'cargando...' : '<span class="empty-hint">sin diagrama referenciado</span>'}</div>`;
  openDrawer({ id: 'DOMINIO', title: name, bodyHtml, footButtons: [] });
  if (mmdMatch) {
    try {
      const raw = await fetch('/' + mmdMatch[0]).then(r => r.ok ? r.text() : null);
      if (raw) renderMermaidInto(document.getElementById('domain-diagram'), raw, 'mmd-' + name);
      else document.getElementById('domain-diagram').innerHTML = '<span class="empty-hint">referencia rota</span>';
    } catch (e) { /* noop */ }
  }
}

/* ================================================================
   FLUJOS (canvas infinito con entrada a subflujos)
   ================================================================ */
async function renderFlowsCanvas(flowId = null) {
  STATE.currentFlowId = flowId;
  const container = document.getElementById('canvas-flujos');
  const canvas = createInfiniteCanvas(container);
  renderFlowBreadcrumb(container);

  let currentFlow = null;
  if (flowId) currentFlow = await API.get(`/api/flows/${flowId}`);

  const children = await API.get(`/api/flows?padre=${flowId || ''}`);
  const positions = STATE.data.positions.flows || {};

  let startY = 60;
  if (currentFlow) {
    const html = flowCurrentCardHtml(currentFlow);
    canvas.addNode({ id: '__current__', x: 60, y: 60, html, cls: 'flow current-flow', draggable: false });
    startY = 60; // los hijos se acomodan a la derecha
  }

  const offsetX = currentFlow ? 420 : 60;
  children.forEach((f, i) => {
    const pos = positions[f.id] || { x: offsetX + (i % 3) * 260, y: startY + Math.floor(i / 3) * 170 };
    const html = flowNodeHtml(f);
    const el = canvas.addNode({
      id: f.id, x: pos.x, y: pos.y, html, cls: 'flow',
      onDrag: (x, y) => API.post('/api/positions', { seccion: 'flows', id: f.id, x, y }),
    });
    el.dataset.estado = f.estado;
    el.querySelector('[data-a="entrar"]').addEventListener('mousedown', (e) => e.stopPropagation());
    el.querySelector('[data-a="entrar"]').addEventListener('click', () => enterFlow(f.id, f.nombre));
    el.querySelector('[data-a="desplegar"]').addEventListener('mousedown', (e) => e.stopPropagation());
    el.querySelector('[data-a="desplegar"]').addEventListener('click', () => openFlowDrawer(f.id));
    if (currentFlow) canvas.addEdge('__current__', f.id, 'parent-link');
  });

  if (!currentFlow && !children.length) {
    container.innerHTML += '<div class="empty-hint" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);">Todavía no hay flujos documentados. Se crean cuando un comportamiento cruza más de un dominio.</div>';
  }

  const addBtn = document.createElement('button');
  addBtn.className = 'btn primary';
  addBtn.style.cssText = 'position:absolute;bottom:14px;right:14px;z-index:5;';
  addBtn.textContent = currentFlow ? '+ subflujo aquí' : '+ nuevo flujo';
  addBtn.onclick = () => openNewFlowModal(flowId);
  container.appendChild(addBtn);
}

function flowNodeHtml(f) {
  const dominios = (f.dominios || []).join(', ') || '—';
  return `
    <div class="node-id">${f.id}</div>
    <div class="node-title">${escapeHtml(f.nombre)}</div>
    <div class="node-meta">estado: ${f.estado}</div>
    <div class="node-meta">dominios: ${escapeHtml(dominios)}</div>
    <div class="node-actions">
      <button data-a="entrar">entrar ↳</button>
      <button data-a="desplegar">desplegar</button>
    </div>`;
}

function flowCurrentCardHtml(current) {
  const d = current.data;
  const dominios = (d.dominios || []).join(', ') || '—';
  const secciones = splitSections(current.body);
  return `
    <div class="node-id">${d.id} · actual</div>
    <div class="node-title">${escapeHtml(d.nombre)}</div>
    <div class="node-meta">estado: ${d.estado} · dominios: ${escapeHtml(dominios)}</div>
    <div style="font-size:12px;margin-top:8px;max-height:180px;overflow:auto;">
      ${renderMarkdown(codeRefPills(secciones['Resumen'] || ''))}
    </div>
    <div class="node-actions">
      <button data-a="desplegar-actual">ver todo</button>
    </div>`;
}

function splitSections(body) {
  const out = {}; const re = /^##\s+(.+?)\s*$/gm; let m; const idxs = [];
  while ((m = re.exec(body))) idxs.push({ title: m[1], start: re.lastIndex });
  idxs.forEach((cur, i) => {
    const end = i + 1 < idxs.length ? idxs[i + 1].start - (idxs[i + 1].title.length + 4) : body.length;
    out[cur.title] = body.slice(cur.start, end).trim();
  });
  return out;
}

function renderFlowBreadcrumb(container) {
  const bc = document.createElement('div');
  bc.className = 'breadcrumb';
  const parts = ['<span class="crumb" data-i="-1">Flujos</span>', ...STATE.flowBreadcrumb.map((c, i) => `<span class="sep">/</span><span class="crumb" data-i="${i}">${escapeHtml(c.nombre)}</span>`)];
  bc.innerHTML = parts.join('');
  container.appendChild(bc);
  bc.querySelectorAll('.crumb').forEach(el => {
    el.addEventListener('click', () => {
      const i = parseInt(el.dataset.i, 10);
      if (i === -1) { STATE.flowBreadcrumb = []; renderFlowsCanvas(null); return; }
      STATE.flowBreadcrumb = STATE.flowBreadcrumb.slice(0, i + 1);
      renderFlowsCanvas(STATE.flowBreadcrumb[i].id);
    });
  });
}

function enterFlow(id, nombre) {
  STATE.flowBreadcrumb.push({ id, nombre });
  renderFlowsCanvas(id);
}

async function openFlowDrawer(id) {
  const full = await API.get(`/api/flows/${id}`);
  const secciones = splitSections(full.body);
  const bodyHtml = `
    <div class="badges"><span class="badge estado-${full.data.estado === 'vigente' ? 'in_progress' : full.data.estado === 'desactualizado' ? 'blocked' : ''}">${full.data.estado}</span></div>
    <div class="section-label">Disparador</div><div>${escapeHtml(full.data.disparador || '—')}</div>
    <div class="section-label">Resumen</div><div class="rendered-md">${renderMarkdown(secciones['Resumen'] || '')}</div>
    <div class="section-label">Pasos</div><div class="rendered-md">${renderMarkdown(codeRefPills(secciones['Pasos'] || ''))}</div>
    <div class="section-label">Diagrama</div><div id="flow-diagram">${/diagrams\/flows\//.test(full.body) ? 'cargando...' : '<span class="empty-hint">sin diagrama</span>'}</div>
    <div class="section-label">Dominios relacionados</div><div>${renderMarkdown(secciones['Dominios relacionados'] || '')}</div>
    <div class="section-label">Notas de mantenimiento</div><div class="rendered-md">${renderMarkdown(secciones['Notas de mantenimiento'] || '')}</div>`;

  const buttons = [
    { label: 'Marcar vigente', cls: 'ghost', onClick: async () => { await API.post(`/api/flows/${id}/estado`, { estado: 'vigente' }); closeDrawer(); renderFlowsCanvas(STATE.currentFlowId); } },
    { label: 'Marcar desactualizado', cls: 'danger', onClick: async () => { await API.post(`/api/flows/${id}/estado`, { estado: 'desactualizado' }); closeDrawer(); renderFlowsCanvas(STATE.currentFlowId); } },
    { label: 'Entrar a subflujos', cls: 'primary', onClick: () => { closeDrawer(); enterFlow(id, full.data.nombre); } },
  ];
  openDrawer({ id: full.data.id, title: full.data.nombre, bodyHtml, footButtons: buttons });

  const mmdMatch = full.body.match(/diagrams\/flows\/[\w./-]+\.mmd/);
  if (mmdMatch) {
    const raw = await fetch('/' + mmdMatch[0]).then(r => r.ok ? r.text() : null).catch(() => null);
    if (raw) renderMermaidInto(document.getElementById('flow-diagram'), raw, 'mmd-flow-' + id);
    else document.getElementById('flow-diagram').innerHTML = '<span class="empty-hint">referencia rota</span>';
  }
}

function openNewFlowModal(padreId) {
  openModal(`
    <h3>${padreId ? 'Nuevo subflujo' : 'Nuevo flujo'}</h3>
    <div class="field-group"><label>Nombre</label><input class="field" id="m-nombre"></div>
    <div class="field-group"><label>Dominios que cruza (separados por coma)</label><input class="field" id="m-dominios" placeholder="ej: input, combate, animacion"></div>
    <div class="field-group"><label>Qué lo dispara</label><input class="field" id="m-disparador"></div>
    <div class="actions">
      <button class="btn ghost" id="m-cancel">Cancelar</button>
      <button class="btn primary" id="m-save">Crear</button>
    </div>`);
  document.getElementById('m-cancel').onclick = closeModal;
  document.getElementById('m-save').onclick = async () => {
    const nombre = document.getElementById('m-nombre').value.trim();
    if (!nombre) return;
    const dominios = document.getElementById('m-dominios').value.split(',').map(s => s.trim()).filter(Boolean);
    await API.post('/api/flows', { nombre, dominios, disparador: document.getElementById('m-disparador').value.trim(), padre: padreId });
    closeModal(); await loadAll(); renderFlowsCanvas(padreId);
  };
}

/* ================================================================
   SESIONES / DECISIONES / SKILLS
   ================================================================ */
function renderSessions() {
  const root = document.getElementById('list-sesiones'); root.innerHTML = '';
  if (!STATE.data.sessions.length) { root.innerHTML = '<div class="empty-hint">todavía no hay sesiones registradas</div>'; return; }
  STATE.data.sessions.forEach(s => {
    const row = document.createElement('div'); row.className = 'list-row';
    row.innerHTML = `<span class="id">${s.data.id}</span><span class="titulo">${escapeHtml(s.data.resumen || '')}</span><span class="fecha">${s.data.fecha}</span>`;
    row.onclick = () => openDrawer({
      id: s.data.id, title: s.data.resumen || '(sin resumen)',
      bodyHtml: `<div class="section-label">Agente</div><div>${escapeHtml(s.data.agente || '')}</div>
        <div class="section-label">Tareas tocadas</div><div>${(s.data.tareas_tocadas || []).join(', ') || '—'}</div>
        <div class="section-label">Eventos</div><div class="rendered-md">${renderMarkdown(s.body)}</div>`,
      footButtons: [],
    });
    root.appendChild(row);
  });
}

function renderDecisions() {
  const root = document.getElementById('list-decisiones'); root.innerHTML = '';
  if (!STATE.data.decisions.length) { root.innerHTML = '<div class="empty-hint">todavía no hay decisiones registradas</div>'; }
  STATE.data.decisions.forEach(d => {
    const row = document.createElement('div'); row.className = 'list-row';
    row.innerHTML = `<span class="id">${d.id}</span><span class="titulo">${escapeHtml(d.titulo)}</span><span class="estado-tag ${d.estado}">${d.estado}</span><span class="fecha">${d.fecha}</span>`;
    row.onclick = async () => {
      const r = await API.get(`/api/decisions/${d.id}`);
      const bodyText = r.body.replace(/^---[\s\S]*?---\n/, '');
      openDrawer({ id: d.id, title: d.titulo, bodyHtml: `<div class="rendered-md">${renderMarkdown(bodyText)}</div>`, footButtons: [] });
    };
    root.appendChild(row);
  });
  const addBtn = document.createElement('div');
  addBtn.className = 'add-card-btn'; addBtn.textContent = '+ nueva decisión (ADR)';
  addBtn.onclick = openNewDecisionModal;
  root.appendChild(addBtn);
}

function openNewDecisionModal() {
  openModal(`
    <h3>Nueva decisión (ADR)</h3>
    <div class="field-group"><label>Título</label><input class="field" id="m-titulo"></div>
    <div class="actions"><button class="btn ghost" id="m-cancel">Cancelar</button><button class="btn primary" id="m-save">Crear</button></div>`);
  document.getElementById('m-cancel').onclick = closeModal;
  document.getElementById('m-save').onclick = async () => {
    const titulo = document.getElementById('m-titulo').value.trim();
    if (!titulo) return;
    await API.post('/api/decisions', { titulo });
    closeModal(); await loadAll(); renderDecisions();
  };
}

function renderSkills() {
  const root = document.getElementById('list-skills'); root.innerHTML = '';
  STATE.data.skills.forEach(s => {
    const row = document.createElement('div'); row.className = 'list-row';
    row.innerHTML = `<span class="id">${s.id}</span><span class="titulo">${escapeHtml(s.nombre)} <span style="color:var(--ink-faint);">(${s.tipo})</span></span><span class="estado-tag ${s.estado}">${s.estado}</span>`;
    if (s.estado === 'propuesta') {
      const btn = document.createElement('button');
      btn.className = 'btn primary'; btn.textContent = 'Promover';
      btn.onclick = async (e) => { e.stopPropagation(); await API.post(`/api/skills/${s.id}/promote`); await loadAll(); renderSkills(); };
      row.appendChild(btn);
    }
    root.appendChild(row);
  });
}

/* ================================================================
   GRAFO DE RELACIONES
   ================================================================ */
function renderGrafo() {
  const input = document.getElementById('grafo-input');
  const tree = document.getElementById('grafo-tree');
  tree.innerHTML = '<div class="empty-hint">Ingresá un ID (tarea, flujo, decisión o dominio) y presioná "Grafo"</div>';

  document.getElementById('grafo-btn').onclick = async () => {
    const eid = input.value.trim();
    if (!eid) return;
    tree.innerHTML = '<div class="empty-hint">cargando...</div>';
    const r = await API.get(`/api/graph/${eid}`);
    if (r.error) { tree.innerHTML = `<div class="empty-hint">${escapeHtml(r.error)}</div>`; return; }
    renderGrafoTree(tree, r, 0);
  };

  input.onkeydown = (e) => { if (e.key === 'Enter') document.getElementById('grafo-btn').click(); };
}

function renderGrafoTree(container, r, depth) {
  const e = r.entity;
  if (!e) { container.innerHTML = '<div class="empty-hint">sin datos</div>'; return; }

  let html = `<div class="grafo-root">
    <span class="id">${escapeHtml(e.id)}</span>
    <span class="tipo">${escapeHtml(e.tipo)}</span>
    <span class="titulo">${escapeHtml(e.titulo)}</span>
  </div>`;

  if (r.directo && r.directo.length) {
    html += '<div class="grafo-section">→ Relaciones directas</div>';
    r.directo.forEach(link => {
      html += `<div class="grafo-link" data-id="${escapeHtml(link.id)}">
        <span class="rel">${escapeHtml(link.rel)}</span>
        <span class="id">${escapeHtml(link.id)}</span>
      </div>`;
    });
  }

  if (r.inverso && r.inverso.length) {
    html += '<div class="grafo-section">← Relaciones inversas</div>';
    r.inverso.forEach(link => {
      html += `<div class="grafo-link" data-id="${escapeHtml(link.id)}">
        <span class="rel">${escapeHtml(link.rel)}</span>
        <span class="id">${escapeHtml(link.id)}</span>
      </div>`;
    });
  }

  if (!r.directo.length && !r.inverso.length) {
    html += '<div class="empty-hint">sin relaciones registradas</div>';
  }

  container.innerHTML = html;

  container.querySelectorAll('.grafo-link').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', async () => {
      const id = el.dataset.id;
      const r2 = await API.get(`/api/graph/${id}`);
      if (r2.error) { return; }
      const sub = document.createElement('div');
      sub.className = 'grafo-subtree';
      renderGrafoTree(sub, r2, depth + 1);
      const existing = el.nextElementSibling;
      if (existing && existing.classList.contains('grafo-subtree')) {
        existing.remove();
      } else {
        el.parentNode.insertBefore(sub, el.nextSibling);
      }
    });
  });
}

/* ================================================================
   CONTEXTO
   ================================================================ */
function renderContexto() {
  const ctx = STATE.data.context;
  document.getElementById('contexto-meta').textContent = ctx.data.actualizado
    ? `actualizado ${ctx.data.actualizado} por ${ctx.data.actualizado_por}` : 'todavía no existe CONTEXT.md';
  document.getElementById('contexto-rendered').innerHTML = renderMarkdown(ctx.body);
  document.getElementById('contexto-editor').style.display = 'none';
}
document.getElementById('btn-edit-contexto').onclick = () => {
  document.getElementById('contexto-textarea').value = STATE.data.context.body || '';
  document.getElementById('contexto-editor').style.display = '';
};
document.getElementById('btn-cancel-contexto').onclick = () => { document.getElementById('contexto-editor').style.display = 'none'; };
document.getElementById('btn-save-contexto').onclick = async () => {
  const body = document.getElementById('contexto-textarea').value;
  const r = await API.post('/api/context', { body, actualizado_por: 'usuario' });
  if (r.aviso) alert('Aviso: ' + r.aviso);
  await loadAll(); renderContexto();
};

/* ================================================================
   INIT
   ================================================================ */
loadAll().catch(err => {
  document.getElementById('view-tablero').innerHTML =
    `<div class="empty-hint">No se pudo conectar con el servidor: ${err.message}</div>`;
});
