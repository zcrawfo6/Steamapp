"use client";
// Hidden gem: a well-loved, lesser-known game in the bottom-right corner (wide screens only).
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmtPrice } from "@/lib/profile";
import type { GameSummary } from "@/lib/types";

export default function Gem() {
  const [g, setG] = useState<GameSummary | null>(null);
  useEffect(() => {
    if (!window.matchMedia("(min-width: 1600px)").matches) return; // only shown on wide screens
    api.gem().then(setG).catch(() => {});
  }, []);
  if (!g) return null;
  return (
    <aside className="gem">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={g.image ?? `https://cdn.akamai.steamstatic.com/steam/apps/${g.app_id}/header.jpg`} alt="" />
      <div className="gb">
        <span className="gpill">HIDDEN GEM</span>
        {g.rating}% positive
        <a href={g.store_url} target="_blank" rel="noreferrer">
          {g.title} ↗
        </a>
        {(g.reviews ?? 0).toLocaleString()} reviews · {fmtPrice(g.price)}
      </div>
    </aside>
  );
}
