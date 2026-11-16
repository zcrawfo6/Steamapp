"use client";
// One EASE-safe pick: capsule, reviews, screenshots, the "match receipt" and the "Why this pick" analysis.
import Link from "next/link";
import { short, tasteTags } from "@/lib/profile";
import { THEMES, themeFor } from "@/lib/themes";
import type { Card } from "@/lib/types";
import { Bar, Chips } from "./ui";

export const FLAG_NAMES = { quit: "Like games you quit", short: "Short (median 2h or less)", neg: "Negative Steam reviews" } as const;
const FLAG_HELP = {
  quit: "its tags look more like the games you quit in under 2 hours than the ones you kept playing",
  short: "most players finish it in 2 hours or less",
  neg: "its Steam reviews are Mostly Negative or worse",
} as const;

export const capsule = (id: number) => `https://cdn.akamai.steamstatic.com/steam/apps/${id}/header.jpg`;

function Price({ c }: { c: Card }) {
  if (c.price_text == null) return <span className="why">Price unknown</span>;
  return (
    <>
      <span className="chip sel">{c.price_text}</span>
      {c.discount > 0 && c.price_initial ? (
        <span className="why">
          {" "}was ${c.price_initial.toFixed(2)} (-{c.discount}%)
        </span>
      ) : null}
    </>
  );
}

function Analysis({ c }: { c: Card }) {
  const mx = Math.max(...c.contrib.map(([, v]) => v), 0) || 1;
  return (
    <div className="ana">
      <div>
        <div className="lbl">Your games behind this pick</div>
        {c.contrib.length ? (
          c.contrib.map(([t, v]) => (
            <div className="mode" key={t}>
              <div className="mh">
                <span>{t}</span>
                <span>{Math.round((v / mx) * 100)}%</span>
              </div>
              <Bar pct={(v / mx) * 100} />
            </div>
          ))
        ) : (
          <div className="why">No single game stands out.</div>
        )}
        <div className="note">Relative pull from each game you played, strongest = 100%.</div>
      </div>
      <div>
        <div className="lbl">Safe check</div>
        {c.flags.length ? (
          c.flags.map((f) => (
            <div className="why" key={f}>
              ⚠️ <b>{FLAG_NAMES[f]}</b>: {FLAG_HELP[f]}, so it was moved down.
            </div>
          ))
        ) : (
          <div className="why">✅ No soft-fail flags: not like the games you quit, not a 2-hour game, and not negatively reviewed.</div>
        )}
      </div>
    </div>
  );
}

export function detailHref(c: Card, rank: number) {
  const p = new URLSearchParams({ rank: String(rank) });
  if (c.because.length) p.set("because", c.because.join("|"));
  if (c.flags.length) p.set("flags", c.flags.join(","));
  return `/game/${c.app_id}?${p}`;
}

export default function RecCard({ c, rank, aff, shots, fresh }: { c: Card; rank: number; aff: Record<string, number>; shots?: string[]; fresh?: boolean }) {
  // same tag source as the profile (full user tags minus format tags), so "you play" lines up with your profile
  const tags = tasteTags(c);
  const world = THEMES[themeFor(c.raw_tags?.length ? c.raw_tags : tags)];
  const mine = tags.filter((t) => t in aff);
  const other = tags.filter((t) => !(t in aff));
  const flags = c.flags.map((f) => FLAG_NAMES[f]);
  return (
    <div className="rec">
      <div className="body">
        <div className="top">
          <div className="cap" style={{ backgroundImage: `url('${c.image ?? capsule(c.app_id)}')` }} />
          <div>
            <h3>
              <a href={c.store_url} target="_blank" rel="noreferrer">
                {c.title}
              </a>
              <span className="pct">#{rank} {fresh ? "new direction" : "pick"}</span>
              <span className="mi" title={world.name}>
                {world.icon}
              </span>
            </h3>
            <div>
              {rank === 1 && !fresh && <span className="badge">Best match</span>}
              {fresh && c.new_tag && <span className="badge new">New for you: {c.new_tag}</span>}
            </div>
          </div>
          <div className="rev">
            {c.rating != null ? (
              <>
                Steam reviews <b>{c.rating}% positive</b>
                <Bar pct={c.rating} />
                {short(c.reviews)} total
              </>
            ) : (
              "No Steam rating yet"
            )}
          </div>
        </div>
        {shots && shots.length > 0 && (
          <div className="shots">
            {shots.map((u) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={u} src={u} loading="lazy" alt="" />
            ))}
          </div>
        )}
        <div className="lbl">Match receipt</div>
        <div className="receipt">
          <div>
            <div className="lbl">
              <span>Because you played</span>
            </div>
            {c.because.length ? <Chips items={c.because} sel /> : <span className="why">Your library as a whole</span>}
          </div>
          <div>
            <div className="lbl">
              <span>Tags</span>
              <b>{mine.length} you play</b>
            </div>
            <Chips items={mine} sel />
            <Chips items={other} />
            {!tags.length && <span className="why">No tags</span>}
          </div>
          <div>
            <div className="lbl">
              <span>Price</span>
            </div>
            <Price c={c} />
          </div>
          <div>
            <div className="lbl">
              <span>Safe check</span>
              <b>
                {flags.length} flag{flags.length === 1 ? "" : "s"}
              </b>
            </div>
            {flags.length ? <Chips items={flags} /> : <span className="chip sel">✅ No flags</span>}
          </div>
        </div>
      </div>
      <details>
        <summary>Why this pick</summary>
        <Analysis c={c} />
        <Link className="viewlink" href={detailHref(c, rank)}>
          📊 See full stats for {c.title} →
        </Link>
      </details>
    </div>
  );
}
