// Browser-side calls to the Next.js proxy (/api/m/*), which forwards to Modal.
import type { Card, GameDetail, GameSummary, LibGame, Player, RecResult } from "./types";

export class ApiError extends Error {}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`/api/m/${path}`, init);
  } catch {
    throw new ApiError("Couldn't reach the server. Check your connection and try again.");
  }
  let j: unknown = null;
  try {
    j = await r.json();
  } catch {
    /* non-JSON error page */
  }
  if (!r.ok) {
    const msg = (j as { error?: string; detail?: string } | null)?.error ?? (j as { detail?: string } | null)?.detail;
    throw new ApiError(msg || `Request failed (${r.status})`);
  }
  return j as T;
}

export const api = {
  search: (q: string) => call<GameSummary[]>(`search?q=${encodeURIComponent(q)}`),
  games: (ids: number[]) => call<GameSummary[]>(`games?ids=${ids.join(",")}`),
  game: (id: number) => call<GameDetail>(`game/${id}`),
  gem: () => call<GameSummary | null>("gem"),
  demo: () => call<(GameSummary & { hours: number })[]>("demo"),
  player: (q: string) => call<Player>(`player?q=${encodeURIComponent(q)}`),
  recommend: (
    library: { app_id: number; hours: number }[],
    opts: { n?: number; max_price?: number | null; cc?: string; include_explicit?: boolean; owned?: number[] } = {},
  ) =>
    call<RecResult>("recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ library, ...opts }),
    }),
};

export async function screenshots(ids: number[]): Promise<Record<string, string[]>> {
  if (!ids.length) return {};
  try {
    const r = await fetch(`/api/shots?ids=${ids.join(",")}`);
    return r.ok ? r.json() : {};
  } catch {
    return {};
  }
}

/** The library as the recommender wants it: every game with its hours. */
export const libraryPayload = (lib: LibGame[]) => lib.map((g) => ({ app_id: g.app_id, hours: g.hours }));

export type { Card };
