"use client";
// One game's stats page (port of Steamapp_Juan_Model/game_detail.py): its world, facts, reviews, standing in its
// genre and how it compares with the genre and catalog averages.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, screenshots } from "@/lib/api";
import { fmtPrice, num } from "@/lib/profile";
import { themeFor } from "@/lib/themes";
import type { GameDetail, Metric } from "@/lib/types";
import { FLAG_NAMES } from "./RecCard";
import { COLD } from "./RecommendationsTab";
import { Bar, Msg, Spinner, WorldCard } from "./ui";

type Why = { rank: number; because: string[]; flags: string[] } | null;

const METRICS: [string, keyof GameDetail["metrics"], (v: number) => string][] = [
  ["Price", "price", (v) => (v === 0 ? "Free" : `$${v.toFixed(2)}`)],
  ["Positive reviews", "rating", (v) => `${v.toFixed(1)}%`],
  ["Total reviews", "reviews", num],
  ["Estimated owners", "owners", num],
  ["Avg. playtime", "hours", (v) => `${v.toFixed(1)}h`],
  ["Median playtime", "median_hours", (v) => `${v.toFixed(1)}h`],
  ["Peak concurrent players", "peak_ccu", num],
  ["Achievements", "achievements", num],
];

function reviewLabel(rating: number, reviews: number) {
  if (reviews < 10) return "Not enough reviews";
  for (const [floor, label] of [[95, "Overwhelmingly Positive"], [80, "Very Positive"], [70, "Mostly Positive"], [40, "Mixed"], [20, "Mostly Negative"]] as const)
    if (rating >= floor) return floor === 95 && reviews < 500 ? "Very Positive" : label;
  return reviews >= 500 ? "Overwhelmingly Negative" : "Very Negative";
}

function Delta({ v, avg }: { v: number; avg: number | null }) {
  if (!avg) return <span className="down">–</span>;
  const r = v / avg;
  const txt = r >= 3 ? `${r.toFixed(1)}×` : `${r >= 1 ? "+" : ""}${((r - 1) * 100).toFixed(0)}%`;
  return <span className={r >= 1 ? "up" : "down"}>{txt}</span>;
}

function MetricRow({ label, m, fmt }: { label: string; m: Metric; fmt: (v: number) => string }) {
  const v = m.value;
  const top = Math.max(v ?? 0, m.genre_avg ?? 0) || 1;
  return (
    <tr>
      <td>{label}</td>
      <td><b>{v != null ? fmt(v) : <span className="down">n/a</span>}</b></td>
      <td>{m.genre_avg != null ? fmt(m.genre_avg) : "n/a"}</td>
      <td>{m.all_avg != null ? fmt(m.all_avg) : "n/a"}</td>
      <td>{v != null && <Delta v={v} avg={m.genre_avg} />}</td>
      <td style={{ width: "26%", minWidth: 90 }}>
        <Bar pct={((v ?? 0) / top) * 100} />
        {m.genre_avg ? <Bar className="b2" pct={(m.genre_avg / top) * 100} /> : null}
      </td>
    </tr>
  );
}

export default function GameView({ appId, why }: { appId: number; why: Why }) {
  const [g, setG] = useState<GameDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [shots, setShots] = useState<string[]>([]);
  useEffect(() => {
    let live = true;
    api.game(appId).then((d) => live && setG(d)).catch((e) => live && setErr(e instanceof ApiError ? e.message : "Couldn't load this game."));
    screenshots([appId]).then((s) => live && setShots(s[appId] ?? []));
    return () => {
      live = false;
    };
  }, [appId]);

  const back = (
    <Link href="/" className="btn ghost" style={{ display: "inline-block", textDecoration: "none", marginTop: 22 }}>
      ← Back to recommendations
    </Link>
  );
  if (err) return (<main>{back}<Msg kind="error">{err === "game not in catalog" ? "That game isn't in the catalog." : err}</Msg></main>);
  if (!g) return (<main>{back}<Spinner>{COLD}</Spinner></main>);

  const tags = g.raw_tags.length ? g.raw_tags : g.genres;
  const world = themeFor(tags);
  const M = g.metrics;
  const reviews = (g.positive ?? 0) + (g.negative ?? 0);
  const pos = reviews ? ((g.positive ?? 0) / reviews) * 100 : 0;
  const pname = g.primary_genre;
  const flags = (why?.flags ?? []).map((f) => FLAG_NAMES[f as keyof typeof FLAG_NAMES] ?? f);

  return (
    <main>
      {back}
      <WorldCard world={world} title={g.title}>
        <div>
          {tags.slice(0, 14).map((t) => (
            <span key={t} className="chip sel">{t}</span>
          ))}
        </div>
        <div style={{ marginTop: 8 }}>
          <span className="fact"><b>Developer</b> {g.developer ?? "n/a"}</span>
          <span className="fact"><b>Publisher</b> {g.publisher ?? "n/a"}</span>
          <span className="fact"><b>Released</b> {g.release_date ?? "n/a"}</span>
          {!g.in_model && <span className="fact"><b>Model</b> not known to EASE yet</span>}
          <a className="fact" href={g.store_url} target="_blank" rel="noreferrer" style={{ color: "var(--ca2)" }}>Steam store ↗</a>
        </div>
        {why && (
          <div className="why" style={{ marginTop: 10 }}>
            <b>Why it was recommended:</b> pick #{why.rank} for you
            {why.because.length > 0 && <> · players who played <b>{why.because.join(", ")}</b> went on to play this</>}
            {flags.length ? ` · flagged: ${flags.join(", ")}` : " · no soft-fail flags"}
          </div>
        )}
        {g.description && <p className="desc">{g.description.length > 600 ? `${g.description.slice(0, 600)}…` : g.description}</p>}
      </WorldCard>

      <div className="kpi">
        <div><b>{M.rating.value != null ? `${M.rating.value.toFixed(0)}%` : "n/a"}</b><span>positive reviews</span></div>
        <div><b>{M.reviews.value != null ? num(M.reviews.value) : "0"}</b><span>total reviews</span></div>
        {g.owners_lo != null && g.owners_hi != null && (
          <div><b>{num(g.owners_lo)}–{num(g.owners_hi)}</b><span>estimated owners</span></div>
        )}
        <div><b>{M.peak_ccu.value != null ? num(M.peak_ccu.value) : "n/a"}</b><span>peak concurrent players</span></div>
        <div><b>{M.hours.value != null ? `${M.hours.value.toFixed(0)}h` : "n/a"}</b><span>average playtime</span></div>
        <div><b>{fmtPrice(g.price)}</b><span>price</span></div>
      </div>

      {shots.length > 0 && (
        <div className="shots" style={{ marginBottom: 12 }}>
          {shots.map((u) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img key={u} src={u} alt="" loading="lazy" />
          ))}
        </div>
      )}

      <div className="grid2">
        <div className="card">
          <h2>Player reviews</h2>
          {reviews ? (
            <>
              <div className="gd-big">{g.steam_rating_label ?? reviewLabel(pos, reviews)}</div>
              <div className="why" style={{ margin: "4px 0 12px" }}>
                {pos.toFixed(1)}% of {reviews.toLocaleString()} reviews are positive
              </div>
              <div className="split">
                <i className="pos" style={{ width: `${pos.toFixed(1)}%` }} />
                <i className="neg" style={{ width: `${(100 - pos).toFixed(1)}%` }} />
              </div>
              <div className="mh sm">
                <span>{(g.positive ?? 0).toLocaleString()} positive</span>
                <span>{(g.negative ?? 0).toLocaleString()} negative</span>
              </div>
            </>
          ) : (
            <div className="why">No review counts in the dataset yet.</div>
          )}
        </div>
        <div className="card">
          <h2>Standing in {pname}</h2>
          <div className="gd-pct">
            {([["Rated higher than", "rating"], ["More owners than", "owners"], ["Longer playtime than", "hours"]] as const).map(([label, k]) => (
              <div key={k}>
                <b>{M[k].genre_pct_below != null ? `${M[k].genre_pct_below!.toFixed(0)}%` : "n/a"}</b>
                {M[k].genre_pct_below != null ? `${label} of ${pname} games` : `${label} (no data)`}
              </div>
            ))}
          </div>
          <div className="note">Ranked against {g.n_genre.toLocaleString()} {pname} games with 50+ reviews.</div>
        </div>
      </div>

      <div className="card">
        <h2>This game vs. the averages</h2>
        <div className="tscroll">
          <table className="t">
            <thead>
              <tr>
                <th>Statistic</th><th>This game</th><th>{pname} avg.</th><th>All games avg.</th><th>vs. {pname}</th><th>Compared</th>
              </tr>
            </thead>
            <tbody>
              {METRICS.map(([label, k, fmt]) => (
                <MetricRow key={k} label={label} m={M[k]} fmt={fmt} />
              ))}
            </tbody>
          </table>
        </div>
        <div className="note">
          Averages cover catalog games with 50+ reviews ({g.n_all.toLocaleString()} games, {g.n_genre.toLocaleString()} in {pname}).
          Playtime, peak players and achievements ignore games with no data (0). In the bars, the bright one is this game and
          the grey one is the {pname} average.
        </div>
      </div>
    </main>
  );
}
