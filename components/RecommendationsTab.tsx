"use client";
import { useEffect, useMemo, useState } from "react";
import { libraryPayload, screenshots } from "@/lib/api";
import { profile } from "@/lib/profile";
import { useStore } from "@/lib/store";
import { useRecs } from "@/lib/useRecs";
import RecCard from "./RecCard";
import { Empty, Msg, Spinner } from "./ui";

const PRESETS: [string, string, number][] = [
  ["Any price", "No budget cap", 60],
  ["Under $20", "Hide anything pricier than $20", 20],
  ["Under $10", "Hide anything pricier than $10", 10],
  ["Free only", "Only free-to-play games", 0],
];
export const COLD = "Asking the recommender... the first request after a quiet spell can take 10–20 seconds while it wakes up.";

export default function RecommendationsTab() {
  const { library, settings, set } = useStore();
  const adv = settings.mode === "Advanced";
  const P = useMemo(() => profile(library), [library]);
  const payload = useMemo(() => libraryPayload(library), [library]);
  const { data, error, loading } = useRecs(P.n ? payload : null, {
    n: 8,
    max_price: settings.budget >= 60 ? null : settings.budget,
    include_explicit: settings.adult,
  });
  const [shots, setShots] = useState<Record<string, string[]>>({});
  const ids = data ? [...data.for_you, ...data.try_new].map((c) => c.app_id) : [];
  const idKey = ids.join(",");
  useEffect(() => {
    if (!idKey) return;
    let live = true;
    screenshots(idKey.split(",").map(Number)).then((s) => live && setShots(s));
    return () => {
      live = false;
    };
  }, [idKey]);

  return (
    <div className="recwrap">
      <div>
        {adv && (
          <div className="panel">
            <h5>Tune the recommender</h5>
            <label className="why" htmlFor="budget" style={{ display: "block", marginBottom: 6 }}>
              Max budget: <b style={{ color: "var(--text)" }}>{settings.budget >= 60 ? "no limit" : settings.budget === 0 ? "free only" : `$${settings.budget}`}</b>
              {" "}(checked against the current Steam store price)
            </label>
            <input id="budget" type="range" min={0} max={60} step={5} value={settings.budget} onChange={(e) => set({ budget: Number(e.target.value) })} />
            <label className="check">
              <input type="checkbox" checked={settings.adult} onChange={(e) => set({ adult: e.target.checked })} />
              Show adult games
            </label>
          </div>
        )}
        {error ? (
          <Msg kind="error">{error}</Msg>
        ) : loading || !data ? (
          <Spinner>{COLD}</Spinner>
        ) : (
          <>
            <div className="rhead">
              <div>
                <div className="t">Recommendations</div>
                <div className="n">
                  Top {data.for_you.length} of {data.n_candidates.toLocaleString()} games the EASE-safe model can recommend
                </div>
              </div>
              <div className="lbl">
                Sorted by<span>EASE-safe rank</span>
              </div>
            </div>
            {!data.for_you.length && <Empty>Nothing fits that budget. Raise the max budget.</Empty>}
            {data.for_you.map((c, i) => (
              <RecCard key={c.app_id} c={c} rank={i + 1} aff={P.aff} shots={shots[c.app_id]} />
            ))}
            {data.try_new.length > 0 && (
              <>
                <div className="rhead section-h">
                  <div>
                    <div className="t">Try something new</div>
                    <div className="n">Still picked by the model, but outside your usual tags</div>
                  </div>
                </div>
                {data.try_new.slice(0, 5).map((c, i) => (
                  <RecCard key={c.app_id} c={c} rank={i + 1} aff={P.aff} shots={shots[c.app_id]} fresh />
                ))}
              </>
            )}
          </>
        )}
      </div>
      <div className="shape">
        <h5>Budget</h5>
        {PRESETS.map(([title, desc, val]) => (
          <div key={title}>
            <button className={`btn block ${settings.budget === val ? "" : "off"}`} onClick={() => set({ budget: val })} aria-pressed={settings.budget === val}>
              {title}
            </button>
            <div className="pd">{desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
