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
        loadTransactions();
      } catch (err) {
        alert(`Withdrawal failed: ${err.message}`);
      }
    });
  }

  async function refreshWalletSummary() {
    try {
      const wallet = await apiRequest('/wallet/balance');
      if (availableBalEl) availableBalEl.textContent = `₹${wallet.available_balance_inr.toFixed(2)}`;
      if (lockedBalEl) lockedBalEl.textContent = `₹${wallet.locked_balance_inr.toFixed(2)}`;
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
          <td style="color: ${tx.type.includes('DEPOSIT') || tx.type.includes('WIN') ? '#10b981' : '#ef4444'}; font-weight: 700;">
            ${tx.type.includes('DEPOSIT') || tx.type.includes('WIN') ? '+' : '-'}₹${tx.amount_inr.toFixed(2)}
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
  loadWalletConfig();
  refreshWalletSummary();

  // High-frequency live background sync (300ms ultra-fast polling)
  setInterval(() => {
    refreshWalletSummary();
    loadTransactions();
  }, 300);
});



