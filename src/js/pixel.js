// Pixel characters for the Land of Cooooode, built from textured blocks (a blocky voxel style, all original).
// Usage:
//   const chomp = Pixel.mount(element, "chomp", { size: 240 });
//   chomp.setMood("talk" | "idle" | "celebrate");   chomp.setStill(true) for calm mode
//   chomp.setMouth(true | false | null)  lip-sync: open, shut, or automatic
// Characters: "chomp", "ponder", "megabug", "tinybug".
(function () {
  const OUTLINE = "#1b1f1a";

  // Block materials: base color, speckle colors (the texture), and light/dark shades for 3D-looking faces.
  const M = {
    green:   { base: "#5fae3c", spk: ["#53a034", "#6cbd47", "#4f962f"], light: "#7fcc58", dark: "#3f7f27" },
    greenDk: { base: "#3f7f27", spk: ["#376f22", "#468b2c"], light: "#4f9332", dark: "#2e5f1c" },
    belly:   { base: "#d3eaa2", spk: ["#c4df90", "#dcf0b0"], light: "#e6f6c0", dark: "#b2cf7c" },
    belt:    { base: "#d9822b", spk: ["#c97422", "#e38f37"], light: "#efa04a", dark: "#a95f1b" },
    gold:    { base: "#f4cf3a", spk: ["#e6bf2b"], light: "#fde06a", dark: "#c99f1c" },
    skin:    { base: "#9fd36a", spk: ["#92c75e", "#acdc78"], light: "#bce68c", dark: "#73a648" },
    skinDk:  { base: "#73a648", spk: ["#679a3f"], light: "#86b956", dark: "#5c8a37" },
    shell:   { base: "#2f8f7c", spk: ["#28806f", "#37a08b", "#257565"], light: "#47b39c", dark: "#1f6a5b" },
    plate:   { base: "#62c3a6", spk: ["#55b597", "#70cfb2"], light: "#86dcc0", dark: "#3f9c81" },
    rim:     { base: "#d9b066", spk: ["#c99f57", "#e3bd75"], light: "#ecca86", dark: "#a8833f" },
    lily:    { base: "#4fae5c", spk: ["#45a052", "#5bbd68"], light: "#6fcc7a", dark: "#357a3f" },
    bug:     { base: "#b04cc0", spk: ["#a043b0", "#bf5bcf", "#9a3fab"], light: "#d17ade", dark: "#7c2e8c" },
    bugDk:   { base: "#7c2e8c", spk: ["#6e2780"], light: "#8f3aa0", dark: "#5c2069" },
    paper:   { base: "#f6f1df", spk: ["#ebe4cc"], light: "#fffaea", dark: "#d8cfb2" },
  };
  const FLAT = { white: "#ffffff", black: "#141414", mouth: "#6e1f2d", tongue: "#e9798a", blush: "#ef9aa6", pink: "#f39ac1",
                 yellow: "#ffe55c", glitch: "#3fe8ec", ink: "#8d8574", tooth: "#fffbe8", spark: "#ffe14a" };

  // Same texture every time for the same pixel, so nothing flickers between frames.
  const hash = (x, y, s) => { let h = (x * 374761393 + y * 668265263 + s * 2147483647) | 0; h = (h ^ (h >>> 13)) * 1274126177; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };

  function canvas(w, h) {
    const px = Array.from({ length: h }, () => Array(w).fill(null));
    const set = (x, y, c) => { if (x >= 0 && y >= 0 && x < w && y < h) px[y][x] = c; };
    return {
      w, h, px, set,
      // A textured block with a lit top edge and a shaded right/bottom edge.
      box(x, y, bw, bh, mat, seed = 1) {
        const m = M[mat];
        for (let j = 0; j < bh; j++) for (let i = 0; i < bw; i++) {
          let c = m.base;
          const r = hash(x + i, y + j, seed);
          if (r < 0.32) c = m.spk[Math.floor(r * 100) % m.spk.length];
          if (j === 0 && bh > 2) c = m.light;
          else if ((i === bw - 1 && bw > 2) || (j === bh - 1 && bh > 2)) c = m.dark;
          set(x + i, y + j, c);
        }
      },
      fill(x, y, bw, bh, color) { for (let j = 0; j < bh; j++) for (let i = 0; i < bw; i++) set(x + i, y + j, color); },
    };
  }

  // Turns the pixel grid into SVG rects (runs of the same color merged), with a 1-pixel outline around the shape.
  function toSprite(cv, label) {
    const { w, h, px } = cv;
    const W = w + 2, H = h + 2;
    const out = Array.from({ length: H }, () => Array(W).fill(null));
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (px[y][x]) out[y + 1][x + 1] = px[y][x];
    const solid = (x, y) => out[y] && out[y][x] && out[y][x] !== OUTLINE;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (!out[y][x] && (solid(x - 1, y) || solid(x + 1, y) || solid(x, y - 1) || solid(x, y + 1))) out[y][x] = OUTLINE;
    }
    let svg = "";
    for (let y = 0; y < H; y++) {
      let x = 0;
      while (x < W) {
        const c = out[y][x];
        if (!c) { x++; continue; }
        let run = 1;
        while (x + run < W && out[y][x + run] === c) run++;
        svg += `<rect x="${x}" y="${y}" width="${run}" height="1" fill="${c}"/>`;
        x += run;
      }
    }
    return { width: W, height: H, label, svg, pixel: true };
  }

  // ---------------------------------------------------------------- Chomp the Gator (faces right)
  function chomp({ blink = false, mouthOpen = false, armsUp = false } = {}) {
    const c = canvas(40, 34);
    c.box(1, 20, 9, 4, "green", 2); c.box(0, 22, 3, 3, "green", 3);                 // tail
    c.box(11, 27, 5, 5, "green", 4); c.box(19, 27, 5, 5, "green", 5);               // legs
    c.box(10, 31, 7, 2, "greenDk"); c.box(18, 31, 7, 2, "greenDk");                 // feet
    if (armsUp) c.box(6, 7, 3, 9, "green", 6); else c.box(7, 16, 3, 8, "green", 6);  // back arm
    c.box(9, 14, 17, 14, "green", 7);                                                // body
    c.box(16, 16, 9, 10, "belly", 8);                                                // belly
    for (const y of [18, 21]) c.fill(16, y, 9, 1, M.belly.dark);
    for (const y of [15, 18, 21]) c.set(8, y, M.green.dark);                         // back ridge
    c.box(9, 24, 17, 2, "belt"); c.box(18, 24, 3, 2, "gold");                        // belt + buckle
    c.box(10, 4, 15, 11, "green", 9);                                                // head
    c.box(12, 1, 5, 4, "green", 10); c.box(18, 1, 5, 4, "green", 11);               // eye bumps
    if (mouthOpen) {
      c.box(24, 3, 14, 4, "green", 12);                                              // top jaw, lifted
      c.fill(24, 7, 13, 5, FLAT.mouth); c.fill(27, 10, 7, 2, FLAT.tongue);
      for (const x of [26, 29, 32, 35]) c.set(x, 7, FLAT.tooth);
      for (const x of [28, 31, 34]) c.set(x, 11, FLAT.tooth);
      c.box(24, 12, 13, 2, "green", 13);                                             // lower jaw
      c.set(36, 4, OUTLINE);
    } else {
      c.box(24, 6, 14, 4, "green", 12);                                              // top jaw
      c.fill(24, 10, 13, 1, OUTLINE);                                                 // closed mouth line
      for (const x of [26, 29, 32]) c.set(x, 10, FLAT.tooth);
      c.box(24, 11, 13, 3, "green", 13);                                             // lower jaw
      c.set(36, 7, OUTLINE);                                                         // nostril
    }
    c.fill(21, mouthOpen ? 13 : 12, 2, 1, FLAT.blush);
    if (blink) { c.fill(13, 3, 3, 1, OUTLINE); c.fill(19, 3, 3, 1, OUTLINE); }
    else {
      c.fill(13, 2, 3, 2, FLAT.white); c.fill(19, 2, 3, 2, FLAT.white);
      c.fill(15, 2, 1, 2, FLAT.black); c.fill(21, 2, 1, 2, FLAT.black);
    }
    if (armsUp) { c.box(26, 15, 8, 3, "green", 14); c.box(33, 11, 3, 5, "green", 15); } // front arm waving
    else c.box(25, 16, 3, 8, "green", 14);
    if (armsUp) for (const [x, y] of [[2, 4], [38, 18], [4, 12]]) { c.set(x, y, FLAT.spark); c.set(x - 1, y, FLAT.spark); c.set(x + 1, y, FLAT.spark); c.set(x, y - 1, FLAT.spark); c.set(x, y + 1, FLAT.spark); }
    return toSprite(c, "Chomp the Gator");
  }

  // ---------------------------------------------------------------- Ponder the Turtle (faces right)
  function ponder({ blink = false, mouthOpen = false, armsUp = false } = {}) {
    const c = canvas(42, 27);
    c.box(0, 16, 5, 2, "skin", 2);                                                   // tail
    c.box(7, 19, 5, 6, "skin", 3); c.box(23, 19, 5, 6, "skin", 4);                   // legs
    c.fill(7, 24, 5, 1, M.skinDk.dark); c.fill(23, 24, 5, 1, M.skinDk.dark);
    c.box(30, 11, 4, 8, "skin", 5);                                                  // neck
    c.box(31, 4, 10, 9, "skin", 6);                                                  // head
    c.box(9, 4, 18, 3, "shell", 7); c.box(6, 7, 24, 4, "shell", 8); c.box(4, 11, 28, 6, "shell", 9);
    for (const [x, y, w, h] of [[11, 5, 5, 3], [19, 5, 5, 3], [8, 9, 5, 3], [15, 9, 6, 3], [23, 9, 5, 3], [6, 13, 6, 3], [14, 13, 7, 3], [23, 13, 6, 3]]) c.box(x, y, w, h, "plate", x * y);
    c.box(3, 17, 30, 2, "rim", 10);                                                  // shell rim
    c.box(30, 2, 12, 2, "lily", 11); c.set(38, 2, M.lily.dark);                       // lily pad hat
    c.fill(32, 0, 3, 2, FLAT.pink); c.set(33, 0, FLAT.yellow);                        // flower
    c.fill(35, 10, 1, 1, FLAT.blush);
    if (blink) c.fill(36, 7, 3, 1, OUTLINE);
    else { c.fill(36, 6, 3, 3, FLAT.white); c.fill(38, 7, 1, 2, FLAT.black); c.fill(36, 6, 3, 1, M.skinDk.base); } // sleepy eye
    if (mouthOpen) { c.fill(37, 10, 4, 2, FLAT.mouth); c.fill(38, 11, 2, 1, FLAT.tongue); }
    else c.fill(37, 10, 4, 1, OUTLINE);
    if (armsUp) for (const [x, y] of [[3, 4], [28, 1], [1, 10], [40, 15]]) { c.set(x, y, FLAT.spark); c.set(x - 1, y, FLAT.spark); c.set(x + 1, y, FLAT.spark); c.set(x, y - 1, FLAT.spark); c.set(x, y + 1, FLAT.spark); }
    return toSprite(c, "Ponder the Turtle");
  }

  // ---------------------------------------------------------------- MEGA-BUG (a grumpy, glitchy cube)
  function megabug({ blink = false, glitch = false, mouthOpen = false } = {}) {
    const c = canvas(36, 32);
    c.box(10, 1, 2, 6, "bugDk"); c.box(24, 1, 2, 6, "bugDk");                         // antennae
    c.fill(9, 0, 4, 2, FLAT.glitch); c.fill(23, 0, 4, 2, FLAT.glitch);
    c.box(8, 26, 3, 5, "bugDk"); c.box(16, 26, 3, 5, "bugDk"); c.box(24, 26, 3, 5, "bugDk"); // legs
    c.box(5, 6, 26, 21, "bug", 3);                                                   // body cube
    c.box(5, 6, 26, 3, "bug", 4);
    c.fill(7, 8, 5, 1, M.bug.light);
    c.box(25, 8, 7, 6, "paper", 5); c.fill(26, 10, 4, 1, FLAT.ink); c.fill(26, 12, 3, 1, FLAT.ink);   // sticky notes
    c.box(2, 17, 6, 5, "paper", 6); c.fill(3, 19, 3, 1, FLAT.ink);
    if (blink) { c.fill(9, 14, 6, 1, OUTLINE); c.fill(20, 14, 6, 1, OUTLINE); }
    else {
      c.fill(9, 12, 6, 5, FLAT.white); c.fill(20, 12, 6, 5, FLAT.white);
      c.fill(12, 14, 2, 2, FLAT.black); c.fill(21, 14, 2, 2, FLAT.black);
    }
    for (let i = 0; i < 5; i++) { c.set(8 + i, 9 + Math.floor(i / 2), OUTLINE); c.set(26 - i, 9 + Math.floor(i / 2), OUTLINE); } // angry brows
    if (mouthOpen) {
      c.fill(10, 19, 16, 6, FLAT.mouth); c.fill(14, 22, 8, 2, FLAT.tongue);
      for (const x of [11, 14, 17, 20, 23]) c.set(x, 19, FLAT.tooth);
      for (const x of [12, 16, 20, 24]) c.set(x, 24, FLAT.tooth);
    } else {
      c.fill(11, 21, 14, 2, FLAT.mouth);
      for (const x of [12, 15, 18, 21, 24]) c.set(x, 21, FLAT.tooth);
    }
    const strips = glitch ? [[0, 12, 7, 2], [29, 20, 7, 2], [12, 27, 6, 1]] : [[1, 14, 5, 2], [30, 17, 6, 2]];
    for (const [x, y, w, h] of strips) c.fill(x, y, w, h, FLAT.glitch);
    return toSprite(c, "MEGA-BUG");
  }

  function tinybug({ blink = false } = {}) {
    const c = canvas(15, 13);
    c.box(4, 0, 1, 3, "bugDk"); c.box(9, 0, 1, 3, "bugDk");
    c.box(2, 3, 10, 7, "bug", 2);
    c.box(3, 10, 2, 2, "bugDk"); c.box(9, 10, 2, 2, "bugDk");
    c.box(12, 3, 2, 4, "bug", 3); c.fill(13, 1, 1, 2, M.bug.dark);                    // saluting arm
    if (blink) { c.fill(4, 6, 2, 1, OUTLINE); c.fill(8, 6, 2, 1, OUTLINE); }
    else { c.fill(4, 5, 2, 2, FLAT.white); c.fill(8, 5, 2, 2, FLAT.white); c.set(5, 6, FLAT.black); c.set(9, 6, FLAT.black); }
    c.fill(6, 8, 2, 1, OUTLINE);
    return toSprite(c, "tiny bug");
  }

  // ---------------------------------------------------------------- Freddie the Frog (faces left, toward Ponder)
  function frog({ blink = false, mouthOpen = false, armsUp = false } = {}) {
    const c = canvas(30, 24);
    c.box(1, 18, 9, 5, "green", 2); c.box(20, 18, 9, 5, "green", 3);                 // back legs
    c.box(3, 9, 24, 12, "green", 4);                                                 // body
    c.box(8, 13, 14, 7, "belly", 5);                                                 // belly
    c.box(4, 2, 8, 8, "green", 6); c.box(18, 2, 8, 8, "green", 7);                   // eye bumps
    if (blink) { c.fill(5, 6, 6, 1, OUTLINE); c.fill(19, 6, 6, 1, OUTLINE); }
    else { c.fill(5, 3, 6, 5, FLAT.white); c.fill(19, 3, 6, 5, FLAT.white); c.fill(6, 5, 2, 2, FLAT.black); c.fill(20, 5, 2, 2, FLAT.black); }
    c.fill(4, 11, 3, 2, FLAT.blush); c.fill(23, 11, 3, 2, FLAT.blush);
    if (mouthOpen) { c.fill(8, 10, 14, 3, FLAT.mouth); c.fill(11, 11, 8, 2, FLAT.tongue); }
    else c.fill(8, 11, 14, 1, OUTLINE);
    if (armsUp) { c.box(0, 6, 3, 6, "green", 8); c.box(27, 6, 3, 6, "green", 9); }
    else { c.box(5, 19, 4, 4, "greenDk"); c.box(21, 19, 4, 4, "greenDk"); }
    return toSprite(c, "Freddie the Frog");
  }

  const SPRITES = { chomp, ponder, megabug, tinybug, frog };
  const NS = "http://www.w3.org/2000/svg";

  // Builds an <svg>. Accepts block sprites ({svg}) or the simple {width, height, layers:[[x,y,w,h,color]]} format.
  function svgFor(sprite, size, label) {
    const svg = document.createElementNS(NS, "svg");
    let W, H;
    if (sprite.svg) {
      W = sprite.width; H = sprite.height;
      svg.setAttribute("viewBox", sprite.viewBox || `0 0 ${W} ${H}`);
      svg.innerHTML = sprite.svg;
    } else {
      W = sprite.width + 2; H = sprite.height + 2;
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      for (const [x, y, w, h, c] of sprite.layers) {
        const r = document.createElementNS(NS, "rect");
        r.setAttribute("x", x + 1); r.setAttribute("y", y + 1);
        r.setAttribute("width", w); r.setAttribute("height", h); r.setAttribute("fill", c);
        svg.appendChild(r);
      }
    }
    svg.setAttribute("class", "px-svg");
    svg.setAttribute("shape-rendering", "crispEdges");
    svg.setAttribute("width", size);
    svg.setAttribute("height", Math.round((size * H) / W));
    if (label === "") svg.setAttribute("aria-hidden", "true");
    else { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", label || sprite.label); }
    return svg;
  }

  const prefersReduced = () => {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
  };

  /** Puts an animated character in `el`. Returns { setMood, setStill, setMouth, destroy }. */
  function mount(el, name, { size = 240, mood = "idle", still = false, label } = {}) {
    const make = SPRITES[name];
    let state = { mood, still: still || prefersReduced(), blink: false, flap: false, mouthCtl: null };
    const timers = [];
    const cache = {};
    const wrap = document.createElement("div");
    wrap.className = "px-char px-" + name;
    el.replaceChildren(wrap);

    function render() {
      const celebrating = state.mood === "celebrate";
      const talking = state.mood === "talk";
      const mouthOpen = state.mouthCtl !== null ? state.mouthCtl : celebrating || (talking && !state.still && state.flap);
      const opts = name === "megabug" ? { blink: state.blink, glitch: !state.still && state.flap, mouthOpen }
        : name === "tinybug" ? { blink: state.blink }
        : { blink: state.blink, mouthOpen, armsUp: celebrating };
      const key = JSON.stringify(opts);
      if (wrap.dataset.key !== key) {
        cache[key] = cache[key] || make(opts);
        wrap.replaceChildren(svgFor(cache[key], size, label));
        wrap.dataset.key = key;
      }
      wrap.classList.toggle("px-bob", !state.still && !celebrating && name !== "megabug");
      wrap.classList.toggle("px-talk", !state.still && talking);
      wrap.classList.toggle("px-jump", !state.still && celebrating);
      wrap.classList.toggle("px-wobble", !state.still && name === "megabug");
    }

    function clearTimers() { while (timers.length) clearTimeout(timers.pop()); }
    function start() {
      clearTimers();
      if (state.still) { state.blink = false; state.flap = false; render(); return; }
      const blinkLoop = () => {
        timers.push(setTimeout(() => {
          state.blink = true; render();
          timers.push(setTimeout(() => { state.blink = false; render(); blinkLoop(); }, 140));
        }, 2400 + Math.random() * 2600));
      };
      blinkLoop();
      const speed = name === "megabug" ? 200 : name === "ponder" ? 240 : 140; // Ponder talks slowly
      const flapLoop = () => {
        timers.push(setTimeout(() => {
          if ((state.mood === "talk" && state.mouthCtl === null) || name === "megabug") { state.flap = !state.flap; render(); }
          flapLoop();
        }, speed));
      };
      flapLoop();
      render();
    }

    start();
    return {
      setMood(m) { state.mood = m; render(); },
      setStill(s) { state.still = s || prefersReduced(); start(); },
      setMouth(v) { state.mouthCtl = v; render(); },
      destroy() { clearTimers(); wrap.remove(); },
    };
  }

  /** A row of saluting tiny bugs popping in one by one. */
  function squad(el, { count = 5, size = 64, still = false } = {}) {
    const row = document.createElement("div");
    row.className = "px-squad";
    row.setAttribute("role", "img");
    row.setAttribute("aria-label", `${count} tiny bugs saluting`);
    for (let i = 0; i < count; i++) {
      const cell = document.createElement("div");
      if (!still && !prefersReduced()) { cell.className = "px-pop"; cell.style.animationDelay = `${i * 0.12}s`; }
      cell.appendChild(svgFor(tinybug(), size, ""));
      row.appendChild(cell);
    }
    el.replaceChildren(row);
  }

  // Shared animation styles: chunky stepped motion for a retro block-game feel.
  const style = document.createElement("style");
  style.textContent = `
    .px-svg { display: block; image-rendering: pixelated }
    .px-char { display: inline-block; transform-origin: 50% 100% }
    @keyframes px-bob { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-3%) } }
    @keyframes px-talk { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-2%) } }
    @keyframes px-jump { 0%,100% { transform: translateY(0) scale(1,1) } 15% { transform: translateY(0) scale(1.08,.92) } 45%,55% { transform: translateY(-16%) scale(.95,1.06) } 85% { transform: translateY(0) scale(1.06,.94) } }
    @keyframes px-wobble { 0%,100% { transform: scale(1,1) } 25% { transform: scale(1.05,.95) } 75% { transform: scale(.95,1.05) } }
    @keyframes px-pop { 0% { transform: scale(0) translateY(40%); opacity: 0 } 60% { transform: scale(1.15) translateY(-10%); opacity: 1 } 80%,100% { transform: scale(1) translateY(0); opacity: 1 } }
    .px-bob { animation: px-bob 1.6s steps(4) infinite }
    .px-bob.px-talk { animation: px-talk .5s steps(2) infinite }
    .px-jump { animation: px-jump .8s steps(8) infinite }
    .px-wobble { animation: px-wobble 1.2s steps(6) infinite }
    .px-pop { animation: px-pop .5s steps(5) both }
    .px-squad { display: flex; gap: 10px; align-items: flex-end; justify-content: center }
    @media (prefers-reduced-motion: reduce) { .px-bob, .px-jump, .px-wobble, .px-pop, .px-talk { animation: none !important } }
  `;
  document.head.appendChild(style);

  window.Pixel = { mount, squad, sprites: SPRITES, svgFor };
})();
