// Employee Management UI.
// SECURITY RULE: data from the API is always written with textContent,
// never innerHTML, so a name like <img onerror=...> is shown as text, not run.
'use strict';

const API = '/api/employees';

const state = {
  page: 0,
  size: 10,
  sort: 'name',
  dir: 'asc',
  search: '',
  department: '',
  totalPages: 0,
  editingId: null,
  deletingId: null,
};

const $ = (id) => document.getElementById(id);
const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

// ---------- helpers ----------

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 204) return null;
  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const err = new Error((body && body.message) || `Request failed (${res.status})`);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

let toastTimer;
function toast(message, kind = 'info') {
  const t = $('toast');
  t.textContent = message;
  t.className = `toast toast-${kind}`;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 3500);
}

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

// ---------- health badge ----------

async function checkHealth() {
  const badge = $('health');
  try {
    const res = await fetch('/actuator/health');
    const body = await res.json();
    const up = res.ok && body.status === 'UP';
    badge.textContent = up ? 'API: Healthy' : 'API: Unhealthy';
    badge.className = `badge ${up ? 'badge-up' : 'badge-down'}`;
  } catch {
    badge.textContent = 'API: Unreachable';
    badge.className = 'badge badge-down';
  }
}

// ---------- dashboard ----------

async function loadStats() {
  try {
    const s = await api(`${API}/stats`);
    const box = $('stats');
    box.replaceChildren();
    const card = (label, value) => {
      const c = el('div', null, 'card');
      c.append(el('span', label, 'card-label'), el('span', value, 'card-value'));
      box.append(c);
    };
    card('Total', s.total);
    Object.entries(s.byDepartment)
      .sort(([a], [b]) => a.localeCompare(b))
      .forEach(([dept, count]) => card(dept, count));
    card('Avg salary', s.averageSalary === null ? '—' : money.format(Number(s.averageSalary)));
  } catch (e) {
    toast(`Could not load stats: ${e.message}`, 'error');
  }
}

// ---------- table ----------

async function loadEmployees() {
  const params = new URLSearchParams({
    page: state.page,
    size: state.size,
    sort: `${state.sort},${state.dir}`,
  });
  if (state.search) params.set('search', state.search);
  if (state.department) params.set('department', state.department);

  try {
    const data = await api(`${API}?${params}`);
    // If a delete emptied the last page, step back one page.
    if (data.content.length === 0 && state.page > 0 && data.totalElements > 0) {
      state.page -= 1;
      return loadEmployees();
    }
    renderRows(data.content);
    state.totalPages = data.totalPages;
    $('page-info').textContent = data.totalElements === 0
      ? '0 results'
      : `Page ${data.page + 1} of ${data.totalPages} · ${data.totalElements} total`;
    $('prev').disabled = state.page === 0;
    $('next').disabled = state.page + 1 >= data.totalPages;
    $('empty').hidden = data.content.length > 0;
    renderSortIndicators();
  } catch (e) {
    toast(`Could not load employees: ${e.message}`, 'error');
  }
}

function renderRows(employees) {
  const tbody = $('employee-rows');
  tbody.replaceChildren();
  for (const emp of employees) {
    const tr = document.createElement('tr');
    const cells = [
      ['ID', emp.id],
      ['Name', emp.name],
      ['Email', emp.email],
      ['Department', emp.department],
      ['Salary', money.format(Number(emp.salary))],
    ];
    for (const [label, value] of cells) {
      const td = el('td', value);
      td.dataset.label = label; // used by the mobile card layout
      tr.append(td);
    }
    const actionsCell = el('td', null, 'actions-cell');
    actionsCell.dataset.label = 'Actions';
    const actions = el('div', null, 'actions');
    const edit = el('button', 'Edit', 'btn btn-small');
    edit.type = 'button';
    edit.addEventListener('click', () => openForm(emp));
    const del = el('button', 'Delete', 'btn btn-small btn-danger');
    del.type = 'button';
    del.addEventListener('click', () => openDelete(emp));
    actions.append(edit, del);
    actionsCell.append(actions);
    tr.append(actionsCell);
    tbody.append(tr);
  }
}

function renderSortIndicators() {
  document.querySelectorAll('button.sort').forEach((b) => {
    const active = b.dataset.field === state.sort;
    b.classList.toggle('active', active);
    b.dataset.dir = active ? state.dir : '';
    b.closest('th').setAttribute('aria-sort',
      active ? (state.dir === 'asc' ? 'ascending' : 'descending') : 'none');
  });
}

function refresh() {
  return Promise.all([loadEmployees(), loadStats()]);
}

// ---------- add / edit ----------

function clearFieldErrors() {
  document.querySelectorAll('.field-error').forEach((e) => { e.textContent = ''; });
  $('form-error').textContent = '';
}

function openForm(emp = null) {
  const form = $('employee-form');
  form.reset();
  clearFieldErrors();
  state.editingId = emp ? emp.id : null;
  $('form-title').textContent = emp ? 'Edit Employee' : 'Add Employee';
  if (emp) {
    form.name.value = emp.name;
    form.email.value = emp.email;
    form.department.value = emp.department;
    form.salary.value = emp.salary;
  }
  $('form-dialog').showModal();
  form.name.focus();
}

async function submitForm(event) {
  event.preventDefault();
  clearFieldErrors();
  const form = event.target;
  const payload = {
    name: form.name.value,
    email: form.email.value,
    department: form.department.value,
    salary: form.salary.value === '' ? null : form.salary.value,
  };
  const editing = state.editingId !== null;
  try {
    await api(editing ? `${API}/${state.editingId}` : API, {
      method: editing ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
    });
    $('form-dialog').close();
    toast(editing ? 'Employee updated' : 'Employee added', 'success');
    await refresh();
  } catch (e) {
    if (e.status === 400 && e.body && e.body.fieldErrors && e.body.fieldErrors.length) {
      for (const fe of e.body.fieldErrors) {
        const slot = document.querySelector(`.field-error[data-for="${CSS.escape(fe.field)}"]`);
        if (slot) slot.textContent = fe.message;
        else $('form-error').textContent = fe.message;
      }
    } else if (e.status === 409) {
      document.querySelector('.field-error[data-for="email"]').textContent = 'Email already exists';
    } else {
      $('form-error').textContent = e.message;
    }
  }
}

// ---------- delete ----------

function openDelete(emp) {
  state.deletingId = emp.id;
  $('delete-name').textContent = emp.name;
  $('delete-email').textContent = emp.email;
  $('delete-dialog').showModal();
}

async function confirmDelete() {
  try {
    await api(`${API}/${state.deletingId}`, { method: 'DELETE' });
    toast('Employee deleted', 'success');
  } catch (e) {
    toast(e.status === 404 ? 'Employee was already deleted' : e.message, 'error');
  }
  $('delete-dialog').close();
  await refresh();
}

// ---------- wiring ----------

function init() {
  $('search').addEventListener('input', debounce((e) => {
    state.search = e.target.value.trim();
    state.page = 0;
    loadEmployees();
  }, 300));

  $('department-filter').addEventListener('change', (e) => {
    state.department = e.target.value;
    state.page = 0;
    loadEmployees();
  });

  document.querySelectorAll('button.sort').forEach((b) => {
    b.addEventListener('click', () => {
      const field = b.dataset.field;
      state.dir = state.sort === field && state.dir === 'asc' ? 'desc' : 'asc';
      state.sort = field;
      state.page = 0;
      loadEmployees();
    });
  });

  $('prev').addEventListener('click', () => { if (state.page > 0) { state.page -= 1; loadEmployees(); } });
  $('next').addEventListener('click', () => {
    if (state.page + 1 < state.totalPages) { state.page += 1; loadEmployees(); }
  });

  $('add-btn').addEventListener('click', () => openForm());
  $('employee-form').addEventListener('submit', submitForm);
  $('confirm-delete').addEventListener('click', confirmDelete);
  document.querySelectorAll('[data-close]').forEach((b) => {
    b.addEventListener('click', () => b.closest('dialog').close());
  });

  checkHealth();
  setInterval(checkHealth, 30000);
  refresh();
}

document.addEventListener('DOMContentLoaded', init);
