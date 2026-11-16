"use client";
// Home: hero + one big search box, then Recommendations / Player Profile / Compare (Steamapp_Juan_Model/app.py).
import { useMemo, useState } from "react";
import CompareTab from "@/components/CompareTab";
import GameSearch from "@/components/GameSearch";
import Gem from "@/components/Gem";
import MyGames from "@/components/MyGames";
import ProfileTab from "@/components/ProfileTab";
import RecommendationsTab from "@/components/RecommendationsTab";
import { Empty, Mark, Msg } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { MIN_HOURS, profile } from "@/lib/profile";
import { useStore } from "@/lib/store";

const TABS = ["Recommendations", "Player Profile", "Compare"] as const;

export default function Home() {
  const { ready, library, settings, replace, clear } = useStore();
  const [tab, setTab] = useState<(typeof TABS)[number]>("Recommendations");
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoErr, setDemoErr] = useState<string | null>(null);
  const P = useMemo(() => profile(library), [library]);

  async function demo() {
    setDemoBusy(true);
    setDemoErr(null);
    try {
      replace(await api.demo());
    } catch (e) {
      setDemoErr(e instanceof ApiError ? e.message : "Couldn't load a demo profile.");
    } finally {
      setDemoBusy(false);
    }
  }

  const need = library.length ? (
    <Empty>
      None of your games have {MIN_HOURS}+ hours yet, so there&apos;s nothing to build a taste profile from. Add a game
      you&apos;ve spent more time in, or raise the hours in Advanced mode.
    </Empty>
  ) : (
    <Empty>
      Search for a few games you&apos;ve played above (or hit <b>Try a demo profile</b>) to build your player profile.
    </Empty>
  );

  return (
    <main>
      <div className="hero">
        <div className="ttl">
          <Mark />
          <h1>Find what to play next</h1>
        </div>
        <p>
          Add the games you&apos;ve played. TasteForge learns what you spend your hours on (genres, prices, play styles) and
          finds what fits you next.
        </p>
      </div>
      <div className="heromid">
        <GameSearch />
        <div className="row center">
          <button className="btn ghost" onClick={demo} disabled={demoBusy}>
            {demoBusy ? "Loading..." : "Try a demo profile"}
          </button>
          {library.length > 0 && (
            <button className="btn ghost" onClick={clear}>
              Clear
            </button>
          )}
        </div>
        {demoErr && <Msg kind="error">{demoErr}</Msg>}
        <details className="why-box">
          <summary>How the recommender works</summary>
          <div className="inner">
            <p>
              Recommendations come from <b>EASE-safe</b>, a collaborative-filtering model trained on the libraries of
              thousands of Steam players. It recommends games that <b>players who played the same games as you went on to
              play</b>, and names which of your games pushed each pick up.
            </p>
            <p>
              <b>EASE</b> (Embarrassingly Shallow Autoencoder) learns how strongly each game predicts every other game. Your
              scores are the sum of those links from every game you&apos;ve played. The <b>safe</b> step then re-ranks the top
              50 so likely misses move down (they aren&apos;t removed): games whose tags look more like the games you quit in
              under 2 hours than the ones you kept playing, games most people finish in 2 hours or less, and games with
              negative Steam reviews.
            </p>
            <p>
              The model only knows games that 100+ players in its training data played (about 13,000), mostly from 2017 to
              2023, so very new or niche games won&apos;t be recommended yet.
            </p>
            <p style={{ margin: 0 }}>
              Your <b>Player Profile</b> (genres, prices, play styles) is built from your hours. Switch to <b>Advanced</b>{" "}
              (top right) to set hours per game or cap the budget. Use <b>Import from Steam</b> to fill the list from your
              library. Everything you enter stays in this browser.
            </p>
          </div>
        </details>
      </div>
      <div className="src">Live data · ~13,000 Steam games the EASE-safe model knows, served from Modal</div>

      {settings.mode === "Advanced" && <MyGames />}

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>
      {!ready ? null : (
        <>
          <div hidden={tab !== "Recommendations"}>{tab === "Recommendations" && (P.n ? <RecommendationsTab /> : need)}</div>
          <div hidden={tab !== "Player Profile"}>{P.n ? <ProfileTab /> : need}</div>
          <div hidden={tab !== "Compare"}>
            <CompareTab />
          </div>
        </>
      )}
      <Gem />
    </main>
  );
}
