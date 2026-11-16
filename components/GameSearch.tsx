"use client";
// One big search box: picked games as removable chips, live search of the model's catalog underneath.
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { hrs } from "@/lib/profile";
import { useStore } from "@/lib/store";
import type { GameSummary } from "@/lib/types";

const SHOW = 14; // chips shown before "+N more" (an imported library can have hundreds)

export default function GameSearch() {
  const { library, add, remove } = useStore();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<GameSummary[] | null>(null);
  const [active, setActive] = useState(0);
  const [open, setOpen] = useState(false);
  const [all, setAll] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = q.trim();
    if (t.length < 2) {
      setHits(null);
      return;
    }
    let live = true;
    const id = setTimeout(async () => {
      try {
        const r = await api.search(t);
        if (live) {
          setHits(r);
          setActive(0);
        }
      } catch {
        if (live) setHits([]);
      }
    }, 200);
    return () => {
      live = false;
      clearTimeout(id);
    };
  }, [q]);

  useEffect(() => {
    const off = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", off);
    return () => document.removeEventListener("mousedown", off);
  }, []);

  const have = new Set(library.map((g) => g.app_id));
  const list = (hits ?? []).filter((g) => !have.has(g.app_id));
  const pick = (g: GameSummary) => {
    add(g);
    setQ("");
    setHits(null);
    input.current?.focus();
  };
  const shown = all ? library : library.slice(0, SHOW);

  return (
    <div className="search" ref={box}>
      <div className="box" onClick={() => input.current?.focus()}>
        {shown.map((g) => (
          <span key={g.app_id} className="tagchip" title={g.in_model ? undefined : "The model doesn't know this game yet; it only shapes your profile"}>
            {g.title}
            <span className="h">{hrs(g.hours)}h</span>
            <button aria-label={`Remove ${g.title}`} onClick={(e) => (e.stopPropagation(), remove(g.app_id))}>
              ×
            </button>
          </span>
        ))}
        {library.length > SHOW && (
          <button className="tagchip more" style={{ cursor: "pointer" }} onClick={(e) => (e.stopPropagation(), setAll((a) => !a))}>
            {all ? "show less" : `+${library.length - SHOW} more`}
          </button>
        )}
        <input
          ref={input}
          value={q}
          onChange={(e) => (setQ(e.target.value), setOpen(true))}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((a) => Math.min(a + 1, list.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => Math.max(a - 1, 0));
            } else if (e.key === "Enter" && list[active]) {
              e.preventDefault();
              pick(list[active]);
            } else if (e.key === "Backspace" && !q && library.length) {
              remove(library[library.length - 1].app_id);
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder={library.length ? "Add another game..." : "Search a game you've played..."}
          aria-label="Search games you've played"
          role="combobox"
          aria-expanded={open && !!hits}
          aria-controls="search-results"
          autoComplete="off"
        />
      </div>
      {open && hits && (
        <div className="results" id="search-results" role="listbox">
          {list.length ? (
            list.map((g, i) => (
              <button key={g.app_id} role="option" aria-selected={i === active} onMouseEnter={() => setActive(i)} onClick={() => pick(g)}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={g.image ?? `https://cdn.akamai.steamstatic.com/steam/apps/${g.app_id}/header.jpg`} alt="" loading="lazy" />
                <span>
                  {g.title}
                  <div className="meta">
                    {g.rating != null ? `${g.rating}% positive · ` : ""}
                    {g.reviews ? `${g.reviews.toLocaleString()} reviews` : "no reviews"}
                    {!g.in_model && " · not known to the model yet"}
                  </div>
                </span>
              </button>
            ))
          ) : (
            <div className="none">No matching games{hits.length ? " you haven't added" : ""}.</div>
          )}
        </div>
      )}
    </div>
  );
}
