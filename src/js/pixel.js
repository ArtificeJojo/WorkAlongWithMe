// Cartoon characters for the Land of Cooooode: smooth vector art with thick outlines,
// flat candy colors and bouncy squash-and-stretch (Adventure Time-inspired, all original).
// Usage (same as before, so every page keeps working):
//   const chomp = Pixel.mount(element, "chomp", { size: 240 });
//   chomp.setMood("talk" | "idle" | "celebrate");   chomp.setStill(true) for calm mode
// Characters: "chomp", "ponder", "megabug", "tinybug".
(function () {
  const INK = "#1b1b2f";
  const C = {
    white: "#ffffff", mouth: "#7a2040", tongue: "#ff8fa3", blush: "#ff9db0",
    green: "#6cc24a", greenDark: "#4c9a36", belly: "#d8f2a6", bellyLine: "#b5dc7e", belt: "#ff8a3d", buckle: "#ffd94a",
    skin: "#a8dc6c", skinDark: "#7fb64a", shell: "#2fa38f", shellLight: "#7fd8bf", shellDark: "#1f7d6e", rim: "#f2c46b",
    lily: "#5cc46a", lilyDark: "#3d9a4c", flower: "#ff9ecf",
    bug: "#c856d6", bugDark: "#8e3aa0", bugLight: "#ea9af2", glitch: "#3ff0f0", paper: "#fffbea", ink: "#9a94a8", spark: "#ffe14a",
  };

  // Every fill shape gets a thick dark outline. `merged` draws shapes twice (outlined, then fill only)
  // so touching shapes melt into one clean silhouette, like a hand-inked cartoon.
  const OUT = `stroke="${INK}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"`;
  const LINE = `stroke="${INK}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"`;
  const merged = (...shapes) => shapes.map(s => s.replace("%S%", OUT)).join("") + shapes.map(s => s.replace("%S%", 'stroke="none"')).join("");
  const ink = (shape) => shape.replace("%S%", LINE);
  // Noodle limbs: a dark stroke under a colored stroke.
  const noodle = (d, color, w = 9) =>
    `<path d="${d}" fill="none" stroke="${INK}" stroke-width="${w + 6}" stroke-linecap="round" stroke-linejoin="round"/>` +
    `<path d="${d}" fill="none" stroke="${color}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
  const star = (x, y, r, color) =>
    `<path d="M${x} ${y - r} Q${x + r * 0.18} ${y - r * 0.18} ${x + r} ${y} Q${x + r * 0.18} ${y + r * 0.18} ${x} ${y + r} Q${x - r * 0.18} ${y + r * 0.18} ${x - r} ${y} Q${x - r * 0.18} ${y - r * 0.18} ${x} ${y - r}Z" fill="${color}" ${LINE.replace('3"', '2.2"')}/>`;

  // ---------------------------------------------------------------- Chomp the Gator (faces right)
  function chomp() {
    const G = C.green;
    const svg =
      `<g class="st-tail">${merged(`<path d="M46 116 C22 124 6 112 3 94 C14 104 30 104 48 98 Z" fill="${G}" %S%/>`)}</g>` +
      noodle("M58 128 L56 146", G, 10) + noodle("M84 128 L86 146", G, 10) +
      ink(`<ellipse cx="51" cy="149" rx="11" ry="5.5" fill="${C.greenDark}" %S%/>`) +
      ink(`<ellipse cx="92" cy="149" rx="11" ry="5.5" fill="${C.greenDark}" %S%/>`) +
      // arms: resting, or both up and waving when celebrating
      `<g class="st-down">${noodle("M44 94 Q30 106 34 122", G)}${ink(`<circle cx="34" cy="124" r="5.5" fill="${G}" %S%/>`)}</g>` +
      `<g class="st-up"><g class="st-armL">${noodle("M46 92 Q30 78 26 58", G)}${ink(`<circle cx="26" cy="55" r="6" fill="${G}" %S%/>`)}</g></g>` +
      merged(`<ellipse cx="71" cy="104" rx="32" ry="34" fill="${G}" %S%/>`) +
      `<ellipse cx="74" cy="108" rx="19" ry="24" fill="${C.belly}"/>` +
      `<path d="M58 98 Q74 102 90 98 M56 108 Q74 112 92 108" fill="none" stroke="${C.bellyLine}" stroke-width="2.5" stroke-linecap="round"/>` +
      `<ellipse cx="48" cy="96" rx="3" ry="2.2" fill="${C.greenDark}"/><ellipse cx="45" cy="108" rx="2.5" ry="2" fill="${C.greenDark}"/>` +
      ink(`<path d="M40 117 Q71 127 102 117 L101 125 Q71 135 41 125 Z" fill="${C.belt}" %S%/>`) +
      ink(`<rect x="65" y="119" width="12" height="11" rx="2.5" fill="${C.buckle}" %S%/>`) +
      // head: round skull + long snout + two eye bumps, melted into one outline
      merged(
        `<circle cx="62" cy="58" r="27" fill="${G}" %S%/>`,
        `<rect x="62" y="46" width="74" height="30" rx="15" fill="${G}" %S%/>`,
        `<circle cx="50" cy="33" r="13" fill="${G}" %S%/>`,
        `<circle cx="77" cy="31" r="13" fill="${G}" %S%/>`,
      ) +
      `<ellipse cx="122" cy="53" rx="2.4" ry="1.8" fill="${INK}"/><ellipse cx="129" cy="54" rx="2.4" ry="1.8" fill="${INK}"/>` +
      `<ellipse cx="93" cy="66" rx="6.5" ry="3.5" fill="${C.blush}" opacity=".85"/>` +
      `<g class="st-shut"><path d="M76 68 Q104 75 133 64" fill="none" ${LINE}/>` +
      [88, 99, 110, 121].map(x => `<path d="M${x} ${70 + (x - 76) * 0.02} l3.5 5 l3.5 -5 z" fill="#fff" stroke="${INK}" stroke-width="1.6" stroke-linejoin="round"/>`).join("") + `</g>` +
      `<g class="st-open-mouth">${ink(`<path d="M76 66 Q104 96 135 66 Q104 76 76 66 Z" fill="${C.mouth}" %S%/>`)}` +
      `<ellipse cx="104" cy="80" rx="11" ry="5" fill="${C.tongue}"/>` +
      [88, 99, 110, 121].map(x => `<path d="M${x} 69 l3.5 5 l3.5 -5 z" fill="#fff" stroke="${INK}" stroke-width="1.6" stroke-linejoin="round"/>`).join("") + `</g>` +
      `<g class="st-eyes">${ink(`<circle cx="51" cy="33" r="8.5" fill="#fff" %S%/>`)}${ink(`<circle cx="78" cy="31" r="8.5" fill="#fff" %S%/>`)}` +
      `<circle cx="54" cy="34" r="4.3" fill="${INK}"/><circle cx="81" cy="32" r="4.3" fill="${INK}"/>` +
      `<circle cx="55.5" cy="32.4" r="1.5" fill="#fff"/><circle cx="82.5" cy="30.4" r="1.5" fill="#fff"/></g>` +
      `<g class="st-closed"><path d="M43 34 Q51 40 59 34 M70 32 Q78 38 86 32" fill="none" ${LINE}/></g>` +
      // front arm last, so it sits over the belly
      `<g class="st-down">${noodle("M98 94 Q112 106 108 122", G)}${ink(`<circle cx="108" cy="124" r="5.5" fill="${G}" %S%/>`)}</g>` +
      `<g class="st-up"><g class="st-armR">${noodle("M98 96 Q130 100 146 82", G)}${ink(`<circle cx="148" cy="79" r="6" fill="${G}" %S%/>`)}</g></g>` +
      `<g class="st-spark">${star(16, 36, 7, C.spark)}${star(138, 30, 6, C.spark)}${star(8, 70, 4, C.spark)}</g>`;
    return { width: 150, height: 160, viewBox: "-4 6 150 156", label: "Chomp the Gator", svg };
  }

  // ---------------------------------------------------------------- Ponder the Turtle (faces right)
  function ponder() {
    const S = C.skin;
    const svg =
      `<g class="st-spark">${star(14, 22, 7, C.spark)}${star(110, 8, 6, C.spark)}${star(4, 52, 4, C.spark)}</g>` +
      ink(`<path d="M24 80 L4 88 L26 92 Z" fill="${S}" %S%/>`) +
      ink(`<ellipse cx="40" cy="97" rx="12" ry="12" fill="${S}" %S%/>`) + ink(`<ellipse cx="106" cy="97" rx="12" ry="12" fill="${S}" %S%/>`) +
      `<path d="M33 104 v3 M40 105 v3 M47 104 v3 M99 104 v3 M106 105 v3 M113 104 v3" stroke="${INK}" stroke-width="2" stroke-linecap="round"/>` +
      // neck + head (the head nods slowly)
      `<g class="st-head">` +
      `<path d="M110 76 Q124 64 132 52" fill="none" stroke="${INK}" stroke-width="22" stroke-linecap="round"/>` +
      `<circle cx="138" cy="46" r="19" fill="${S}" ${OUT}/>` +
      `<path d="M110 76 Q124 64 132 52" fill="none" stroke="${S}" stroke-width="16" stroke-linecap="round"/>` +
      `<circle cx="138" cy="46" r="19" fill="${S}"/>` +
      `<ellipse cx="141" cy="57" rx="5" ry="3" fill="${C.blush}" opacity=".85"/>` +
      `<g class="st-eyes">${ink(`<ellipse cx="145" cy="43" rx="6.5" ry="7.5" fill="#fff" %S%/>`)}<circle cx="147" cy="45.5" r="3.4" fill="${INK}"/>` +
      `<path d="M138.4 43 A6.6 7.5 0 0 1 151.6 43 Z" fill="${C.skinDark}" stroke="${INK}" stroke-width="2.6" stroke-linejoin="round"/></g>` +
      `<g class="st-closed"><path d="M139 44 Q145 48 151 44" fill="none" ${LINE}/></g>` +
      `<g class="st-shut"><path d="M140 58 Q147 62 153 56" fill="none" ${LINE}/></g>` +
      `<g class="st-open-mouth">${ink(`<path d="M139 56 Q147 70 155 55 Z" fill="${C.mouth}" %S%/>`)}<ellipse cx="147" cy="62" rx="3.4" ry="2" fill="${C.tongue}"/></g>` +
      // lily pad hat with a flower
      ink(`<path d="M138 28 L156 25 A20 7 0 1 0 156 31 Z" fill="${C.lily}" %S%/>`) +
      `<path d="M126 28 Q136 25 146 28" fill="none" stroke="${C.lilyDark}" stroke-width="2" stroke-linecap="round"/>` +
      ink(`<circle cx="128" cy="22" r="4.2" fill="${C.flower}" %S%/>`) + `<circle cx="128" cy="22" r="1.6" fill="#fff6a8"/>` +
      `</g>` +
      // shell
      ink(`<path d="M18 84 C18 40 46 16 76 16 C108 16 130 40 130 84 Z" fill="${C.shell}" %S%/>`) +
      [[52, 42, 13, 10], [86, 40, 13, 10], [36, 66, 11, 10], [70, 64, 14, 11], [104, 64, 11, 10]]
        .map(([x, y, rx, ry]) => `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${C.shellLight}" stroke="${C.shellDark}" stroke-width="2.4"/>`).join("") +
      `<path d="M40 30 Q56 20 72 21" fill="none" stroke="#c9f5e8" stroke-width="3.5" stroke-linecap="round"/>` +
      ink(`<rect x="11" y="78" width="126" height="14" rx="7" fill="${C.rim}" %S%/>`) +
      `<path d="M30 85 h8 M54 85 h8 M78 85 h8 M102 85 h8" stroke="#d29a44" stroke-width="2.4" stroke-linecap="round"/>`;
    return { width: 164, height: 116, viewBox: "-4 0 164 116", label: "Ponder the Turtle", svg };
  }

  // ---------------------------------------------------------------- MEGA-BUG (grumpy glitchy blob)
  function megabug() {
    const B = C.bug;
    const svg =
      noodle("M48 24 Q42 10 34 6", C.bugDark, 5) + noodle("M92 24 Q98 10 106 6", C.bugDark, 5) +
      ink(`<rect x="28" y="0" width="10" height="10" rx="2" fill="${C.glitch}" %S%/>`) + ink(`<rect x="102" y="0" width="10" height="10" rx="2" fill="${C.glitch}" %S%/>`) +
      noodle("M44 108 L38 124", C.bugDark, 7) + noodle("M70 112 L70 126", C.bugDark, 7) + noodle("M96 108 L102 124", C.bugDark, 7) +
      merged(`<path d="M20 70 C14 34 44 18 70 20 C100 18 128 34 122 72 C126 100 104 116 70 114 C38 116 16 102 20 70 Z" fill="${B}" %S%/>`) +
      `<path d="M30 46 Q40 32 56 30" fill="none" stroke="${C.bugLight}" stroke-width="5" stroke-linecap="round"/>` +
      `<path d="M30 96 Q70 112 112 96" fill="none" stroke="${C.bugDark}" stroke-width="4" stroke-linecap="round"/>` +
      // sticky notes of tangled tasks stuck to it
      `<g transform="rotate(12 106 40)">${ink(`<rect x="96" y="30" width="22" height="18" rx="2" fill="${C.paper}" %S%/>`)}<path d="M100 37 h13 M100 42 h9" stroke="${C.ink}" stroke-width="2" stroke-linecap="round"/></g>` +
      `<g transform="rotate(-14 26 80)">${ink(`<rect x="16" y="72" width="20" height="16" rx="2" fill="${C.paper}" %S%/>`)}<path d="M20 78 h11 M20 83 h7" stroke="${C.ink}" stroke-width="2" stroke-linecap="round"/></g>` +
      `<g class="st-eyes">${ink(`<circle cx="54" cy="58" r="12" fill="#fff" %S%/>`)}${ink(`<circle cx="86" cy="58" r="12" fill="#fff" %S%/>`)}` +
      `<circle cx="57" cy="61" r="5" fill="${INK}"/><circle cx="83" cy="61" r="5" fill="${INK}"/></g>` +
      `<g class="st-closed"><path d="M44 60 h20 M76 60 h20" fill="none" ${LINE}/></g>` +
      `<path d="M40 42 L64 50 M100 42 L76 50" fill="none" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>` +
      ink(`<path d="M50 84 Q70 76 90 84 Q70 98 50 84 Z" fill="${C.mouth}" %S%/>`) +
      `<path d="M56 83 l3 5 l3 -6 M66 81 l3 5 l3 -5 M76 81 l3 6 l3 -5" fill="#fff" stroke="${INK}" stroke-width="1.5" stroke-linejoin="round"/>` +
      `<g class="st-g1">${ink(`<rect x="8" y="58" width="16" height="6" rx="1" fill="${C.glitch}" %S%/>`)}${ink(`<rect x="118" y="74" width="16" height="6" rx="1" fill="${C.glitch}" %S%/>`)}</g>` +
      `<g class="st-g2">${ink(`<rect x="2" y="50" width="22" height="6" rx="1" fill="${C.glitch}" %S%/>`)}${ink(`<rect x="114" y="84" width="22" height="6" rx="1" fill="${C.glitch}" %S%/>`)}${ink(`<rect x="40" y="100" width="18" height="4" rx="1" fill="${C.glitch}" %S%/>`)}</g>`;
    return { width: 140, height: 132, viewBox: "-2 -4 140 132", label: "MEGA-BUG", svg };
  }

  // ---------------------------------------------------------------- tiny bug (saluting helper)
  function tinybug() {
    const svg =
      noodle("M20 12 Q18 6 14 4", C.bugDark, 3) + noodle("M30 12 Q32 6 36 4", C.bugDark, 3) +
      noodle("M18 40 L16 46", C.bugDark, 4) + noodle("M32 40 L34 46", C.bugDark, 4) +
      merged(`<circle cx="25" cy="27" r="15" fill="${C.bug}" %S%/>`) +
      `<path d="M15 20 Q19 14 25 13" fill="none" stroke="${C.bugLight}" stroke-width="3" stroke-linecap="round"/>` +
      `<g class="st-eyes"><circle cx="20" cy="25" r="3" fill="${INK}"/><circle cx="30" cy="25" r="3" fill="${INK}"/><circle cx="21" cy="24" r="1" fill="#fff"/><circle cx="31" cy="24" r="1" fill="#fff"/></g>` +
      `<g class="st-closed"><path d="M17 25 h6 M27 25 h6" ${LINE}/></g>` +
      `<path d="M20 32 Q25 36 30 32" fill="none" ${LINE}/>` +
      noodle("M39 30 Q46 22 40 15", C.bug, 4);
    return { width: 52, height: 50, viewBox: "-1 0 52 50", label: "tiny bug", svg };
  }

  const SPRITES = { chomp, ponder, megabug, tinybug };
  const NS = "http://www.w3.org/2000/svg";

  // Builds an <svg>. Accepts the vector sprites above, or the old {width, height, layers:[[x,y,w,h,color]]} pixel format.
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
      svg.setAttribute("shape-rendering", "crispEdges");
      for (const [x, y, w, h, c] of sprite.layers) {
        const r = document.createElementNS(NS, "rect");
        r.setAttribute("x", x + 1); r.setAttribute("y", y + 1);
        r.setAttribute("width", w); r.setAttribute("height", h); r.setAttribute("fill", c);
        svg.appendChild(r);
      }
    }
    svg.setAttribute("class", "px-svg");
    svg.setAttribute("width", size);
    svg.setAttribute("height", Math.round((size * H) / W));
    if (label === "") svg.setAttribute("aria-hidden", "true");
    else { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", label || sprite.label); }
    return svg;
  }

  const prefersReduced = () => {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
  };

  /** Puts an animated character in `el`. Returns { setMood, setStill, destroy }.
   *  The drawing is made once; blinking, talking and celebrating just switch classes, so motion stays smooth. */
  function mount(el, name, { size = 240, mood = "idle", still = false, label } = {}) {
    let state = { mood, still: still || prefersReduced(), flap: false };
    const timers = [];
    const wrap = document.createElement("div");
    wrap.className = "px-char px-" + name;
    wrap.appendChild(svgFor(SPRITES[name](), size, label));
    el.replaceChildren(wrap);

    function render() {
      const celebrating = state.mood === "celebrate";
      const talking = state.mood === "talk";
      wrap.classList.toggle("still", state.still);
      wrap.classList.toggle("party", celebrating);
      wrap.classList.toggle("mouth", celebrating || (talking && !state.still && state.flap));
      wrap.classList.toggle("glitch", name === "megabug" && !state.still && state.flap);
      wrap.classList.toggle("px-bob", !state.still && !celebrating && name !== "megabug");
      wrap.classList.toggle("px-talk", !state.still && talking);
      wrap.classList.toggle("px-jump", !state.still && celebrating);
      wrap.classList.toggle("px-wobble", !state.still && name === "megabug");
    }

    function clearTimers() { while (timers.length) clearTimeout(timers.pop()); }
    function start() {
      clearTimers();
      wrap.classList.remove("blink");
      if (state.still) { state.flap = false; render(); return; }
      const blinkLoop = () => {
        timers.push(setTimeout(() => {
          wrap.classList.add("blink");
          timers.push(setTimeout(() => { wrap.classList.remove("blink"); blinkLoop(); }, 130));
        }, 2200 + Math.random() * 2600));
      };
      blinkLoop();
      const speed = name === "megabug" ? 200 : name === "ponder" ? 240 : 140; // Ponder talks slowly
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

  // Shared styles: which face parts show, plus smooth, bouncy cartoon motion.
  const style = document.createElement("style");
  style.textContent = `
    .px-svg { overflow: visible; display: block }
    .px-svg .st-closed, .px-svg .st-open-mouth, .px-svg .st-up, .px-svg .st-spark, .px-svg .st-g2 { display: none }
    .px-char.blink .st-eyes { display: none } .px-char.blink .st-closed { display: inline }
    .px-char.mouth .st-shut { display: none } .px-char.mouth .st-open-mouth { display: inline }
    .px-char.party .st-down { display: none } .px-char.party .st-up, .px-char.party .st-spark { display: inline }
    .px-char.glitch .st-g1 { display: none } .px-char.glitch .st-g2 { display: inline }
    .px-char { display: inline-block; transform-origin: 50% 100% }
    .px-svg g { transform-box: fill-box }
    .px-svg .st-tail { transform-origin: 100% 40%; animation: px-wag 1.6s ease-in-out infinite }
    .px-svg .st-head { transform-origin: 0% 100%; animation: px-nod 3.2s ease-in-out infinite }
    .px-svg .st-armL { transform-origin: 100% 100%; animation: px-waveL .5s ease-in-out infinite alternate }
    .px-svg .st-armR { transform-origin: 0% 100%; animation: px-waveR .5s ease-in-out infinite alternate }
    .px-svg .st-spark path { transform-box: fill-box; transform-origin: center; animation: px-twinkle .7s ease-in-out infinite alternate }
    .px-svg .st-spark path:nth-child(2) { animation-delay: .25s } .px-svg .st-spark path:nth-child(3) { animation-delay: .5s }
    @keyframes px-wag { 0%,100% { transform: rotate(0) } 50% { transform: rotate(-12deg) } }
    @keyframes px-nod { 0%,100% { transform: rotate(0) } 50% { transform: rotate(4deg) } }
    @keyframes px-waveL { from { transform: rotate(8deg) } to { transform: rotate(-14deg) } }
    @keyframes px-waveR { from { transform: rotate(-8deg) } to { transform: rotate(14deg) } }
    @keyframes px-twinkle { from { transform: scale(.6) rotate(0) } to { transform: scale(1.15) rotate(20deg) } }
    @keyframes px-bob { 0%,100% { transform: translateY(0) scale(1,1) } 50% { transform: translateY(-3%) scale(.98,1.025) } }
    @keyframes px-talk { 0%,100% { transform: rotate(0) scale(1,1) } 30% { transform: rotate(-1.5deg) scale(1.01,.99) } 70% { transform: rotate(1.5deg) scale(.99,1.01) } }
    @keyframes px-jump { 0%,100% { transform: translateY(0) scale(1,1) } 12% { transform: translateY(0) scale(1.1,.88) } 40% { transform: translateY(-16%) scale(.93,1.09) } 60% { transform: translateY(-17%) scale(1,1) } 82% { transform: translateY(0) scale(1.08,.92) } }
    @keyframes px-wobble { 0%,100% { transform: scale(1,1) rotate(0) } 25% { transform: scale(1.05,.95) rotate(-3deg) } 75% { transform: scale(.95,1.05) rotate(3deg) } }
    @keyframes px-pop { 0% { transform: scale(0) translateY(40%); opacity: 0 } 60% { transform: scale(1.2,.9) translateY(-12%); opacity: 1 } 80% { transform: scale(.95,1.05) } 100% { transform: scale(1) translateY(0); opacity: 1 } }
    .px-bob { animation: px-bob 2.2s ease-in-out infinite }
    .px-bob.px-talk { animation: px-talk .9s ease-in-out infinite }
    .px-jump { animation: px-jump .8s cubic-bezier(.3,.6,.4,1) infinite }
    .px-wobble { animation: px-wobble 1.1s ease-in-out infinite }
    .px-pop { animation: px-pop .55s cubic-bezier(.3,.7,.4,1.3) both }
    .px-squad { display: flex; gap: 10px; align-items: flex-end; justify-content: center }
    .px-char.still, .px-char.still * { animation: none !important }
    @media (prefers-reduced-motion: reduce) { .px-char, .px-char *, .px-pop { animation: none !important } }
  `;
  document.head.appendChild(style);

  window.Pixel = { mount, squad, sprites: SPRITES, svgFor };
})();
