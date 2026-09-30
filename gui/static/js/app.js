/**
 * app.js
 *
 * Main Frontend Application Controller for Refrigerator Control System.
 * Connects telemetry polling loop, interactive UI controls, controller switching,
 * Auto Smart Energy Optimizer mode, Web Audio sound synthesis, event logging, and CSV export.
 */

document.addEventListener('DOMContentLoaded', () => {
  const visualizer = new window.RefrigeratorVisualizer();
  const chartManager = new window.TelemetryChartManager('telemetry-chart');

  let isRealtimeRunning = true;
  let pollInterval = null;
  let simSpeed = 1;

  // Web Audio Context Synthesizer
  let audioCtx = null;
  let lastAudioBeepTime = 0;
  let isMuted = false;

  function initAudioContext() {
    if (!audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioCtx = new AudioContextClass();
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  }

  function playAlarmSound(pattern) {
    initAudioContext();
    if (isMuted || !audioCtx) return;

    const now = Date.now();
    // Throttle beep frequency: 400ms for CRITICAL repeated alarm, 1500ms for WARNING
    const intervalMs = pattern === 'REPEATED_ALARM' ? 400 : 1500;
    if (now - lastAudioBeepTime < intervalMs) return;

    lastAudioBeepTime = now;

    try {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      if (pattern === 'REPEATED_ALARM') {
        // High-pitched urgent industrial alarm buzzer
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(960, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(480, audioCtx.currentTime + 0.25);
        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.28);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.28);
      } else {
        // Moderate warning beep
        osc.type = 'sine';
        osc.frequency.setValueAtTime(784, audioCtx.currentTime); // G5 note
        gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.2);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.2);
      }

      osc.connect(gain);
      gain.connect(audioCtx.destination);
    } catch (e) {
      console.warn('Audio play error:', e);
    }
  }

  // DOM Element References
  const tempValEl = document.getElementById('temp-val');
  const setpointValEl = document.getElementById('setpoint-val');
  const powerValEl = document.getElementById('power-val');
  const dutyValEl = document.getElementById('duty-val');
  const timeValEl = document.getElementById('time-val');
  const controllerValEl = document.getElementById('controller-val');

  const qLeakValEl = document.getElementById('q-leak-val');
  const qDoorValEl = document.getElementById('q-door-val');

  // Engineering Debug DOM Elements
  const debugErrorEl = document.getElementById('debug-error-val');
  const debugDtdtEl = document.getElementById('debug-dtdt-val');
  const debugQinEl = document.getElementById('debug-qin-val');
  const debugQnetEl = document.getElementById('debug-qnet-val');

  // Intelligent Feature DOM Elements
  const alertBannerEl = document.getElementById('alert-banner');
  const alertMessageEl = document.getElementById('alert-message');
  const intelDoorStatusEl = document.getElementById('intel-door-status');
  const intelDoorTimerEl = document.getElementById('intel-door-timer');
  const intelQEstEl = document.getElementById('intel-q-est');
  const intelLoadCatEl = document.getElementById('intel-load-cat');
  const intelCoolingReqEl = document.getElementById('intel-cooling-req');
  const intelCompBoostEl = document.getElementById('intel-comp-boost');
  const intelSeverityScoreEl = document.getElementById('intel-severity-score');
  const alarmMuteBtn = document.getElementById('alarm-mute-btn');
  const eventLogTbody = document.getElementById('event-log-tbody');
  const exportCsvBtn = document.getElementById('export-csv-btn');

  // Sliders & Inputs
  const setpointInput = document.getElementById('setpoint-slider');
  const setpointDisp = document.getElementById('setpoint-slider-disp');
  const ambientInput = document.getElementById('ambient-slider');
  const ambientDisp = document.getElementById('ambient-slider-disp');

  // Control Buttons
  const playPauseBtn = document.getElementById('play-pause-btn');
  const fastStepBtn = document.getElementById('fast-step-btn');
  const resetBtn = document.getElementById('reset-btn');
  const runBatchBtn = document.getElementById('run-batch-btn');

  // Controller Selector Chips
  const chipBtns = document.querySelectorAll('.chip-btn');

  // Initialize Web Audio on any click or touch event across document
  window.addEventListener('click', initAudioContext, { passive: true });
  window.addEventListener('keydown', initAudioContext, { passive: true });

  // 1. Fetch Latest Telemetry State
  async function fetchState() {
    try {
      if (isRealtimeRunning) {
        // Step simulation forward automatically when playing
        await fetch('/api/step', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dt_s: 1.0, steps: simSpeed })
        });
      }

      const res = await fetch('/api/state');
      const data = await res.json();
      updateUI(data);
    } catch (err) {
      console.error('Fetch state error:', err);
    }
  }

  // 2. Update UI DOM Elements
  function updateUI(data) {
    if (tempValEl) tempValEl.textContent = `${data.temperature_degc.toFixed(2)}`;
    if (setpointValEl) setpointValEl.textContent = `${data.setpoint_degc.toFixed(1)} °C`;
    if (powerValEl) powerValEl.textContent = `${data.cooling_power_w.toFixed(0)}`;
    if (dutyValEl) dutyValEl.textContent = `${data.duty_cycle_pct.toFixed(1)}%`;
    if (timeValEl) timeValEl.textContent = `${data.time_min.toFixed(1)} min (${data.time_s.toFixed(0)} s)`;
    if (controllerValEl) controllerValEl.textContent = formatControllerName(data);

    if (qLeakValEl) qLeakValEl.textContent = `${data.q_leak_w.toFixed(1)} W`;
    if (qDoorValEl) qDoorValEl.textContent = `${data.q_door_w.toFixed(1)} W`;

    if (debugErrorEl && data.temp_error_degc !== undefined) debugErrorEl.textContent = `${data.temp_error_degc > 0 ? '+' : ''}${data.temp_error_degc.toFixed(2)} °C`;
    if (debugDtdtEl && data.dt_dt_degc_per_s !== undefined) debugDtdtEl.textContent = `${data.dt_dt_degc_per_s.toFixed(5)} °C/s`;
    if (debugQinEl && data.q_in_w !== undefined) debugQinEl.textContent = `${data.q_in_w.toFixed(1)} W`;
    if (debugQnetEl && data.q_net_w !== undefined) debugQnetEl.textContent = `${data.q_net_w > 0 ? '+' : ''}${data.q_net_w.toFixed(1)} W`;

    visualizer.updateState(data);

    if (data.history) {
      chartManager.updateData(data.history);
    }

    if (data.metrics) {
      updateMetricsTable(data.metrics);
    }

    if (data.intelligent_feature) {
      updateIntelligentPanel(data.intelligent_feature);
    }
  }

  function updateIntelligentPanel(intel) {
    if (!intel) return;

    // Alert Banner Styling
    if (alertBannerEl) {
      alertBannerEl.innerHTML = `<span>${intel.display_title}</span>`;

      if (intel.severity_level === 'NORMAL') {
        alertBannerEl.style.background = 'rgba(16, 185, 129, 0.15)';
        alertBannerEl.style.color = 'var(--accent-success)';
        alertBannerEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
      } else if (intel.severity_level === 'WARNING') {
        alertBannerEl.style.background = 'rgba(249, 115, 22, 0.2)';
        alertBannerEl.style.color = 'var(--accent-heat)';
        alertBannerEl.style.borderColor = 'rgba(249, 115, 22, 0.4)';
      } else if (intel.severity_level === 'CRITICAL') {
        alertBannerEl.style.background = 'rgba(239, 68, 68, 0.25)';
        alertBannerEl.style.color = 'var(--accent-danger)';
        alertBannerEl.style.borderColor = 'rgba(239, 68, 68, 0.5)';
      } else if (intel.severity_level === 'RECOVERING') {
        alertBannerEl.style.background = 'rgba(56, 189, 248, 0.2)';
        alertBannerEl.style.color = 'var(--accent-blue)';
        alertBannerEl.style.borderColor = 'rgba(56, 189, 248, 0.4)';
      }
    }

    if (alertMessageEl) {
      alertMessageEl.textContent = intel.display_message;
    }

    if (intelDoorStatusEl) {
      intelDoorStatusEl.textContent = intel.door_status;
      intelDoorStatusEl.style.color = intel.door_status === 'OPEN' ? 'var(--accent-heat)' : 'var(--text-primary)';
    }

    if (intelDoorTimerEl) {
      intelDoorTimerEl.textContent = `${intel.door_open_duration_s.toFixed(1)} s open`;
    }

    if (intelQEstEl) {
      intelQEstEl.textContent = `${intel.estimated_heat_exchange_w.toFixed(1)} W`;
    }

    if (intelLoadCatEl) {
      intelLoadCatEl.textContent = `Load: ${intel.thermal_load_category}`;
    }

    if (intelCoolingReqEl) {
      const powerPct = (intel.compensation_w > 0) ? `+${(intel.compensation_w / 3.44).toFixed(0)}% Boost` : 'Standard';
      intelCoolingReqEl.textContent = powerPct;
    }

    if (intelCompBoostEl) {
      intelCompBoostEl.textContent = `+${intel.compensation_w.toFixed(1)} W Feedforward`;
    }

    if (intelSeverityScoreEl) {
      intelSeverityScoreEl.textContent = `${intel.severity_score.toFixed(1)} / 100`;
    }

    // Audio Alarm Triggering
    isMuted = intel.alarm_muted;
    if (alarmMuteBtn) {
      alarmMuteBtn.innerHTML = isMuted ? '<span>🔇 Alarm: MUTED</span>' : '<span>🔊 Alarm: ON</span>';
      alarmMuteBtn.style.borderColor = isMuted ? 'var(--text-muted)' : 'rgba(249, 115, 22, 0.4)';
    }

    if (intel.should_play_sound && !isMuted) {
      playAlarmSound(intel.audio_pattern);
    }

    // Event Log Updates
    if (intel.recent_events && eventLogTbody) {
      renderEventLog(intel.recent_events);
    }
  }

  function renderEventLog(events) {
    if (!events || events.length === 0) return;

    const html = events.slice().reverse().map(e => `
      <tr>
        <td style="color: var(--text-muted); font-family: var(--font-mono); font-size: 0.8rem;">${e.real_time}</td>
        <td style="color: var(--accent-blue); font-family: var(--font-mono); font-size: 0.8rem;">${e.sim_time}</td>
        <td style="font-weight: 500;">${e.message}</td>
      </tr>
    `).join('');

    eventLogTbody.innerHTML = html;
  }

  function formatControllerName(data) {
    const type = data.controller_type;
    if (type === 'auto') {
      const activeName = data.active_auto_algorithm || 'Smart Energy Optimizer';
      return `🤖 AUTO: ${activeName}`;
    }

    const names = {
      'open_loop': 'Open-Loop (Fixed)',
      'on_off': 'ON/OFF Bang-Bang',
      'pid': 'Standard PID',
      'adaptive_pid': 'Adaptive PID',
      'predictive': 'Predictive MPC'
    };
    return names[type] || type.toUpperCase();
  }

  // Mute Alarm Listener
  if (alarmMuteBtn) {
    alarmMuteBtn.addEventListener('click', async () => {
      initAudioContext();
      const res = await fetch('/api/alarm_mute', { method: 'POST' });
      const data = await res.json();
      updateUI(data);
    });
  }

  // Export CSV Listener
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/export_csv');
        const json = await res.json();
        alert(`Telemetry & Event log exported to:\n${json.filepath}`);
      } catch (err) {
        console.error('Export CSV error:', err);
      }
    });
  }

  // 3. Controller Switching
  chipBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      initAudioContext();
      chipBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const controllerType = btn.getAttribute('data-controller');
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ controller_type: controllerType })
      });
      fetchState();
    });
  });

  // 4. Parameter Inputs (Setpoint & Ambient)
  if (setpointInput) {
    setpointInput.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      if (setpointDisp) setpointDisp.textContent = `${val.toFixed(1)} °C`;
    });
    setpointInput.addEventListener('change', async (e) => {
      const val = parseFloat(e.target.value);
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setpoint_degc: val })
      });
      fetchState();
    });
  }

  if (ambientInput) {
    ambientInput.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      if (ambientDisp) ambientDisp.textContent = `${val.toFixed(1)} °C`;
    });
    ambientInput.addEventListener('change', async (e) => {
      const val = parseFloat(e.target.value);
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ambient_degc: val })
      });
      fetchState();
    });
  }

  // 5. Play / Pause / Step Controls
  if (playPauseBtn) {
    playPauseBtn.addEventListener('click', () => {
      initAudioContext();
      isRealtimeRunning = !isRealtimeRunning;
      playPauseBtn.innerHTML = isRealtimeRunning ? '<span>⏸ PAUSE</span>' : '<span>▶ PLAY</span>';
    });
  }

  if (fastStepBtn) {
    fastStepBtn.addEventListener('click', async () => {
      initAudioContext();
      await fetch('/api/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dt_s: 1.0, steps: 60 })
      });
      fetchState();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      initAudioContext();
      const activeChip = document.querySelector('.chip-btn.active');
      const cType = activeChip ? activeChip.getAttribute('data-controller') : 'auto';

      await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ controller_type: cType })
      });
      fetchState();
    });
  }

  if (runBatchBtn) {
    runBatchBtn.addEventListener('click', async () => {
      initAudioContext();
      runBatchBtn.innerHTML = '<span>⏳ Running 200-Min Sim...</span>';
      runBatchBtn.disabled = true;

      const activeChip = document.querySelector('.chip-btn.active');
      const cType = activeChip ? activeChip.getAttribute('data-controller') : 'auto';

      try {
        const res = await fetch('/api/run_batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ controller_type: cType, duration_s: 12000.0 })
        });
        const batchRes = await res.json();
        chartManager.updateData(batchRes.history);
        updateMetricsTable(batchRes.metrics);
      } catch (err) {
        console.error('Batch run error:', err);
      } finally {
        runBatchBtn.innerHTML = '<span>⏩ RUN FULL 200-MIN SIMULATION BATCH</span>';
        runBatchBtn.disabled = false;
      }
    });
  }

  function updateMetricsTable(metrics) {
    if (!metrics) return;
    const maeEl = document.getElementById('metric-mae');
    const rmseEl = document.getElementById('metric-rmse');
    const energyEl = document.getElementById('metric-energy');
    const peakEl = document.getElementById('metric-peak');

    if (maeEl) maeEl.textContent = `${metrics.mae_degc} °C`;
    if (rmseEl) rmseEl.textContent = `${metrics.rmse_degc} °C`;
    if (energyEl) energyEl.textContent = `${metrics.total_energy_kwh} kWh`;
    if (peakEl) peakEl.textContent = `${metrics.peak_temp_degc} °C`;
  }

  // 6. Start Telemetry Polling Loop (Every 500ms)
  pollInterval = setInterval(fetchState, 500);
  fetchState();
});
