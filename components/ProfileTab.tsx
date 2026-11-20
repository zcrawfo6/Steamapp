"use client";
// Player Profile: KPIs, genre radar, where the hours go, price comfort zone, play style, biggest games.
import { useMemo } from "react";
import { MIN_HOURS, MODES, fmtPrice, hrs, modeShares, profile } from "@/lib/profile";
import { useStore } from "@/lib/store";
import { THEMES, themeForLibrary } from "@/lib/themes";
import { tasteTags } from "@/lib/profile";
import type { Mode } from "@/lib/types";
import { Bar, Radar } from "./ui";

const BUCKETS: [string, number, number][] = [
  ["Free", 0, 0], ["Under $10", 0.01, 9.99], ["$10–20", 10, 20], ["$20–40", 20.01, 40], ["$40+", 40.01, 1e9],
];

export default function ProfileTab() {
  const { library } = useStore();
  const P = useMemo(() => profile(library), [library]);
  const played = library.filter((g) => g.hours >= MIN_HOURS);
  const top = Object.entries(P.aff).sort((a, b) => b[1] - a[1]);
  const rad = top.slice(0, 8);
  while (rad.length < 3) rad.push(["—", 0.0001]);
  const pb = BUCKETS.map(([l, a, b]) => [l, played.filter((g) => (g.price ?? 0) >= a && (g.price ?? 0) <= b).reduce((s, g) => s + g.hours, 0)] as const);
  const mx = Math.max(...pb.map(([, h]) => h), 1);
  const ap = P.avgPrice;
  const arche = `${top[0]?.[0] ?? ""} ${ap < 15 ? "Bargain Hunter" : ap < 35 ? "Value Seeker" : "Premium Collector"}`;
  const modes = Object.entries(P.modes) as [Mode, number][];
  const th = modes.reduce((s, [, h]) => s + h, 0);
  const mainMode = modes.length ? MODES[modes.sort((a, b) => b[1] - a[1])[0][0]].split(" ")[0] : "—";
  const big = [...played].sort((a, b) => b.hours - a.hours).slice(0, 5);
  const [world, drivers] = themeForLibrary(played.map((g) => [g.title, tasteTags(g).concat(g.raw_tags ?? []), g.hours]));
  const w = THEMES[world];

  return (
    <>
      <div className="kpi">
        <div><b>{P.n}</b><span>games tracked</span></div>
        <div><b>{Math.round(P.tot)}h</b><span>total hours</span></div>
        <div><b>{fmtPrice(Math.round(ap * 100) / 100)}</b><span>hour-weighted price</span></div>
        <div><b>{mainMode}</b><span>main mode</span></div>
        <div><b style={{ fontSize: 16 }}>{arche}</b><span>your archetype</span></div>
        <div title={drivers.length ? `Decided by ${drivers.join(", ")}` : undefined}>
          <b style={{ fontSize: 16 }}>{w.name}</b><span>your world</span>
        </div>
      </div>
      <div className="grid2">
        <div className="card">
          <h2>Genre radar</h2>
          <Radar entries={rad} />
        </div>
        <div className="card">
          <h2>Where your hours go</h2>
          {top.slice(0, 7).map(([g, v]) => (
            <div key={g} style={{ margin: "7px 0" }}>
              <div className="mh"><span>{g}</span><span>{Math.round(v * 100)}%</span></div>
              <Bar pct={(v / top[0][1]) * 100} />
            </div>
          ))}
          <h2 style={{ marginTop: 18 }}>Price comfort zone</h2>
          {pb.map(([l, h]) => (
            <div key={l} style={{ display: "grid", gridTemplateColumns: "90px 1fr 50px", gap: 8, alignItems: "center", fontSize: 13, margin: "5px 0" }}>
              <span>{l}</span>
              <Bar pct={(h / mx) * 100} />
              <span>{Math.round(h)}h</span>
            </div>
          ))}
        </div>
      </div>
      <div className="grid2">
        <div className="card">
          <h2>Play style</h2>
          {th ? (
            (Object.keys(MODES) as Mode[]).map((m) =>
              P.modes[m] ? (
                <div className="mode" key={m}>
                  <div className="mh">
                    <span>{MODES[m]}</span>
                    <span>{Math.round(P.modes[m]!)}h · {Math.round((P.modes[m]! / th) * 100)}% of your time</span>
                  </div>
                  <Bar pct={(P.modes[m]! / th) * 100} />
                </div>
              ) : null,
            )
          ) : (
            <div className="why">Tick a mode on a game to see this.</div>
          )}
        </div>
        <div className="card">
          <h2>Your biggest games</h2>
          {big.map((g) => (
            <div className="todo" key={g.app_id}>
              <span>{g.title}</span>
              <span>
                {hrs(g.hours)}h ·{" "}
                {(Object.entries(modeShares(g)) as [Mode, number][]).map(([m, s]) => `${MODES[m].split(" ")[0]} ${Math.round(s * 100)}%`).join(" · ")}
              </span>
            </div>
          ))}
          <div className="note">Hours and how each game&apos;s time splits between story, co-op and PvP (set them in Advanced mode).</div>
        </div>
      </div>
    </>
  );
}
