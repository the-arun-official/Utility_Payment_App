// -------- Elements --------
const authForm = document.getElementById('authForm');
const submitBtn = document.getElementById('submitBtn');
const title = document.getElementById('title');
const switchText = document.getElementById('switchText');
const switchLink = document.getElementById('switchLink');
const status = document.getElementById('status');
const otpArea = document.getElementById('otpArea');
const otpEmail = document.getElementById('otpEmail');
const verifyBtn = document.getElementById('verifyBtn');
const resendBtn = document.getElementById('resendBtn');
const logoutBtn = document.getElementById('logoutBtn');
const togglePwd = document.getElementById('togglePwd');
const passwordInput = document.getElementById('password');
const emailInput = document.getElementById('email');
const otpInput = document.getElementById('otp');
const usernameInput = document.getElementById('username');
const usernameGroup = document.getElementById('usernameGroup');

// -------- State --------
let mode = 'register';
let currentEmail = '';
let currentUsername = '';
let currentPassword = '';

// -------- Utility --------
function showStatus(msg, ok = true) {
  status.textContent = msg;
  status.style.color = ok ? '#0b63ff' : 'crimson';
}

function savePendingUser(email, username, password) {
  sessionStorage.setItem('pendingEmail', email);
  sessionStorage.setItem('pendingUsername', username);
  sessionStorage.setItem('pendingPassword', password);
}

function clearPendingUser() {
  ['pendingEmail', 'pendingUsername', 'pendingPassword'].forEach(k => sessionStorage.removeItem(k));
}

// -------- Mode Switch --------
switchLink.addEventListener('click', (e) => {
  e.preventDefault();
  mode = (mode === 'register') ? 'login' : 'register';
  usernameGroup.style.display = mode === 'register' ? 'block' : 'none';
  title.textContent = submitBtn.textContent = mode === 'register' ? 'Register' : 'Login';
  switchText.innerHTML = mode === 'register'
    ? 'Already have an account? <a href="#" id="switchLink">Login</a>'
    : 'Don’t have an account? <a href="#" id="switchLink">Register</a>';
  [emailInput, usernameInput, passwordInput, otpInput].forEach(el => el.value = '');
  otpArea.classList.add('hide');
  showStatus('');
  document.getElementById('switchLink').addEventListener('click', (e) => {
    e.preventDefault();
    switchLink.click();
  });
});

// -------- Toggle Password Visibility --------
togglePwd.addEventListener('click', () => {
  const isHidden = passwordInput.type === 'password';
  passwordInput.type = isHidden ? 'text' : 'password';
  togglePwd.textContent = isHidden ? '🙈' : '👁️';
});

// -------- Email Validation (debounced) --------
let emailTimer = null;
emailInput.addEventListener('input', () => {
  clearTimeout(emailTimer);
  emailTimer = setTimeout(async () => {
    const email = emailInput.value.trim();
    if (!email) return;
    try {
      const res = await fetch('/auth/check-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const j = await res.json();
      if (!j.valid) showStatus(j.reason || 'Invalid email', false);
      else if (mode === 'register' && j.exists) showStatus('❗Email already registered', false);
      else if (mode === 'register') showStatus('✅Valid', true);
      else showStatus('');
    } catch {}
  }, 500);
});

// -------- Login / Register --------
authForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  showStatus('');
  const email = emailInput.value.trim();
  const password = passwordInput.value;
  if (!email || !password) return showStatus('🤔 Email and password required', false);

  if (mode === 'register') {
    const username = usernameInput.value.trim();
    if (!username) return showStatus('Username required', false);

    const res = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, username })
    });
    const j = await res.json();
    if (!res.ok) return showStatus(j.msg || j.error || 'Register failed', false);

    currentEmail = j.email || email;
    currentUsername = username;
    currentPassword = password;
    otpEmail.textContent = currentEmail;
    otpArea.classList.remove('hide');
    showStatus('OTP sent to your email', true);
    savePendingUser(currentEmail, currentUsername, currentPassword);
  } else {
    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const j = await res.json();
    if (!res.ok) return showStatus(j.msg || j.error || 'Login failed', false);

    sessionStorage.setItem('access_token', j.access_token);
    sessionStorage.setItem('refresh_token', j.refresh_token);
    
    showStatus('✅ Login successful', true);
    
    // Redirect based on role
    setTimeout(() => {
      if (j.role === 'admin') {
        window.location.href = '/admin_dashboard';
      } else {
        window.location.href = '/dashboard';
      }
    }, 800);    
  }
});

// -------- Token Refresh --------
async function refreshAccessToken() {
  const refresh = sessionStorage.getItem('refresh_token');
  if (!refresh) return null;
  const res = await fetch('/auth/refresh', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + refresh }
  });
  if (!res.ok) {
    console.warn('Refresh failed');
    sessionStorage.clear();
    return null;
  }
  const data = await res.json();
  sessionStorage.setItem('access_token', data.access_token);
  return data.access_token;
}

// -------- Auth Fetch Helper --------
async function fetchWithAuth(url, options = {}) {
  const access = sessionStorage.getItem('access_token');
  options.headers = { ...(options.headers || {}), Authorization: 'Bearer ' + access };
  let res = await fetch(url, options);
  if (res.status === 401) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      options.headers.Authorization = 'Bearer ' + newAccess;
      res = await fetch(url, options);
    } else {
      sessionStorage.clear();
      window.location.href = '/';
      return null;
    }
  }
  return res;
}

// -------- OTP Verification --------
verifyBtn.addEventListener('click', async () => {
  const otp = otpInput.value.trim();
  if (!otp || !currentEmail) return showStatus('OTP required', false);

  const res = await fetch('/auth/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: currentEmail, otp })
  });
  const j = await res.json();
  if (!res.ok) return showStatus(j.msg || j.error || 'Verify failed', false);

  showStatus('✅ Email verified! You can now login', true);
  clearPendingUser();
  otpArea.classList.add('hide');
  mode = 'login';
  title.textContent = submitBtn.textContent = 'Login';
});

// -------- Resend OTP --------
resendBtn.addEventListener('click', async () => {
  const email = currentEmail || sessionStorage.getItem('pendingEmail');
  const password = currentPassword || sessionStorage.getItem('pendingPassword');
  const username = currentUsername || sessionStorage.getItem('pendingUsername');
  if (!email || !password || !username) return showStatus('Please register again to resend OTP', false);

  try {
    const res = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, username })
    });
    const j = await res.json();
    if (!res.ok) return showStatus(j.msg || 'Resend failed', false);

    showStatus(j.msg?.includes('OTP') ? 'OTP resent successfully' : 'Something went wrong', true);
    otpEmail.textContent = email;
    otpArea.classList.remove('hide');
  } catch {
    showStatus('Network error while resending OTP', false);
  }
});

// -------- Logout --------
logoutBtn.addEventListener('click', async () => {
  const access = sessionStorage.getItem('access_token');
  if (access) await fetch('/auth/logout', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + access }
  });
  sessionStorage.clear();
  authForm.classList.remove('hide');
  switchText.classList.remove('hide');
  logoutBtn.classList.add('hide');
  showStatus('Logged out', true);
});

// -------- Silent Background Refresh --------
setInterval(async () => {
  const access = sessionStorage.getItem('access_token');
  if (access) await refreshAccessToken();
}, 4 * 60 * 1000);
