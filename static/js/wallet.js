document.addEventListener('DOMContentLoaded', () => {
  const depositForm = document.getElementById('depositForm');
  const withdrawForm = document.getElementById('withdrawForm');
  const txTableBody = document.getElementById('txTableBody');
  const availableBalEl = document.getElementById('availableBalanceText');
  const lockedBalEl = document.getElementById('lockedBalanceText');

  if (depositForm) {
    depositForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(depositForm);

      try {
        const res = await apiRequest('/wallet/deposit', {
          method: 'POST',
          body: formData
        });

        alert(`Deposit request submitted successfully! Request ID #${res.id}. Status: PENDING verification.`);
        depositForm.reset();
        loadDepositClaims();
        loadTransactions();
      } catch (err) {
        alert(`Deposit failed: ${err.message}`);
      }
    });
  }

  if (withdrawForm) {
    withdrawForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const amountInr = parseFloat(document.getElementById('withdrawAmount').value);
      const upiId = document.getElementById('withdrawUpiId').value;
      const bankAcc = document.getElementById('withdrawBankAcc').value;
      const ifsc = document.getElementById('withdrawIfsc').value;

      try {
        const res = await apiRequest('/wallet/withdraw', {
          method: 'POST',
          body: JSON.stringify({
            amount: Math.round(amountInr * 100),
            upi_id: upiId || null,
            bank_account_number: bankAcc || null,
            ifsc_code: ifsc || null
          })
        });

        alert(`Withdrawal request #${res.id} submitted! Amount locked. Pending admin processing.`);
        withdrawForm.reset();
        updateWalletBadge();
        loadWithdrawalClaims();
        loadTransactions();
      } catch (err) {
        alert(`Withdrawal failed: ${err.message}`);
      }
    });
  }

  async function refreshWalletSummary() {
    try {
      const wallet = await apiRequest('/wallet/balance');
      const availEl = document.getElementById('availBalance');
      const lockEl = document.getElementById('lockedBalance');
      if (availEl) availEl.textContent = `₹${wallet.available_balance_inr.toFixed(2)}`;
      if (lockEl) lockEl.textContent = `₹${(wallet.locked_balance / 100).toFixed(2)}`;
    } catch (e) {}
  }

  let lastTxHash = '';
  async function loadTransactions() {
    if (!txTableBody) return;
    try {
      const txs = await apiRequest('/wallet/transactions');
      const hashStr = JSON.stringify(txs);
      if (hashStr === lastTxHash) return;
      lastTxHash = hashStr;

      if (txs.length === 0) {
        txTableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No wallet activity yet.</td></tr>';
        return;
      }

      txTableBody.innerHTML = txs.map(tx => `
        <tr>
          <td><code>${tx.transaction_id.substring(0, 8)}...</code></td>
          <td><span class="badge badge-info">${tx.type}</span></td>
          <td style="color: ${tx.type.includes('DEPOSIT') || tx.type.includes('WIN') || tx.type.includes('REFUND') ? '#10b981' : '#ef4444'}; font-weight: 700;">
            ${tx.type.includes('DEPOSIT') || tx.type.includes('WIN') || tx.type.includes('REFUND') ? '+' : '-'}₹${tx.amount_inr.toFixed(2)}
          </td>
          <td>₹${(tx.balance_after / 100).toFixed(2)}</td>
          <td>${new Date(tx.created_at).toLocaleTimeString()}</td>
          <td>${tx.description || '-'}</td>
        </tr>
      `).join('');
    } catch (err) {
      console.error(err);
    }
  }

  async function loadDepositClaims() {
    const body = document.getElementById('depositClaimsBody');
    if (!body) return;
    try {
      const claims = await apiRequest('/wallet/deposit-claims');
      if (!claims || claims.length === 0) {
        body.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No deposit claims submitted yet.</td></tr>';
        return;
      }
      body.innerHTML = claims.map(c => {
        let badgeClass = 'badge-warning';
        if (c.status === 'APPROVED') badgeClass = 'badge-success';
        if (c.status === 'REJECTED') badgeClass = 'badge-danger';

        return `
          <tr>
            <td><strong>#${c.id}</strong></td>
            <td><code>${c.utr_number}</code></td>
            <td style="font-weight: 800; color: var(--accent-gold);">₹${c.amount_inr.toFixed(2)}</td>
            <td><span class="badge ${badgeClass}">${c.status === 'PENDING' ? 'IN PROGRESS' : (c.status === 'APPROVED' ? 'COMPLETED' : 'FAILED')}</span></td>
            <td style="font-size: 0.85rem; color: ${c.status === 'PENDING' ? 'var(--accent-gold)' : (c.status === 'APPROVED' ? 'var(--accent-green)' : 'var(--accent-red)')}; font-weight: 600;">
              ${c.status_message}
            </td>
            <td>${new Date(c.created_at).toLocaleTimeString()}</td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.error(e);
    }
  }

  async function loadWithdrawalClaims() {
    const body = document.getElementById('withdrawalClaimsBody');
    if (!body) return;
    try {
      const claims = await apiRequest('/wallet/withdrawal-claims');
      if (!claims || claims.length === 0) {
        body.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No withdrawal requests submitted yet.</td></tr>';
        return;
      }
      body.innerHTML = claims.map(w => {
        let badgeClass = 'badge-warning';
        if (w.status === 'APPROVED') badgeClass = 'badge-success';
        if (w.status === 'REJECTED') badgeClass = 'badge-danger';

        let details = w.upi_id ? `UPI: ${w.upi_id}` : `Bank A/C: ${w.bank_account_number || '-'}`;

        return `
          <tr>
            <td><strong>#${w.id}</strong></td>
            <td style="font-weight: 800; color: var(--accent-cyan);">₹${w.amount_inr.toFixed(2)}</td>
            <td><small>${details}</small></td>
            <td><span class="badge ${badgeClass}">${w.status === 'PENDING' ? 'IN PROGRESS' : (w.status === 'APPROVED' ? 'COMPLETED' : 'FAILED')}</span></td>
            <td style="font-size: 0.85rem; color: ${w.status === 'PENDING' ? 'var(--accent-cyan)' : (w.status === 'APPROVED' ? 'var(--accent-green)' : 'var(--accent-red)')}; font-weight: 600;">
              ${w.status_message}
            </td>
            <td>${new Date(w.created_at).toLocaleTimeString()}</td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.error(e);
    }
  }

  async function loadWalletConfig() {
    try {
      const config = await apiRequest('/wallet/config');
      const upiElement = document.getElementById('displayUpiId');
      if (upiElement) upiElement.textContent = config.upi_id;

      const qrImg = document.getElementById('playerUpiQrImg');
      if (qrImg && config.qr_code_url) {
        qrImg.src = config.qr_code_url;
        qrImg.style.display = 'block';
      }

      const minDepInr = config.min_deposit_inr || (config.min_deposit / 100);
      const maxDepInr = config.max_deposit_inr || (config.max_deposit / 100);
      const minWithInr = config.min_withdrawal_inr || (config.min_withdrawal / 100);
      const maxWithInr = config.max_withdrawal_inr || (config.max_withdrawal / 100);

      const depositInput = document.getElementById('depositAmount');
      const depositHint = document.getElementById('depositLimitsHint');
      if (depositInput) {
        depositInput.min = minDepInr;
        depositInput.max = maxDepInr;
      }
      if (depositHint) {
        depositHint.textContent = `Min Deposit: ₹${minDepInr.toFixed(2)} | Max Deposit: ₹${maxDepInr.toFixed(2)}`;
      }

      const withdrawInput = document.getElementById('withdrawAmount');
      const withdrawHint = document.getElementById('withdrawalLimitsHint');
      if (withdrawInput) {
        withdrawInput.min = minWithInr;
        withdrawInput.max = maxWithInr;
      }
      if (withdrawHint) {
        withdrawHint.textContent = `Min Withdrawal: ₹${minWithInr.toFixed(2)} | Max Withdrawal: ₹${maxWithInr.toFixed(2)}`;
      }
    } catch (err) {
      console.error('Failed to load wallet payment config:', err);
    }
  }

  loadTransactions();
  loadDepositClaims();
  loadWithdrawalClaims();
  loadWalletConfig();
  refreshWalletSummary();

  // High-frequency live background sync
  setInterval(() => {
    refreshWalletSummary();
    loadTransactions();
    loadDepositClaims();
    loadWithdrawalClaims();
  }, 1000);
});
