document.addEventListener('DOMContentLoaded', () => {
  const pendingDepositsBody = document.getElementById('pendingDepositsTableBody');
  const pendingWithdrawalsBody = document.getElementById('pendingWithdrawalsTableBody');
  if (!pendingDepositsBody && !pendingWithdrawalsBody) return;

  let activeTab = 'deposits';
  let lastDepositsHash = '';
  let lastWithdrawalsHash = '';

  window.switchDeskTab = function(tabName) {
    activeTab = tabName;
    const depSec = document.getElementById('depositsSection');
    const withSec = document.getElementById('withdrawalsSection');
    const depBtn = document.getElementById('tabDepositsBtn');
    const withBtn = document.getElementById('tabWithdrawalsBtn');

    if (tabName === 'deposits') {
      if (depSec) depSec.style.display = 'block';
      if (withSec) withSec.style.display = 'none';
      if (depBtn) { depBtn.className = 'btn btn-gold'; }
      if (withBtn) { withBtn.className = 'btn btn-secondary'; }
      loadPendingDeposits();
    } else {
      if (depSec) depSec.style.display = 'none';
      if (withSec) withSec.style.display = 'block';
      if (depBtn) { depBtn.className = 'btn btn-secondary'; }
      if (withBtn) { withBtn.className = 'btn btn-primary'; }
      loadPendingWithdrawals();
    }
  };

  async function loadPendingDeposits() {
    if (!pendingDepositsBody) return;
    try {
      const deposits = await apiRequest('/admin/deposits/pending');
      const hashStr = JSON.stringify(deposits);
      if (hashStr === lastDepositsHash) return;
      lastDepositsHash = hashStr;

      if (deposits.length === 0) {
        pendingDepositsBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No pending deposit verification requests.</td></tr>';
        return;
      }

      pendingDepositsBody.innerHTML = deposits.map(d => `
        <tr>
          <td><strong>#${d.id}</strong></td>
          <td>Player ID #${d.user_id}</td>
          <td><code style="color: var(--accent-gold); font-size: 1.05rem;">${d.utr_number}</code></td>
          <td style="font-weight: 800; color: var(--accent-green);">₹${d.amount_inr.toFixed(2)}</td>
          <td>${d.proof_image_path ? `<a href="${d.proof_image_path}" target="_blank" class="btn btn-secondary" style="padding: 0.2rem 0.5rem; font-size: 0.8rem;">View Proof</a>` : 'No Image'}</td>
          <td>
            <button onclick="verifyDeposit(${d.id}, 'APPROVE')" class="btn btn-gold" style="padding: 0.3rem 0.7rem; font-size: 0.85rem;">Approve</button>
            <button onclick="verifyDeposit(${d.id}, 'REJECT')" class="btn btn-danger" style="padding: 0.3rem 0.7rem; font-size: 0.85rem;">Reject</button>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      console.error('Pending deposits update error:', err);
    }
  }

  async function loadPendingWithdrawals() {
    if (!pendingWithdrawalsBody) return;
    try {
      const withdrawals = await apiRequest('/admin/withdrawals/pending');
      const hashStr = JSON.stringify(withdrawals);
      if (hashStr === lastWithdrawalsHash) return;
      lastWithdrawalsHash = hashStr;

      if (withdrawals.length === 0) {
        pendingWithdrawalsBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No pending withdrawal requests.</td></tr>';
        return;
      }

      pendingWithdrawalsBody.innerHTML = withdrawals.map(w => {
        let detailsHtml = '';
        if (w.upi_id) {
          detailsHtml += `<div><span style="color: var(--text-muted); font-size: 0.75rem;">UPI ID:</span> <code style="color: var(--accent-cyan);">${w.upi_id}</code></div>`;
        }
        if (w.bank_account_number) {
          detailsHtml += `<div><span style="color: var(--text-muted); font-size: 0.75rem;">Bank A/C:</span> <code>${w.bank_account_number}</code></div>`;
          detailsHtml += `<div><span style="color: var(--text-muted); font-size: 0.75rem;">IFSC:</span> <code>${w.ifsc_code || '-'}</code></div>`;
          detailsHtml += `<div><span style="color: var(--text-muted); font-size: 0.75rem;">Holder:</span> <strong>${w.account_holder_name || '-'}</strong></div>`;
        }
        if (!detailsHtml) detailsHtml = '<span style="color: var(--text-muted);">-</span>';

        return `
          <tr>
            <td><strong>#${w.id}</strong></td>
            <td>Player ID #${w.user_id}</td>
            <td style="font-weight: 900; color: var(--accent-gold);">₹${w.amount_inr.toFixed(2)}</td>
            <td>${detailsHtml}</td>
            <td><span class="badge badge-warning">IN PROGRESS</span></td>
            <td>
              <button onclick="processWithdrawal(${w.id}, 'APPROVE')" class="btn btn-gold" style="padding: 0.3rem 0.7rem; font-size: 0.85rem; font-weight: 800;">Paid</button>
              <button onclick="processWithdrawal(${w.id}, 'REJECT')" class="btn btn-danger" style="padding: 0.3rem 0.7rem; font-size: 0.85rem; font-weight: 800;">Reject & Refund</button>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Pending withdrawals update error:', err);
    }
  }

  window.verifyDeposit = async function(id, action) {
    const notes = prompt(`Enter mandatory verification notes for ${action} action:`);
    if (!notes || !notes.trim()) {
      alert('Verification notes are mandatory!');
      return;
    }

    try {
      const res = await apiRequest(`/admin/deposits/${id}/verify`, {
        method: 'POST',
        body: JSON.stringify({
          action: action,
          verifier_notes: notes.trim()
        })
      });

      alert(`Deposit claim #${id} marked as ${res.status}.`);
      lastDepositsHash = '';
      loadPendingDeposits();
    } catch (err) {
      alert(`Action failed: ${err.message}`);
    }
  };

  window.processWithdrawal = async function(id, action) {
    const actionLabel = action === 'APPROVE' ? 'Mark as Paid' : 'Reject & Refund';
    const notes = prompt(`Enter notes for withdrawal #${id} (${actionLabel}):`);
    if (notes === null) return; // User cancelled

    try {
      const res = await apiRequest(`/admin/withdrawals/${id}/process`, {
        method: 'POST',
        body: JSON.stringify({
          action: action,
          notes: notes ? notes.trim() : (action === 'APPROVE' ? 'Paid to account' : 'Rejected and refunded')
        })
      });

      if (action === 'APPROVE') {
        alert(`Withdrawal #${id} successfully marked as PAID!`);
      } else {
        alert(`Withdrawal #${id} REJECTED. ₹${res.amount_inr.toFixed(2)} refunded back to Player ID #${res.user_id}!`);
      }
      lastWithdrawalsHash = '';
      loadPendingWithdrawals();
    } catch (err) {
      alert(`Withdrawal processing failed: ${err.message}`);
    }
  };

  loadPendingDeposits();
  loadPendingWithdrawals();

  // High-frequency live background sync loop
  setInterval(() => {
    if (activeTab === 'deposits') {
      loadPendingDeposits();
    } else {
      loadPendingWithdrawals();
    }
  }, 1000);
});
