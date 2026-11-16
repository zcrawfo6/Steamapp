"use client";
// Fetch EASE-safe recommendations for a library, debounced, with a small in-memory cache shared across tabs.
import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { RecResult } from "./types";

type Opts = { n?: number; max_price?: number | null; cc?: string; include_explicit?: boolean; owned?: number[] };
const cache = new Map<string, RecResult>();
const inflight = new Map<string, Promise<RecResult>>();

export function useRecs(library: { app_id: number; hours: number }[] | null, opts: Opts) {
  const key = library && library.length ? JSON.stringify([library, opts]) : null;
  const [state, setState] = useState<{ key: string | null; data: RecResult | null; error: string | null }>({ key: null, data: null, error: null });

  useEffect(() => {
    if (!key) return;
    const hit = cache.get(key);
    if (hit) {
      setState({ key, data: hit, error: null });
      return;
    }
    let live = true;
    const t = setTimeout(async () => {
      try {
        let p = inflight.get(key);
        if (!p) {
          const [lib, o] = JSON.parse(key);
          p = api.recommend(lib, o);
          inflight.set(key, p);
        }
        const data = await p;
        cache.set(key, data);
        if (live) setState({ key, data, error: null });
      } catch (e) {
        if (live) setState({ key, data: null, error: e instanceof ApiError ? e.message : "Something went wrong." });
      } finally {
        inflight.delete(key);
      }
    }, 350);
    return () => {
      live = false;
      clearTimeout(t);
    };
  }, [key]);

  const current = state.key === key;
  return { data: current ? state.data : null, error: current ? state.error : null, loading: !!key && !current };
}
