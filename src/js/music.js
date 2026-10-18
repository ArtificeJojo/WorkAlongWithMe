// Background music for the quests, made live in the browser with Web Audio (no music files).
// Moods:  Music.play("calm" | "suspense" | "evil" | "victory")   Music.stop()
// Also:   Music.cackle()  a booming, echoing monster laugh for MEGA-BUG
//         Music.enabled = false to mute.  The music dips automatically while a character talks.
(function () {
  let ctx = null, master = null, bus = null, mood = null, step = 0, nextTime = 0, timer = null;
  const VOLUME = 0.7;
  const N = n => 440 * Math.pow(2, (n - 69) / 12);  // MIDI note -> Hz

  function init() {
    if (ctx) return true;
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      master = ctx.createGain(); master.gain.value = 0; master.connect(ctx.destination);
      // A soft echo makes everything sound roomier.
      bus = ctx.createGain(); bus.connect(master);
      const echo = ctx.createDelay(); echo.delayTime.value = 0.32;
      const fb = ctx.createGain(); fb.gain.value = 0.28;
      const wet = ctx.createGain(); wet.gain.value = 0.3;
      bus.connect(echo); echo.connect(fb); fb.connect(echo); echo.connect(wet); wet.connect(master);
      return true;
    } catch { return false; }
  }

  // One note with a simple envelope.
  function tone(freq, t, dur, { type = "triangle", vol = 0.3, attack = 0.01, filter = null, glide = null } = {}) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (glide) o.frequency.exponentialRampToValueAtTime(glide, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    let out = o;
    if (filter) { const f = ctx.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = filter; o.connect(f); out = f; }
    out.connect(g); g.connect(bus);
    o.start(t); o.stop(t + dur + 0.05);
  }
  const drum = (t, freq = 90, vol = 0.6, dur = 0.35) => tone(freq, t, dur, { type: "sine", vol, glide: Math.max(30, freq * 0.4) });

  // Each mood: seconds per step, and what plays on each step.
  const MOODS = {
    // Peaceful: a gentle pentatonic arpeggio over soft chords (C, Am, F, G).
    calm: {
      beat: 0.4,
      play(i, t) {
        const chords = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]];
        const c = chords[Math.floor(i / 8) % 4];
        const arp = [0, 1, 2, 1, 2, 1, 0, 2][i % 8];
        tone(N(c[arp] + 12), t, 0.7, { vol: 0.12 });
        if (i % 8 === 0) c.forEach(n => tone(N(n - 12), t, 3.2, { type: "sine", vol: 0.06, attack: 0.6 }));
        if (i % 16 === 6) tone(N(c[2] + 24), t, 1.2, { type: "sine", vol: 0.05 });
      },
    },
    // Suspense: a low, uneasy drone, a slow heartbeat and creepy high notes.
    suspense: {
      beat: 0.5,
      play(i, t) {
        if (i % 8 === 0) { tone(N(38), t, 4.2, { type: "sawtooth", vol: 0.07, attack: 1, filter: 240 }); tone(N(39), t, 4.2, { type: "sine", vol: 0.04, attack: 1.5 }); }
        if (i % 4 === 0) { drum(t, 70, 0.55); drum(t + 0.22, 60, 0.4); }
        if (i % 8 === 5) tone(N(i % 16 === 5 ? 86 : 85), t, 1.6, { type: "sine", vol: 0.035, attack: 0.5 });
      },
    },
    // Evil: a menacing minor bass riff, war drums and a dark organ.
    evil: {
      beat: 0.22,
      play(i, t) {
        const riff = [38, 38, 41, 38, 44, 43, 41, 36];
        tone(N(riff[i % 8]), t, 0.2, { type: "sawtooth", vol: 0.13, filter: 600 });
        if (i % 4 === 0) drum(t, 80, 0.7);
        if (i % 8 === 6) drum(t, 110, 0.4, 0.2);
        if (i % 16 === 0) [50, 53, 56].forEach(n => tone(N(n), t, 3.4, { type: "square", vol: 0.025, attack: 0.3, filter: 900 }));
        if (i % 32 === 24) tone(N(74), t, 1.2, { type: "sawtooth", vol: 0.04, glide: N(62), filter: 1800 });
      },
    },
    // Victory: a bright, bouncy celebration.
    victory: {
      beat: 0.17,
      play(i, t) {
        const melody = [72, 76, 79, 84, 79, 84, 88, 0, 86, 84, 81, 84, 79, 0, 76, 79];
        const m = melody[i % 16];
        if (m) tone(N(m), t, 0.22, { type: "square", vol: 0.07, filter: 3500 });
        const bass = [48, 48, 55, 55, 53, 53, 55, 55][Math.floor(i / 2) % 8];
        if (i % 2 === 0) tone(N(bass), t, 0.3, { type: "triangle", vol: 0.16 });
        if (i % 4 === 0) drum(t, 120, 0.35, 0.18);
        if (i % 4 === 2) tone(8000, t, 0.05, { type: "square", vol: 0.015 });
      },
    },
  };

  function tick() {
    if (!mood) return;
    const m = MOODS[mood];
    while (nextTime < ctx.currentTime + 0.25) {
      m.play(step++, nextTime);
      nextTime += m.beat;
    }
    // Dip the music while someone is talking (their words are highlighted on screen).
    const talking = !!document.querySelector(".line.karaoke");
    const target = Music.enabled ? VOLUME * (talking ? 0.5 : 1) : 0;
    master.gain.setTargetAtTime(target, ctx.currentTime, 0.3);
  }

  const Music = {
    enabled: true,
    // For checking it's running: the audio state, the mood, and the current volume.
    status: () => ({ audio: ctx ? ctx.state : "not started", mood, volume: master ? +master.gain.value.toFixed(3) : 0 }),
    play(name) {
      if (!MOODS[name] || name === mood || !init()) return;
      if (ctx.state === "suspended") ctx.resume().catch(() => {});
      // Fade out, switch, fade back in.
      master.gain.setTargetAtTime(0, ctx.currentTime, 0.15);
      setTimeout(() => {
        mood = name; step = 0; nextTime = ctx.currentTime + 0.05;
        if (!timer) timer = setInterval(tick, 100);
      }, mood ? 450 : 0);
    },
    stop() {
      mood = null;
      if (ctx) master.gain.setTargetAtTime(0, ctx.currentTime, 0.2);
    },
    // The Time Eater's evil laugh, synthesized like a real voice: a buzzing throat sound shaped into "ha"
    // by vowel filters, a breathy "h" at the start of each burst, wobbling pitch, then a deep breath in.
    cackle() {
      if (!Music.enabled || !init()) return;
      const t0 = ctx.currentTime + 0.05;
      const out = ctx.createGain(); out.gain.value = 1.1;
      // a big, dark room
      const verb = ctx.createConvolver(), len = ctx.sampleRate * 2.2, ir = ctx.createBuffer(2, len, ctx.sampleRate);
      for (let c = 0; c < 2; c++) { const d = ir.getChannelData(c); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3); }
      verb.buffer = ir;
      const wet = ctx.createGain(); wet.gain.value = 0.45;
      out.connect(ctx.destination); out.connect(verb); verb.connect(wet); wet.connect(ctx.destination);
      const noiseBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate), nd = noiseBuf.getChannelData(0);
      for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
      // one "ha": pitch (Hz), loudness, length (s)
      const ha = (t, pitch, loud, dur) => {
        const formants = [[700, 1, 6], [1150, 0.6, 8], [2500, 0.25, 10]];  // the "ah" vowel
        const voice = ctx.createOscillator(); voice.type = "sawtooth";
        voice.frequency.setValueAtTime(pitch * 1.08, t);
        voice.frequency.linearRampToValueAtTime(pitch * 1.18, t + dur * 0.3);
        voice.frequency.exponentialRampToValueAtTime(pitch * 0.82, t + dur);
        const vib = ctx.createOscillator(), vibG = ctx.createGain(); vib.frequency.value = 6.5; vibG.gain.value = pitch * 0.03;
        vib.connect(vibG); vibG.connect(voice.frequency);
        const vg = ctx.createGain();
        vg.gain.setValueAtTime(0.0001, t + 0.04); vg.gain.exponentialRampToValueAtTime(loud, t + 0.07); vg.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        formants.forEach(([f, g, q]) => { const bp = ctx.createBiquadFilter(), fg = ctx.createGain(); bp.type = "bandpass"; bp.frequency.value = f; bp.Q.value = q; fg.gain.value = g * 4; voice.connect(bp); bp.connect(fg); fg.connect(vg); });
        vg.connect(out);
        // the breathy "h"
        const h = ctx.createBufferSource(); h.buffer = noiseBuf;
        const hf = ctx.createBiquadFilter(); hf.type = "bandpass"; hf.frequency.value = 1400; hf.Q.value = 1;
        const hg = ctx.createGain(); hg.gain.setValueAtTime(0.0001, t); hg.gain.exponentialRampToValueAtTime(loud * 0.5, t + 0.03); hg.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
        h.connect(hf); hf.connect(hg); hg.connect(out);
        [voice, vib].forEach(o => { o.start(t); o.stop(t + dur + 0.05); }); h.start(t); h.stop(t + 0.12);
      };
      // a low chuckle building up... then the big laugh, sliding down... then a breath in
      let t = t0;
      [[95, 0.25, 0.16], [92, 0.28, 0.16], [90, 0.3, 0.18]].forEach(([p, l, d]) => { ha(t, p, l, d); t += d + 0.08; });
      t += 0.15;
      [[150, 0.6, 0.2], [142, 0.65, 0.2], [135, 0.65, 0.2], [126, 0.6, 0.2], [118, 0.55, 0.21], [108, 0.5, 0.5]].forEach(([p, l, d]) => { ha(t, p, l, d); t += d + 0.04; });
      const inhale = ctx.createBufferSource(); inhale.buffer = noiseBuf;
      const ifl = ctx.createBiquadFilter(); ifl.type = "bandpass"; ifl.Q.value = 2;
      ifl.frequency.setValueAtTime(600, t + 0.1); ifl.frequency.linearRampToValueAtTime(1800, t + 0.7);
      const ig = ctx.createGain(); ig.gain.setValueAtTime(0.0001, t + 0.1); ig.gain.exponentialRampToValueAtTime(0.25, t + 0.5); ig.gain.exponentialRampToValueAtTime(0.0001, t + 0.8);
      inhale.connect(ifl); ifl.connect(ig); ig.connect(out); inhale.start(t + 0.1); inhale.stop(t + 0.85);
    },
    // A rising "whoop" as the Time Eater shrinks down into tiny bugs.
    shrink() {
      if (!Music.enabled || !init()) return;
      const t = ctx.currentTime + 0.02, o = ctx.createOscillator(), g = ctx.createGain();
      o.type = "square";
      o.frequency.setValueAtTime(90, t); o.frequency.exponentialRampToValueAtTime(1800, t + 0.8);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.18, t + 0.05); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.85);
      const f = ctx.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = 3000;
      o.connect(f); f.connect(g); g.connect(ctx.destination); o.start(t); o.stop(t + 0.9);
      [0, 1, 2, 3, 4].forEach(k => {  // five little "pops" as the pieces appear
        const p = ctx.createOscillator(), pg = ctx.createGain(), pt = t + 0.8 + k * 0.07;
        p.frequency.setValueAtTime(900 + k * 150, pt); pg.gain.setValueAtTime(0.15, pt); pg.gain.exponentialRampToValueAtTime(0.0001, pt + 0.08);
        p.connect(pg); pg.connect(ctx.destination); p.start(pt); p.stop(pt + 0.1);
      });
    },
    // Chomping, crunching and a big gulp, for the Time Eater gobbling the schedule.
    gobble() {
      if (!Music.enabled || !init()) return;
      const noiseBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate), nd = noiseBuf.getChannelData(0);
      for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
      const burst = (t, freq, type, vol, dur) => {
        const n = ctx.createBufferSource(); n.buffer = noiseBuf;
        const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq;
        const g = ctx.createGain(); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        n.connect(f); f.connect(g); g.connect(ctx.destination); n.start(t, Math.random() * 0.5); n.stop(t + dur + 0.02);
      };
      const thud = (t, vol) => { const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.setValueAtTime(110, t); o.frequency.exponentialRampToValueAtTime(45, t + 0.15); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.18); o.connect(g); g.connect(ctx.destination); o.start(t); o.stop(t + 0.2); };
      const t0 = ctx.currentTime + 0.05;
      for (let k = 0; k < 6; k++) {
        const t = t0 + k * 0.3;
        thud(t, 0.7);                                               // CHOMP (jaws closing)
        burst(t, 900, "lowpass", 0.6, 0.09);
        for (let c = 0; c < 4; c++) burst(t + 0.05 + c * 0.035, 3000 + Math.random() * 2500, "highpass", 0.35, 0.03);  // crunchy bits
      }
      const gt = t0 + 6 * 0.3 + 0.15;                               // the big GULP
      const o = ctx.createOscillator(), g = ctx.createGain(); o.type = "sine";
      o.frequency.setValueAtTime(380, gt); o.frequency.exponentialRampToValueAtTime(70, gt + 0.35);
      g.gain.setValueAtTime(0.0001, gt); g.gain.exponentialRampToValueAtTime(0.8, gt + 0.03); g.gain.exponentialRampToValueAtTime(0.0001, gt + 0.4);
      o.connect(g); g.connect(ctx.destination); o.start(gt); o.stop(gt + 0.45);
      burst(gt + 0.4, 400, "lowpass", 0.3, 0.25);                  // a satisfied burp-rumble
    },
  };
  // Storm sound effects: steady rain, gusting wind and rolling thunder, faded in and out.
  let storm = null;
  Music.storm = function (on) {
    if (!init()) return;
    if (on && !storm && Music.enabled) {
      const len = ctx.sampleRate * 2, buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      const noise = () => { const n = ctx.createBufferSource(); n.buffer = buf; n.loop = true; return n; };
      const out = ctx.createGain(); out.gain.value = 0.0001; out.connect(ctx.destination);
      out.gain.exponentialRampToValueAtTime(0.5, ctx.currentTime + 1.5);
      const rain = noise(), rainF = ctx.createBiquadFilter(); rainF.type = "highpass"; rainF.frequency.value = 2500;
      const rainG = ctx.createGain(); rainG.gain.value = 0.35; rain.connect(rainF); rainF.connect(rainG); rainG.connect(out);
      const wind = noise(), windF = ctx.createBiquadFilter(); windF.type = "bandpass"; windF.frequency.value = 400; windF.Q.value = 3;
      const windG = ctx.createGain(); windG.gain.value = 0.8; wind.connect(windF); windF.connect(windG); windG.connect(out);
      const lfo = ctx.createOscillator(), lfoG = ctx.createGain(); lfo.frequency.value = 0.18; lfoG.gain.value = 280;  // gusts
      lfo.connect(lfoG); lfoG.connect(windF.frequency);
      rain.start(); wind.start(); lfo.start();
      const thunder = () => {
        const t = ctx.currentTime, n = noise(), f = ctx.createBiquadFilter(), g = ctx.createGain();
        f.type = "lowpass"; f.frequency.value = 180;
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(1.2, t + 0.08); g.gain.exponentialRampToValueAtTime(0.0001, t + 2.6);
        n.connect(f); f.connect(g); g.connect(out); n.start(t); n.stop(t + 2.8);
      };
      thunder();
      storm = { out, nodes: [rain, wind, lfo], timer: setInterval(thunder, 4200) };
    } else if (!on && storm) {
      const s = storm; storm = null;
      clearInterval(s.timer);
      s.out.gain.setTargetAtTime(0.0001, ctx.currentTime, 0.6);
      setTimeout(() => { s.nodes.forEach(n => { try { n.stop(); } catch {} }); s.out.disconnect(); }, 3000);
    }
  };
  window.Music = Music;
})();
