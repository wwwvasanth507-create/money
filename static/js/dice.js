document.addEventListener('DOMContentLoaded', () => {
  const slider = document.getElementById('diceSlider');
  if (!slider) return;

  const rollBtn = document.getElementById('rollDiceBtn');
  const autoRollBtn = document.getElementById('startAutoRollBtn');
  const betInput = document.getElementById('diceBetInput');
  const condToggle = document.getElementById('diceConditionToggle');
  const targetValEl = document.getElementById('diceTargetVal');
  const winChanceEl = document.getElementById('diceWinChance');
  const multiplierEl = document.getElementById('diceMultiplier');
  const profitWinEl = document.getElementById('diceProfitWin');
  const rollResultEl = document.getElementById('diceRollResult');
  const statusBadge = document.getElementById('diceStatusBadge');
  const seedDisplay = document.getElementById('diceSeedDisplay');
  const historyBar = document.getElementById('diceHistoryBar');
  const soundBtn = document.getElementById('diceSoundBtn');

  const manualTabBtn = document.getElementById('manualTabBtn');
  const autoTabBtn = document.getElementById('autoTabBtn');
  const manualControls = document.getElementById('manualControls');
  const autoControls = document.getElementById('autoControls');

  let condition = 'UNDER';
  let soundEnabled = true;
  let audioCtx = null;
  let autoRollActive = false;
  let baseBet = 100.0;

  function initAudio() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) audioCtx = new AudioContext();
    }
    if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
  }

  function playSound(type) {
    if (!soundEnabled) return;
    initAudio();
    if (!audioCtx) return;
    try {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      const now = audioCtx.currentTime;

      if (type === 'roll') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(300, now);
        osc.frequency.linearRampToValueAtTime(600, now + 0.15);
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.18);
        osc.start(now);
        osc.stop(now + 0.18);
      } else if (type === 'win') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.exponentialRampToValueAtTime(1046.50, now + 0.3);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      } else if (type === 'loss') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(160, now);
        osc.frequency.linearRampToValueAtTime(70, now + 0.25);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.3);
        osc.start(now);
        osc.stop(now + 0.3);
      }
    } catch (e) {}
  }

  if (soundBtn) {
    soundBtn.addEventListener('click', () => {
      soundEnabled = !soundEnabled;
      soundBtn.textContent = soundEnabled ? '🔊 Sound ON' : '🔇 Mute';
    });
  }

  // Tab Switching
  if (manualTabBtn && autoTabBtn) {
    manualTabBtn.addEventListener('click', () => {
      manualTabBtn.classList.add('active');
      autoTabBtn.classList.remove('active');
      manualControls.style.display = 'block';
      autoControls.style.display = 'none';
    });

    autoTabBtn.addEventListener('click', () => {
      autoTabBtn.classList.add('active');
      manualTabBtn.classList.remove('active');
      autoControls.style.display = 'block';
      manualControls.style.display = 'none';
    });
  }

  function updateDiceStats() {
    const val = parseFloat(slider.value);
    targetValEl.textContent = val.toFixed(2);

    let winChance = condition === 'UNDER' ? val : (100.0 - val);
    let mult = (99.0 / winChance);

    winChanceEl.textContent = `${winChance.toFixed(2)}%`;
    multiplierEl.textContent = `${mult.toFixed(2)}x`;

    const betInr = parseFloat(betInput.value) || 100;
    const profit = (betInr * mult) - betInr;
    profitWinEl.textContent = `₹${Math.max(0, profit).toFixed(2)}`;
  }

  slider.addEventListener('input', updateDiceStats);
  betInput.addEventListener('input', updateDiceStats);

  condToggle.addEventListener('click', () => {
    condition = condition === 'UNDER' ? 'OVER' : 'UNDER';
    condToggle.textContent = `Roll ${condition}`;
    condToggle.className = condition === 'UNDER' ? 'btn btn-primary' : 'btn btn-gold';
    updateDiceStats();
  });

  updateDiceStats();

  async function executeSingleRoll() {
    const betInr = parseFloat(betInput.value);
    if (!betInr || betInr < 10) {
      alert('Minimum bet is ₹10.00');
      return null;
    }

    playSound('roll');

    try {
      const data = await apiRequest('/games/dice/roll', {
        method: 'POST',
        body: JSON.stringify({
          bet_amount: Math.round(betInr * 100),
          target_value: parseFloat(slider.value),
          condition: condition,
          client_seed: 'client_' + Math.random().toString(36).substring(7)
        })
      });

      const outcome = data.outcome_data || {};
      const rollRes = outcome.roll_result;
      const isWin = outcome.is_win;

      rollResultEl.textContent = rollRes.toFixed(2);

      if (isWin) {
        playSound('win');
        rollResultEl.style.color = '#10b981';
        statusBadge.textContent = `WIN! +₹${(data.payout_amount_inr - (data.bet_amount / 100)).toFixed(2)}`;
        statusBadge.className = 'badge badge-success';
      } else {
        playSound('loss');
        rollResultEl.style.color = '#ef4444';
        statusBadge.textContent = `LOSS -₹${(data.bet_amount / 100).toFixed(2)}`;
        statusBadge.className = 'badge badge-danger';
      }

      seedDisplay.textContent = `Server Seed: ${data.server_seed} (Hash: ${data.server_seed_hash})`;

      // Add pill to history
      if (historyBar) {
        const pill = document.createElement('span');
        pill.className = `history-pill ${isWin ? 'pill-mid' : 'pill-loss'}`;
        pill.textContent = `${rollRes.toFixed(2)} (${isWin ? 'WIN' : 'LOSS'})`;
        historyBar.insertBefore(pill, historyBar.firstChild);
        if (historyBar.children.length > 10) {
          historyBar.removeChild(historyBar.lastChild);
        }
      }

      updateWalletBadge();
      return isWin;
    } catch (err) {
      alert(err.message);
      return null;
    }
  }

  rollBtn.addEventListener('click', async () => {
    rollBtn.disabled = true;
    await executeSingleRoll();
    rollBtn.disabled = false;
  });

  // Auto Roll Engine with Martingale
  if (autoRollBtn) {
    autoRollBtn.addEventListener('click', async () => {
      if (autoRollActive) {
        autoRollActive = false;
        autoRollBtn.textContent = 'START AUTO ROLL';
        autoRollBtn.className = 'btn btn-primary';
        return;
      }

      autoRollActive = true;
      autoRollBtn.textContent = 'STOP AUTO ROLL';
      autoRollBtn.className = 'btn btn-danger';
      baseBet = parseFloat(betInput.value) || 100;

      const totalRolls = parseInt(document.getElementById('autoRollsCount').value) || 50;
      const onLoss = document.querySelector('input[name="onLossStrategy"]:checked')?.value || 'reset';
      const onWin = document.querySelector('input[name="onWinStrategy"]:checked')?.value || 'reset';

      for (let i = 0; i < totalRolls && autoRollActive; i++) {
        const isWin = await executeSingleRoll();
        if (isWin === null) break;

        let currentBet = parseFloat(betInput.value);

        if (isWin) {
          if (onWin === 'increase') {
            betInput.value = (currentBet * 2).toFixed(2);
          } else {
            betInput.value = baseBet.toFixed(2);
          }
        } else {
          if (onLoss === 'martingale') {
            betInput.value = (currentBet * 2).toFixed(2);
          } else {
            betInput.value = baseBet.toFixed(2);
          }
        }

        updateDiceStats();
        await new Promise(r => setTimeout(r, 600)); // Delay between auto rolls
      }

      autoRollActive = false;
      autoRollBtn.textContent = 'START AUTO ROLL';
      autoRollBtn.className = 'btn btn-primary';
      betInput.value = baseBet.toFixed(2);
      updateDiceStats();
    });
  }
});

