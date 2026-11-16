// Player-profile math, ported from Steamapp_Juan_Model/app.py (profile, modes_for, taste_match, ...).
import type { GameSummary, LibGame, Mode } from "./types";

/** Games with fewer hours stay in the library (never recommended) but don't shape the taste profile. */
export const MIN_HOURS = 2.5;

export const MODES: Record<Mode, [string, string]> = {
  story: ["📖", "Story / Campaign"],
  coop: ["🤝", "Co-op (PvE)"],
  pvp: ["⚔️", "PvP"],
};
const STORY_T = new Set(["story rich", "singleplayer", "choices matter", "multiple endings", "visual novel",
  "interactive fiction", "rpg", "jrpg", "adventure", "action-adventure", "walking simulator"]);
const COOP_T = new Set(["co-op", "online co-op", "local co-op", "co-op campaign"]);
const PVP_T = new Set(["pvp", "competitive", "fighting", "2d fighter", "arena shooter", "esports", "moba",
  "battle royale", "hero shooter"]);
const MULTI_T = new Set(["multiplayer", "massively multiplayer", "mmorpg", "local multiplayer"]);

// format / business-model tags: not used as taste (same list as the recommender's BROAD)
const BROAD = new Set(["singleplayer", "multiplayer", "indie", "free to play", "early access", "great soundtrack",
  "co-op", "online co-op", "pvp", "massively multiplayer", "controller", "moddable", "classic", "remake", "remaster",
  "female protagonist", "steam achievements", "family friendly", "masterpiece", "addictive", "replay value",
  "difficult", "short", "beautiful", "funny", "cute", "colorful", "relaxing", "utilities", "software"]);

type Tagged = { tags?: string[]; raw_tags?: string[]; genres?: string[] };
const allTags = (g: Tagged) => (g.raw_tags?.length ? g.raw_tags : g.genres ?? []);

/** Up to 5 taste tags for a game: its user tags without format tags, else the recommender's tags. */
export function tasteTags(g: Tagged): string[] {
  const t = allTags(g).filter((x) => !BROAD.has(x.toLowerCase())).slice(0, 5);
  return t.length ? t : g.tags?.length ? g.tags : (g.genres ?? []).slice(0, 5);
}

/** Which of story / co-op / pvp this game supports, from its tags (story is the fallback). */
export function modesFor(g: GameSummary): Mode[] {
  const s = new Set(allTags(g).map((x) => x.trim().toLowerCase()));
  const any = (set: Set<string>) => [...set].some((x) => s.has(x));
  const coop = any(COOP_T);
  const has: Record<Mode, boolean> = { story: any(STORY_T), coop, pvp: any(PVP_T) || (any(MULTI_T) && !coop) };
  const out = (Object.keys(MODES) as Mode[]).filter((m) => has[m]);
  return out.length ? out : ["story"];
}

/** Default mode split: the tag-suggested modes, even shares. */
export function defaultModes(g: GameSummary): Partial<Record<Mode, number>> {
  const have = modesFor(g);
  return Object.fromEntries(have.map((m) => [m, have.length === 1 ? 100 : 50]));
}

/** {mode: share 0-1} for one game, normalized from its ticked shares. */
export function modeShares(g: LibGame): Partial<Record<Mode, number>> {
  const on = Object.entries(g.modes) as [Mode, number][];
  if (!on.length) return {};
  if (on.length === 1) return { [on[0][0]]: 1 };
  const tot = on.reduce((a, [, v]) => a + v, 0);
  return Object.fromEntries(on.map(([m, v]) => [m, tot ? v / tot : 1 / on.length]));
}

export type Profile = {
  tot: number;
  aff: Record<string, number>; // tag -> share of hours
  avgPrice: number; // hour-weighted (geometric) price
  n: number;
  modes: Partial<Record<Mode, number>>; // mode -> hours
};

/** Taste profile over the games with MIN_HOURS+ (app.py profile()). */
export function profile(games: LibGame[]): Profile {
  const played = games.filter((g) => g.hours >= MIN_HOURS);
  const aff: Record<string, number> = {};
  let tot = 0;
  let wp = 0;
  const modes: Partial<Record<Mode, number>> = {};
  for (const g of played) {
    const h = g.hours;
    tot += h;
    wp += Math.log1p(g.price ?? 0) * h;
    const tags = tasteTags(g);
    for (const x of tags) aff[x] = (aff[x] ?? 0) + h / tags.length;
    for (const [m, share] of Object.entries(modeShares(g)) as [Mode, number][]) modes[m] = (modes[m] ?? 0) + h * share;
  }
  for (const k in aff) aff[k] /= tot || 1;
  const lp = tot ? wp / tot : 0;
  return { tot, aff, avgPrice: Math.exp(lp) - 1, n: played.length, modes };
}

/** Cosine similarity of two genre-affinity profiles, 0-1. */
export function tasteMatch(a: Record<string, number>, b: Record<string, number>): number {
  let dot = 0;
  for (const k in a) dot += a[k] * (b[k] ?? 0);
  const na = Math.sqrt(Object.values(a).reduce((s, v) => s + v * v, 0));
  const nb = Math.sqrt(Object.values(b).reduce((s, v) => s + v * v, 0));
  return na && nb ? dot / (na * nb) : 0;
}

export const fmtPrice = (p: number | null | undefined) => (p == null ? "n/a" : p === 0 ? "Free" : `$${p.toFixed(2)}`);

export function short(n: number): string {
  n = Math.round(n);
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e4) return `${(n / 1e3).toFixed(0)}k`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}k`;
  return String(n);
}

export function num(v: number): string {
  for (const [div, suf] of [[1e9, "B"], [1e6, "M"], [1e3, "K"]] as const)
    if (v >= div) return `${(v / div).toFixed(1).replace(/\.0$/, "")}${suf}`;
  return Math.round(v).toLocaleString();
}

export const hrs = (h: number) => (Number.isInteger(h) ? `${h}` : h.toFixed(1));
