const state = {
  token: null,
  client: null,
  cars: [],
};

const toastEl = document.getElementById('toast');
const logEl = document.getElementById('log');
const carsBody = document.getElementById('cars-body');
const vinOptions = document.getElementById('vin-options');
const authPill = document.getElementById('auth-pill');
const clientEmailEl = document.getElementById('client-email');
const tokenEl = document.getElementById('session-token');
const copyBtn = document.getElementById('copy-token');
const logoutBtn = document.getElementById('logout-btn');
const pages = document.querySelectorAll('.page');
const navLinks = document.querySelectorAll('[data-page-link]');

function showToast(message, tone = 'ok') {
  toastEl.textContent = message;
  toastEl.className = `toast ${tone}`;
}

function writeLog(data) {
  logEl.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

function updateAuthUI() {
  if (state.token) {
    authPill.textContent = 'Logged in';
    authPill.style.background = 'rgba(70, 209, 180, 0.2)';
    clientEmailEl.textContent = state.client?.email || '—';
    tokenEl.textContent = state.token;
    copyBtn.disabled = false;
    logoutBtn.disabled = false;
  } else {
    authPill.textContent = 'Logged out';
    authPill.style.background = 'rgba(255,255,255,0.08)';
    clientEmailEl.textContent = '—';
    tokenEl.textContent = '—';
    copyBtn.disabled = true;
    logoutBtn.disabled = true;
  }
}

async function api(path, { method = 'GET', body = null, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && state.token) headers['Authorization'] = `Bearer ${state.token}`;

  const resp = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });
  const payload = await resp.json().catch(() => ({}));
  writeLog(payload);
  if (!resp.ok) {
    showToast(payload.error || 'Request failed', 'warn');
    throw new Error(payload.error || 'Request failed');
  }
  return payload;
}

function renderCars(cars) {
  carsBody.innerHTML = '';
  vinOptions.innerHTML = '';
  if (!cars.length) {
    carsBody.innerHTML = '<tr><td colspan="4" class="muted center">No cars available</td></tr>';
    return;
  }
  cars.forEach((car) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${car.vin}</td>
      <td>${car.model}</td>
      <td>${car.location}</td>
      <td><span class="badge ${car.status === 'available' ? 'ok' : 'busy'}">${car.status}</span></td>
    `;
    carsBody.appendChild(row);

    const opt = document.createElement('option');
    opt.value = car.vin;
    vinOptions.appendChild(opt);
  });
}

async function refreshCars() {
  if (!state.token) {
    showToast('Login first to fetch cars', 'warn');
    return;
  }
  try {
    const data = await api('/cars');
    state.cars = data.cars || [];
    renderCars(state.cars);
  showToast('Cars refreshed', 'ok');
  } catch (err) {
    console.error(err);
  }
}

function setPage(page) {
  let target = page || 'register';
  if (target === 'dashboard' && !state.token) {
    showToast('Login first to access dashboard', 'warn');
    target = 'login';
  }
  pages.forEach((p) => {
    p.classList.toggle('active', p.dataset.page === target);
  });
  navLinks.forEach((link) => {
    link.classList.toggle('active', link.dataset.pageLink === target);
  });
  window.location.hash = target;
}

function logout() {
  state.token = null;
  state.client = null;
  renderCars([]);
  writeLog('Logged out.');
  updateAuthUI();
  setPage('login');
  showToast('Logged out', 'ok');
}

function hookForms() {
  document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const body = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      driver_license: form.license.value.trim(),
      payment_method: form.payment.value.trim(),
      pin: form.pin.value.trim(),
    };
    try {
      const res = await api('/register', { method: 'POST', body, auth: false });
      showToast(res.message || 'Registered', 'ok');
      setPage('login');
    } catch (err) {
      console.error(err);
    }
  });

  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const body = { email: form.email.value.trim(), pin: form.pin.value.trim() };
    try {
      const res = await api('/login', { method: 'POST', body, auth: false });
      state.token = res.token;
      state.client = res.client;
      updateAuthUI();
      showToast('Logged in', 'ok');
      setPage('dashboard');
    } catch (err) {
      console.error(err);
    }
  });

  document.getElementById('refresh-cars').addEventListener('click', refreshCars);

  document.getElementById('start-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.token) return showToast('Login first', 'warn');
    const vin = e.target.vin.value.trim();
    try {
      const res = await api('/rentals/start', { method: 'POST', body: { vin } });
      showToast(res.message || 'Rental started', 'ok');
      refreshCars();
    } catch (err) {
      console.error(err);
    }
  });

  document.getElementById('end-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.token) return showToast('Login first', 'warn');
    const vin = e.target.vin.value.trim();
    try {
      const res = await api('/rentals/end', { method: 'POST', body: { vin } });
      showToast(res.message || 'Rental ended', 'ok');
      refreshCars();
    } catch (err) {
      console.error(err);
    }
  });

  document.getElementById('state-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const vin = form.vin.value.trim();
    const body = {};
    if (form.doors.value) body.doors_closed = form.doors.value === 'closed';
    if (form.lights.value) body.lights_off = form.lights.value === 'off';
    if (form.locked.value) body.locked = form.locked.value === 'true';
    if (!vin) return showToast('VIN required', 'warn');
    if (!Object.keys(body).length) return showToast('No changes to apply', 'warn');

    try {
      const res = await api(`/cars/${vin}/telematics`, { method: 'PATCH', body, auth: false });
      showToast('Telematics updated', 'ok');
      writeLog(res);
    } catch (err) {
      console.error(err);
    }
  });

  copyBtn.addEventListener('click', async () => {
    if (!state.token) return;
    try {
      await navigator.clipboard.writeText(state.token);
      showToast('Token copied', 'ok');
    } catch (_) {
      showToast('Copy not available', 'warn');
    }
  });

  logoutBtn.addEventListener('click', logout);

  navLinks.forEach((link) =>
    link.addEventListener('click', (e) => {
      e.preventDefault();
      setPage(link.dataset.pageLink);
    }),
  );
}

function init() {
  hookForms();
  updateAuthUI();
  showToast('Ready. Register or login to begin.');
  const hash = window.location.hash.replace('#', '') || 'register';
  setPage(hash);
}

document.addEventListener('DOMContentLoaded', init);
