document.addEventListener('DOMContentLoaded', () => {
  const gridEl = document.getElementById('minesGrid');
  if (!gridEl) return;

  const startBtn = document.getElementById('startMinesBtn');
  const cashoutBtn = document.getElementById('cashoutMinesBtn');
  const autoPickBtn = document.getElementById('autoPickTileBtn');
  const betInput = document.getElementById('minesBetInput');
  const minesCountInput = document.getElementById('minesCountInput');
  const nextMultDisplay = document.getElementById('nextTileMultDisplay');
  const currentWinDisplay = document.getElementById('currentWinDisplay');
  const hashDisplay = document.getElementById('minesServerSeedHash');
  const soundBtn = document.getElementById('minesSoundBtn');

  let activeSession = null;
  let soundEnabled = true;
  let audioCtx = null;

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

      if (type === 'gem') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.15); // A5
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.2);
        osc.start(now);
        osc.stop(now + 0.2);
      } else if (type === 'mine') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(150, now);
        osc.frequency.exponentialRampToValueAtTime(40, now + 0.4);
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.45);
        osc.start(now);
        osc.stop(now + 0.45);
      } else if (type === 'win') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.exponentialRampToValueAtTime(1046.50, now + 0.3);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.linearRampToValueAtTime(0.01, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      }
    } catch (e) {}
  }

  if (soundBtn) {
    soundBtn.addEventListener('click', () => {
      soundEnabled = !soundEnabled;
      soundBtn.textContent = soundEnabled ? '🔊 Sound ON' : '🔇 Mute';
    });
  }

  // Mine Chip Selection
  const chips = document.querySelectorAll('.mine-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      if (activeSession && activeSession.status === 'ACTIVE') return;
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      minesCountInput.value = chip.dataset.val;
      updateNextMultiplierPreview();
    });
  });

  function calculateMinesMultiplier(minesCount, safeStep) {
    if (safeStep <= 0) return 1.0;
    const totalTiles = 25;
    const safeTilesCount = totalTiles - minesCount;
    let mult = 1.0;
    for (let i = 0; i < safeStep; i++) {
      mult *= (totalTiles - i) / (safeTilesCount - i);
    }
    // Apply 1% house edge
    mult = mult * 0.99;
    return parseFloat(mult.toFixed(2));
  }

  function updateNextMultiplierPreview() {
    const minesCount = parseInt(minesCountInput.value) || 15;
    const currentStep = (activeSession && activeSession.outcome_data) ? (activeSession.outcome_data.revealed_tiles || []).length : 0;
    const nextMult = calculateMinesMultiplier(minesCount, currentStep + 1);
    if (nextMultDisplay) nextMultDisplay.textContent = `${nextMult.toFixed(2)}x`;
  }

  updateNextMultiplierPreview();

  // Render 5x5 Grid
  function renderGrid() {
    gridEl.innerHTML = '';
    for (let i = 0; i < 25; i++) {
      const tile = document.createElement('div');
      tile.className = 'mine-tile';
      tile.dataset.index = i;
      tile.textContent = '?';
      tile.addEventListener('click', () => onTileClick(i, tile));
      gridEl.appendChild(tile);
    }
  }

  renderGrid();

  startBtn.addEventListener('click', async () => {
    const betInr = parseFloat(betInput.value);
    const minesCount = parseInt(minesCountInput.value) || 15;

    if (!betInr || betInr < 10) {
      alert('Minimum bet is ₹10.00');
      return;
    }

    startBtn.disabled = true;
    cashoutBtn.disabled = true;
    autoPickBtn.disabled = false;
    currentWinDisplay.textContent = '₹0.00';
    renderGrid();

    try {
      const data = await apiRequest('/games/start', {
        method: 'POST',
        body: JSON.stringify({
          game_code: 'MINES',
          bet_amount: Math.round(betInr * 100),
          mines_count: minesCount,
          client_seed: 'client_' + Math.random().toString(36).substring(7)
        })
      });

      activeSession = data;
      if (hashDisplay) hashDisplay.textContent = data.server_seed_hash;
      updateNextMultiplierPreview();
      updateWalletBadge();
    } catch (err) {
      alert(err.message);
      startBtn.disabled = false;
      autoPickBtn.disabled = true;
    }
  });

  async function onTileClick(index, tileEl) {
    if (!activeSession || activeSession.status !== 'ACTIVE') return;
    if (tileEl.classList.contains('revealed-safe') || tileEl.classList.contains('revealed-mine')) return;

    try {
      const res = await apiRequest('/games/mines/reveal', {
        method: 'POST',
        body: JSON.stringify({
          session_id: activeSession.id,
          tile_index: index
        })
      });

      activeSession = res;

      if (res.status === 'BUST') {
        playSound('mine');
        tileEl.classList.add('revealed-mine');
        tileEl.textContent = '💣';

        const outcome = res.outcome_data || {};
        const mines = outcome.mines_locations || [];
        mines.forEach(mIdx => {
          const t = gridEl.children[mIdx];
          if (t) {
            t.classList.add('revealed-mine');
            t.textContent = '💣';
          }
        });

        startBtn.disabled = false;
        cashoutBtn.disabled = true;
        autoPickBtn.disabled = true;
        cashoutBtn.textContent = 'BUSTED';
        document.getElementById('minesRevealedSeed').textContent = res.server_seed;
      } else {
        playSound('gem');
        tileEl.classList.add('revealed-safe');
        tileEl.textContent = '💎';

        const winInr = (res.bet_amount * res.multiplier) / 100.0;
        currentWinDisplay.textContent = `₹${winInr.toFixed(2)}`;
        cashoutBtn.textContent = `CASHOUT ₹${winInr.toFixed(2)} (${res.multiplier.toFixed(2)}x)`;
        cashoutBtn.disabled = false;

        updateNextMultiplierPreview();

        if (res.status === 'CASHOUT') {
          playSound('win');
          alert(`All safe tiles revealed! You won ₹${res.payout_amount_inr.toFixed(2)}!`);
          startBtn.disabled = false;
          cashoutBtn.disabled = true;
          autoPickBtn.disabled = true;
          document.getElementById('minesRevealedSeed').textContent = res.server_seed;
        }
      }

      updateWalletBadge();
    } catch (err) {
      alert(err.message);
    }
  }

  // Auto Pick Random Unrevealed Tile
  autoPickBtn.addEventListener('click', () => {
    if (!activeSession || activeSession.status !== 'ACTIVE') return;
    const unrevealed = [];
    for (let i = 0; i < gridEl.children.length; i++) {
      const tile = gridEl.children[i];
      if (!tile.classList.contains('revealed-safe') && !tile.classList.contains('revealed-mine')) {
        unrevealed.push({ idx: i, el: tile });
      }
    }
    if (unrevealed.length > 0) {
      const pick = unrevealed[Math.floor(Math.random() * unrevealed.length)];
      onTileClick(pick.idx, pick.el);
    }
  });

  cashoutBtn.addEventListener('click', async () => {
    if (!activeSession || activeSession.status !== 'ACTIVE') return;

    try {
      const res = await apiRequest('/games/cashout', {
        method: 'POST',
        body: JSON.stringify({ session_id: activeSession.id })
      });

      playSound('win');
      alert(`Cashout successful! Won ₹${res.payout_amount_inr.toFixed(2)} (${res.multiplier.toFixed(2)}x)`);
      startBtn.disabled = false;
      cashoutBtn.disabled = true;
      autoPickBtn.disabled = true;
      cashoutBtn.textContent = `CASHED OUT ₹${res.payout_amount_inr.toFixed(2)}`;
      document.getElementById('minesRevealedSeed').textContent = res.server_seed;

      updateWalletBadge();
    } catch (err) {
      alert(err.message);
    }
  });
});

