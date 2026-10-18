// Pixel-art characters for the Land of Cooooode, drawn as SVG squares.
// Usage:
//   const chomp = Pixel.mount(element, "chomp", { size: 240 });
//   chomp.setMood("talk" | "idle" | "celebrate");   chomp.setStill(true) for calm mode
// Characters: "chomp", "ponder", "megabug", "tinybug".
(function () {
  const C = {
    outline: "#1d2620", white: "#ffffff", pupil: "#141414", mouth: "#7a2633", tongue: "#ee7a8a", blush: "#f2a3a3",
    green: "#5cae4f", greenDark: "#3d7d36", belly: "#b9e09a", bellyLine: "#94c877", belt: "#e8873a", buckle: "#f6d44a",
    skin: "#a3d36f", skinDark: "#6f9e45", shell: "#3c8f7c", shellLight: "#6cc3a8", shellRim: "#d4ad62",
    lily: "#4fae5c", lilyDark: "#357a3f", flower: "#f39ac1",
    bug: "#c94fb0", bugDark: "#8f3480", bugLight: "#e88ad6", glitch: "#3fe0e6", paper: "#fdfbf2", ink: "#8a8a8a",
  };

  const outlined = (rects) => [
    ...rects.map(([x, y, w, h]) => [x - 1, y - 1, w + 2, h + 2, C.outline]),
    ...rects,
  ];

  function chomp({ blink = false, mouthOpen = false, armsUp = false } = {}) {
    const arms = armsUp
      ? [[6, 6, 3, 8, C.green], [21, 15, 6, 3, C.green]]
      : [[6, 15, 3, 6, C.green], [21, 15, 3, 6, C.green]];
    const shapes = outlined([
      [1, 18, 3, 2, C.greenDark], [3, 16, 4, 4, C.greenDark], [6, 15, 4, 5, C.greenDark],
      ...arms,
      [10, 25, 3, 3, C.green], [17, 25, 3, 3, C.green],
      [9, 12, 12, 13, C.green],
      [12, 1, 4, 3, C.green], [17, 1, 4, 3, C.green],
      [10, 3, 13, 9, C.green], [22, 6, 9, 6, C.green],
    ]);
    const details = [
      [12, 14, 6, 9, C.belly], [12, 16, 6, 1, C.bellyLine], [12, 19, 6, 1, C.bellyLine],
      [9, 13, 1, 1, C.greenDark], [9, 16, 1, 1, C.greenDark], [9, 19, 1, 1, C.greenDark],
      [10, 4, 1, 1, C.greenDark], [10, 7, 1, 1, C.greenDark],
      [9, 21, 12, 2, C.belt], [14, 21, 2, 2, C.buckle],
      [9, 27, 5, 1, C.greenDark], [16, 27, 5, 1, C.greenDark],
      [29, 7, 1, 1, C.greenDark], [13, 9, 2, 1, C.blush],
    ];
    const eyes = blink
      ? [[13, 3, 2, 1, C.outline], [18, 3, 2, 1, C.outline]]
      : [[13, 2, 2, 2, C.white], [18, 2, 2, 2, C.white], [14, 2, 1, 2, C.pupil], [19, 2, 1, 2, C.pupil]];
    const mouth = mouthOpen
      ? [[19, 9, 12, 3, C.mouth], [23, 10, 5, 2, C.tongue], [21, 9, 1, 1, C.white], [24, 9, 1, 1, C.white], [27, 9, 1, 1, C.white], [30, 9, 1, 1, C.white]]
      : [[19, 10, 12, 1, C.outline], [18, 9, 1, 1, C.outline], [21, 11, 1, 1, C.white], [24, 11, 1, 1, C.white], [27, 11, 1, 1, C.white]];
    return { width: 33, height: 30, label: "Chomp the Gator", layers: [...shapes, ...details, ...eyes, ...mouth] };
  }

  // Ponder the Turtle: sleepy, patient, lily pad hat. Faces right.
  function ponder({ blink = false, mouthOpen = false, armsUp = false } = {}) {
    const frontLeg = [19, 17, 4, 4, C.skin];
    // Celebrating: little sparkles pop around his shell.
    const sparkles = armsUp
      ? [[3, 3, 1, 3, C.buckle], [2, 4, 3, 1, C.buckle], [25, 1, 1, 3, C.buckle], [24, 2, 3, 1, C.buckle], [1, 9, 1, 1, C.buckle]]
      : [];
    const shapes = outlined([
      [3, 13, 3, 2, C.skin], // tail
      [7, 17, 4, 4, C.skin], // back leg
      frontLeg,
      [22, 11, 3, 5, C.skin], // neck
      [24, 7, 7, 6, C.skin], // head
      [9, 3, 12, 2, C.shell], // shell dome
      [7, 5, 16, 3, C.shell],
      [6, 8, 18, 8, C.shell],
      [5, 15, 20, 2, C.shellRim], // rim
      [25, 5, 6, 2, C.lily], // lily pad hat
    ]);
    const details = [
      // shell pattern
      [10, 6, 4, 3, C.shellLight], [16, 6, 4, 3, C.shellLight],
      [8, 10, 3, 3, C.shellLight], [13, 10, 4, 3, C.shellLight], [19, 10, 3, 3, C.shellLight],
      [11, 4, 2, 1, C.shellLight],
      // feet + lily pad notch + flower
      [6, 20, 5, 1, C.skinDark], [19, 20, 5, 1, C.skinDark],
      [28, 5, 1, 1, C.lilyDark], [26, 4, 2, 1, C.flower],
      [26, 11, 1, 1, C.blush],
    ];
    // Sleepy half-closed eyes; closed line when blinking.
    const eyes = blink
      ? [[27, 9, 2, 1, C.outline]]
      : [[27, 8, 2, 2, C.white], [28, 9, 1, 1, C.pupil], [27, 8, 2, 1, C.skinDark]];
    const mouth = mouthOpen
      ? [[28, 11, 3, 2, C.mouth], [29, 12, 1, 1, C.tongue]]
      : [[28, 11, 3, 1, C.outline]];
    return { width: 32, height: 22, label: "Ponder the Turtle", layers: [...sparkles, ...shapes, ...details, ...eyes, ...mouth] };
  }

  function megabug({ blink = false, glitch = false } = {}) {
    const shapes = outlined([
      [11, 2, 1, 5, C.bugDark], [20, 2, 1, 5, C.bugDark],
      [9, 26, 2, 2, C.bugDark], [15, 26, 2, 2, C.bugDark], [21, 26, 2, 2, C.bugDark],
      [8, 6, 16, 2, C.bug], [4, 10, 2, 12, C.bug], [26, 10, 2, 12, C.bug], [6, 8, 20, 18, C.bug],
    ]);
    const details = [
      [10, 1, 3, 2, C.glitch], [19, 1, 3, 2, C.glitch], [8, 22, 16, 3, C.bugDark], [7, 9, 4, 2, C.bugLight],
      [22, 8, 5, 4, C.paper], [23, 9, 3, 1, C.ink], [23, 11, 2, 1, C.ink], [5, 17, 4, 4, C.paper], [6, 18, 2, 1, C.ink],
      [10, 10, 2, 1, C.outline], [12, 11, 3, 1, C.outline], [18, 11, 3, 1, C.outline], [21, 10, 2, 1, C.outline],
    ];
    const eyes = blink
      ? [[10, 14, 5, 1, C.outline], [18, 14, 5, 1, C.outline]]
      : [[10, 12, 5, 5, C.white], [18, 12, 5, 5, C.white], [12, 14, 2, 2, C.pupil], [19, 14, 2, 2, C.pupil]];
    const mouth = [[11, 19, 10, 2, C.mouth], [12, 19, 1, 1, C.white], [15, 19, 1, 1, C.white], [18, 19, 1, 1, C.white]];
    const strips = glitch
      ? [[2, 13, 7, 2, C.glitch], [23, 19, 8, 2, C.glitch], [9, 23, 6, 1, C.glitch]]
      : [[4, 15, 5, 2, C.glitch], [25, 17, 6, 2, C.glitch]];
    return { width: 32, height: 29, label: "MEGA-BUG", layers: [...shapes, ...details, ...eyes, ...mouth, ...strips] };
  }

  function tinybug({ blink = false, salute = true } = {}) {
    const shapes = outlined([
      [4, 1, 1, 2, C.bugDark], [8, 1, 1, 2, C.bugDark],
      [3, 3, 7, 1, C.bug], [2, 4, 9, 5, C.bug], [3, 9, 7, 1, C.bug],
      ...(salute ? [[10, 5, 2, 1, C.bugDark], [11, 2, 1, 3, C.bugDark]] : []),
    ]);
    const face = blink
      ? [[4, 6, 2, 1, C.outline], [7, 6, 2, 1, C.outline]]
      : [[4, 5, 2, 2, C.white], [7, 5, 2, 2, C.white], [5, 6, 1, 1, C.pupil], [8, 6, 1, 1, C.pupil]];
    return {
      width: 13, height: 12, label: "tiny bug",
      layers: [...shapes, [3, 4, 2, 1, C.bugLight], ...face, [5, 8, 3, 1, C.outline], [3, 10, 1, 1, C.bugDark], [6, 10, 1, 1, C.bugDark], [9, 10, 1, 1, C.bugDark]],
    };
  }

  const SPRITES = { chomp, ponder, megabug, tinybug };
  const NS = "http://www.w3.org/2000/svg";

  function svgFor(sprite, size, label) {
    const W = sprite.width + 2, H = sprite.height + 2;
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("width", size);
    svg.setAttribute("height", Math.round((size * H) / W));
    svg.setAttribute("shape-rendering", "crispEdges");
    if (label === "") svg.setAttribute("aria-hidden", "true");
    else { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", label || sprite.label); }
    for (const [x, y, w, h, c] of sprite.layers) {
      const r = document.createElementNS(NS, "rect");
      r.setAttribute("x", x + 1); r.setAttribute("y", y + 1);
      r.setAttribute("width", w); r.setAttribute("height", h); r.setAttribute("fill", c);
      svg.appendChild(r);
    }
    return svg;
  }

  const prefersReduced = () => {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
  };

  /** Puts an animated character in `el`. Returns { setMood, setStill, destroy }. */
  function mount(el, name, { size = 240, mood = "idle", still = false, label } = {}) {
    const make = SPRITES[name];
    let state = { mood, still: still || prefersReduced(), blink: false, flap: false };
    const timers = [];
    const wrap = document.createElement("div");
    wrap.className = "px-char";
    el.replaceChildren(wrap);

    function render() {
      const talking = state.mood === "talk";
      const sprite =
        name === "megabug" ? make({ blink: state.blink, glitch: !state.still && state.flap })
        : name === "tinybug" ? make({ blink: state.blink })
        : make({
            blink: state.blink,
            mouthOpen: state.mood === "celebrate" || (talking && (state.still ? false : state.flap)),
            armsUp: state.mood === "celebrate",
          });
      wrap.replaceChildren(svgFor(sprite, size, label));
      wrap.classList.toggle("px-bob", !state.still && state.mood !== "celebrate" && name !== "megabug");
      wrap.classList.toggle("px-jump", !state.still && state.mood === "celebrate");
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
        }, 2500 + Math.random() * 2500));
      };
      blinkLoop();
      const speed = name === "megabug" ? 220 : name === "ponder" ? 260 : 160; // Ponder talks slowly
      const flapLoop = () => {
        timers.push(setTimeout(() => {
          if (state.mood === "talk" || name === "megabug") { state.flap = !state.flap; render(); }
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

  // Shared animation styles (stepped easing keeps the retro pixel feel).
  const style = document.createElement("style");
  style.textContent = `
    @keyframes px-bob { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-4%) } }
    @keyframes px-jump { 0%,100% { transform: translateY(0) } 40%,60% { transform: translateY(-14%) } }
    @keyframes px-wobble { 0%,100% { transform: scale(1,1) rotate(0) } 25% { transform: scale(1.04,.96) rotate(-2deg) } 75% { transform: scale(.96,1.04) rotate(2deg) } }
    @keyframes px-pop { 0% { transform: scale(0) translateY(40%); opacity: 0 } 60% { transform: scale(1.15) translateY(-10%); opacity: 1 } 80%,100% { transform: scale(1) translateY(0); opacity: 1 } }
    .px-char { display: inline-block }
    .px-bob { animation: px-bob 1.6s steps(4) infinite }
    .px-jump { animation: px-jump .7s steps(5) infinite }
    .px-wobble { animation: px-wobble 1.2s steps(6) infinite; transform-origin: 50% 100% }
    .px-pop { animation: px-pop .5s steps(5) both }
    .px-squad { display: flex; gap: 10px; align-items: flex-end; justify-content: center }
    @media (prefers-reduced-motion: reduce) { .px-bob, .px-jump, .px-wobble, .px-pop { animation: none !important } }
  `;
  document.head.appendChild(style);

  window.Pixel = { mount, squad, sprites: SPRITES, svgFor };
})();
