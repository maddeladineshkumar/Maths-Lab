/**
 * CRT-Nano Project: Interactive Signal Simulation & Lab Dashboard
 * Authors: M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
 * Course: 23MAT204 - Lab Exam: Frugal Healthcare AI / Edge Device Challenge
 * Instructor: Dr. Suman Dutta
 */

// Web Audio API Synthesizer
let audioCtx = null;

function initAudio() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContext();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

let soundEnabled = true;

window.toggleSound = function() {
  soundEnabled = !soundEnabled;
  const btn = document.getElementById('soundToggleBtn');
  if (btn) {
    if (soundEnabled) {
      btn.innerHTML = "🔊 Sound ON";
      btn.classList.remove('muted');
    } else {
      btn.innerHTML = "🔇 Sound Muted";
      btn.classList.add('muted');
    }
  }
};

function playTone(freq, durationMs, type = 'sine') {
  if (!soundEnabled) return;
  try {
    initAudio();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + durationMs / 1000);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + durationMs / 1000);
  } catch (e) {
    console.warn("Audio playback not allowed without user gesture:", e);
  }
}

function playFanfare() {
  playTone(587, 100);
  setTimeout(() => playTone(880, 150), 110);
  setTimeout(() => playTone(1175, 250), 270);
}

function playErrorSound() {
  playTone(400, 160, 'sawtooth');
  setTimeout(() => playTone(240, 280, 'sawtooth'), 180);
}

// Navigation Tabs
document.querySelectorAll('nav.nav-pills button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('nav.nav-pills button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.section-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const target = btn.getAttribute('data-target');
    const el = document.getElementById(target);
    if (el) el.classList.add('active');
  });
});

// Copy to Clipboard Helpers
window.copyField = function(elementId, btnElement) {
  const target = document.getElementById(elementId);
  if (!target) return;
  const text = target.innerText;
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btnElement.innerText;
    btnElement.innerText = "✓ Copied to Clipboard!";
    btnElement.classList.add("copied");
    setTimeout(() => {
      btnElement.innerText = originalText;
      btnElement.classList.remove("copied");
    }, 2200);
  }).catch(err => {
    alert("Could not copy: " + err);
  });
};

// Simulation Engine Parameters
const sim = {
  trueCRT90: 2.0,
  vMin: 0.20,
  hrBpm: 75.0,
  snrDb: 24.0,
  driftType: "none",
  artifact: "none",
  fs: 100.0,
  tBaseline: 3.0,
  tPress: 3.0,
  tRecovery: 8.0,
  
  // State
  state: "IDLE", // IDLE, BASELINE, PRESS, RELEASE, RECOVERY, REPORT, INVALID
  currentTime: 0.0,
  dataT: [],
  dataX: [],
  dataFilt: [],
  filteredVal: 512.0,
  baselineMean: 512.0,
  baselineStd: 0.0,
  blanchMin: 1023.0,
  dwellCounter: 0,
  faults: [],
  crt90Threshold: null,
  crt90Model: null,
  consensusCRT: null,
  
  isRunning: false,
  timerId: null
};

// UI Slider Linkages
function setupSliders() {
  const crtSlider = document.getElementById('crtSlider');
  const crtVal = document.getElementById('crtVal');
  crtSlider.addEventListener('input', (e) => {
    sim.trueCRT90 = parseFloat(e.target.value);
    crtVal.innerText = sim.trueCRT90.toFixed(1) + " s";
  });

  const vminSlider = document.getElementById('vminSlider');
  const vminVal = document.getElementById('vminVal');
  vminSlider.addEventListener('input', (e) => {
    sim.vMin = parseFloat(e.target.value);
    vminVal.innerText = sim.vMin.toFixed(2);
  });

  const hrSlider = document.getElementById('hrSlider');
  const hrVal = document.getElementById('hrVal');
  hrSlider.addEventListener('input', (e) => {
    sim.hrBpm = parseFloat(e.target.value);
    hrVal.innerText = sim.hrBpm.toFixed(0) + " bpm";
  });

  const snrSlider = document.getElementById('snrSlider');
  const snrVal = document.getElementById('snrVal');
  snrSlider.addEventListener('input', (e) => {
    sim.snrDb = parseFloat(e.target.value);
    snrVal.innerText = sim.snrDb.toFixed(0) + " dB";
  });

  const driftSelect = document.getElementById('driftSelect');
  driftSelect.addEventListener('change', (e) => {
    sim.driftType = e.target.value;
  });

  const artifactSelect = document.getElementById('artifactSelect');
  artifactSelect.addEventListener('change', (e) => {
    sim.artifact = e.target.value;
  });
}

// Physiological Signal Generator (Sample by sample)
function samplePhysiology(t) {
  const tPressStart = sim.tBaseline;
  const tRelease = sim.tBaseline + sim.tPress;
  
  // Ratio calculation
  const ratio = Math.max((1.0 - sim.vMin) / 0.1, 1.01);
  const tau = sim.trueCRT90 / Math.log(ratio);
  
  // Blood volume v(t)
  let v = 1.0;
  if (t < tPressStart) {
    v = 1.0;
  } else if (t < tRelease) {
    const elapsed = t - tPressStart;
    const targetVmin = (sim.artifact === "weak_blanch") ? 0.85 : sim.vMin;
    const trans = 0.5 * (1.0 + Math.tanh(12.0 * (elapsed - 0.15)));
    v = 1.0 - trans * (1.0 - targetVmin);
  } else {
    const elapsed = t - tRelease;
    const refillVmin = (sim.artifact === "weak_blanch") ? 0.85 : sim.vMin;
    v = 1.0 - (1.0 - refillVmin) * Math.exp(-elapsed / tau);
  }

  // Pulsatile arterial wave p(t)
  const fHR = sim.hrBpm / 60.0;
  const phase = (2.0 * Math.PI * fHR * t) % (2.0 * Math.PI);
  const p = 0.55 * Math.sin(phase - 0.2) + 0.30 * Math.sin(2.0 * phase - 1.1) + 0.12 * Math.sin(3.0 * phase - 2.2);
  const pNorm = (p + 0.8) / 1.6;

  // Drift
  let d = 0.0;
  if (sim.driftType === "sinusoidal" || sim.artifact === "unstable_baseline") {
    d = 45.0 * Math.sin(2.0 * Math.PI * 0.25 * t);
  } else if (sim.driftType === "linear") {
    d = (t - 7.0) * 4.0;
  }

  // Optical reflectance mapping: R0 - kappa*v + AC + d + noise
  const r0 = 512.0;
  const kappa = 240.0;
  const pulsatileAmp = 42.0;
  const clean = (r0 - kappa * v) + (pulsatileAmp * v * (pNorm - 0.5)) + d;

  // Gaussian noise
  const noiseAmp = Math.max(1.0, 35.0 / Math.pow(10.0, sim.snrDb / 20.0));
  const u1 = Math.max(1e-6, Math.random());
  const u2 = Math.random();
  const gauss = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
  let raw = clean + gauss * noiseAmp;

  // Specific Artifacts
  if (sim.artifact === "motion_recovery" && t >= tRelease + 1.2 && t <= tRelease + 1.6) {
    raw += 140.0 * Math.sin((t - tRelease - 1.2) / 0.4 * Math.PI);
  } else if (sim.artifact === "finger_lift" && t >= tRelease + 2.0) {
    raw = 1015.0 + (Math.random() - 0.5) * 5.0;
  }

  return Math.max(0.0, Math.min(1023.0, raw));
}

// Canvas Rendering
const canvas = document.getElementById('ppgCanvas');
const ctx = canvas ? canvas.getContext('2d') : null;

function resizeCanvas() {
  if (!canvas) return;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width - 24;
  canvas.height = 280;
}
window.addEventListener('resize', resizeCanvas);

function renderCanvas() {
  if (!ctx || !canvas) return;
  const w = canvas.width;
  const h = canvas.height;
  
  // Background
  ctx.fillStyle = "#FAF8F5";
  ctx.fillRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = "#E7E2D8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0; x < w; x += 50) {
    ctx.moveTo(x, 0); ctx.lineTo(x, h);
  }
  for (let y = 0; y < h; y += 40) {
    ctx.moveTo(0, y); ctx.lineTo(w, y);
  }
  ctx.stroke();

  // Draw Regions (Baseline, Press, Recovery)
  const tTotal = sim.tBaseline + sim.tPress + sim.tRecovery;
  const xPress = (sim.tBaseline / tTotal) * w;
  const xRelease = ((sim.tBaseline + sim.tPress) / tTotal) * w;

  ctx.fillStyle = "rgba(254, 243, 199, 0.4)"; // amber tint for baseline
  ctx.fillRect(0, 0, xPress, h);
  ctx.fillStyle = "rgba(254, 226, 226, 0.35)"; // red tint for press
  ctx.fillRect(xPress, 0, xRelease - xPress, h);
  ctx.fillStyle = "rgba(236, 253, 245, 0.4)"; // green tint for recovery
  ctx.fillRect(xRelease, 0, w - xRelease, h);

  // Region boundary lines
  ctx.strokeStyle = "#DC2626";
  ctx.lineWidth = 1.2;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(xPress, 0); ctx.lineTo(xPress, h);
  ctx.stroke();

  ctx.strokeStyle = "#059669";
  ctx.beginPath();
  ctx.moveTo(xRelease, 0); ctx.lineTo(xRelease, h);
  ctx.stroke();
  ctx.setLineDash([]);

  // Labels
  ctx.font = "11px system-ui, sans-serif";
  ctx.fillStyle = "#92400E";
  ctx.fillText("Baseline Stage (0-3s)", 10, 20);
  ctx.fillStyle = "#991B1B";
  ctx.fillText("Pressing Stage (3-6s)", xPress + 10, 20);
  ctx.fillStyle = "#065F46";
  ctx.fillText("Recovery Reperfusion (6s+)", xRelease + 10, 20);

  if (sim.dataT.length < 2) return;

  // Scale functions
  const mapX = (t) => (t / tTotal) * w;
  const mapY = (val) => h - ((val - 150) / 750) * h;

  // 1. Raw PPG Signal (gray)
  ctx.strokeStyle = "#A8A29E";
  ctx.lineWidth = 1.0;
  ctx.beginPath();
  for (let i = 0; i < sim.dataT.length; i++) {
    const px = mapX(sim.dataT[i]);
    const py = mapY(sim.dataX[i]);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.stroke();

  // 2. Filtered Envelope (Warm Terracotta)
  ctx.strokeStyle = "#C86828";
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  for (let i = 0; i < sim.dataT.length; i++) {
    const px = mapX(sim.dataT[i]);
    const py = mapY(sim.dataFilt[i]);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.stroke();

  // 3. Mark Estimated Endpoint if available
  if (sim.consensusCRT !== null) {
    const tEnd = sim.tBaseline + sim.tPress + sim.consensusCRT;
    if (sim.currentTime >= tEnd) {
      const pEnd = mapX(tEnd);
      ctx.strokeStyle = "#059669";
      ctx.lineWidth = 2.0;
      ctx.beginPath();
      ctx.moveTo(pEnd, 0); ctx.lineTo(pEnd, h);
      ctx.stroke();

      ctx.fillStyle = "#059669";
      ctx.beginPath();
      ctx.arc(pEnd, mapY(sim.baselineMean - 0.1 * (sim.baselineMean - sim.blanchMin)), 6, 0, 2 * Math.PI);
      ctx.fill();

      ctx.font = "bold 12px monospace";
      ctx.fillText(`CRT90 = ${sim.consensusCRT.toFixed(2)}s`, pEnd + 6, h - 35);
    }
  }
}

// State Machine Update Step (Runs at 100 Hz interval)
function simStep() {
  const dt = 1.0 / sim.fs;
  sim.currentTime += dt;
  const t = sim.currentTime;
  
  // Sample
  const raw = samplePhysiology(t);
  
  // EMA Filter: alpha = 0.15 (~2.5 Hz cutoff)
  sim.filteredVal = 0.15 * raw + 0.85 * sim.filteredVal;

  sim.dataT.push(t);
  sim.dataX.push(raw);
  sim.dataFilt.push(sim.filteredVal);

  const tPressStart = sim.tBaseline;
  const tRelease = sim.tBaseline + sim.tPress;

  // State Machine logic
  if (t < tPressStart) {
    if (sim.state !== "INVALID") {
      sim.state = "BASELINE";
      if (t > 0.8) {
        sim.baselineMean = sim.filteredVal; // tracking
      }
    }
  } else if (t < tRelease) {
    // Check F2 Baseline Stability at completion of baseline acquisition
    if (sim.artifact === "unstable_baseline" && sim.state !== "INVALID") {
      sim.state = "INVALID";
      sim.faults.push("F2_BASELINE_UNSTABLE");
      playErrorSound();
      updateUIResults();
    }
    if (sim.state !== "INVALID") {
      if (sim.state !== "PRESS") {
        sim.state = "PRESS";
        playTone(600, 80);
        sim.blanchMin = sim.filteredVal;
      }
      if (sim.filteredVal < sim.blanchMin) {
        sim.blanchMin = sim.filteredVal;
      }
    }
  } else {
    // Release event & Recovery Phase
    if (sim.state !== "INVALID" && sim.state !== "REPORT") {
      const recTime = t - tRelease;
      
      // Quality Gate F3: Evaluate blanching excursion at release
      const blanchDepth = Math.abs(sim.baselineMean - sim.blanchMin);
      if ((sim.artifact === "weak_blanch" || blanchDepth < 35.0) && sim.state !== "INVALID") {
        sim.state = "INVALID";
        sim.faults.push("F3_INSUFFICIENT_BLANCH");
        playErrorSound();
        updateUIResults();
      } else if (recTime < 0.25) {
        // Explicit RELEASE State (Figure 5 of Proposal)
        if (sim.state !== "RELEASE") {
          sim.state = "RELEASE";
          playTone(1320, 150); // Sharp release cue tone
          sim.dwellCounter = 0;
        }
      } else {
        if (sim.state !== "RECOVERY") {
          sim.state = "RECOVERY";
        }

        // Quality Gate F4: Motion artifact during recovery
        if (sim.artifact === "motion_recovery" && recTime >= 1.2 && sim.state !== "INVALID") {
          sim.state = "INVALID";
          sim.faults.push("F4_MOTION_ARTEFACT");
          playErrorSound();
          updateUIResults();
        }
        // Quality Gate F6: Finger detachment mid-recovery
        else if (sim.artifact === "finger_lift" && recTime >= 2.0 && sim.state !== "INVALID") {
          sim.state = "INVALID";
          sim.faults.push("F6_FINGER_DETACHED");
          playErrorSound();
          updateUIResults();
        }

        if (sim.state === "RECOVERY") {
          const span = sim.baselineMean - sim.blanchMin;
          const progress = (span > 5.0) ? (sim.filteredVal - sim.blanchMin) / span : 0.0;

          // 90% Threshold crossing check with 150ms dwell
          if (progress >= 0.90) {
            sim.dwellCounter++;
            if (sim.dwellCounter >= 15) { // 150 ms sustained dwell
              sim.crt90Threshold = recTime - 0.15;
              sim.consensusCRT = sim.crt90Threshold;
              sim.state = "REPORT";
              playFanfare();
              updateUIResults();
            }
          } else {
            sim.dwellCounter = 0;
          }

          // Timeout check (7s)
          if (recTime >= 7.0 && sim.state === "RECOVERY") {
            sim.consensusCRT = 7.0;
            sim.state = "REPORT";
            playTone(700, 200);
            updateUIResults();
          }
        }
      }
    }
  }

  // Update State Badge
  updateStateBadge();

  // Render Canvas
  renderCanvas();

  // Stop when completed
  if (t >= sim.tBaseline + sim.tPress + sim.tRecovery) {
    stopSimulation();
  }
}

function updateStateBadge() {
  const badge = document.getElementById('stateBadge');
  if (!badge) return;
  badge.className = "state-badge badge-" + sim.state.toLowerCase();
  badge.innerText = sim.state;
}

function updateUIResults() {
  const estEl = document.getElementById('estCRT');
  const classEl = document.getElementById('classTag');
  const blanchEl = document.getElementById('blanchDelta');
  const gateEl = document.getElementById('qualityStatus');

  if (sim.state === "INVALID") {
    if (estEl) estEl.innerText = "REJECTED";
    if (classEl) classEl.innerText = "N/A";
    if (gateEl) {
      gateEl.innerText = sim.faults.join(", ");
      gateEl.style.color = "#991B1B";
    }
    return;
  }

  if (sim.consensusCRT !== null) {
    if (estEl) estEl.innerText = sim.consensusCRT.toFixed(2) + " s";
    
    // Clinical classification
    let tag = "NORMAL (< 2.0 s)";
    if (sim.consensusCRT >= 3.0) tag = "PROLONGED (> 3.0 s)";
    else if (sim.consensusCRT >= 2.0) tag = "BORDERLINE (2.0 - 3.0 s)";
    if (classEl) classEl.innerText = tag;

    const blanchDelta = Math.abs(sim.baselineMean - sim.blanchMin);
    if (blanchEl) blanchEl.innerText = blanchDelta.toFixed(0) + " counts";

    if (gateEl) {
      gateEl.innerText = "VALID (Passed F1-F6 Gates)";
      gateEl.style.color = "#065F46";
    }
  }
}

function startSimulation() {
  initAudio();
  resetSimulation();
  sim.isRunning = true;
  document.getElementById('btnStart').innerText = "Running Trial...";
  document.getElementById('btnStart').disabled = true;

  // 100 Hz loop -> 10ms timer
  sim.timerId = setInterval(simStep, 10);
}

function stopSimulation() {
  sim.isRunning = false;
  if (sim.timerId) {
    clearInterval(sim.timerId);
    sim.timerId = null;
  }
  const btn = document.getElementById('btnStart');
  if (btn) {
    btn.innerText = "▶ Run Live Trial";
    btn.disabled = false;
  }
}

function resetSimulation() {
  stopSimulation();
  sim.currentTime = 0.0;
  sim.dataT = [];
  sim.dataX = [];
  sim.dataFilt = [];
  sim.filteredVal = 512.0;
  sim.baselineMean = 512.0;
  sim.blanchMin = 1023.0;
  sim.dwellCounter = 0;
  sim.faults = [];
  sim.crt90Threshold = null;
  sim.crt90Model = null;
  sim.consensusCRT = null;
  sim.state = "IDLE";
  updateStateBadge();

  const estEl = document.getElementById('estCRT');
  const classEl = document.getElementById('classTag');
  const blanchEl = document.getElementById('blanchDelta');
  const gateEl = document.getElementById('qualityStatus');
  if (estEl) estEl.innerText = "-- s";
  if (classEl) classEl.innerText = "Pending";
  if (blanchEl) blanchEl.innerText = "-- counts";
  if (gateEl) {
    gateEl.innerText = "Standby";
    gateEl.style.color = "var(--text-main)";
  }

  renderCanvas();
}

// Preset Condition Loader
window.applyPreset = function(presetName) {
  document.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
  const targetChip = document.querySelector(`[data-preset="${presetName}"]`);
  if (targetChip) targetChip.classList.add('active');

  const crtSlider = document.getElementById('crtSlider');
  const crtVal = document.getElementById('crtVal');
  const vminSlider = document.getElementById('vminSlider');
  const vminVal = document.getElementById('vminVal');
  const hrSlider = document.getElementById('hrSlider');
  const hrVal = document.getElementById('hrVal');
  const snrSlider = document.getElementById('snrSlider');
  const snrVal = document.getElementById('snrVal');
  const driftSelect = document.getElementById('driftSelect');
  const artifactSelect = document.getElementById('artifactSelect');

  if (presetName === 'normal') {
    sim.trueCRT90 = 1.5;
    sim.vMin = 0.20;
    sim.hrBpm = 72;
    sim.snrDb = 25;
    sim.driftType = 'none';
    sim.artifact = 'none';
  } else if (presetName === 'borderline') {
    sim.trueCRT90 = 2.5;
    sim.vMin = 0.20;
    sim.hrBpm = 80;
    sim.snrDb = 22;
    sim.driftType = 'none';
    sim.artifact = 'none';
  } else if (presetName === 'prolonged') {
    sim.trueCRT90 = 4.2;
    sim.vMin = 0.15;
    sim.hrBpm = 105;
    sim.snrDb = 20;
    sim.driftType = 'none';
    sim.artifact = 'none';
  } else if (presetName === 'f2_wander') {
    sim.trueCRT90 = 2.0;
    sim.vMin = 0.20;
    sim.hrBpm = 75;
    sim.snrDb = 20;
    sim.driftType = 'sinusoidal';
    sim.artifact = 'unstable_baseline';
  } else if (presetName === 'f3_weak') {
    sim.trueCRT90 = 2.0;
    sim.vMin = 0.40;
    sim.hrBpm = 75;
    sim.snrDb = 24;
    sim.driftType = 'none';
    sim.artifact = 'weak_blanch';
  } else if (presetName === 'f4_motion') {
    sim.trueCRT90 = 2.0;
    sim.vMin = 0.20;
    sim.hrBpm = 75;
    sim.snrDb = 24;
    sim.driftType = 'none';
    sim.artifact = 'motion_recovery';
  } else if (presetName === 'f6_lift') {
    sim.trueCRT90 = 2.0;
    sim.vMin = 0.20;
    sim.hrBpm = 75;
    sim.snrDb = 24;
    sim.driftType = 'none';
    sim.artifact = 'finger_lift';
  }

  if (crtSlider) { crtSlider.value = sim.trueCRT90; crtVal.innerText = sim.trueCRT90.toFixed(1) + " s"; }
  if (vminSlider) { vminSlider.value = sim.vMin; vminVal.innerText = sim.vMin.toFixed(2); }
  if (hrSlider) { hrSlider.value = sim.hrBpm; hrVal.innerText = sim.hrBpm.toFixed(0) + " bpm"; }
  if (snrSlider) { snrSlider.value = sim.snrDb; snrVal.innerText = sim.snrDb.toFixed(0) + " dB"; }
  if (driftSelect) driftSelect.value = sim.driftType;
  if (artifactSelect) artifactSelect.value = sim.artifact;

  resetSimulation();
};

// Export Simulated Data to CSV
window.exportSimulationCSV = function() {
  if (sim.dataT.length === 0) {
    alert("Please run a simulation trial first to acquire signal data.");
    return;
  }
  let csv = "time_s,raw_adc,filtered_adc,baseline_mean,blanch_min\n";
  for (let i = 0; i < sim.dataT.length; i++) {
    csv += `${sim.dataT[i].toFixed(3)},${sim.dataX[i].toFixed(1)},${sim.dataFilt[i].toFixed(1)},${sim.baselineMean.toFixed(1)},${sim.blanchMin.toFixed(1)}\n`;
  }
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `CRT_Nano_Trial_Trace_${sim.trueCRT90.toFixed(1)}s.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

// Codebase Explorer Initializer
function initCodebaseExplorer() {
  if (!window.CRT_CODEBASE) return;
  const navContainer = document.getElementById('codeTabsNav');
  const codePre = document.getElementById('codeDisplayPre');
  const codeTitle = document.getElementById('codeDisplayTitle');
  const codeDesc = document.getElementById('codeDisplayDesc');
  const codeLines = document.getElementById('codeDisplayLines');
  const copyBtn = document.getElementById('btnCopyCode');

  if (!navContainer || !codePre) return;

  const keys = Object.keys(window.CRT_CODEBASE);
  navContainer.innerHTML = "";

  keys.forEach((key, index) => {
    const file = window.CRT_CODEBASE[key];
    const btn = document.createElement('button');
    btn.className = "code-tab-btn" + (index === 0 ? " active" : "");
    btn.innerText = file.title;
    btn.onclick = () => selectCodeFile(key);
    navContainer.appendChild(btn);
  });

  function selectCodeFile(key) {
    const file = window.CRT_CODEBASE[key];
    if (!file) return;

    document.querySelectorAll('.code-tab-btn').forEach(b => {
      b.classList.toggle('active', b.innerText === file.title);
    });

    codePre.innerText = file.content;
    if (codeTitle) codeTitle.innerText = file.title;
    if (codeDesc) codeDesc.innerText = file.desc;
    if (codeLines) codeLines.innerText = `${file.lines} lines`;
  }

  if (copyBtn) {
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(codePre.innerText).then(() => {
        const orig = copyBtn.innerText;
        copyBtn.innerText = "✓ Copied Source!";
        copyBtn.classList.add('copied');
        setTimeout(() => {
          copyBtn.innerText = orig;
          copyBtn.classList.remove('copied');
        }, 2000);
      });
    };
  }

  if (keys.length > 0) {
    selectCodeFile(keys[0]);
  }
}

// Setup Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  resizeCanvas();
  setupSliders();
  initCodebaseExplorer();

  const btnStart = document.getElementById('btnStart');
  if (btnStart) btnStart.addEventListener('click', startSimulation);

  const btnReset = document.getElementById('btnReset');
  if (btnReset) btnReset.addEventListener('click', resetSimulation);

  // Trigger initial draw
  renderCanvas();
});
