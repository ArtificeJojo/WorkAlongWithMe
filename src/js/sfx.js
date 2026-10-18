// Sound effects for the Land of Cooooode, made live with the Web Audio API
// (no audio files, nothing to license). Usage: Sfx.play("splash"); Sfx.enabled = false to mute.
// Browsers only allow sound after the person clicks something, so the first
// Sfx.play() should happen inside a click handler (e.g. "Start the adventure").
(function () {
  let ctx = null;
  let master = null;
  const Sfx = { enabled: true, volume: 0.5 };

  function audio() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = Sfx.volume;
      master.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  // ---- building blocks
  function tone({ type = "sine", from = 440, to = from, start = 0, dur = 0.15, vol = 0.4, attack = 0.005 }) {
    const a = audio(); if (!a) return;
    const t = a.currentTime + start;
    const osc = a.createOscillator();
    const g = a.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(from, t);
    osc.frequency.exponentialRampToValueAtTime(Math.max(20, to), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    osc.connect(g).connect(master);
    osc.start(t); osc.stop(t + dur + 0.05);
  }

  let noiseBuffer = null;
  function noise({ start = 0, dur = 0.3, vol = 0.4, filter = "lowpass", from = 1200, to = from, q = 0.8, attack = 0.01 }) {
    const a = audio(); if (!a) return;
    if (!noiseBuffer) {
      noiseBuffer = a.createBuffer(1, a.sampleRate * 2, a.sampleRate);
      const d = noiseBuffer.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    const t = a.currentTime + start;
    const src = a.createBufferSource();
    src.buffer = noiseBuffer;
    const f = a.createBiquadFilter();
    f.type = filter; f.Q.value = q;
    f.frequency.setValueAtTime(from, t);
    f.frequency.exponentialRampToValueAtTime(Math.max(30, to), t + dur);
    const g = a.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f).connect(g).connect(master);
    src.start(t, Math.random()); src.stop(t + dur + 0.05);
  }

  const notes = (list, { type = "square", gap = 0.09, dur = 0.12, vol = 0.18, start = 0 } = {}) =>
    list.forEach((f, i) => tone({ type, from: f, start: start + i * gap, dur, vol }));

  // ---- the sound library
  const SOUNDS = {
    // UI
    select: () => { tone({ type: "triangle", from: 520, to: 780, dur: 0.08, vol: 0.25 }); },
    toggle: () => { tone({ type: "triangle", from: 660, to: 440, dur: 0.07, vol: 0.2 }); },
    next: () => { noise({ filter: "bandpass", from: 600, to: 2400, dur: 0.18, vol: 0.12, q: 1.5 }); tone({ type: "sine", from: 380, to: 620, dur: 0.12, vol: 0.12 }); },
    back: () => { tone({ type: "triangle", from: 500, to: 330, dur: 0.1, vol: 0.18 }); },
    start: () => notes([392, 523, 659, 784], { type: "square", gap: 0.07, vol: 0.14 }),

    // water
    bubbles: () => { for (let i = 0; i < 6; i++) tone({ type: "sine", from: 300 + Math.random() * 300, to: 900 + Math.random() * 500, start: i * 0.17, dur: 0.07, vol: 0.18 }); },
    splash: () => {
      noise({ filter: "lowpass", from: 3500, to: 300, dur: 0.9, vol: 0.55, attack: 0.008 });
      noise({ filter: "highpass", from: 2500, to: 5000, dur: 0.35, vol: 0.18, start: 0.03 });
      tone({ type: "sine", from: 180, to: 60, dur: 0.3, vol: 0.35 });
      for (let i = 0; i < 6; i++) tone({ type: "sine", from: 900 + Math.random() * 900, to: 400, start: 0.25 + i * 0.07, dur: 0.06, vol: 0.12 });
    },
    swim: () => { for (let i = 0; i < 5; i++) noise({ filter: "bandpass", from: 500, to: 900, q: 2, start: i * 0.45, dur: 0.35, vol: 0.14 }); },
    ripple: () => { tone({ type: "sine", from: 700, to: 300, dur: 0.25, vol: 0.15 }); },

    // Kanban Swamp
    sparkle: () => notes([1046, 1318, 1568, 2093], { type: "sine", gap: 0.05, dur: 0.15, vol: 0.12 }),
    clunk: () => { tone({ type: "square", from: 160, to: 90, dur: 0.12, vol: 0.25 }); noise({ filter: "lowpass", from: 900, to: 200, dur: 0.12, vol: 0.2 }); },
    pops: () => { for (let i = 0; i < 5; i++) tone({ type: "sine", from: 500 + i * 120, to: 1200 + i * 150, start: i * 0.12, dur: 0.06, vol: 0.25 }); },
    whoosh: () => { noise({ filter: "bandpass", from: 300, to: 3000, q: 1.2, dur: 0.6, vol: 0.35, attack: 0.15 }); },
    boom: () => { tone({ type: "sine", from: 120, to: 40, dur: 0.5, vol: 0.45 }); noise({ filter: "lowpass", from: 1500, to: 100, dur: 0.6, vol: 0.35 }); notes([523, 659, 784, 1046], { start: 0.35, gap: 0.05, vol: 0.1 }); },
    planks: () => { for (let i = 0; i < 4; i++) { tone({ type: "triangle", from: 260 - i * 10, to: 140, start: i * 0.2, dur: 0.09, vol: 0.3 }); noise({ filter: "bandpass", from: 1800, q: 3, start: i * 0.2, dur: 0.05, vol: 0.15 }); } },
    boing: () => { tone({ type: "sine", from: 150, to: 600, dur: 0.18, vol: 0.3 }); tone({ type: "sine", from: 600, to: 200, start: 0.18, dur: 0.25, vol: 0.2 }); },
    unlock: () => { tone({ type: "square", from: 880, dur: 0.06, vol: 0.12 }); tone({ type: "square", from: 1320, start: 0.08, dur: 0.06, vol: 0.12 }); noise({ filter: "highpass", from: 3000, start: 0.15, dur: 0.08, vol: 0.12 }); notes([523, 784, 1046], { start: 0.25, gap: 0.08, vol: 0.12, type: "triangle" }); },
    rocket: () => { noise({ filter: "lowpass", from: 400, to: 4000, dur: 1.8, vol: 0.4, attack: 0.3 }); tone({ type: "sawtooth", from: 80, to: 400, dur: 1.6, vol: 0.12, attack: 0.3 }); },

    // Ping Pond
    clink: () => { tone({ type: "sine", from: 2200, to: 2000, dur: 0.25, vol: 0.15 }); tone({ type: "sine", from: 3100, to: 2900, start: 0.04, dur: 0.2, vol: 0.1 }); },
    tick: () => { for (let i = 0; i < 4; i++) tone({ type: "square", from: i % 2 ? 1500 : 1200, start: i * 0.25, dur: 0.03, vol: 0.12 }); },
    ribbit: () => { for (let i = 0; i < 2; i++) { tone({ type: "sawtooth", from: 180, to: 320, start: i * 0.22, dur: 0.12, vol: 0.18 }); tone({ type: "square", from: 140, to: 260, start: i * 0.22 + 0.02, dur: 0.1, vol: 0.08 }); } },
    thunder: () => { noise({ filter: "lowpass", from: 600, to: 60, dur: 1.4, vol: 0.4, attack: 0.05 }); noise({ filter: "lowpass", from: 300, to: 50, start: 0.3, dur: 1.2, vol: 0.3 }); },
    calm: () => notes([523, 659, 784], { type: "sine", gap: 0.12, dur: 0.4, vol: 0.12 }),
    fanfare: () => notes([392, 392, 523, 659, 523, 659, 784], { type: "square", gap: 0.11, dur: 0.13, vol: 0.13 }),

    // rewards
    success: () => notes([523, 659, 784, 1046, 784, 1046], { type: "square", gap: 0.09, dur: 0.14, vol: 0.14 }),
    badge: () => { notes([784, 988, 1318], { type: "triangle", gap: 0.1, dur: 0.3, vol: 0.16 }); tone({ type: "sine", from: 2637, start: 0.32, dur: 0.6, vol: 0.08 }); },
  };

  Sfx.play = (name) => {
    if (!Sfx.enabled) return;
    try { (SOUNDS[name] || SOUNDS.select)(); } catch {}
  };
  Sfx.names = Object.keys(SOUNDS);
  window.Sfx = Sfx;
})();
