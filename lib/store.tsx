"use client";
// Client-side state: the player's library and settings, kept in this browser only (localStorage).
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { defaultModes } from "./profile";
import type { GameSummary, LibGame } from "./types";

type Settings = { mode: "Simple" | "Advanced"; budget: number; adult: boolean };
const DEFAULTS: Settings = { mode: "Simple", budget: 60, adult: false };
const KEY = "tasteforge:v1";

type Store = {
  ready: boolean;
  library: LibGame[];
  settings: Settings;
  add: (g: GameSummary, hours?: number) => void;
  remove: (appId: number) => void;
  update: (appId: number, patch: Partial<LibGame>) => void;
  replace: (games: (GameSummary & { hours: number })[]) => void;
  clear: () => void;
  set: (patch: Partial<Settings>) => void;
};

const Ctx = createContext<Store | null>(null);

export const toLib = (g: GameSummary, hours = 20): LibGame => ({ ...g, hours, modes: defaultModes(g) });

export function StoreProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [library, setLibrary] = useState<LibGame[]>([]);
  const [settings, setSettings] = useState<Settings>(DEFAULTS);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const s = JSON.parse(raw);
        if (Array.isArray(s.library)) setLibrary(s.library);
        if (s.settings) setSettings({ ...DEFAULTS, ...s.settings });
      }
    } catch {
      /* storage blocked or corrupt: start fresh */
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try {
      localStorage.setItem(KEY, JSON.stringify({ library, settings }));
    } catch {
      /* storage full or blocked */
    }
  }, [ready, library, settings]);

  const add = useCallback((g: GameSummary, hours?: number) => {
    setLibrary((lib) => (lib.some((x) => x.app_id === g.app_id) ? lib : [...lib, toLib(g, hours)]));
  }, []);
  const remove = useCallback((id: number) => setLibrary((lib) => lib.filter((x) => x.app_id !== id)), []);
  const update = useCallback(
    (id: number, patch: Partial<LibGame>) => setLibrary((lib) => lib.map((x) => (x.app_id === id ? { ...x, ...patch } : x))),
    [],
  );
  const replace = useCallback((games: (GameSummary & { hours: number })[]) => setLibrary(games.map((g) => toLib(g, g.hours))), []);
  const clear = useCallback(() => setLibrary([]), []);
  const set = useCallback((patch: Partial<Settings>) => setSettings((s) => ({ ...s, ...patch })), []);

  const value = useMemo(
    () => ({ ready, library, settings, add, remove, update, replace, clear, set }),
    [ready, library, settings, add, remove, update, replace, clear, set],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useStore outside StoreProvider");
  return s;
}
