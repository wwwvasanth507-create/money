document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('crashCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const multDisplay = document.getElementById('crashMultiplier');
  const activeSeedHashEl = document.getElementById('activeSeedHash');
  const revealedSeedEl = document.getElementById('revealedServerSeed');
  const historyBar = document.getElementById('crashHistoryBar');
  const soundToggleBtn = document.getElementById('soundToggleBtn');

  // Audio Synth (Web Audio API)
  let soundEnabled = true;
  let audioCtx = null;

  function initAudio() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) audioCtx = new AudioContext();
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
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

      if (type === 'win') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.exponentialRampToValueAtTime(1046.50, now + 0.3);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      } else if (type === 'crash') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(180, now);
        osc.frequency.exponentialRampToValueAtTime(40, now + 0.4);
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.45);
        osc.start(now);
        osc.stop(now + 0.45);
      } else if (type === 'start') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(220, now);
        osc.frequency.exponentialRampToValueAtTime(440, now + 0.2);
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      }
    } catch (e) {}
  }

  if (soundToggleBtn) {
    soundToggleBtn.addEventListener('click', () => {
      soundEnabled = !soundEnabled;
      soundToggleBtn.textContent = soundEnabled ? '🔊 Sound ON' : '🔇 Mute';
      soundToggleBtn.style.color = soundEnabled ? 'var(--accent-gold)' : 'var(--text-muted)';
    });
  }

  // Dual Bet Panels
  const panels = {
    p1: {
      btn: document.getElementById('p1BetBtn'),
      input: document.getElementById('p1BetInput'),
      autoToggle: document.getElementById('p1AutoCashoutToggle'),
      autoTarget: document.getElementById('p1AutoTarget'),
      badge: document.getElementById('p1StatusBadge'),
      betPlaced: false,
      cashedOut: false,
      betInfo: null
    },
    p2: {
      btn: document.getElementById('p2BetBtn'),
      input: document.getElementById('p2BetInput'),
      autoToggle: document.getElementById('p2AutoCashoutToggle'),
      autoTarget: document.getElementById('p2AutoTarget'),
      badge: document.getElementById('p2StatusBadge'),
      betPlaced: false,
      cashedOut: false,
      betInfo: null
    }
  };

  let particles = [];
  let currentPhase = 'BETTING';
  let lastRoundId = null;

  function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function addParticle(x, y) {
    particles.push({
      x: x,
      y: y,
      vx: (Math.random() - 0.5) * 2 - 2,
      vy: (Math.random() - 0.5) * 2 + 1,
      size: Math.random() * 4 + 2,
      alpha: 1.0,
      color: Math.random() > 0.4 ? '#fbbf24' : '#ef4444'
    });
  }

  function drawCanvas(mult, isCrashed = false) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Grid mesh lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 50) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    const marginX = 40;
    const marginY = 40;
    const startX = marginX;
    const startY = canvas.height - marginY;

    const progress = Math.min(1.0, (mult - 1.0) / 12.0);
    const endX = startX + progress * (canvas.width - marginX * 2);
    const endY = startY - Math.pow(progress, 1.5) * (canvas.height - marginY * 2);

    if (currentPhase === 'IN_FLIGHT' || isCrashed) {
      const grad = ctx.createLinearGradient(0, startY, 0, endY);
      if (isCrashed) {
        grad.addColorStop(0, 'rgba(239, 68, 68, 0.0)');
        grad.addColorStop(1, 'rgba(239, 68, 68, 0.25)');
      } else {
        grad.addColorStop(0, 'rgba(6, 182, 212, 0.0)');
        grad.addColorStop(1, 'rgba(6, 182, 212, 0.3)');
      }

      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.quadraticCurveTo(startX + (endX - startX) * 0.5, startY, endX, endY);
      ctx.lineTo(endX, startY);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
    }

    // Trajectory Line
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.quadraticCurveTo(startX + (endX - startX) * 0.5, startY, endX, endY);

    if (isCrashed) {
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 4;
      ctx.shadowColor = '#ef4444';
      ctx.shadowBlur = 15;
    } else {
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 4;
      ctx.shadowColor = '#06b6d4';
      ctx.shadowBlur = 15;
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Draw Clean Glowing Point / Dot ONLY (No rocket, no extra animations)
    ctx.beginPath();
    ctx.arc(endX, endY, 7, 0, Math.PI * 2);
    if (isCrashed) {
      ctx.fillStyle = '#ef4444';
      ctx.shadowColor = '#ef4444';
      ctx.shadowBlur = 15;
    } else {
      ctx.fillStyle = '#fbbf24';
      ctx.shadowColor = '#fbbf24';
      ctx.shadowBlur = 15;
    }
    ctx.fill();
    ctx.shadowBlur = 0;
  }


  // Setup Bet Panel Button Listeners
  setupPanel('p1');
  setupPanel('p2');

  function setupPanel(pKey) {
    const p = panels[pKey];
    if (!p.btn) return;

    p.btn.addEventListener('click', async () => {
      if (currentPhase === 'BETTING' && !p.betPlaced) {
        // Place Bet for upcoming flight
        await placePanelBet(pKey);
      } else if (currentPhase === 'IN_FLIGHT' && p.betPlaced && !p.cashedOut) {
        // Cashout active bet
        await cashoutPanelBet(pKey);
      }
    });
  }

  async function placePanelBet(pKey) {
    const p = panels[pKey];
    const betInr = parseFloat(p.input.value);

    if (!betInr || betInr < 10) {
      alert('Minimum bet is ₹10.00');
      return;
    }

    try {
      playSound('start');
      const data = await apiRequest('/games/crash/bet', {
        method: 'POST',
        body: JSON.stringify({
          panel_key: pKey,
          bet_amount: Math.round(betInr * 100),
          client_seed: 'client_' + Math.random().toString(36).substring(7)
        })
      });

      p.betPlaced = true;
      p.cashedOut = false;
      p.betInfo = data;
      p.badge.textContent = 'BET WAITING';
      p.badge.className = 'badge badge-warning';
      p.btn.textContent = `BET ACCEPTED (₹${betInr.toFixed(2)})`;
      p.btn.disabled = true;

      updateWalletBadge();
    } catch (err) {
      alert(err.message);
    }
  }

  async function cashoutPanelBet(pKey) {
    const p = panels[pKey];
    if (!p.betPlaced || p.cashedOut) return;

    try {
      const res = await apiRequest('/games/crash/cashout', {
        method: 'POST',
        body: JSON.stringify({ panel_key: pKey })
      });

      p.cashedOut = true;
      playSound('win');
      p.badge.textContent = `WON ₹${res.payout_amount_inr.toFixed(2)}`;
      p.badge.className = 'badge badge-success';
      p.btn.textContent = `CASHED OUT (${res.cashout_multiplier.toFixed(2)}x)`;
      p.btn.disabled = true;

      updateWalletBadge();
    } catch (err) {
      console.error('Cashout error:', err.message);
    }
  }

  function updateHistoryBar(history) {
    if (!historyBar || !history) return;
    historyBar.innerHTML = history.map(mult => {
      const cls = mult >= 10 ? 'pill-high' : (mult >= 2 ? 'pill-mid' : 'pill-low');
      return `<span class="history-pill ${cls}">${mult.toFixed(2)}x</span>`;
    }).join('');
  }

  // Real-time Flight State Sync Loop (100ms)
  async function syncFlightLoop() {
    try {
      const state = await apiRequest('/games/crash/state');
      currentPhase = state.phase;

      if (activeSeedHashEl) activeSeedHashEl.textContent = state.server_seed_hash;

      if (state.round_id !== lastRoundId) {
        // New Flight Round Started!
        lastRoundId = state.round_id;
        particles = [];
        updateHistoryBar(state.history);

        // Reset panel states for new round
        ['p1', 'p2'].forEach(pKey => {
          const p = panels[pKey];
          p.betPlaced = false;
          p.cashedOut = false;
          p.betInfo = null;
          p.badge.textContent = 'READY';
          p.badge.className = 'badge badge-info';
          p.btn.disabled = false;

          const betVal = parseFloat(p.input.value || 0).toFixed(2);
          p.btn.textContent = `BET ₹${betVal}`;
          p.btn.className = pKey === 'p1' ? 'btn btn-gold' : 'btn btn-primary';
        });

        if (revealedSeedEl) revealedSeedEl.textContent = '[Revealed on Flight Crash]';
      }

      if (state.phase === 'BETTING') {
        multDisplay.textContent = `NEXT FLIGHT IN ${state.countdown.toFixed(1)}s`;
        multDisplay.style.color = 'var(--accent-cyan)';
        drawCanvas(1.0);

        ['p1', 'p2'].forEach(pKey => {
          const p = panels[pKey];
          if (!p.betPlaced) {
            p.btn.disabled = false;
            const betVal = parseFloat(p.input.value || 0).toFixed(2);
            p.btn.textContent = `BET ₹${betVal}`;
          }
        });
      } else if (state.phase === 'IN_FLIGHT') {
        const liveMult = state.live_multiplier;
        multDisplay.textContent = `${liveMult.toFixed(2)}x`;
        multDisplay.style.color = 'var(--accent-gold)';
        drawCanvas(liveMult);

        // Update Panel Buttons for Active Bets
        ['p1', 'p2'].forEach(pKey => {
          const p = panels[pKey];
          if (p.betPlaced && !p.cashedOut) {
            p.badge.textContent = 'IN FLIGHT';
            p.badge.className = 'badge badge-warning';

            const betInr = parseFloat(p.input.value || 0);
            const winInr = betInr * liveMult;
            p.btn.disabled = false;
            p.btn.className = 'btn btn-primary';
            p.btn.textContent = `CASHOUT ₹${winInr.toFixed(2)} (${liveMult.toFixed(2)}x)`;

            // Auto Cashout Check
            if (p.autoToggle && p.autoToggle.checked) {
              const target = parseFloat(p.autoTarget.value) || 2.0;
              if (liveMult >= target) {
                cashoutPanelBet(pKey);
              }
            }
          }
        });
      } else if (state.phase === 'CRASHED') {
        const crashPoint = state.crash_point || 1.0;
        multDisplay.textContent = `FLEW AWAY @ ${crashPoint.toFixed(2)}x`;
        multDisplay.style.color = '#ef4444';
        drawCanvas(crashPoint, true);

        if (state.server_seed && revealedSeedEl) {
          revealedSeedEl.textContent = state.server_seed;
        }

        // Busted panels update
        ['p1', 'p2'].forEach(pKey => {
          const p = panels[pKey];
          if (p.betPlaced && !p.cashedOut) {
            p.badge.textContent = 'BUSTED';
            p.badge.className = 'badge badge-danger';
            p.btn.textContent = 'BUSTED';
            p.btn.disabled = true;
          }
        });
      }
    } catch (err) {
      console.error('Flight state sync error:', err);
    }
  }

  // Start continuous server-synchronized flight loop (100ms)
  syncFlightLoop();
  setInterval(syncFlightLoop, 100);
});


