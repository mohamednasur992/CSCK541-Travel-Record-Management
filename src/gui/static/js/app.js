/* =====================================================================
   Page logic for the Travel Agent Record Manager.

   The page holds no business rules. Every create, search, update and
   delete goes to the Python bridge (gui/bridge.py) through
   window.pywebview.api, and the page shows what comes back. The design's
   components (custom drop-downs, calendar, city suggestions, toasts,
   dialogs, themes) are kept from design.html; the sample data is
   replaced by the real records.

   Layouts: "expanded" (wide window: list + side panel), "medium" and
   "compact" (narrow window or touch screen: the form opens as a sheet over
   the list, and on compact the record types move to a bottom bar within
   thumb reach). Display preferences (theme, contrast, effects, density,
   panel width) are stored by Python in settings.json.
   ===================================================================== */
'use strict';

(function () {
  const VIEWS = ['Flight', 'Client', 'Airline'];
  const TITLES = { Flight: 'Flights', Client: 'Clients', Airline: 'Airlines' };
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'];
  const PALETTE = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#0EA5E9', '#EC4899', '#14B8A6'];
  const CHECK_SVG = '<svg class="option-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>';
  const CHEVRON_SVG = '<svg class="trigger-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>';

  const state = {
    meta: null,
    view: 'Flight',
    records: { Flight: [], Client: [], Airline: [] },
    results: { Flight: [], Client: [], Airline: [] },
    selected: { Flight: null, Client: null, Airline: null },   // keys
    search: { Flight: { text: '', field: 'All fields' }, Client: { text: '', field: 'All fields' }, Airline: { text: '', field: 'All fields' } },
    sort: { key: 'Date', asc: true },
    choices: { Client: [], Airline: [] },
    nextId: { Client: 1, Airline: 1 },
    summary: null,
    dirty: false,
    date: '',
    busy: false,
    prefs: { theme: 'system', contrast: 'system', effects: 'system', density: 'comfortable', panel_width: 440 },
    undo: null,              // { view, label } while the latest change is an undoable delete
    scroll: {},              // per-view scroll positions, restored when switching back
    sheetOpen: false,
    sheetReturnFocus: null,
  };
  const MQ = {
    compact: window.matchMedia('(max-width: 699.98px)'),
    sheet: window.matchMedia('(max-width: 1099.98px)'),
    dark: window.matchMedia('(prefers-color-scheme: dark)'),
    contrast: window.matchMedia('(prefers-contrast: more)'),
    calm: window.matchMedia('(prefers-reduced-motion: reduce)'),
  };
  const layout = () => (MQ.compact.matches ? 'compact' : MQ.sheet.matches ? 'medium' : 'expanded');
  const sheetMode = () => layout() !== 'expanded';
  const ui = { selects: {}, form: {} };
  let api = null;

  /* ------------------------------------------------------------ utils */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  const sameKey = (a, b) => a !== null && b !== null && JSON.stringify(a) === JSON.stringify(b);
  const pad = (n) => String(n).padStart(2, '0');
  function initials(name) {
    const parts = String(name).trim().split(/\s+/).filter(Boolean);
    return ((parts[0] || '?')[0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
  }
  function colourFor(text) {
    let h = 0;
    for (const ch of String(text)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }
  function debounce(fn, ms) {
    let t = null;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }
  // Flight dates are "YYYY-MM-DD HH:MM"; the calendar works on the date part.
  function parseDate(text) {
    const m = /^(\d{4})-(\d{2})-(\d{2})(?: \d{2}:\d{2})?$/.exec(text || '');
    if (!m) return null;
    const d = new Date(+m[1], +m[2] - 1, +m[3]);
    return d.getMonth() === +m[2] - 1 ? d : null;
  }
  const dateText = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  function niceDate(text) {
    const d = parseDate(text);
    const time = /\d{2}:\d{2}$/.exec(text || '');
    return d ? `${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)} ${d.getFullYear()}${time ? ' · ' + time[0] : ''}` : '';
  }
  function countdown(text) {
    const d = parseDate(text);
    if (!d) return { kind: 'none', text: '' };
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const days = Math.round((d.getTime() - today.getTime()) / 86400000);
    const amount = `${Math.abs(days)} day${Math.abs(days) === 1 ? '' : 's'}`;
    if (days === 0) return { kind: 'future', text: 'Departs today' };
    return days > 0 ? { kind: 'future', text: `Departs in ${amount}` }
      : { kind: 'past', text: `Departed ${amount} ago (past flight)` };
  }
  function announce(message) {
    const el = $('#a11yAnnouncer');
    el.textContent = '';
    setTimeout(() => { el.textContent = message; }, 50);
  }
  function isTyping(el) {
    return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
  }

  /* ----------------------------------------------------------- toasts */
  /** Show a toast. It pauses while hovered or focused; an optional action
      (e.g. Undo) gets a longer time and is also available from the keyboard. */
  function toast(type, title, message = '', { action = null, duration = null } = {}) {
    const box = document.createElement('div');
    const ms = duration || (action ? 10000 : 4000);
    box.className = `toast-card toast-${type}`;
    box.setAttribute('role', type === 'error' ? 'alert' : 'status');
    box.innerHTML = `<div class="toast-content"><span class="toast-title">${esc(title)}</span>` +
      `${message ? `<span class="toast-desc">${esc(message)}</span>` : ''}</div>` +
      (action ? `<button type="button" class="toast-action-btn">${esc(action.label)}</button>` : '') +
      '<button type="button" class="toast-close-btn" aria-label="Dismiss notification">✕</button>' +
      `<div class="toast-progress-bar" style="animation-duration:${ms}ms"></div>`;
    box.querySelector('.toast-close-btn').addEventListener('click', () => box.remove());
    if (action) box.querySelector('.toast-action-btn').addEventListener('click', () => { box.remove(); action.run(); });
    $('#toastContainer').appendChild(box);
    announce(message ? `${title}: ${message}` : title);
    let left = ms;
    let started = Date.now();
    let timer = null;
    const dismiss = () => {
      box.style.opacity = '0';
      box.style.transform = 'translateY(10px)';
      setTimeout(() => box.remove(), 200);
    };
    const resume = () => { started = Date.now(); timer = setTimeout(dismiss, left); box.classList.remove('paused'); };
    const pause = () => { clearTimeout(timer); left -= Date.now() - started; box.classList.add('paused'); };
    box.addEventListener('mouseenter', pause);
    box.addEventListener('mouseleave', resume);
    box.addEventListener('focusin', pause);
    box.addEventListener('focusout', resume);
    resume();
    return box;
  }

  /* ----------------------------------------------------------- dialog */
  let dialogResolve = null;
  let dialogCancelValue = null;
  let dialogReturnFocus = null;
  /** Show a modal dialog; resolves with the value of the button pressed. */
  function dialog({ kind = 'info', title, message = '', html = '', buttons, cancelValue }) {
    if (dialogResolve) dialogResolve(dialogCancelValue);
    const icons = { info: 'i', warning: '!', error: '✕' };
    $('#dialogKind').className = `dialog-kind ${kind}`;
    $('#dialogKind').textContent = icons[kind] || 'i';
    $('#dialogTitle').textContent = title;
    $('#dialogBody').innerHTML = html || `<p class="dialog-message">${esc(message)}</p>`;
    const actions = $('#dialogActions');
    actions.innerHTML = '';
    let focusBtn = null;
    buttons.forEach((b) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = b.style === 'primary' ? 'btn-primary-action' : b.style === 'danger' ? 'btn-danger' : 'btn-secondary';
      btn.textContent = b.label;
      btn.dataset.value = b.value;
      btn.addEventListener('click', () => closeDialog(b.value));
      actions.appendChild(btn);
      if (b.focus) focusBtn = btn;
    });
    dialogCancelValue = cancelValue !== undefined ? cancelValue : buttons[0].value;
    dialogReturnFocus = document.activeElement;
    $('#dialogOverlay').classList.add('open');
    (focusBtn || actions.querySelector('button')).focus();
    return new Promise((resolve) => { dialogResolve = resolve; });
  }
  function closeDialog(value) {
    $('#dialogOverlay').classList.remove('open');
    const resolve = dialogResolve;
    dialogResolve = null;
    if (dialogReturnFocus && dialogReturnFocus.focus) dialogReturnFocus.focus();
    if (resolve) resolve(value);
  }
  const dialogOpen = () => $('#dialogOverlay').classList.contains('open');

  /* --------------------------------------------- custom select widget */
  const openSelects = new Set();
  function makeSelect({ id, ariaLabel, placeholder, compact = false, icon = '', onChange }) {
    const wrap = document.createElement('div');
    wrap.className = `custom-select-wrapper${compact ? ' custom-select-compact' : ''}`;
    wrap.id = `${id}Wrapper`;
    wrap.innerHTML = `<div class="custom-select-trigger" id="${id}" tabindex="0" role="combobox" aria-haspopup="listbox" aria-expanded="false" aria-label="${esc(ariaLabel)}">` +
      `<div class="trigger-val-container"></div>${CHEVRON_SVG}</div>` +
      `<div class="custom-select-menu" role="listbox" aria-label="${esc(ariaLabel)}"></div>`;
    const trigger = wrap.firstChild;
    const display = trigger.firstChild;
    const menu = wrap.lastChild;
    let options = [];
    let value = '';
    let highlighted = -1;

    function renderDisplay() {
      const opt = options.find((o) => String(o.value) === String(value));
      display.innerHTML = opt ? icon + optionLeft(opt, true) : `${icon}<span class="placeholder-text">${esc(placeholder)}</span>`;
    }
    function optionLeft(o, compactDisplay = false) {
      const art = o.avatar ? `<div class="option-avatar" style="background:${o.color}">${esc(o.avatar)}</div>`
        : o.badge ? `<span class="option-airline-badge" style="background:${o.color}22; color:${o.color}">${esc(o.badge)}</span>` : '';
      if (compactDisplay) return `${art}<span class="option-main-label">${esc(o.label)}</span>`;
      return `<div class="option-left">${art}<div class="option-meta-text"><span class="option-main-label">${esc(o.label)}</span>` +
        `${o.sub ? `<span class="option-sub-label">${esc(o.sub)}</span>` : ''}</div></div>`;
    }
    function renderMenu() {
      menu.innerHTML = options.length ? options.map((o, i) =>
        `<div class="custom-select-option${String(o.value) === String(value) ? ' selected' : ''}${i === highlighted ? ' highlighted' : ''}" role="option" data-index="${i}" aria-selected="${String(o.value) === String(value)}">` +
        `${optionLeft(o)}${CHECK_SVG}</div>`).join('')
        : `<div class="custom-select-option" aria-disabled="true"><span class="option-sub-label">${esc(api_empty_text(id))}</span></div>`;
    }
    function open() {
      openSelects.forEach((s) => s !== api_ && s.close());
      wrap.classList.add('open');
      trigger.classList.add('active');
      trigger.setAttribute('aria-expanded', 'true');
      highlighted = Math.max(0, options.findIndex((o) => String(o.value) === String(value)));
      renderMenu();
      openSelects.add(api_);
    }
    function close() {
      wrap.classList.remove('open');
      trigger.classList.remove('active');
      trigger.setAttribute('aria-expanded', 'false');
      openSelects.delete(api_);
    }
    function choose(i, fire = true) {
      if (!options[i]) return;
      value = options[i].value;
      renderDisplay();
      close();
      trigger.removeAttribute('aria-invalid');
      if (fire && onChange) onChange(value);
    }
    trigger.addEventListener('click', () => (wrap.classList.contains('open') ? close() : open()));
    menu.addEventListener('mousedown', (e) => e.preventDefault());
    menu.addEventListener('click', (e) => {
      const el = e.target.closest('[data-index]');
      if (el) { choose(+el.dataset.index); trigger.focus(); }
    });
    trigger.addEventListener('keydown', (e) => {
      const isOpen = wrap.classList.contains('open');
      if (e.key === 'Escape' && isOpen) { e.preventDefault(); e.stopPropagation(); close(); return; }
      if (['Enter', ' ', 'ArrowDown', 'ArrowUp'].includes(e.key)) {
        e.preventDefault();
        if (!isOpen) { open(); return; }
        if (e.key === 'ArrowDown') highlighted = Math.min(options.length - 1, highlighted + 1);
        else if (e.key === 'ArrowUp') highlighted = Math.max(0, highlighted - 1);
        else { choose(highlighted); return; }
        renderMenu();
        const el = menu.querySelector('.highlighted');
        if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Tab') {
        close();
      } else if (e.key.length === 1 && /\S/.test(e.key)) {
        const i = options.findIndex((o) => o.label.toLowerCase().startsWith(e.key.toLowerCase()));
        if (i >= 0) { if (isOpen) { highlighted = i; renderMenu(); } else choose(i); }
      }
    });
    const api_ = {
      el: wrap, trigger,
      setOptions(list) { options = list; if (!options.some((o) => String(o.value) === String(value))) value = ''; renderDisplay(); renderMenu(); },
      setValue(v, fire = false) { value = v == null ? '' : v; renderDisplay(); renderMenu(); if (fire && onChange) onChange(value); },
      getValue: () => value,
      setInvalid(flag) { if (flag) trigger.setAttribute('aria-invalid', 'true'); else trigger.removeAttribute('aria-invalid'); trigger.classList.toggle('has-error', !!flag); },
      close, open,
    };
    return api_;
  }
  function api_empty_text(id) {
    if (id === 'f-Client_ID') return 'No clients yet – add one in the Clients view first.';
    if (id === 'f-Airline_ID') return 'No airlines yet – add one in the Airlines view first.';
    return 'No options';
  }

  /* ---------------------------------------------------------- toolbars */
  function buildToolbars() {
    VIEWS.forEach((view) => {
      const bar = $(`[data-toolbar="${view}"]`);
      const examples = { Flight: 'Johannesburg, Maduna, 2026-11', Client: 'Maduna, Johannesburg, +27', Airline: 'Emirates, 2' };
      bar.innerHTML = `<div class="filter-cluster"></div>`;
      const cluster = bar.firstChild;
      const filterIcon = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>';
      const select = makeSelect({ id: `searchField-${view}`, ariaLabel: `Search ${TITLES[view].toLowerCase()} in field`, placeholder: 'All fields', compact: true, icon: filterIcon,
        onChange: (v) => { state.search[view].field = v; runSearch(view); } });
      select.setOptions(state.meta.search_fields[view].map((f) => ({ value: f.value, label: f.label })));
      select.setValue('All fields');
      ui.selects[`search-${view}`] = select;
      cluster.appendChild(select.el);
      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'text-input';
      input.id = `search-${view}`;
      input.style.flex = '1';
      input.placeholder = `Search ${TITLES[view].toLowerCase()} (e.g. ${examples[view]}) — press /`;
      input.setAttribute('aria-label', `Search ${TITLES[view].toLowerCase()}`);
      const debounced = debounce(() => runSearch(view), 120);
      input.addEventListener('input', () => { state.search[view].text = input.value; debounced(); });
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); runSearch(view); }
        if (e.key === 'ArrowDown') { e.preventDefault(); focusFirstResult(view); }
      });
      cluster.appendChild(input);
      const showAll = document.createElement('button');
      showAll.type = 'button';
      showAll.className = 'btn-secondary';
      showAll.textContent = 'Show all';
      showAll.addEventListener('click', () => resetSearch(view));
      cluster.appendChild(showAll);
      if (view === 'Flight') {
        // Column headers sort the table; on compact layouts they are hidden, so offer the same choice here.
        const sortIcon = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h13M3 12h9M3 18h5M17 8l3-3 3 3M20 5v14"/></svg>';
        const sortSel = makeSelect({ id: 'sortField-Flight', ariaLabel: 'Sort flights by', placeholder: 'Sort', compact: true, icon: sortIcon,
          onChange: (v) => { state.sort = { key: v, asc: true }; renderFlights(); } });
        sortSel.setOptions([['Date', 'Date'], ['client_name', 'Client'], ['airline_name', 'Airline'], ['Start City', 'Start city'], ['End City', 'End city']]
          .map(([value, label]) => ({ value, label: `Sort: ${label}` })));
        sortSel.setValue('Date');
        sortSel.el.classList.add('compact-only');
        ui.selects['sort-Flight'] = sortSel;
        cluster.appendChild(sortSel.el);
      }
    });
  }
  function resetSearch(view) {
    state.search[view] = { text: '', field: 'All fields' };
    $(`#search-${view}`).value = '';
    ui.selects[`search-${view}`].setValue('All fields');
    runSearch(view);
  }
  async function runSearch(view) {
    const { text, field } = state.search[view];
    $(`[data-toolbar="${view}"] .filter-cluster`).classList.toggle('has-query', !!text.trim() || field !== 'All fields');
    if (!text.trim() && field === 'All fields') {
      state.results[view] = state.records[view];
    } else {
      const res = await api.search(view, text, field);
      state.results[view] = res.ok ? res.records : [];
    }
    renderResults(view);
  }
  async function refreshAllResults() {
    await Promise.all(VIEWS.map((v) => runSearch(v)));
  }
  function focusFirstResult(view) {
    const el = view === 'Flight' ? $('#flightTableBody tr') : $(`#${view.toLowerCase()}Cards .entity-card`);
    if (el) el.focus();
  }

  /* ----------------------------------------------------------- results */
  function renderResults(view) {
    if (view === 'Flight') renderFlights(); else renderCards(view);
    $('#flightTableBody').removeAttribute('aria-busy');
    const total = state.records[view].length;
    const shown = state.results[view].length;
    $$(`[data-count="${view}"]`).forEach((el) => { el.textContent = `Showing ${shown} of ${total} ${TITLES[view].toLowerCase()}`; });
    const empty = $(`[data-empty="${view}"]`);
    if (shown === 0) {
      const query = state.search[view].text.trim();
      const noun = TITLES[view].toLowerCase();
      empty.innerHTML = '<svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>' +
        (query || state.search[view].field !== 'All fields'
          ? `<strong style="color:var(--text-primary); font-size:0.95rem;">No ${noun} match “${esc(query)}”</strong><p style="font-size:0.8rem; max-width:320px;">Try another word or field, or clear the search.</p><button type="button" class="btn-secondary" data-action="clear-search" data-view="${view}">Show all</button>`
          : `<strong style="color:var(--text-primary); font-size:0.95rem;">No ${noun} yet</strong><p style="font-size:0.8rem; max-width:320px;">${sheetMode() ? 'Tap <strong>New</strong> to create the first one.' : 'Use the form on the right (or Ctrl+N) to create the first one.'}</p>`);
      empty.classList.remove('hidden');
    } else {
      empty.classList.add('hidden');
    }
  }
  function sortedFlights() {
    const { key, asc } = state.sort;
    const rows = state.results.Flight.slice();
    rows.sort((a, b) => {
      const va = String(a[key]).toLowerCase();
      const vb = String(b[key]).toLowerCase();
      return (va < vb ? -1 : va > vb ? 1 : (a.Date < b.Date ? -1 : 1)) * (asc ? 1 : -1);
    });
    return rows;
  }
  function renderFlights() {
    const tbody = $('#flightTableBody');
    const rows = sortedFlights();
    tbody.innerHTML = rows.map((f, i) => {
      const selected = sameKey(f.key, state.selected.Flight);
      return `<tr role="row" tabindex="0" aria-rowindex="${i + 1}" aria-selected="${selected}" data-key='${esc(JSON.stringify(f.key))}'>` +
        `<td role="gridcell" class="tabular-nums">${esc(f.Date)}</td>` +
        `<td role="gridcell"><div class="client-name-cell"><span>${esc(f.client_name)}</span><span class="tier-indicator">#${esc(f.Client_ID)}</span></div></td>` +
        `<td role="gridcell"><div style="display:flex; flex-direction:column;"><span style="font-weight:700; color:var(--text-primary);">${esc(f.airline_name)}</span>` +
        `<span class="tabular-nums" style="font-size:0.7rem; color:var(--text-muted);">Airline #${esc(f.Airline_ID)}${f.upcoming ? '' : ' · past flight'}</span></div></td>` +
        `<td role="gridcell"><div class="route-cell"><span>${esc(f['Start City'])}</span></div></td>` +
        `<td role="gridcell"><div class="route-cell"><span>${esc(f['End City'])}</span></div></td></tr>`;
    }).join('');
    $$('#flightTable th.sortable').forEach((th) => {
      th.setAttribute('aria-sort', th.dataset.sort === state.sort.key ? (state.sort.asc ? 'ascending' : 'descending') : 'none');
    });
    $('#flightTable').setAttribute('aria-rowcount', String(rows.length));
  }
  function renderCards(view) {
    const grid = $(`#${view.toLowerCase()}Cards`);
    grid.innerHTML = state.results[view].map((r) => {
      const selected = sameKey(r.key, state.selected[view]);
      const flights = `${r.flights} flight${r.flights === 1 ? '' : 's'}`;
      if (view === 'Client') {
        const place = [r.City, r.State, r['Zip Code'], r.Country].filter(Boolean).join(', ');
        return `<div class="entity-card${selected ? ' selected' : ''}" role="listitem" tabindex="0" data-key="${esc(r.ID)}" aria-selected="${selected}">` +
          `<div class="entity-title"><span style="display:flex; align-items:center; gap:10px;"><span class="option-avatar" style="background:${colourFor(r.Name)}">${esc(initials(r.Name))}</span><strong>${esc(r.Name)}</strong></span>` +
          `<span class="tier-indicator">#${esc(r.ID)}</span></div>` +
          `<span class="entity-sub">${esc(r['Address Line 1'] || 'No address')}</span>` +
          `<span class="entity-sub">${esc(place || 'No city')}</span>` +
          `<div class="entity-meta"><span>Phone: <strong class="tabular-nums">${esc(r['Phone Number'] || '—')}</strong></span><span><strong>${flights}</strong></span></div></div>`;
      }
      return `<div class="entity-card${selected ? ' selected' : ''}" role="listitem" tabindex="0" data-key="${esc(r.ID)}" aria-selected="${selected}">` +
        `<div class="entity-title"><span style="display:flex; align-items:center; gap:10px;"><span class="option-airline-badge" style="background:${colourFor(r['Company Name'])}22; color:${colourFor(r['Company Name'])}">${esc(initials(r['Company Name']))}</span><strong>${esc(r['Company Name'])}</strong></span>` +
        `<span class="tier-indicator">#${esc(r.ID)}</span></div>` +
        `<div class="entity-meta"><span>Flights booked: <strong class="tabular-nums">${r.flights}</strong></span>` +
        `<span class="spec-badge">${r.flights ? 'IN USE' : 'NO FLIGHTS'}</span></div></div>`;
    }).join('');
  }

  /* ----------------------------------------------- summary and route */
  function renderSummary() {
    const s = state.summary;
    if (!s) return;
    $('#kpiClients').textContent = s.clients;
    $('#kpiClientsSub').textContent = `${s.clients_with_flights} with flights booked`;
    $('#kpiAirlines').textContent = s.airlines;
    $('#kpiAirlinesSub').textContent = `${s.airlines_with_flights} with flights booked`;
    $('#kpiFlights').textContent = s.flights;
    $('#kpiFlightsSub').textContent = `${s.upcoming} upcoming · ${s.past} past`;
    const ratio = s.flights ? s.upcoming / s.flights : 0;
    $('#kpiUpcomingRing').style.strokeDashoffset = String(100 - ratio * 100);
    $('#kpiUpcomingRingWrap').title = `${Math.round(ratio * 100)}% of flights still to depart`;
    if (s.next) {
      $('#kpiNext').textContent = s.next.Date;
      $('#kpiNextSub').textContent = `${s.next['Start City']} → ${s.next['End City']} · ${s.next.client_name}`;
    } else {
      $('#kpiNext').textContent = '—';
      $('#kpiNextSub').textContent = 'No upcoming flights';
    }
    const pill = $('#savePill');
    pill.classList.toggle('unsaved', !!s.modified);
    $('#saveText').textContent = s.modified ? 'Unsaved changes' : 'All changes saved';
    $$('[data-system]').forEach((el) => { el.textContent = `${s.clients} clients, ${s.airlines} airlines, ${s.flights} flights`; });
  }
  function renderRoute() {
    const flight = state.records.Flight.find((f) => sameKey(f.key, state.selected.Flight)) || (state.summary && state.summary.next);
    const card = $('#routeCard');
    if (!flight) {
      $('#routeStartCity').textContent = '—';
      $('#routeEndCity').textContent = '—';
      $('#routeAirline').textContent = 'No flight selected';
      $('#routeClient').textContent = '—';
      $('#routeDate').textContent = '—';
      $('#routeCountdown').textContent = '';
      card.classList.remove('conflict');
      setGlyph(0);
      return;
    }
    $('#routeStartCity').textContent = flight['Start City'];
    $('#routeEndCity').textContent = flight['End City'];
    $('#routeAirline').textContent = flight.airline_name;
    $('#routeClient').textContent = flight.client_name;
    $('#routeDate').textContent = niceDate(flight.Date);
    $('#routeCountdown').textContent = countdown(flight.Date).text;
    setGlyph(flight.upcoming ? 0.04 : 1);
  }
  function setGlyph(progress) {
    const x = 40 + 720 * progress;
    const y = 38 - Math.sin(progress * Math.PI) * 32;
    $('#aircraftGlyph').setAttribute('transform', `translate(${x}, ${y})`);
    $('#flightProgressPath').style.strokeDashoffset = String(800 - progress * 760);
  }

  /* -------------------------------------------------------------- form */
  function fieldMeta(view, name) {
    return state.meta.fields[view].find((f) => f.name === name);
  }
  function labelHtml(view, name, forId) {
    const f = fieldMeta(view, name);
    const hint = name === 'Date' ? 'calendar or quick buttons' : f.hint;
    return `<label for="${forId}"><span>${esc(f.label)}${f.required ? ' <span class="required" aria-hidden="true">*</span>' : ''}</span>` +
      `${hint ? `<span class="label-hint">${esc(hint)}</span>` : ''}</label>`;
  }
  function buildForm(view) {
    const form = $('#recordForm');
    form.innerHTML = '';
    ui.form = { view, inputs: {} };
    state.meta.form_rows[view].forEach((row) => {
      const holder = document.createElement('div');
      holder.className = row.length > 1 ? 'form-row-2col' : '';
      if (row[0] === 'ID') holder.dataset.ratio = '1-3';   // short ID, long name
      row.forEach((name) => holder.appendChild(buildField(view, name)));
      form.appendChild(row.length > 1 ? holder : holder.firstChild);
    });
    if (view === 'Flight') {
      const conflict = document.createElement('div');
      conflict.className = 'inline-field-error';
      conflict.id = 'routeConflictAlert';
      conflict.innerHTML = '<strong>Route conflict:</strong>&nbsp;Start and End City cannot be the same.';
      form.appendChild(conflict);
    }
    const bar = document.createElement('div');
    bar.className = 'form-actions-bar';
    bar.innerHTML = '<button type="button" class="btn-secondary" data-action="cancel" title="Clear the form (Esc)"><span>Cancel (Esc)</span></button>' +
      '<button type="submit" class="btn-primary-action" id="saveBtn" title="Create or update (Ctrl+S)"><span id="saveBtnText">Create</span></button>' +
      '<button type="button" class="btn-danger" id="deleteBtn" data-action="delete" title="Delete this record (Delete key)" disabled><span>Delete</span></button>';
    form.appendChild(bar);
  }
  function buildField(view, name) {
    const row = document.createElement('div');
    row.className = 'form-row';
    row.dataset.field = name;
    const id = `f-${name.replace(/\s+/g, '_')}`;
    if (name === 'Client_ID' || name === 'Airline_ID') {
      const type = name === 'Client_ID' ? 'Client' : 'Airline';
      row.innerHTML = labelHtml(view, name, id);
      const sel = makeSelect({ id, ariaLabel: type, placeholder: `Select ${type.toLowerCase()}…`, onChange: () => { markDirty(); clearFieldError(name); } });
      row.appendChild(sel.el);
      ui.form.inputs[name] = { kind: 'select', select: sel, focusEl: sel.trigger };
    } else if (name === 'Date') {
      row.classList.add('datetime-group');
      row.innerHTML = labelHtml(view, name, 'dateTrigger') + datePickerHtml();
      ui.form.inputs[name] = { kind: 'date', focusEl: null };
    } else {
      const f = fieldMeta(view, name);
      const isCity = name === 'Start City' || name === 'End City' || name === 'City' || name === 'Company Name';
      row.innerHTML = labelHtml(view, name, id) +
        (isCity ? `<div class="input-with-icon"><svg class="input-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 0 0-10 10c0 5.25 10 12 10 12s10-6.75 10-12a10 10 0 0 0-10-10z"/><circle cx="12" cy="10" r="3"/></svg>` : '') +
        `<input type="text" class="text-input${isCity ? ' text-input-icon' : ''}" id="${id}" name="${esc(name)}" maxlength="${f.max_length}" ${f.required ? 'aria-required="true"' : ''} autocomplete="off" placeholder="${isCity ? 'e.g. ' + ({ 'Start City': 'Johannesburg', 'End City': 'London', City: 'Johannesburg', 'Company Name': 'Emirates (EK)' })[name] : ''}">` +
        (isCity ? `</div><div class="airport-autocomplete-popover" id="${id}-suggest" role="listbox"></div>` : '');
      const input = row.querySelector('input');
      input.addEventListener('input', () => { markDirty(); clearFieldError(name); if (isCity) { showCitySuggestions(input); checkRouteConflict(); suggestCountry(input); } });
      if (isCity) attachCitySuggest(input);
      ui.form.inputs[name] = { kind: 'text', input, focusEl: input };
    }
    const err = document.createElement('span');
    err.className = 'inline-field-error';
    err.id = `err-${id}`;
    err.setAttribute('role', 'alert');
    row.appendChild(err);
    if (name === 'Date') ui.form.inputs.Date.focusEl = row.querySelector('#dateTrigger');
    return row;
  }

  /* -------------------------------------------------------- date picker */
  const cal = { year: 2026, month: 0, day: 1 };
  const DEFAULT_TIME = '09:00';
  /** The value sent to Python: "YYYY-MM-DD HH:MM" (or what the user has so far, for validation). */
  function dateTimeValue() {
    const time = $('#timeInput').value;
    return state.date && time ? `${state.date} ${time}` : state.date;
  }
  function datePickerHtml() {
    return '<div class="date-time-row"><div class="custom-datetime-trigger" id="dateTrigger" tabindex="0" role="button" aria-haspopup="dialog" aria-expanded="false" aria-label="Choose travel date">' +
      '<div class="trigger-content"><svg class="trigger-cal-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>' +
      '<span class="trigger-text" id="dateDisplay"><span class="placeholder-text">Choose date…</span></span></div>' + CHEVRON_SVG + '</div>' +
      '<input type="time" class="text-input time-input" id="timeInput" aria-label="Departure time" step="300"></div>' +
      '<div class="calendar-popover" id="calendarPopover" role="dialog" aria-label="Travel date picker">' +
      '<div class="cal-header"><button type="button" class="cal-nav-btn" data-cal="prev" aria-label="Previous month">‹</button><span class="cal-month-title" id="calMonthTitle"></span><button type="button" class="cal-nav-btn" data-cal="next" aria-label="Next month">›</button></div>' +
      '<div class="cal-weekdays"><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span><span>Su</span></div>' +
      '<div class="cal-days-grid" id="calDaysGrid"></div>' +
      '<div class="cal-footer-actions"><button type="button" class="btn-secondary" data-cal="close">Close</button><button type="button" class="btn-primary-action" data-cal="set">Set date</button></div></div>' +
      '<div class="preset-pills" role="group" aria-label="Quick departure shortcuts">' +
      [['today', 'Today'], ['tomorrow', 'Tomorrow'], ['+3d', '+3 Days'], ['+1w', '+1 Week']]
        .map(([k, l]) => `<button type="button" class="preset-pill-btn" data-preset="${k}">${l}</button>`).join('') + '</div>' +
      '<span id="dateCountdown" class="countdown-chip"></span>';
  }
  /** Set the flight date ("YYYY-MM-DD") and optionally time ("YYYY-MM-DD HH:MM"). */
  function setDate(text, { dirty = true } = {}) {
    const [day, time] = (text || '').split(' ');
    state.date = day || '';
    const timeInput = $('#timeInput');
    if (time) timeInput.value = time;
    else if (!state.date) timeInput.value = '';
    else if (!timeInput.value) timeInput.value = DEFAULT_TIME;     // a date needs a time; 09:00 until changed
    const d = parseDate(state.date);
    $('#dateDisplay').innerHTML = d ? esc(niceDate(state.date)) : '<span class="placeholder-text">Choose date…</span>';
    const chip = $('#dateCountdown');
    const cd = countdown(state.date);
    chip.textContent = cd.text;
    chip.classList.toggle('active', !!cd.text);
    chip.classList.toggle('past', cd.kind === 'past');
    if (d) Object.assign(cal, { year: d.getFullYear(), month: d.getMonth(), day: d.getDate() });
    if (dirty) { markDirty(); clearFieldError('Date'); }
  }
  function calText() {
    const last = new Date(cal.year, cal.month + 1, 0).getDate();
    cal.day = Math.min(cal.day, last);
    return `${cal.year}-${pad(cal.month + 1)}-${pad(cal.day)}`;
  }
  function toggleCalendar(force) {
    const pop = $('#calendarPopover');
    if (!pop) return;
    const open = force !== undefined ? force : !pop.classList.contains('open');
    pop.classList.toggle('open', open);
    $('#dateTrigger').classList.toggle('active', open);
    $('#dateTrigger').setAttribute('aria-expanded', String(open));
    if (open) {
      if (!parseDate(state.date)) {
        const now = new Date();
        Object.assign(cal, { year: now.getFullYear(), month: now.getMonth(), day: now.getDate() });
      }
      renderCalendar();
      if (pop.scrollIntoView) pop.scrollIntoView({ block: 'nearest' });
      const sel = $('#calDaysGrid .selected') || $('#calDaysGrid button');
      if (sel) sel.focus();
    }
  }
  function renderCalendar() {
    $('#calMonthTitle').textContent = `${MONTHS[cal.month]} ${cal.year}`;
    const grid = $('#calDaysGrid');
    const first = (new Date(cal.year, cal.month, 1).getDay() + 6) % 7;
    const days = new Date(cal.year, cal.month + 1, 0).getDate();
    const today = new Date();
    let html = '<div class="cal-day-cell empty"></div>'.repeat(first);
    for (let d = 1; d <= days; d++) {
      const isToday = today.getFullYear() === cal.year && today.getMonth() === cal.month && today.getDate() === d;
      html += `<button type="button" class="cal-day-cell${d === cal.day ? ' selected' : ''}${isToday ? ' today' : ''}" data-day="${d}" aria-label="${d} ${MONTHS[cal.month]} ${cal.year}">${d}</button>`;
    }
    grid.innerHTML = html;
  }
  function onCalendarClick(e) {
    const t = e.target.closest('[data-cal],[data-day],[data-time],[data-preset]');
    if (!t) return;
    e.stopPropagation();
    if (t.dataset.day) { cal.day = +t.dataset.day; renderCalendar(); setDate(calText()); return; }
    if (t.dataset.preset) { applyPreset(t.dataset.preset); return; }
    const a = t.dataset.cal;
    if (a === 'prev' || a === 'next') {
      cal.month += a === 'next' ? 1 : -1;
      if (cal.month > 11) { cal.month = 0; cal.year += 1; }
      if (cal.month < 0) { cal.month = 11; cal.year -= 1; }
      renderCalendar();
    } else if (a === 'close') { toggleCalendar(false); $('#dateTrigger').focus(); }
    else if (a === 'set') { setDate(calText()); toggleCalendar(false); $('#dateTrigger').focus(); toast('info', 'Date set', niceDate(state.date)); }
  }
  function applyPreset(key) {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const base = parseDate(state.date) || new Date(now);
    let d;
    if (key === 'today') d = now;
    else if (key === 'tomorrow') { d = new Date(now); d.setDate(d.getDate() + 1); }
    else if (key === '+3d') { d = new Date(base); d.setDate(d.getDate() + 3); }
    else if (key === '+1w') { d = new Date(base); d.setDate(d.getDate() + 7); }
    setDate(dateText(d));
    if ($('#calendarPopover').classList.contains('open')) renderCalendar();
  }

  /* ------------------------------------------------- city suggestions */
  function knownCities() {
    const set = new Map();
    state.meta.cities.forEach((c) => set.set(c.toLowerCase(), c));
    state.records.Flight.forEach((f) => { [f['Start City'], f['End City']].forEach((c) => c && set.set(c.toLowerCase(), c)); });
    state.records.Client.forEach((c) => { if (c.City) set.set(c.City.toLowerCase(), c.City); });
    return Array.from(set.values()).sort((a, b) => a.localeCompare(b));
  }
  function suggestionsFor(input) {
    return input.name === 'Company Name' ? state.meta.airlines : knownCities();
  }
  function attachCitySuggest(input) {
    input.addEventListener('focus', () => showCitySuggestions(input));
    input.addEventListener('blur', () => setTimeout(() => hideSuggest(input), 150));
    input.addEventListener('keydown', (e) => {
      const pop = $(`#${input.id}-suggest`);
      const items = $$('.airport-item', pop);
      if (!pop.classList.contains('open') || !items.length) return;
      let i = items.findIndex((el) => el.classList.contains('active'));
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        i = e.key === 'ArrowDown' ? Math.min(items.length - 1, i + 1) : Math.max(0, i - 1);
        items.forEach((el, n) => el.classList.toggle('active', n === i));
      } else if (e.key === 'Enter' && i >= 0) {
        e.preventDefault();
        chooseCity(input, items[i].dataset.city);
      } else if (e.key === 'Escape') {
        e.stopPropagation();
        hideSuggest(input);
      }
    });
  }
  function showCitySuggestions(input) {
    const pop = $(`#${input.id}-suggest`);
    const q = input.value.trim().toLowerCase();
    const list = suggestionsFor(input).filter((c) => c.toLowerCase().includes(q) && c.toLowerCase() !== q).slice(0, 6);
    if (!list.length) { hideSuggest(input); return; }
    pop.innerHTML = list.map((c) => `<div class="airport-item" role="option" data-city="${esc(c)}"><span>${esc(c)}</span><span class="airport-code-pill">suggested</span></div>`).join('');
    $$('.airport-item', pop).forEach((el) => el.addEventListener('mousedown', (e) => { e.preventDefault(); chooseCity(input, el.dataset.city); }));
    pop.classList.add('open');
  }
  function hideSuggest(input) {
    const pop = $(`#${input.id}-suggest`);
    if (pop) pop.classList.remove('open');
  }
  function chooseCity(input, city) {
    input.value = city;
    hideSuggest(input);
    markDirty();
    clearFieldError(input.name);
    checkRouteConflict();
    suggestCountry(input);
  }
  function suggestCountry(input) {
    const nat = ui.form.inputs.Country;
    if (input.name !== 'City' || !nat || nat.input.value.trim()) return;
    const found = state.meta.city_country[input.value.trim()];
    if (found) nat.input.value = found;
  }
  function checkRouteConflict() {
    const a = ui.form.inputs['Start City'];
    const b = ui.form.inputs['End City'];
    if (!a || !b) return;
    const clash = a.input.value.trim() && a.input.value.trim().toLowerCase() === b.input.value.trim().toLowerCase();
    $('#routeConflictAlert').classList.toggle('active', !!clash);
  }

  /* --------------------------------------------- form state and errors */
  function markDirty() {
    if (!state.dirty) { state.dirty = true; api.set_form_dirty(true); }
  }
  function setClean() {
    if (state.dirty) { state.dirty = false; api.set_form_dirty(false); }
  }
  function banner(kind, title, message = '') {
    const el = $('#formBanner');
    if (!kind) { el.className = 'form-banner hidden'; el.innerHTML = ''; return; }
    el.className = `form-banner ${kind}`;
    el.innerHTML = `<div><strong>${esc(title)}</strong>${message ? `<span>${esc(message)}</span>` : ''}</div>`;
  }
  function errorEl(name) {
    return $(`#err-f-${name.replace(/\s+/g, '_')}`);
  }
  function clearFieldError(name) {
    const err = errorEl(name);
    if (err) { err.textContent = ''; err.classList.remove('active'); }
    const inp = ui.form.inputs[name];
    if (!inp) return;
    if (inp.kind === 'select') inp.select.setInvalid(false);
    else if (inp.kind === 'date') $('#dateTrigger').removeAttribute('aria-invalid');
    else inp.input.removeAttribute('aria-invalid');
  }
  function clearErrors() {
    Object.keys(ui.form.inputs).forEach(clearFieldError);
    const conflict = $('#routeConflictAlert');
    if (conflict) conflict.classList.remove('active');
  }
  function showErrors(errors, messages) {
    clearErrors();
    let first = null;
    const formNames = Object.keys(ui.form.inputs);
    const other = [];
    Object.entries(errors).forEach(([name, msg], i) => {
      const inp = ui.form.inputs[name];
      if (!inp) { other.push(messages[i]); return; }
      const err = errorEl(name);
      err.textContent = msg;
      err.classList.add('active');
      if (inp.kind === 'select') inp.select.setInvalid(true);
      else if (inp.kind === 'date') $('#dateTrigger').setAttribute('aria-invalid', 'true');
      else inp.input.setAttribute('aria-invalid', 'true');
      if (!first || formNames.indexOf(name) < formNames.indexOf(first)) first = name;
    });
    const n = Object.keys(errors).length;
    banner('error', `${n} field${n === 1 ? ' needs' : 's need'} attention`,
      other.length ? other.join(' ') : 'Fix the fields marked in red, then try again.');
    if (first && ui.form.inputs[first].focusEl) ui.form.inputs[first].focusEl.focus();
  }

  function fillForm(record) {
    const view = state.view;
    const editing = !!record;
    clearErrors();
    Object.entries(ui.form.inputs).forEach(([name, inp]) => {
      const value = record ? record[name] : '';
      if (inp.kind === 'select') inp.select.setValue(value);
      else if (inp.kind === 'date') setDate(value, { dirty: false });
      else inp.input.value = value == null ? '' : value;
    });
    if (view !== 'Flight') {
      const idInput = ui.form.inputs.ID.input;
      idInput.disabled = editing;
      if (!editing) idInput.value = state.nextId[view];
    }
    $('#formBadge').textContent = editing ? 'EDITING' : 'NEW';
    $('#formBadge').style.cssText = editing ? 'background:rgba(37,99,235,0.1); color:var(--accent-primary);' : '';
    $('#saveBtnText').textContent = `${editing ? 'Update' : 'Create'} ${view}`;
    $('#deleteBtn').disabled = !editing;
    if (view === 'Flight') {
      $('#formTitle').textContent = editing ? `Edit Flight · ${record.client_name}` : 'Create New Flight';
      $('#formSubtext').textContent = editing ? `${record['Start City']} → ${record['End City']} with ${record.airline_name}` : 'Book an existing client on an existing airline.';
    } else {
      const name = record ? (record.Name || record['Company Name']) : '';
      $('#formTitle').textContent = editing ? `Edit ${view} #${record.ID}` : `Create New ${view}`;
      $('#formSubtext').textContent = editing ? `${name} · the ID cannot be changed` : (view === 'Client' ? "Add a client's name, address and phone number." : 'Add an airline company.');
    }
    checkRouteConflict();
    setClean();
  }
  function refreshFormChoices() {
    if (state.view !== 'Flight' || !ui.form.inputs || !ui.form.inputs.Client_ID) return;
    ui.form.inputs.Client_ID.select.setOptions(state.choices.Client.map((c) => ({
      value: c.id, label: c.name, sub: `#${c.id} · ${c.detail}`, avatar: initials(c.name), color: colourFor(c.name) })));
    ui.form.inputs.Airline_ID.select.setOptions(state.choices.Airline.map((a) => ({
      value: a.id, label: a.name, sub: a.detail, badge: initials(a.name), color: colourFor(a.name) })));
  }
  function guidance() {
    if (state.view !== 'Flight' || state.selected.Flight) return;
    const missing = [];
    if (!state.choices.Client.length) missing.push('a client');
    if (!state.choices.Airline.length) missing.push('an airline');
    if (missing.length) banner('info', 'Before you book a flight', `A flight must refer to an existing client and airline. Create ${missing.join(' and ')} first in the Clients / Airlines views.`);
  }
  function collectForm() {
    const data = {};
    Object.entries(ui.form.inputs).forEach(([name, inp]) => {
      if (inp.kind === 'select') data[name] = inp.select.getValue() === '' ? '' : String(inp.select.getValue());
      else if (inp.kind === 'date') data[name] = dateTimeValue();
      else data[name] = inp.input.value;
    });
    if (state.view !== 'Flight' && ui.form.inputs.ID.input.disabled) data.ID = String(state.selected[state.view]);
    return data;
  }

  /* ----------------------------------------------------------- actions */
  async function confirmDiscard() {
    if (!state.dirty) return true;
    const choice = await dialog({ kind: 'warning', title: 'Discard changes?',
      message: 'The form has changes that have not been saved.',
      buttons: [{ label: 'Keep editing', value: 'keep', focus: true }, { label: 'Discard', value: 'discard', style: 'danger' }], cancelValue: 'keep' });
    return choice === 'discard';
  }
  function scrollBox(view) {
    return view === 'Flight' ? $('#view-Flight .table-scroll') : $(`#view-${view} .cards-scroll`);
  }
  async function setView(view) {
    if (view === state.view) return;
    if (!(await confirmDiscard())) return;
    state.scroll[state.view] = { page: window.scrollY, box: scrollBox(state.view).scrollTop };
    if (state.sheetOpen) closePanel({ force: true, restoreFocus: false });
    state.view = view;
    VIEWS.forEach((v) => {
      $(`#view-${v}`).classList.toggle('hidden', v !== view);
      const tab = $(`#tab-${v}`);
      tab.classList.toggle('active', v === view);
      tab.setAttribute('aria-selected', String(v === view));
      if (v === view) $(`#btab-${v}`).setAttribute('aria-current', 'page'); else $(`#btab-${v}`).removeAttribute('aria-current');
    });
    $('#headerNewText').textContent = `+ New ${view}`;
    $('#fabNew').setAttribute('aria-label', `New ${view.toLowerCase()}`);
    buildForm(view);
    refreshFormChoices();
    const rec = state.records[view].find((r) => sameKey(r.key, state.selected[view]));
    banner(null);
    fillForm(rec || null);
    if (!rec) state.selected[view] = null;
    guidance();
    renderResults(view);
    if (view === 'Flight') renderRoute();
    const saved = state.scroll[view] || { page: 0, box: 0 };
    scrollBox(view).scrollTop = saved.box;
    if (sheetMode()) window.scrollTo(0, saved.page);
  }

  /* ------------------------------------- sheet (narrow windows / touch) */
  const BACKGROUND = ['.app-header', '.kpi-strip', '#mainWorkspace > main', '.bottom-nav', '#fabNew'];
  function openPanel() {
    if (!sheetMode() || state.sheetOpen) return;
    state.sheetOpen = true;
    const active = document.activeElement;
    state.sheetReturnFocus = active && active !== document.body ? active : null;
    document.body.classList.add('sheet-open');
    $('#recordPanel').setAttribute('role', 'dialog');
    $('#recordPanel').setAttribute('aria-modal', 'true');
    BACKGROUND.forEach((sel) => $$(sel).forEach((el) => { el.inert = true; }));
  }
  /** Close the sheet; asks first if the form has unsaved edits (unless forced). */
  async function closePanel({ force = false, restoreFocus = true } = {}) {
    if (!state.sheetOpen) return true;
    if (!force && !(await confirmDiscard())) return false;
    state.sheetOpen = false;
    document.body.classList.remove('sheet-open');
    $('#recordPanel').removeAttribute('role');
    $('#recordPanel').removeAttribute('aria-modal');
    BACKGROUND.forEach((sel) => $$(sel).forEach((el) => { el.inert = false; }));
    if (state.dirty) { fillForm(state.records[state.view].find((r) => sameKey(r.key, state.selected[state.view])) || null); }
    // Lists re-render after changes, so fall back to the selected row/card, then the New button.
    let back = state.sheetReturnFocus;
    if (!back || !back.isConnected) back = selectedElement(state.view) || $('#fabNew');
    if (restoreFocus && back && back.focus) back.focus();
    return true;
  }
  function selectedElement(view) {
    const key = state.selected[view];
    if (key === null) return null;
    return view === 'Flight'
      ? $$('#flightTableBody tr[data-key]').find((tr) => sameKey(JSON.parse(tr.dataset.key), key)) || null
      : $(`#${view.toLowerCase()}Cards [data-key="${key}"]`);
  }
  /** After a change on a narrow window: close the sheet and show the record in the list. */
  function revealSelected(view) {
    const el = selectedElement(view);
    if (el) { el.scrollIntoView({ block: 'nearest' }); state.sheetReturnFocus = el; }
  }
  function applyLayout() {
    // Switch without animating the sheet in or out (it would flash on screen).
    document.body.classList.add('layout-switching');
    document.body.dataset.layout = layout();
    requestAnimationFrame(() => requestAnimationFrame(() => document.body.classList.remove('layout-switching')));
    if (!sheetMode() && state.sheetOpen) closePanel({ force: true, restoreFocus: false });
  }

  async function newRecord() {
    if (!(await confirmDiscard())) return;
    state.selected[state.view] = null;
    banner(null);
    fillForm(null);
    guidance();
    renderResults(state.view);
    if (state.view === 'Flight') renderRoute();
    openPanel();
    const first = state.view === 'Flight' ? ui.form.inputs.Client_ID.focusEl : ui.form.inputs[state.view === 'Client' ? 'Name' : 'Company Name'].input;
    first.focus();
  }
  /** Esc and the Cancel button: close the sheet on narrow windows, clear the form on wide ones. */
  function cancelForm() {
    if (state.sheetOpen) closePanel(); else newRecord();
  }
  async function selectRecord(view, key) {
    if (sameKey(key, state.selected[view])) { openPanel(); if (state.sheetOpen) $('#formTitle').focus(); return; }
    if (!(await confirmDiscard())) return;
    const rec = state.records[view].find((r) => sameKey(r.key, key));
    if (!rec) return;
    state.selected[view] = rec.key;
    banner(null);
    fillForm(rec);
    renderResults(view);
    if (view === 'Flight') renderRoute();
    openPanel();
    if (state.sheetOpen) $('#formTitle').focus();
    announce(`Editing ${view.toLowerCase()} ${view === 'Flight' ? rec.Date : rec.ID}`);
  }
  function applySnapshot(snap) {
    // The change was made but the file could not be written; Python keeps it and saves again on close.
    if (snap.save_error) toast('warning', 'Change kept, but not yet saved to the file', snap.save_error, { duration: 10000 });
    state.records = snap.records;
    state.choices = snap.choices;
    state.nextId = snap.next_id;
    state.summary = snap.summary;
    renderSummary();
    refreshFormChoices();
  }
  async function saveRecord() {
    if (state.busy) return;
    state.busy = true;
    try {
      const view = state.view;
      const data = collectForm();
      const editing = state.selected[view] !== null;
      const res = editing ? await api.update(view, state.selected[view], data) : await api.create(view, data);
      if (!res.ok) {
        if (res.errors) {
          showErrors(res.errors, res.messages || []);
          toast('error', `${view} not saved`, 'Correct the highlighted fields and try again.');
        } else {
          toast('error', 'Not saved', res.error || 'Unknown error');
        }
        return;
      }
      applySnapshot(res);
      state.selected[view] = res.record.key;
      state.dirty = false;
      fillForm(res.record);
      banner('success', `${view} ${editing ? 'updated' : 'created'}`, 'The record was saved to the data file.');
      state.undo = null;
      toast('success', `${view} ${editing ? 'updated' : 'created'} successfully`);
      await refreshAllResults();
      if (view === 'Flight') renderRoute();
      if (state.sheetOpen) { revealSelected(view); closePanel({ force: true }); }
    } finally {
      state.busy = false;
    }
  }
  async function deleteRecord() {
    const view = state.view;
    const key = state.selected[view];
    if (key === null) { toast('info', 'Nothing selected', 'Select a record to delete it.'); return; }
    const check = await api.delete_check(view, key);
    if (!check.ok) { toast('error', 'Record not found', check.error); return; }
    const r = check.record;
    const what = view === 'Flight' ? `the flight on ${r.Date} from ${r['Start City']} to ${r['End City']}`
      : `${view.toLowerCase()} ${r.ID} (${r.Name || r['Company Name']})`;
    if (!check.allowed && check.reason) {
      await dialog({ kind: 'warning', title: 'Cannot delete', message: check.reason,
        buttons: [{ label: 'OK', value: 'ok', style: 'primary', focus: true }] });
      banner('warning', 'Delete blocked', check.reason);
      toast('warning', 'Flight not deleted', 'It would break the same-day journey.');
      return;
    }
    if (!check.allowed) {
      const article = view === 'Airline' ? 'an' : 'a';
      await dialog({ kind: 'warning', title: 'Cannot delete',
        message: `${what[0].toUpperCase() + what.slice(1)} has ${check.linked_flights} flight(s).\n\nDelete or change those flights first, so that no flight is left without ${article} ${view.toLowerCase()}.`,
        buttons: [{ label: 'OK', value: 'ok', style: 'primary', focus: true }] });
      banner('warning', 'Delete blocked', `${check.linked_flights} flight(s) still refer to this ${view.toLowerCase()}.`);
      toast('warning', `${view} not deleted`, 'It still has flights.');
      return;
    }
    const choice = await dialog({ kind: 'warning', title: 'Confirm delete', message: `Permanently delete ${what}?`,
      buttons: [{ label: 'Cancel', value: 'no', focus: true }, { label: 'Delete', value: 'yes', style: 'danger' }], cancelValue: 'no' });
    if (choice !== 'yes') { toast('info', 'Delete cancelled'); return; }
    const res = await api.delete(view, key);
    if (!res.ok) { toast('error', 'Cannot delete', res.error); return; }
    applySnapshot(res);
    state.selected[view] = null;
    state.dirty = false;
    fillForm(null);
    banner(null);
    guidance();
    await refreshAllResults();
    if (view === 'Flight') renderRoute();
    if (state.sheetOpen) closePanel({ force: true });
    state.undo = res.undo ? { view } : null;
    toast('success', `${view} deleted`, 'Undo is available until your next change (Ctrl+Z).',
      res.undo ? { action: { label: 'Undo', run: undoDelete } } : {});
  }
  async function undoDelete() {
    if (!state.undo) { toast('info', 'Nothing to undo'); return; }
    const { view } = state.undo;
    state.undo = null;
    const res = await api.undo_delete();
    if (!res.ok) { toast('error', 'Could not undo', res.error); return; }
    applySnapshot(res);
    await refreshAllResults();
    if (state.view !== view) await setView(view);
    state.selected[view] = res.record.key;
    fillForm(res.record);
    renderResults(view);
    if (view === 'Flight') renderRoute();
    revealSelected(view);
    banner('success', `${view} restored`, 'The deleted record is back, exactly as it was.');
    toast('success', `${view} restored`);
  }
  async function saveAll() {
    const res = await api.save_all();
    if (res.ok) {
      state.summary = res.summary;
      renderSummary();
      toast('success', 'All records saved', res.path);
    } else {
      toast('error', 'Records could not be saved', res.error);
    }
    return res.ok;
  }
  /* ------------------------------------------- display preferences */
  // Each preference may be "system" (follow the computer's setting) or explicit.
  function resolvedPrefs() {
    const p = state.prefs;
    return {
      theme: p.theme === 'system' ? (MQ.dark.matches ? 'dark' : 'light') : p.theme,
      contrast: p.contrast === 'system' ? (MQ.contrast.matches ? 'high' : 'standard') : p.contrast,
      stimulation: p.effects === 'system' ? (MQ.calm.matches ? 'low' : 'standard') : p.effects,
      density: p.density,
    };
  }
  function applyPrefs() {
    const r = resolvedPrefs();
    const root = document.documentElement;
    root.setAttribute('data-theme', r.theme);
    root.setAttribute('data-contrast', r.contrast);
    root.setAttribute('data-stimulation', r.stimulation);
    root.setAttribute('data-density', r.density);
    root.style.setProperty('--panel-width', `${state.prefs.panel_width}px`);
    $('#panelResizer').setAttribute('aria-valuenow', String(state.prefs.panel_width));
    Object.entries(state.prefs).forEach(([name, value]) => {
      const input = $(`#displayPanel input[name="pref-${name}"][value="${value}"]`);
      if (input) input.checked = true;
    });
  }
  async function setPref(name, value, { quiet = false } = {}) {
    if (state.prefs[name] === value) return;
    state.prefs[name] = value;
    applyPrefs();
    const res = await api.set_preference(name, value);
    if (!res.ok) toast('warning', 'Display setting not saved', res.error);
    else if (!quiet) announce(`${name[0].toUpperCase() + name.slice(1)}: ${value}`);
  }
  function toggleTheme() {
    const next = resolvedPrefs().theme === 'dark' ? 'light' : 'dark';
    setPref('theme', next, { quiet: true });
    toast('info', 'Theme switched', `${next === 'dark' ? 'Dark' : 'Light'} theme is active. Choose “System” in Display to follow your computer.`);
  }
  function openDisplay(open = $('#displayPanel').hidden) {
    const panel = $('#displayPanel');
    panel.hidden = !open;
    $('#displayBtn').setAttribute('aria-expanded', String(open));
    if (open) (panel.querySelector('input:checked') || panel.querySelector('input')).focus();
    else $('#displayBtn').focus();
  }

  /* ------------------------------------------------ resizable panel */
  function bindResizer() {
    const handle = $('#panelResizer');
    const [low, high] = [360, 720];
    const clamp = (w) => Math.max(low, Math.min(high, Math.round(w)));
    const preview = (w) => {
      state.prefs.panel_width = clamp(w);
      document.documentElement.style.setProperty('--panel-width', `${state.prefs.panel_width}px`);
      handle.setAttribute('aria-valuenow', String(state.prefs.panel_width));
    };
    const commit = debounce(() => api.set_preference('panel_width', state.prefs.panel_width), 300);
    handle.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      handle.setPointerCapture(e.pointerId);
      handle.classList.add('dragging');
      const startX = e.clientX;
      let moved = false;
      const move = (ev) => { if (Math.abs(ev.clientX - startX) > 3) moved = true; if (moved) preview(window.innerWidth - ev.clientX); };
      const up = () => {
        handle.classList.remove('dragging'); handle.removeEventListener('pointermove', move); handle.removeEventListener('pointerup', up);
        // A plain click (no drag) toggles between the default and a wide panel: resizing without dragging (WCAG 2.5.7).
        if (!moved) preview(state.prefs.panel_width < 560 ? 600 : 440);
        commit();
      };
      handle.addEventListener('pointermove', move);
      handle.addEventListener('pointerup', up);
    });
    handle.addEventListener('keydown', (e) => {
      const steps = { ArrowLeft: 24, ArrowRight: -24, Home: high, End: low };
      if (!(e.key in steps)) return;
      e.preventDefault();
      preview(e.key === 'Home' || e.key === 'End' ? steps[e.key] : state.prefs.panel_width + steps[e.key]);
      commit();
    });
  }
  function showHelp() {
    const rows = [
      ['Ctrl+1 / Ctrl+2 / Ctrl+3', 'Flights / Clients / Airlines'],
      ['/', 'Search box (results update as you type)'],
      ['↓ in the search box', 'Move into the results'],
      ['↑ / ↓ and Enter', 'Move between rows and open one'],
      ['Ctrl+N', 'New record'],
      ['Esc', 'Cancel – clear the form (or close a pop-up or sheet)'],
      ['Ctrl+S or Enter', 'Create / update the record'],
      ['Delete', 'Delete the selected record'],
      ['Ctrl+Z', 'Undo the last delete'],
      ['Ctrl+Shift+S', 'Save all records to the file now'],
      ['Ctrl+Shift+L', 'Light / dark theme'],
      ['Ctrl+Shift+D', 'Display settings (theme, contrast, effects, density)'],
      ['← / → on the panel edge', 'Make the details panel wider or narrower'],
      ['F1', 'This help'],
    ];
    dialog({ kind: 'info', title: 'Keyboard shortcuts',
      html: `<table class="shortcut-table">${rows.map(([k, d]) => `<tr><td><kbd>${esc(k)}</kbd></td><td>${esc(d)}</td></tr>`).join('')}</table>` +
        `<p style="margin-top:14px; font-size:0.8rem;">Records file: <code>${esc(state.meta.data_file)}</code><br>Loaded when the program starts and saved after every change.</p>`,
      buttons: [{ label: 'Close', value: 'close', style: 'primary', focus: true }] });
  }

  /* ------------------------------------------------------------ events */
  function bindEvents() {
    document.addEventListener('click', (e) => {
      const t = e.target.closest('[data-action]');
      if (!e.target.closest('.custom-select-wrapper')) openSelects.forEach((s) => s.close());
      const pop = $('#calendarPopover');
      if (pop && pop.classList.contains('open') && !e.target.closest('#calendarPopover') && !e.target.closest('#dateTrigger') && !e.target.closest('.preset-pill-btn')) toggleCalendar(false);
      const a = t ? t.dataset.action : null;
      const display = $('#displayPanel');
      if (!display.hidden && !e.target.closest('#displayPanel') && a !== 'display') openDisplay(false);
      if (!t) return;
      if (a === 'view') { e.preventDefault(); setView(t.dataset.view); }
      else if (a === 'new') newRecord();
      else if (a === 'cancel') cancelForm();
      else if (a === 'close-panel') closePanel();
      else if (a === 'delete') deleteRecord();
      else if (a === 'save-all') saveAll();
      else if (a === 'display') openDisplay();
      else if (a === 'display-close') openDisplay(false);
      else if (a === 'help') showHelp();
      else if (a === 'clear-search') resetSearch(t.dataset.view);
    });
    $('#recordForm').addEventListener('submit', (e) => { e.preventDefault(); saveRecord(); });
    $('#recordForm').addEventListener('click', (e) => {
      if (e.target.closest('#dateTrigger')) { toggleCalendar(); return; }
      if (e.target.closest('#calendarPopover, .preset-pills')) onCalendarClick(e);
    });
    $('#recordForm').addEventListener('keydown', (e) => {
      if (e.target.id === 'dateTrigger' && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); toggleCalendar(); }
    });
    // Rows and cards
    $('#flightTableBody').addEventListener('click', (e) => {
      const tr = e.target.closest('tr[data-key]');
      if (tr) selectRecord('Flight', JSON.parse(tr.dataset.key));
    });
    ['Client', 'Airline'].forEach((view) => {
      $(`#${view.toLowerCase()}Cards`).addEventListener('click', (e) => {
        const card = e.target.closest('[data-key]');
        if (card) selectRecord(view, Number(card.dataset.key));
      });
    });
    $$('#flightTable th.sortable').forEach((th) => {
      const sort = () => {
        state.sort = { key: th.dataset.sort, asc: state.sort.key === th.dataset.sort ? !state.sort.asc : true };
        renderFlights();
      };
      th.addEventListener('click', sort);
      th.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sort(); } });
    });
    $('#dialogOverlay').addEventListener('click', (e) => { if (e.target.id === 'dialogOverlay') closeDialog(dialogCancelValue); });
    $('#displayPanel').addEventListener('change', (e) => {
      const fieldset = e.target.closest('[data-pref]');
      if (fieldset) setPref(fieldset.dataset.pref, e.target.value);
    });
    $('#displayPanel').addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); openDisplay(false); }
    });
    bindResizer();
    [MQ.dark, MQ.contrast, MQ.calm].forEach((mq) => mq.addEventListener('change', applyPrefs));
    [MQ.compact, MQ.sheet].forEach((mq) => mq.addEventListener('change', applyLayout));
    document.addEventListener('keydown', onKeyDown);
  }
  function onKeyDown(e) {
    const ctrl = e.ctrlKey || e.metaKey;
    const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    if (dialogOpen()) {
      if (e.key === 'Escape') { e.preventDefault(); closeDialog(dialogCancelValue); }
      if (e.key === 'Tab') { // keep focus inside the dialog
        const btns = $$('#dialogOverlay button');
        const i = btns.indexOf(document.activeElement);
        e.preventDefault();
        btns[(i + (e.shiftKey ? btns.length - 1 : 1)) % btns.length].focus();
      }
      return;
    }
    if (ctrl && e.shiftKey && key === 's') { e.preventDefault(); saveAll(); return; }
    if (ctrl && e.shiftKey && key === 'l') { e.preventDefault(); toggleTheme(); return; }
    if (ctrl && e.shiftKey && key === 'd') { e.preventDefault(); openDisplay(); return; }
    if (ctrl && !e.shiftKey && key === 'z' && !isTyping(document.activeElement)) { e.preventDefault(); undoDelete(); return; }
    if (ctrl && key === 'n') { e.preventDefault(); newRecord(); return; }
    if (ctrl && key === 's') { e.preventDefault(); saveRecord(); return; }
    if (ctrl && ['1', '2', '3'].includes(key)) { e.preventDefault(); setView(VIEWS[+key - 1]); return; }
    if (e.key === 'F1') { e.preventDefault(); showHelp(); return; }
    if (e.key === 'Escape') {
      const pop = $('#calendarPopover');
      if (pop && pop.classList.contains('open')) { toggleCalendar(false); $('#dateTrigger').focus(); return; }
      if (openSelects.size) { openSelects.forEach((s) => s.close()); return; }
      e.preventDefault();
      cancelForm();
      return;
    }
    if (isTyping(document.activeElement)) return;
    if (e.key === '/') { e.preventDefault(); $(`#search-${state.view}`).focus(); return; }
    const row = document.activeElement && document.activeElement.closest && document.activeElement.closest('tr[data-key], .entity-card[data-key]');
    if (row) {
      const list = state.view === 'Flight' ? $$('#flightTableBody tr') : $$(`#${state.view.toLowerCase()}Cards .entity-card`);
      const i = list.indexOf(row);
      const keyOf = (el) => (state.view === 'Flight' ? JSON.parse(el.dataset.key) : Number(el.dataset.key));
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); if (list[i + 1]) list[i + 1].focus(); }
      else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); if (list[i - 1]) list[i - 1].focus(); }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectRecord(state.view, keyOf(row)); }
      else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        selectRecord(state.view, keyOf(row)).then(() => { if (sameKey(state.selected[state.view], keyOf(row))) deleteRecord(); });
      }
    }
  }

  /* -------------------------------------------- closing (from Python) */
  window.rmsCloseBlocked = async function (info) {
    if (info.kind === 'unsaved-form') {
      const choice = await dialog({ kind: 'warning', title: 'Unsaved form',
        message: 'The form has changes that were not saved as a record.\n\nClose anyway? Records already in the lists will still be saved to the file.',
        buttons: [{ label: 'Keep editing', value: 'keep', focus: true }, { label: 'Discard and close', value: 'close', style: 'danger' }], cancelValue: 'keep' });
      if (choice === 'close') { state.dirty = false; await api.request_close(true); }
    } else if (info.kind === 'save-failed') {
      const choice = await dialog({ kind: 'error', title: 'Records could not be saved',
        message: `${info.message}\n\nClose WITHOUT saving? Changes made in this session will be lost.`,
        buttons: [{ label: 'Cancel', value: 'cancel', focus: true }, { label: 'Try again', value: 'retry', style: 'primary' },
          { label: 'Close without saving', value: 'discard', style: 'danger' }], cancelValue: 'cancel' });
      if (choice === 'retry') { if (await saveAll()) await api.request_close(true); }
      else if (choice === 'discard') await api.request_close(false);
    }
  };

  /* --------------------------------------------- error reporting to Python */
  // Unexpected script errors are written to the program's log file, so they can be diagnosed later.
  function reportError(message, source, line) {
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.log_client_error) {
        window.pywebview.api.log_client_error(String(message), String(source || ''), Number(line) || 0);
      }
    } catch (e) { /* reporting must never cause a second error */ }
  }
  window.addEventListener('error', (e) => reportError(e.message, e.filename, e.lineno));
  window.addEventListener('unhandledrejection', (e) => {
    const r = e.reason;
    reportError(r && r.stack ? r.stack : (r && r.message) || r, 'promise', 0);
  });

  /* -------------------------------------------------------------- start */
  async function start() {
    if (api) return;
    api = window.pywebview.api;
    let boot;
    try {
      boot = await api.bootstrap();
      if (!boot.ok) throw new Error(boot.error);
    } catch (err) {
      document.body.setAttribute('data-ready', 'error');
      $('#formBanner').className = 'form-banner error';
      $('#formBanner').textContent = `The records could not be loaded: ${err && err.message ? err.message : err}. Close the window and try again.`;
      return;
    }
    state.meta = boot;
    state.prefs = { ...state.prefs, ...(boot.preferences || {}) };
    applyPrefs();
    applyLayout();
    applySnapshot(boot);
    buildToolbars();
    bindEvents();
    VIEWS.forEach((v) => { state.results[v] = state.records[v]; renderResults(v); });
    buildForm('Flight');
    refreshFormChoices();
    fillForm(null);
    guidance();
    renderRoute();
    document.body.setAttribute('data-ready', 'true');
    if (boot.warnings && boot.warnings.length) {
      await dialog({ kind: 'warning', title: 'Data file problem', message: boot.warnings.join('\n\n'),
        buttons: [{ label: 'OK', value: 'ok', style: 'primary', focus: true }] });
    }
  }
  window.rmsApp = { state };
  if (window.pywebview && window.pywebview.api && window.pywebview.api.bootstrap) start();
  else window.addEventListener('pywebviewready', start);
})();
