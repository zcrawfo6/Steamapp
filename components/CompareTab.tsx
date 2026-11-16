"use client";
// Compare with another player: taste match, genre shares, shared games, each other's favorites, both rec lists.
import Link from "next/link";
import { useMemo, useState } from "react";
import { api, ApiError, libraryPayload } from "@/lib/api";
import { MIN_HOURS, fmtPrice, hrs, profile, tasteMatch } from "@/lib/profile";
import { useStore, toLib } from "@/lib/store";
import type { Card, LibGame, Player } from "@/lib/types";
import { useRecs } from "@/lib/useRecs";
import { COLD } from "./RecommendationsTab";
import { Empty, Msg, Spinner, TwoBar } from "./ui";

function RecList({ title, cards, other, loading, error }: { title: string; cards?: Card[]; other: Set<number>; loading: boolean; error: string | null }) {
  return (
    <div className="card">
      <h2>{title}</h2>
      {error ? (
        <div className="why">{error}</div>
      ) : loading || !cards ? (
        <Spinner>{COLD}</Spinner>
      ) : cards.length ? (
        cards.map((c, i) => (
          <div className="todo" key={c.app_id}>
            <span>
              #{i + 1} <Link href={`/game/${c.app_id}`}>{c.title}</Link> {other.has(c.app_id) && <span className="chip sel">for both of you</span>}
            </span>
            <span>{c.price_text ?? ""}</span>
          </div>
        ))
      ) : (
        <div className="why">No recommendations.</div>
      )}
    </div>
  );
}

function FavList({ title, src, other }: { title: string; src: LibGame[]; other: Set<number> }) {
  const rows = [...src].sort((a, b) => b.hours - a.hours).filter((g) => !other.has(g.app_id)).slice(0, 6);
  return (
    <div className="card">
      <h2>{title}</h2>
      {rows.length ? (
        rows.map((g) => (
          <div className="todo" key={g.app_id}>
            <Link href={`/game/${g.app_id}`}>{g.title}</Link>
            <span>{hrs(g.hours)}h · {fmtPrice(g.price)}</span>
          </div>
        ))
      ) : (
        <div className="why">Nothing here: you have the same favorites.</div>
      )}
    </div>
  );
}

export default function CompareTab() {
  const { library } = useStore();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [rv, setRv] = useState<Player | null>(null);

  async function load() {
    if (!q.trim()) return setErr("Enter their custom URL name, profile link or SteamID64.");
    setBusy(true);
    setErr(null);
    try {
      const p = await api.player(q.trim());
      if (!p.games.some((g) => g.in_catalog && g.hours >= MIN_HOURS)) {
        setErr(`${p.name ?? "That player"} owns ${p.n_owned} games, but none of the ones in the catalog have ${MIN_HOURS}+ hours played.`);
        setRv(null);
      } else setRv(p);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Couldn't load that profile.");
    } finally {
      setBusy(false);
    }
  }

  const mine = useMemo(() => profile(library), [library]);
  const theirLib = useMemo(() => (rv ? rv.games.filter((g) => g.in_catalog).map((g) => toLib(g, g.hours)) : []), [rv]);
  const them = useMemo(() => profile(theirLib), [theirLib]);
  const myPayload = useMemo(() => libraryPayload(library), [library]);
  const theirPayload = useMemo(
    () => (rv ? rv.games.filter((g) => g.playtime_min > 0).slice(0, 500).map((g) => ({ app_id: g.app_id, hours: g.hours })) : null),
    [rv],
  );
  const theirOwned = useMemo(() => (rv ? rv.games.map((g) => g.app_id).slice(0, 5000) : []), [rv]);
  const ready = !!rv && mine.n > 0;
  const myRecs = useRecs(ready ? myPayload : null, { n: 8, max_price: null, include_explicit: false });
  const theirRecs = useRecs(ready ? theirPayload : null, { n: 8, max_price: null, cc: rv?.cc, owned: theirOwned });

  const name = rv?.name ?? "Them";
  const myPlayed = library.filter((g) => g.hours >= MIN_HOURS);
  const theirPlayed = theirLib.filter((g) => g.hours >= MIN_HOURS);
  const theirH = new Map(theirPlayed.map((g) => [g.app_id, g.hours]));
  const shared = myPlayed.filter((g) => theirH.has(g.app_id));
  const keys = [...new Set([...Object.keys(mine.aff), ...Object.keys(them.aff)])]
    .sort((a, b) => (them.aff[b] ?? 0) + (mine.aff[b] ?? 0) - (them.aff[a] ?? 0) - (mine.aff[a] ?? 0))
    .slice(0, 8);
  const mx = Math.max(...keys.flatMap((k) => [mine.aff[k] ?? 0, them.aff[k] ?? 0]), 1e-9);
  const hm = Math.max(...shared.map((g) => Math.max(g.hours, theirH.get(g.app_id)!)), 1);
  const legend = (
    <div className="why" style={{ marginBottom: 8 }}>
      <b style={{ color: "var(--accent2)" }}>■ You</b> &nbsp; <b style={{ color: "var(--them)" }}>■ {name}</b>
    </div>
  );
  const myIds = new Set(myRecs.data?.for_you.map((c) => c.app_id));
  const theirIds = new Set(theirRecs.data?.for_you.map((c) => c.app_id));

  return (
    <>
      <h5>Compare with another player</h5>
      <form className="panel row" onSubmit={(e) => (e.preventDefault(), load())} style={{ flexWrap: "nowrap" }}>
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Their Steam profile: custom URL name, profile URL or SteamID64"
          aria-label="Their Steam profile" autoComplete="off" />
        <button className="btn" disabled={busy} style={{ whiteSpace: "nowrap" }}>
          {busy ? "Loading..." : "Compare"}
        </button>
      </form>
      {err && <Msg kind="error">{err}</Msg>}
      {!rv ? (
        <Empty>Enter someone&apos;s Steam profile to compare your libraries and recommendations. Their profile&apos;s Game details must be public.</Empty>
      ) : !mine.n ? (
        <Empty>Add a few games you&apos;ve played (with {MIN_HOURS}+ hours) above to compare with {name}.</Empty>
      ) : (
        <>
          <div className="kpi">
            <div><b>{Math.round(tasteMatch(mine.aff, them.aff) * 100)}%</b><span>taste match (genre profile)</span></div>
            <div><b>{shared.length}</b><span>games you both play</span></div>
            <div><b>{mine.n} · {Math.round(mine.tot)}h</b><span>you: games · hours</span></div>
            <div><b style={{ color: "var(--them)" }}>{them.n} · {Math.round(them.tot)}h</b><span>{name}: games · hours</span></div>
          </div>
          <div className="grid2">
            <div className="card">
              <h2>Genres: share of hours</h2>
              {legend}
              {keys.map((k) => (
                <div key={k} style={{ margin: "8px 0" }}>
                  <div className="mh"><span>{k}</span><span>{Math.round((mine.aff[k] ?? 0) * 100)}% · {Math.round((them.aff[k] ?? 0) * 100)}%</span></div>
                  <TwoBar you={((mine.aff[k] ?? 0) / mx) * 100} them={((them.aff[k] ?? 0) / mx) * 100} />
                </div>
              ))}
            </div>
            <div className="card">
              <h2>Games you both play</h2>
              {legend}
              {shared.length ? (
                shared
                  .sort((a, b) => b.hours + theirH.get(b.app_id)! - a.hours - theirH.get(a.app_id)!)
                  .slice(0, 10)
                  .map((g) => (
                    <div key={g.app_id} style={{ margin: "8px 0" }}>
                      <div className="mh"><span>{g.title}</span><span>{hrs(g.hours)}h · {hrs(theirH.get(g.app_id)!)}h</span></div>
                      <TwoBar you={(g.hours / hm) * 100} them={(theirH.get(g.app_id)! / hm) * 100} />
                    </div>
                  ))
              ) : (
                <div className="why">No games in common (with {MIN_HOURS}+ hours each).</div>
              )}
            </div>
          </div>
          <div className="grid2">
            <FavList title={`${name}'s favorites you don't own`} src={theirPlayed} other={new Set(library.map((g) => g.app_id))} />
            <FavList title={`Your favorites ${name} doesn't own`} src={myPlayed} other={new Set(theirOwned)} />
          </div>
          <div className="grid2">
            <RecList title="Recommended for you" cards={myRecs.data?.for_you} other={theirIds} loading={myRecs.loading} error={myRecs.error} />
            <RecList title={`Recommended for ${name}`} cards={theirRecs.data?.for_you} other={myIds} loading={theirRecs.loading} error={theirRecs.error} />
          </div>
          <div className="note">
            {name}: {rv.n_played} played of {rv.n_owned} owned; compared on their {theirPlayed.length} catalog games with {MIN_HOURS}+ hours.
            Recommendations come from the EASE-safe model over each full library, with no budget limit.
          </div>
        </>
      )}
    </>
  );
}
