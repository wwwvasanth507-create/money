// Global Auth & API Helper
const API_BASE = '/api/v1';

function getToken() {
  return localStorage.getItem('aura_token');
}

function setAuthToken(token, role, username) {
  localStorage.setItem('aura_token', token);
  localStorage.setItem('aura_role', role);
  localStorage.setItem('aura_username', username);
}

function clearAuth() {
  localStorage.removeItem('aura_token');
  localStorage.removeItem('aura_role');
  localStorage.removeItem('aura_username');
  window.location.href = '/login';
}

async function apiRequest(endpoint, options = {}) {
  const token = getToken();
  const headers = options.headers || {};
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  options.headers = headers;

  const response = await fetch(`${API_BASE}${endpoint}`, options);
  
  if (response.status === 401) {
    if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
      clearAuth();
    }
  }

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'An API error occurred');
  }

  return data;
}

let lastBalanceVal = null;
async function updateWalletBadge() {
  const badgeEl = document.getElementById('walletBalanceDisplay');
  if (!badgeEl) return;

  try {
    const wallet = await apiRequest('/wallet/balance');
    const newBal = `₹${wallet.available_balance_inr.toFixed(2)}`;
    if (newBal !== lastBalanceVal) {
      badgeEl.textContent = newBal;
      badgeEl.classList.add('pulse-balance');
      setTimeout(() => badgeEl.classList.remove('pulse-balance'), 600);
      lastBalanceVal = newBal;
    }
  } catch (err) {
    console.error('Failed to fetch wallet balance:', err);
  }
}

// Live background sync loop (300ms ultra-fast polling)
function startLiveBalanceLoop() {
  updateWalletBadge();
  setInterval(() => {
    if (getToken()) {
      updateWalletBadge();
    }
  }, 300);
}


document.addEventListener('DOMContentLoaded', () => {
  const token = getToken();
  const username = localStorage.getItem('aura_username');
  const role = localStorage.getItem('aura_role');

  const userGreeting = document.getElementById('userGreeting');
  const mobileNav = document.querySelector('.mobile-bottom-nav');

  if (token && username) {
    if (userGreeting) {
      userGreeting.textContent = `${username}`;
    }
    startLiveBalanceLoop();

    // Show admin / verifier links if applicable
    if (role === 'PAYMENT_VERIFIER' || role === 'ADMIN' || role === 'SUPER_ADMIN') {
      const verifierLink = document.getElementById('navVerifierLink');
      if (verifierLink) verifierLink.style.display = 'inline-block';

      if (mobileNav && !document.getElementById('mobileVerifierNav')) {
        const verifierA = document.createElement('a');
        verifierA.id = 'mobileVerifierNav';
        verifierA.href = '/admin/verification-desk';
        verifierA.innerHTML = '<span>⚡</span>Desk';
        mobileNav.appendChild(verifierA);
      }
    }

    if (role === 'ADMIN' || role === 'SUPER_ADMIN') {
      const adminLink = document.getElementById('navAdminLink');
      if (adminLink) adminLink.style.display = 'inline-block';

      if (mobileNav && !document.getElementById('mobileAdminNav')) {
        const adminA = document.createElement('a');
        adminA.id = 'mobileAdminNav';
        adminA.href = '/admin/dashboard';
        adminA.innerHTML = '<span>👑</span>Admin';
        mobileNav.appendChild(adminA);
      }
    }
  } else {
    const path = window.location.pathname;
    if (path !== '/login' && path !== '/register') {
      window.location.href = '/login';
    }
  }

  // Active state for Mobile Bottom Nav
  if (mobileNav) {
    const currentPath = window.location.pathname;
    const links = mobileNav.querySelectorAll('a');
    links.forEach(link => {
      if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
      }
    });
  }

  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      clearAuth();
    });
  }
});

