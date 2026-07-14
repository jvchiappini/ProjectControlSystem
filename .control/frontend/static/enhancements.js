'use strict';

/* ================================================================
   MEJORAS: SSE en tiempo real, atajos de teclado, filtros,
   editor dividido, búsqueda rápida.
   ================================================================ */

/* ---- 1. SSE en tiempo real ---- */
let _eventSource = null;

function connectSSE() {
  if (_eventSource) {
    _eventSource.close();
  }
  _eventSource = new EventSource('/api/events');
  _eventSource.onmessage = function (e) {
    try {
      const ev = JSON.parse(e.data);
      handleEvent(ev);
    } catch (_) { /* ignorar */ }
  };
  _eventSource.onerror = function () {
    // reconectar tras 3s
    setTimeout(connectSSE, 3000);
  };
}

function handleEvent(ev) {
  // Recargar datos cuando algo cambia
  const recargar = ['task-created', 'task-moved', 'task-body-edited',
    'flow-created', 'flow-status-changed', 'flow-body-edited',
    'arch-touched', 'arch-body-edited',
    'decision-created', 'decision-body-edited',
    'session-started', 'session-event', 'session-closed',
    'skill-proposed', 'skill-promoted',
    'reindex',
  ];
  if (recargar.includes(ev.type)) {
    loadAll();
  }
}

/* ---- 2. Atajos de teclado ---- */
document.addEventListener('keydown', function (e) {
  // No activar si el focus está en un input/textarea
  const tag = document.activeElement && document.activeElement.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

  if (e.key === 'n' || e.key === 'N') {
    e.preventDefault();
    // Abrir modal de nueva tarea
    if (typeof openNewTaskModal === 'function') openNewTaskModal();
  }
  if (e.key === '/' && !e.ctrlKey) {
    e.preventDefault();
    const input = document.querySelector('#grafo-input');
    if (input) {
      input.focus();
      input.select();
    }
  }
  if (e.key === 'r' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    loadAll();
  }
  if (e.key === '1') { e.preventDefault(); switchView('tablero'); }
  if (e.key === '2') { e.preventDefault(); switchView('arquitectura'); }
  if (e.key === '3') { e.preventDefault(); switchView('flujos'); }
  if (e.key === '4') { e.preventDefault(); switchView('sesiones'); }
  if (e.key === '5') { e.preventDefault(); switchView('decisiones'); }
  if (e.key === '6') { e.preventDefault(); switchView('skills'); }
});

/* ---- 3. Filtros en kanban ---- */
function injectKanbanFilters() {
  const root = document.getElementById('view-tablero');
  if (!root) return;
  const filterBar = document.createElement('div');
  filterBar.className = 'kanban-filters';
  filterBar.innerHTML = `
    <label>Filtrar: </label>
    <select id="filter-prioridad">
      <option value="">todas</option>
      <option value="baja">baja</option>
      <option value="media">media</option>
      <option value="alta">alta</option>
      <option value="critica">critica</option>
    </select>
    <select id="filter-tipo">
      <option value="">todos</option>
      <option value="feature">feature</option>
      <option value="bug">bug</option>
      <option value="refactor">refactor</option>
      <option value="investigacion">investigacion</option>
      <option value="chore">chore</option>
    </select>
    <input id="filter-texto" placeholder="buscar en título..." style="padding:4px 8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-alt);color:var(--ink);font-size:12px;">
    <button class="btn ghost" id="filter-clear" style="font-size:11px;">limpiar</button>
  `;
  root.insertBefore(filterBar, root.firstChild);

  function applyFilter() {
    const prio = document.getElementById('filter-prioridad').value;
    const tipo = document.getElementById('filter-tipo').value;
    const texto = document.getElementById('filter-texto').value.toLowerCase();
    const cards = root.querySelectorAll('.task-card');
    cards.forEach(function (card) {
      const tid = card.querySelector('.id')?.textContent || '';
      const tarea = STATE.data.tasks.find(function (t) { return t.id === tid; });
      if (!tarea) { card.style.display = ''; return; }
      const matchPrio = !prio || tarea.prioridad === prio;
      const matchTipo = !tipo || tarea.tipo === tipo;
      const matchTexto = !texto || (tarea.titulo || '').toLowerCase().includes(texto);
      card.style.display = (matchPrio && matchTipo && matchTexto) ? '' : 'none';
    });
    // Show/hide column add buttons
    root.querySelectorAll('.kanban-col').forEach(function (col) {
      const visibleCards = col.querySelectorAll('.task-card[style*="display: none"]');
      const totalCards = col.querySelectorAll('.task-card').length;
      const addBtn = col.querySelector('.add-card-btn');
      if (addBtn) {
        addBtn.style.display = (visibleCards.length === totalCards) ? 'none' : '';
      }
    });
  }

  document.getElementById('filter-prioridad').onchange = applyFilter;
  document.getElementById('filter-tipo').onchange = applyFilter;
  document.getElementById('filter-texto').oninput = applyFilter;
  document.getElementById('filter-clear').onclick = function () {
    document.getElementById('filter-prioridad').value = '';
    document.getElementById('filter-tipo').value = '';
    document.getElementById('filter-texto').value = '';
    applyFilter();
  };
}

/* ---- 4. Editor dividido (preview en vivo) en task drawer ---- */
// Modifica el openTaskDrawer para agregar preview en vivo
const _origOpenTaskDrawer = window.openTaskDrawer;
if (_origOpenTaskDrawer) {
  window.openTaskDrawer = async function (tid) {
    // Llamar al original primero para abrir el drawer
    await _origOpenTaskDrawer(tid);

    // Agregar botón "Preview" en el drawer si hay textareas
    const drawerBody = document.getElementById('drawer-body');
    if (!drawerBody) return;
    const textareas = drawerBody.querySelectorAll('textarea');
    if (!textareas.length) return;

    // Botón toggle preview
    const previewBtn = document.createElement('button');
    previewBtn.className = 'btn ghost';
    previewBtn.textContent = '📄 Vista previa';
    previewBtn.style.cssText = 'position:absolute;top:40px;right:40px;z-index:10;font-size:11px;';
    previewBtn.onclick = function () {
      const existingPreview = drawerBody.querySelector('.live-preview');
      if (existingPreview) {
        existingPreview.remove();
        previewBtn.textContent = '📄 Vista previa';
        return;
      }
      const preview = document.createElement('div');
      preview.className = 'live-preview';
      preview.style.cssText = 'position:absolute;top:70px;right:40px;width:45%;max-height:60%;overflow:auto;background:var(--bg-alt);border:1px solid var(--border);border-radius:8px;padding:12px;z-index:10;font-size:13px;';
      preview.innerHTML = '<div class="section-label">Preview</div><div class="rendered-md"></div>';
      drawerBody.appendChild(preview);
      previewBtn.textContent = '✕ Cerrar preview';

      // Actualizar preview al escribir
      const renderPreview = function () {
        const mdDiv = preview.querySelector('.rendered-md');
        if (!mdDiv) return;
        const combined = Array.from(drawerBody.querySelectorAll('textarea')).map(function (ta) {
          return ta.value;
        }).join('\n\n');
        mdDiv.innerHTML = renderMarkdown(combined);
      };
      textareas.forEach(function (ta) { ta.addEventListener('input', renderPreview); });
      renderPreview();
    };
    drawerBody.appendChild(previewBtn);
  };
}

/* ---- 5. Skills: click para ver markdown completo ---- */
const _origRenderSkills = window.renderSkills;
if (_origRenderSkills) {
  window.renderSkills = function () {
    _origRenderSkills();
    document.querySelectorAll('#list-skills .list-row').forEach(function (row) {
      const idEl = row.querySelector('.id');
      if (!idEl) return;
      const sid = idEl.textContent.trim();
      row.style.cursor = 'pointer';
      row.onclick = async function () {
        try {
          const url = '/api/skills/' + sid;
          console.log('[skill click] fetching', url);
          const r = await API.get(url);
          const rendered = r.body
            ? '<div class="rendered-md">' + renderMarkdown(r.body) + '</div>'
            : '<div class="empty-hint">(sin contenido markdown)</div>';
          const metaHtml = r.data ? '<div style="font-family:var(--mono);font-size:11px;color:var(--ink-faint);margin-bottom:12px;">' +
            'tipo: ' + escapeHtml(r.data.tipo) + ' · estado: ' + escapeHtml(r.data.estado) + ' · disparador: ' + escapeHtml(r.data.disparador || '—') +
            '</div>' : '';
          openDrawer({
            id: sid,
            title: (r.data && r.data.nombre) || sid,
            bodyHtml: metaHtml + rendered,
            footButtons: [],
          });
        } catch (e) {
          alert('Error al cargar skill: ' + e.message);
        }
      };
    });
  };
}

/* ---- 6. Inicialización ---- */
// Esperar a que loadAll esté lista y conectar SSE
const _origLoadAll = window.loadAll;
if (_origLoadAll) {
  window.loadAll = async function () {
    await _origLoadAll();
    // Inyectar filtros si no están
    if (!document.querySelector('.kanban-filters')) {
      injectKanbanFilters();
    }
  };
}

// Conectar SSE al cargar
document.addEventListener('DOMContentLoaded', function () {
  connectSSE();
  // Nota: los filtros se inyectan en el primer loadAll()
});

// Si ya se cargó, conectar
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  connectSSE();
}
