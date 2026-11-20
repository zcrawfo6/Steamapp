"use client";
// Advanced mode: each game's hours, which modes you play, and the share of hours in each (app.py game_inputs).
import { useState } from "react";
import { MIN_HOURS, MODES, hrs } from "@/lib/profile";
import { useStore } from "@/lib/store";
import type { LibGame, Mode } from "@/lib/types";

const PAGE = 30;

function GameEditor({ g }: { g: LibGame }) {
  const { update } = useStore();
  const on = Object.keys(g.modes) as Mode[];
  const solo = on.length === 1;
  const toggle = (m: Mode, checked: boolean) => {
    const modes = { ...g.modes };
    if (checked) modes[m] = 50;
    else delete modes[m];
    update(g.app_id, { modes });
  };
  return (
    <details>
      <summary>
        <b title={g.title}>{g.title}</b>
        <span>{hrs(g.hours)}h</span>
      </summary>
      <div className="field">
        <label htmlFor={`h-${g.app_id}`}>Hours played</label>
        <input id={`h-${g.app_id}`} className="input" type="number" min={0} max={9999} step={1} value={g.hours}
          onChange={(e) => update(g.app_id, { hours: Math.max(0, Math.min(9999, Number(e.target.value) || 0)) })} />
        {g.hours < MIN_HOURS && <div className="why">Under {MIN_HOURS}h: left out of your taste profile.</div>}
      </div>
      {(Object.keys(MODES) as Mode[]).map((m) => (
        <div className="field" key={m}>
          <label className="check" style={{ color: "var(--text)" }}>
            <input type="checkbox" checked={m in g.modes} onChange={(e) => toggle(m, e.target.checked)} />
            {MODES[m]}
          </label>
          {m in g.modes && (
            <div className="row" style={{ flexWrap: "nowrap" }} title={solo ? "Locked at 100% while this is the only mode ticked." : "Share of your hours on this game in this mode"}>
              <input type="range" min={0} max={100} disabled={solo} value={solo ? 100 : g.modes[m]}
                aria-label={`${MODES[m]} share of hours`}
                onChange={(e) => update(g.app_id, { modes: { ...g.modes, [m]: Number(e.target.value) } })} />
              <span className="why" style={{ margin: 0, minWidth: 36 }}>{solo ? 100 : g.modes[m]}%</span>
            </div>
          )}
        </div>
      ))}
      {!g.in_model && <div className="why">The model doesn&apos;t know this game yet, so it only shapes your profile.</div>}
    </details>
  );
}

export default function MyGames() {
  const { library } = useStore();
  const [n, setN] = useState(PAGE);
  if (!library.length) return null;
  return (
    <div className="panel">
      <h5>Your games · hours and play modes</h5>
      <div className="mygames">
        {library.slice(0, n).map((g) => (
          <GameEditor key={g.app_id} g={g} />
        ))}
      </div>
      {library.length > n && (
        <button className="btn ghost" style={{ marginTop: 10 }} onClick={() => setN((x) => x + PAGE)}>
          Show {Math.min(PAGE, library.length - n)} more of {library.length - n}
        </button>
      )}
      <div className="note">
        Set each game&apos;s hours, which modes you play (story, co-op, PvP) and what percentage of your hours went into each
        (locked to 100% when only one is ticked). Modes are pre-ticked from the game&apos;s Steam tags.
      </div>
    </div>
  );
}
