// Atmosphere engine, ported from Steamapp_Juan_Model/themes.py.
// Every game tag can pull a card toward a "world" (medieval, cyberpunk, horror ...): a palette, a font pairing,
// a drifting particle effect and a skyline silhouette drawn as SVG.

export const FONT_URL =
  "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Big+Shoulders+Display:wght@700;900&family=DM+Sans:wght@400;500;700" +
  "&family=Cinzel:wght@600;800&family=EB+Garamond:wght@400;600&family=Orbitron:wght@600;900" +
  "&family=Rajdhani:wght@500;700&family=Audiowide&family=Exo+2:wght@400;600&family=Creepster" +
  "&family=Lora:wght@400;600&family=Fredoka:wght@500;700&family=Nunito:wght@400;700&family=Press+Start+2P" +
  "&family=Space+Mono:wght@400;700&family=Black+Ops+One&family=Saira+Condensed:wght@400;600" +
  "&family=Mochiy+Pop+One&family=Zen+Maru+Gothic:wght@400;700&family=Russo+One&family=Chakra+Petch:wght@400;600" +
  "&family=Playfair+Display:wght@700;900&family=Libre+Franklin:wght@400;600&display=swap";

type Palette = { bg: string; panel: string; panel2: string; line: string; text: string; mute: string; accent: string; accent2: string };
type PartKind = "ember" | "pixel" | "ash" | "stars" | "rain" | "petal" | "firefly" | "streak" | "fog";
export type World = {
  name: string;
  tag: string;
  disp: string;
  body: string;
  c: Palette;
  grad: string;
  sil: string;
  skyk: string;
  part: [PartKind, string, number];
  tags: Record<string, number>;
};

export const DEFAULT = "forge";

export const THEMES: Record<string, World> = {
  forge: {
    name: "The Forge", tag: "Hammer your taste into shape.",
    disp: "'Big Shoulders Display',Impact,sans-serif", body: "'DM Sans',system-ui,sans-serif",
    c: { bg: "#0e0f11", panel: "rgba(26,28,31,.86)", panel2: "rgba(38,40,44,.92)", line: "#45484e", text: "#ece8e4", mute: "#9a958f", accent: "#ff5a1f", accent2: "#ffb000" },
    grad: "linear-gradient(180deg,#111214,#5a210b)", sil: "#08090a", skyk: "foundry", part: ["ember", "#ffb000", 26], tags: {},
  },
  medieval: {
    name: "Age of Steel", tag: "Torchlight, stone halls and sharpened steel.",
    disp: "'Cinzel',Georgia,serif", body: "'EB Garamond',Georgia,serif",
    c: { bg: "#12100c", panel: "rgba(30,24,17,.84)", panel2: "rgba(46,37,25,.92)", line: "#5a4a2c", text: "#efe6d2", mute: "#b3a381", accent: "#d0584a", accent2: "#f0c75e" },
    grad: "linear-gradient(180deg,#1d1a2a,#6b3b1a)", sil: "#080604", skyk: "castle", part: ["ember", "#ffa94d", 26],
    tags: { medieval: 3, "dark fantasy": 2.5, fantasy: 1.5, "souls-like": 2, historical: 1.5, "hack and slash": 1, "dungeon crawler": 1.5, "party-based rpg": 1, "tactical rpg": 1, swordplay: 2, "grand strategy": 1 },
  },
  cyber: {
    name: "Neon Sprawl", tag: "Neon rain. Chrome nerves. Static in the sky.",
    disp: "'Orbitron',sans-serif", body: "'Rajdhani',sans-serif",
    c: { bg: "#07050f", panel: "rgba(14,10,32,.8)", panel2: "rgba(28,18,58,.9)", line: "#3a2a7a", text: "#e8f3ff", mute: "#8f9bd6", accent: "#00e5ff", accent2: "#ff2bd6" },
    grad: "linear-gradient(180deg,#1a0838,#5c1670)", sil: "#06030f", skyk: "neon", part: ["rain", "#5ff3ff", 46],
    tags: { cyberpunk: 3, robots: 1.5, mechs: 1.2, "immersive sim": 1, futuristic: 2, transhumanism: 2, hacking: 2, "sci-fi": 0.8 },
  },
  space: {
    name: "Deep Void", tag: "Silence, starlight and a long way from home.",
    disp: "'Audiowide',sans-serif", body: "'Exo 2',sans-serif",
    c: { bg: "#05070f", panel: "rgba(10,16,36,.8)", panel2: "rgba(20,28,62,.9)", line: "#28407a", text: "#e6eeff", mute: "#8da2d6", accent: "#7aa2ff", accent2: "#b388ff" },
    grad: "linear-gradient(180deg,#05061a,#2a1a6a)", sil: "#040612", skyk: "peaks", part: ["stars", "#dfe8ff", 70],
    tags: { "sci-fi": 2, space: 3, "4x": 1.5, flight: 1, "space sim": 3, aliens: 2, "colony sim": 0.5, futuristic: 0.5 },
  },
  horror: {
    name: "The Haunting", tag: "Something is watching. Keep playing.",
    disp: "'Creepster',cursive", body: "'Lora',Georgia,serif",
    c: { bg: "#0b0809", panel: "rgba(22,12,14,.84)", panel2: "rgba(40,18,22,.92)", line: "#4d1d22", text: "#eadcd8", mute: "#a58a86", accent: "#c0242f", accent2: "#e0cfa8" },
    grad: "linear-gradient(180deg,#1a0508,#4a0f16)", sil: "#050304", skyk: "tombs", part: ["fog", "#8c7f86", 7],
    tags: { horror: 3, "psychological horror": 3, "survival horror": 3, zombies: 2, gore: 1.5, lovecraftian: 3, dark: 1.2, thriller: 1.5, supernatural: 2, atmospheric: 0.3 },
  },
  cozy: {
    name: "Lantern Hollow", tag: "Warm lanterns, soft light, no rush.",
    disp: "'Fredoka',sans-serif", body: "'Nunito',sans-serif",
    c: { bg: "#17131f", panel: "rgba(36,28,50,.8)", panel2: "rgba(54,42,72,.9)", line: "#5a4a78", text: "#f6ecf5", mute: "#b9a6c9", accent: "#ff9eb5", accent2: "#ffd98a" },
    grad: "linear-gradient(180deg,#2a2050,#e07a6a)", sil: "#120d1c", skyk: "hills", part: ["firefly", "#ffe38a", 22],
    tags: { cozy: 3, "farming sim": 2.5, relaxing: 2.5, cute: 2, "life sim": 2, casual: 1, "family friendly": 1.5, wholesome: 3, crafting: 0.4, building: 0.4 },
  },
  retro: {
    name: "Arcade Wave", tag: "Insert coin. High scores forever.",
    disp: "'Press Start 2P',monospace", body: "'Space Mono',monospace",
    c: { bg: "#0d0221", panel: "rgba(26,8,52,.82)", panel2: "rgba(44,14,84,.9)", line: "#5b2a9e", text: "#fdf1ff", mute: "#c19be0", accent: "#ff4fa3", accent2: "#3df5ff" },
    grad: "linear-gradient(180deg,#1a0540,#ff4fa3)", sil: "#14052e", skyk: "pixel", part: ["pixel", "#3df5ff", 30],
    tags: { "pixel graphics": 2, retro: 3, arcade: 3, classic: 1.5, platformer: 1.2, "shoot 'em up": 2, "bullet hell": 2, "2d platformer": 1.5, "side scroller": 1, "beat 'em up": 1.5, rhythm: 1.5, metroidvania: 1, pinball: 2 },
  },
  war: {
    name: "Ashfall", tag: "Smoke on the horizon. Hold the line.",
    disp: "'Black Ops One',sans-serif", body: "'Saira Condensed',sans-serif",
    c: { bg: "#0e100c", panel: "rgba(24,27,20,.84)", panel2: "rgba(38,43,30,.92)", line: "#4a5238", text: "#e4e6d8", mute: "#9ea58a", accent: "#9aa84a", accent2: "#e0a030" },
    grad: "linear-gradient(180deg,#2a2a1a,#8a5a20)", sil: "#080905", skyk: "ruins", part: ["ash", "#b9b9a8", 34],
    tags: { "post-apocalyptic": 3, war: 3, "world war ii": 3, military: 2.5, wargame: 2.5, survival: 0.8, "open world survival craft": 0.8, tactical: 1, fps: 0.5, shooter: 0.4, "real time tactics": 1.5, "turn-based tactics": 1 },
  },
  anime: {
    name: "Sakura Dreams", tag: "Petals drift. Every story is a love letter.",
    disp: "'Mochiy Pop One',sans-serif", body: "'Zen Maru Gothic',sans-serif",
    c: { bg: "#1a1020", panel: "rgba(42,24,54,.8)", panel2: "rgba(62,36,78,.9)", line: "#7a4a96", text: "#fff0f8", mute: "#d3a9d9", accent: "#ff7fb0", accent2: "#8fd7ff" },
    grad: "linear-gradient(180deg,#3a2060,#ff9cc6)", sil: "#1a0f24", skyk: "fuji", part: ["petal", "#ffb7d5", 26],
    tags: { anime: 3, "visual novel": 2.5, "dating sim": 2.5, romance: 2, jrpg: 2, manga: 3, otome: 3, "female protagonist": 0.3 },
  },
  racing: {
    name: "Redline", tag: "Redline everything.",
    disp: "'Russo One',sans-serif", body: "'Chakra Petch',sans-serif",
    c: { bg: "#0a0c10", panel: "rgba(18,22,30,.84)", panel2: "rgba(30,36,50,.92)", line: "#3a4660", text: "#f0f4fa", mute: "#98a6c0", accent: "#ff3b30", accent2: "#ffd60a" },
    grad: "linear-gradient(180deg,#10141c,#b8281f)", sil: "#07090d", skyk: "road", part: ["streak", "#ffd60a", 18],
    tags: { racing: 3, driving: 2.5, sports: 1.5, "automobile sim": 3, parkour: 1, "fast-paced": 0.8, football: 2, basketball: 2, soccer: 2 },
  },
  noir: {
    name: "Midnight Case", tag: "Rain on the glass. Every case has a secret.",
    disp: "'Playfair Display',Georgia,serif", body: "'Libre Franklin',sans-serif",
    c: { bg: "#0c0c0e", panel: "rgba(22,22,26,.84)", panel2: "rgba(36,36,42,.92)", line: "#46464f", text: "#ece8df", mute: "#a09c92", accent: "#9a9aa6", accent2: "#e5c07b" },
    grad: "linear-gradient(180deg,#141416,#3c3c44)", sil: "#060607", skyk: "noir", part: ["rain", "#a8a8b4", 40],
    tags: { detective: 3, crime: 2.5, mystery: 2.5, stealth: 1.2, noir: 3, "point & click": 0.8, "interactive fiction": 0.8, investigation: 3 },
  },
};

// ---------------------------------------------------------------- picking a world
function tagScores(tags: string[]) {
  const s: Record<string, number> = {};
  for (const g of tags) {
    const k = String(g).trim().toLowerCase();
    for (const [tk, t] of Object.entries(THEMES)) {
      const w = t.tags[k];
      if (w) s[tk] = (s[tk] ?? 0) + w;
    }
  }
  return s;
}

const argmax = (s: Record<string, number>) => Object.keys(s).reduce((a, b) => (s[b] > s[a] ? b : a));

/** World for one game (its tag list). */
export function themeFor(tags: string[]): string {
  const s = tagScores(tags);
  return Object.keys(s).length ? argmax(s) : DEFAULT;
}

const RELATED = new Set(["cyber|noir", "cyber|space", "cyber|retro", "medieval|horror", "cozy|anime"]);
const related = (a: string, b: string) => RELATED.has(`${a}|${b}`) || RELATED.has(`${b}|${a}`);

/** games: [name, tags, hours] -> [world, names of the games that decided it] (see themes.py theme_for_library). */
export function themeForLibrary(games: [string, string[], number][]): [string, string[]] {
  const direct: Record<string, number> = {};
  const drivers: Record<string, [number, string][]> = {};
  for (const [name, tags, hours] of games) {
    const s = tagScores(tags);
    if (!Object.keys(s).length) continue;
    const best = argmax(s);
    const w = hours * (0.75 + (0.25 * Math.min(s[best], 3)) / 3);
    direct[best] = (direct[best] ?? 0) + w;
    (drivers[best] ??= []).push([w, name]);
  }
  const keys = Object.keys(direct);
  if (!keys.length) return [DEFAULT, []];
  const total: Record<string, number> = {};
  for (const t of keys) total[t] = direct[t] + 0.5 * keys.filter((u) => related(t, u)).reduce((a, u) => a + direct[u], 0);
  const best = keys.reduce((a, b) => {
    const ka = [total[a], Math.max(...drivers[a].map((d) => d[0])), direct[a]];
    const kb = [total[b], Math.max(...drivers[b].map((d) => d[0])), direct[b]];
    for (let i = 0; i < 3; i++) if (kb[i] !== ka[i]) return kb[i] > ka[i] ? b : a;
    return a;
  });
  return [best, drivers[best].sort((x, y) => y[0] - x[0]).slice(0, 3).map((d) => d[1])];
}

// ---------------------------------------------------------------- seeded random (stand-in for Python's random.Random)
function rng(seed: number) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return {
    random: next,
    randint: (lo: number, hi: number) => lo + Math.floor(next() * (hi - lo + 1)),
    uniform: (lo: number, hi: number) => lo + next() * (hi - lo),
    choice: <T,>(xs: readonly T[]) => xs[Math.floor(next() * xs.length)],
  };
}

export function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

// ---------------------------------------------------------------- skylines (SVG silhouettes)
const poly = (pts: string[], fill: string) => `<polygon points="${pts.join(" ")}" fill="${fill}"/>`;
const f1 = (n: number) => n.toFixed(1);

function castle(fill: string, lit: string) {
  const r = rng(7);
  let o = `<rect x="0" y="140" width="1200" height="60" fill="${fill}"/>`;
  for (let x = 0; x < 1200; x += 24) o += `<rect x="${x}" y="130" width="12" height="12" fill="${fill}"/>`;
  let x = 30;
  while (x < 1160) {
    const w = r.choice([46, 56, 66]);
    const h = r.randint(70, 150);
    const y = 200 - h;
    o += `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"/>`;
    for (let k = 0; k < w - 6; k += 13) o += `<rect x="${x + k}" y="${y - 10}" width="7" height="11" fill="${fill}"/>`;
    if (r.random() < 0.55) o += poly([`${x - 5},${y - 9}`, `${x + w / 2},${y - 58}`, `${x + w + 5},${y - 9}`], fill);
    o += `<rect x="${x + w / 2 - 3}" y="${y + 22}" width="6" height="14" fill="${lit}"/>`;
    x += w + r.randint(60, 150);
  }
  return o;
}

function city(fill: string, wins: string[] | null, seed: number, density = 0.5, maxh = 170, broken = false, antenna = false) {
  const r = rng(seed);
  let x = 0;
  let o = "";
  while (x < 1200) {
    const w = r.randint(36, 90);
    const h = r.randint(50, maxh);
    const y = 200 - h;
    if (broken) {
      const pts = [`${x},200`, `${x},${y}`];
      for (let k = 1; k < 4; k++) pts.push(`${Math.round(x + (w * k) / 4)},${y + r.randint(0, 28)}`);
      pts.push(`${x + w},${y + r.randint(0, 20)}`, `${x + w},200`);
      o += poly(pts, fill);
    } else {
      o += `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"/>`;
      if (antenna && r.random() < 0.3) o += `<rect x="${x + Math.floor(w / 2)}" y="${y - 26}" width="2" height="26" fill="${fill}"/>`;
    }
    for (let wy = y + 10; wy < 190; wy += 14)
      for (let wx = x + 6; wx < x + w - 8; wx += 12)
        if (wins && r.random() < density) o += `<rect x="${wx}" y="${wy}" width="5" height="7" fill="${r.choice(wins)}" opacity=".85"/>`;
    x += w + r.randint(-6, 6);
  }
  return o;
}

const ground = (x: number) => 150 + 25 * Math.sin(x / 170) + 14 * Math.sin(x / 57);

function hills(fill: string, glow: string) {
  const pts: string[] = [];
  for (let x = 0; x <= 1200; x += 20) pts.push(`${x},${f1(ground(x))}`);
  let o = poly(["0,200", ...pts, "1200,200"], fill);
  const r = rng(3);
  for (let i = 0; i < 18; i++) {
    const x = r.randint(10, 1190);
    const yb = ground(x) + 4;
    const h = r.randint(26, 52);
    for (let k = 0; k < 3; k++) {
      const w = 16 + k * 7;
      o += poly([`${x - w / 2},${f1(yb - (k * h) / 3.2)}`, `${x},${f1(yb - h / 2.2 - (k * h) / 3.2)}`, `${x + w / 2},${f1(yb - (k * h) / 3.2)}`], fill);
    }
  }
  for (const x of [260, 830]) {
    const yb = ground(x) + 3;
    o += `<rect x="${x - 17}" y="${f1(yb - 24)}" width="34" height="26" fill="${fill}"/>`;
    o += poly([`${x - 23},${f1(yb - 23)}`, `${x},${f1(yb - 46)}`, `${x + 23},${f1(yb - 23)}`], fill);
    o += `<rect x="${x - 5}" y="${f1(yb - 16)}" width="9" height="9" fill="${glow}"/>`;
  }
  return o;
}

function tombs(fill: string) {
  const pts: string[] = [];
  for (let x = 0; x <= 1200; x += 20) pts.push(`${x},${f1(168 + 8 * Math.sin(x / 90))}`);
  let o = poly(["0,200", ...pts, "1200,200"], fill);
  const r = rng(11);
  for (let i = 0; i < 22; i++) {
    const x = r.randint(10, 1180);
    const h = r.randint(20, 40);
    o += `<rect x="${x}" y="${170 - h + 6}" width="16" height="${h}" rx="8" fill="${fill}"/>`;
  }
  for (const x of [150, 700, 1050])
    o += `<path d="M${x},175 L${x},110 L${x - 22},80 M${x},135 L${x + 26},100 M${x},120 L${x - 12},95 M${x + 26},100 L${x + 34},80" stroke="${fill}" stroke-width="6" fill="none" stroke-linecap="round"/>`;
  return o;
}

function peaks(fill: string, seed: number) {
  const r = rng(seed);
  const pts = ["0,200"];
  let x = 0;
  while (x < 1200) {
    pts.push(`${x},${r.randint(70, 175)}`);
    x += r.randint(50, 110);
  }
  return poly([...pts, "1200,175", "1200,200"], fill);
}

function pixel(fill: string, seed: number) {
  const r = rng(seed);
  const pts = ["0,200"];
  let x = 0;
  let y = 140;
  while (x < 1200) {
    const w = r.choice([40, 60, 80, 100]);
    pts.push(`${x},${y}`, `${x + w},${y}`);
    x += w;
    y = Math.max(90, Math.min(180, y + r.choice([-30, -20, 20, 30])));
  }
  return poly([...pts, "1200,200"], fill);
}

function fuji(fill: string, blossom: string) {
  let o = `<path d="M0,200 L0,182 C300,172 420,112 520,84 C560,72 640,72 680,84 C780,112 900,172 1200,182 L1200,200Z" fill="${fill}"/>`;
  for (const [x, s] of [[120, 1], [330, 0.8], [930, 1.1], [1090, 0.9]]) {
    o += `<rect x="${x - 3}" y="${Math.round(150 - 10 * s)}" width="6" height="${Math.round(50 + 10 * s)}" fill="${fill}"/>`;
    for (const [dx, dy, rr] of [[0, -32, 24], [-18, -16, 18], [18, -16, 18]])
      o += `<circle cx="${Math.round(x + dx * s)}" cy="${Math.round(150 + dy * s)}" r="${Math.round(rr * s)}" fill="${blossom}" opacity=".85"/>`;
  }
  return o;
}

function road(fill: string, accent: string, seed: number) {
  let o = city("#0a0d14", null, seed, 0.5, 70);
  o += poly(["0,200", "1200,200", "690,62", "510,62"], fill);
  o += `<path d="M0,200 L510,62 M1200,200 L690,62" stroke="${accent}" stroke-width="3" fill="none"/>`;
  for (let i = 0; i < 6; i++) {
    const t0 = i / 6;
    const t1 = (i + 0.55) / 6;
    const y0 = 200 - 138 * t0;
    const y1 = 200 - 138 * t1;
    const w0 = 14 - 12 * t0;
    const w1 = 14 - 12 * t1;
    o += poly([`${f1(600 - w0)},${f1(y0)}`, `${f1(600 + w0)},${f1(y0)}`, `${f1(600 + w1)},${f1(y1)}`, `${f1(600 - w1)},${f1(y1)}`], "#ffd60a");
  }
  return o;
}

const skyCache: Record<string, string> = {};
export function skyUri(key: string): string {
  if (skyCache[key]) return skyCache[key];
  const t = THEMES[key];
  const f = t.sil;
  const a = t.c.accent;
  const a2 = t.c.accent2;
  const inner = (
    {
      castle: () => castle(f, "#ffb347"),
      foundry: () => city(f, ["#ff8a3d"], 5, 0.12, 120, false, true),
      neon: () => city(f, [a, a2, "#7a5cff"], 21, 0.45, 170, false, true),
      noir: () => city(f, ["#e5c07b"], 33, 0.12),
      ruins: () => city(f, null, 9, 0.5, 140, true),
      tombs: () => tombs(f),
      hills: () => hills(f, "#ffd98a"),
      peaks: () => peaks(f, 4),
      pixel: () => pixel(f, 8),
      fuji: () => fuji(f, "#ff9cc6"),
      road: () => road(f, a, 12),
    } as Record<string, () => string>
  )[t.skyk]();
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 200" preserveAspectRatio="none">${inner}</svg>`;
  return (skyCache[key] = `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`);
}

// ---------------------------------------------------------------- particles
// kind: [size min, size max, seconds min, seconds max, horizontal drift px, y min %, y max %]
const PART: Record<PartKind, number[]> = {
  ember: [2, 5, 8, 18, 80, 0, 0], pixel: [4, 8, 7, 16, 0, 0, 0], ash: [2, 4, 12, 24, 60, 0, 0],
  stars: [1, 3, 2, 6, 0, 0, 78], rain: [1, 2.2, 0.8, 1.7, 22, 0, 0], petal: [8, 14, 9, 17, 140, 0, 0],
  firefly: [3, 5, 5, 11, 60, 15, 92], streak: [2, 6, 1.2, 3, 0, 4, 96], fog: [16, 30, 14, 30, 0, 6, 78],
};

export type Particle = Record<string, string>;
export function particles(kind: PartKind, n: number, seed: number, mini = false): Particle[] {
  const r = rng(seed);
  const [smin, smax, tmin, tmax, xmax, ymin, ymax] = PART[kind];
  const k = mini ? (kind === "fog" ? 0.4 : 0.65) : 1;
  return Array.from({ length: n }, () => ({
    "--l": `${f1(r.uniform(0, 100))}%`,
    "--y": `${f1(r.uniform(ymin, ymax))}%`,
    "--s": `${f1(r.uniform(smin, smax) * k)}px`,
    "--t": `${f1(r.uniform(tmin, tmax) * (mini ? 0.7 : 1))}s`,
    "--d": `-${f1(r.uniform(0, tmax))}s`,
    "--x": `${xmax ? r.randint(-xmax, xmax) : 0}px`,
  }));
}

/** CSS variables that colour a card in a world's palette. */
export function cardVars(key: string): Record<string, string> {
  const t = THEMES[key];
  return { "--ca": t.c.accent, "--ca2": t.c.accent2, "--cl": t.c.line, "--cp": t.c.panel2, "--cd": t.disp, "--cb": t.body };
}
