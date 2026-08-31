document.addEventListener('DOMContentLoaded', () => {
  const pendingDepositsBody = document.getElementById('pendingDepositsTableBody');
  if (!pendingDepositsBody) return;

  let lastDepositsHash = '';

  async function loadPendingDeposits() {
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

  loadPendingDeposits();

  // High-frequency live background sync loop (300ms ultra-fast polling)
  setInterval(() => {
    loadPendingDeposits();
  }, 300);
});


