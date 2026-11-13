"""TasteForge: Streamlit dashboard over the Steam games tables in Supabase.
Run: streamlit run app.py
Settings (.streamlit/secrets.toml or the environment):
  GAMES_SUPABASE_URL + GAMES_SUPABASE_KEY  full Steam catalog (`games` table, see games_db.py) for the recommender
  MODAL_API_URL      Modal API: the Genre Success tab, and the old 3,000-game catalog when the two above are unset
  GAMES_MIN_REVIEWS  catalog floor, default 10 (below that Steam shows no rating to score a game on)
  STEAMREC_ARTIFACTS folder with ease.npz + items.parquet (default ease/artifacts; see ease/README.md)
  STEAMREC_DATA      folder with games.parquet + team_eval/games.parquet (default ease/artifacts)
Layout: a centered search-first page over a dimmed game-shelf backdrop, with Steam import and a Simple / Advanced
mode switch in the top right. Category cards and game pages get an animated world built from their tags (themes.py).
"""
import math
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor
from html import escape

import numpy as np
import pandas as pd
import requests
import streamlit as st

import game_detail as gd
import games_db as db
from ease import recommender as E
import steam_import as S
import themes as T

st.set_page_config(page_title="TasteForge · Find what to play next", page_icon="🎮", layout="wide",
                   initial_sidebar_state="collapsed")


def setting(name: str) -> str:
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, "")


API_URL = setting("MODAL_API_URL")
GAMES_URL = str(setting("GAMES_SUPABASE_URL")).strip()
GAMES_KEY = str(setting("GAMES_SUPABASE_KEY")).strip()
FULL_CATALOG = bool(GAMES_URL and GAMES_KEY)
MIN_REVIEWS = int(setting("GAMES_MIN_REVIEWS") or 10)
STEAM_KEY = setting("STEAM_API_KEY")
# Where Steam sends people back after signing in: this app's own address
APP_URL = setting("APP_URL") or "http://localhost:8501/"
MIN_HOURS = 2.5  # games with fewer hours stay in the library (never recommended) but don't shape the taste profile
_EASE_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ease", "artifacts")
# same settings as Juan's app, so one copy of the Supabase download works for both
STEAMREC_ARTIFACTS = str(setting("STEAMREC_ARTIFACTS") or _EASE_DEFAULT)
STEAMREC_DATA = str(setting("STEAMREC_DATA") or _EASE_DEFAULT)

# What a player can track per game. A mode is offered when the game's Steam tags say it has one.
MODES = {"story": ("📖", "Story / Campaign"), "coop": ("🤝", "Co-op (PvE)"), "pvp": ("⚔️", "PvP")}
STORY_T = {"story rich", "singleplayer", "choices matter", "multiple endings", "visual novel", "interactive fiction",
           "rpg", "jrpg", "adventure", "action-adventure", "walking simulator"}
COOP_T = {"co-op", "online co-op", "local co-op", "co-op campaign"}
PVP_T = {"pvp", "competitive", "fighting", "2d fighter", "arena shooter", "esports", "moba", "battle royale",
         "hero shooter"}
MULTI_T = {"multiplayer", "massively multiplayer", "mmorpg", "local multiplayer"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#05101c;--panel:rgba(15,28,41,.88);--panel2:#172533;--field:#0f1c29;--line:#2d3640;--line2:#3b5060;
--text:#e2f1fa;--mute:#94a9ba;--accent:#38bdf8;--accent2:#b8e6fe;--btn:#1b374a;--btnh:#24485f;--ink:#dff2fe;
--disp:'Inter',system-ui,sans-serif;--body:'Inter',system-ui,sans-serif}
.stApp{isolation:isolate;font-family:var(--body);color:var(--text);background:var(--bg)}
[data-testid=stAppViewContainer],[data-testid=stMain],[data-testid=stHeader],[data-testid=stBottom],[data-testid=stBottom]>div{background:transparent!important}
[data-testid=stMainBlockContainer]{max-width:1060px;padding-top:4.4rem;padding-bottom:4rem}
div[data-testid=stElementContainer]:has(.fx-host){position:absolute;width:0;height:0;overflow:visible}
.stApp p,.stApp label,.stApp li,.stApp input,.stApp textarea,.stApp button,.stApp [data-baseweb]{font-family:var(--body)}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6{font-family:var(--disp)}
.stApp h5{text-transform:uppercase;letter-spacing:.12em;font-size:13px;font-weight:600;color:var(--mute)}
.stApp a{color:var(--accent2)}
/* backdrop: shelves of game cases, blurred and dimmed */
.shelves{position:fixed;inset:-12px;z-index:-1;pointer-events:none;background-size:auto 100%;background-repeat:repeat-x;filter:blur(1.5px) saturate(.85)}
.shelves::after{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 75% 65% at 50% 38%,rgba(5,16,28,.58),rgba(5,16,28,.92))}
/* top bar */
.brand{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:500;color:#fff}
.brand b{font-weight:800}.brand svg{width:34px;height:auto}
.st-key-topbar [data-testid=stPopover] button,[data-testid=stBaseButton-secondary]{background:rgba(23,37,51,.92)!important;border:1px solid var(--line2)!important;color:var(--ink)!important;border-radius:999px}
.st-key-topbar [data-testid=stPopover] button:hover,[data-testid=stBaseButton-secondary]:hover{border-color:var(--accent)!important;color:#fff!important}
.st-key-topbar [data-testid=stPopover]:last-child button{background:var(--btn)!important;border-color:#2f5670!important}
[data-testid=stPopoverBody]{background:var(--field);border:1px solid var(--line);border-radius:16px}
/* hero */
.hero{text-align:center;margin:7vh auto 26px;max-width:780px}
.hero .ttl{display:inline-flex;align-items:center;gap:16px;flex-wrap:wrap;justify-content:center}
.hero .ttl svg{width:70px;height:auto;margin-top:14px}
.hero h1{font-size:clamp(34px,6vw,62px);font-weight:800;letter-spacing:-.02em;line-height:1.05;margin:0;padding:0;color:#fff;text-shadow:0 2px 24px rgba(0,0,0,.6)}
.hero p{font-size:clamp(15px,2vw,18px);color:#d5e6f2;line-height:1.6;max-width:560px;margin:14px auto 0}
.st-key-heromid{max-width:720px;width:100%;margin:0 auto}
.st-key-search [data-testid=stMultiSelect] [role=group]{min-height:60px;border:1px solid var(--line)!important;border-radius:16px!important;padding-left:38px;
background:var(--field) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' stroke='%2394a9ba' stroke-width='2' stroke-linecap='round'%3E%3Ccircle cx='8' cy='8' r='6'/%3E%3Cpath d='m13 13 4 4'/%3E%3C/svg%3E") no-repeat 18px center!important;
box-shadow:0 20px 52px rgba(0,0,0,.32)}
.st-key-search input::placeholder{color:var(--mute)}
.st-key-why [data-testid=stExpander] details{background:transparent!important;border:0!important}
.st-key-why summary{width:fit-content;margin:0 auto}
.st-key-why summary p{text-decoration:underline;text-underline-offset:5px;color:#d5e6f2;font-size:15px}
.st-key-why [data-testid=stExpanderDetails]{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px 20px;backdrop-filter:blur(8px)}
.src{text-align:center;color:var(--mute);font-size:12px;margin:2px 0 6vh}
/* inputs, buttons */
[data-testid=stMultiSelect] [role=group],[data-baseweb=select]>div,[data-baseweb=base-input],[data-baseweb=input]>div,textarea{background:var(--field)!important;border-color:var(--line)!important;border-radius:12px!important}
span[data-baseweb=tag],span[data-tag]{background:var(--btn)!important;border:1px solid #2f5670;border-radius:99px!important}
span[data-baseweb=tag] span,span[data-baseweb=tag] svg,span[data-tag] *{color:var(--ink)!important;fill:var(--ink)!important}
[data-testid=stBaseButton-primary]{background:var(--btn)!important;color:var(--ink)!important;border:1px solid #2f5670!important;border-radius:14px;font-weight:600}
[data-testid=stBaseButton-primary]:hover{background:var(--btnh)!important;border-color:var(--accent)!important}
[data-testid=stBaseButton-primary] p{color:var(--ink)!important}
[data-testid=stSlider] [role=slider]{background:var(--accent2)!important}
[data-testid=stSliderThumbValue]{color:var(--accent2)!important}
[data-testid=stExpander] details{background:var(--panel);border:1px solid var(--line)!important;border-radius:14px;backdrop-filter:blur(8px)}
/* tabs as a centred pill bar */
.stTabs [role=tablist]{gap:4px;width:fit-content;max-width:100%;overflow-x:auto;margin:0 auto 22px;padding:5px;background:rgba(15,28,41,.88);border:1px solid var(--line)!important;border-radius:999px;backdrop-filter:blur(8px);box-shadow:none!important}
.stTabs .react-aria-SelectionIndicator,.stTabs [role=tablist]::before,.stTabs [role=tablist]::after,.stTabs [role=tab]::before,.stTabs [role=tab]::after{display:none!important}
.stTabs [role=tab]{height:auto;padding:8px 16px;border-radius:999px;background:transparent;border:0!important;box-shadow:none!important;white-space:nowrap}
.stTabs [role=tab] p{font-size:14px;font-weight:600;color:var(--mute)}
.stTabs [role=tab]:hover p{color:var(--ink)}
.stTabs [role=tab][aria-selected=true]{background:var(--btn)}
.stTabs [role=tab][aria-selected=true] p{color:var(--ink)}
/* panels */
.st-key-tune,.st-key-mygames{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px 18px;backdrop-filter:blur(8px)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:12px;backdrop-filter:blur(8px);box-shadow:0 20px 52px -28px rgba(0,0,0,.7)}
.card h2{margin:0 0 10px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.14em;color:var(--mute)}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.kpi div{flex:1;min-width:120px;background:var(--panel);border:1px solid var(--line);padding:12px 14px;border-radius:14px;backdrop-filter:blur(8px)}
.kpi b{display:block;font-size:24px;font-weight:700;color:#fff}.kpi span{font-size:12px;color:var(--mute)}
.bar{height:8px;border-radius:5px;background:rgba(23,37,51,.95);overflow:hidden}
.bar i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,var(--ca,#2b7fb0),var(--ca2,var(--accent2)))}
.chip{display:inline-block;padding:3px 10px;border-radius:99px;font-size:12px;background:rgba(23,37,51,.9);border:1px solid var(--line2);color:var(--text);margin:2px 3px 2px 0}
.chip.sel{background:var(--btn);color:var(--ink);border-color:#2f5670}
.catcard .chip.sel{background:var(--ca2);color:#10130a;border-color:var(--ca2)}
.hint{color:var(--mute);font-size:13px;text-align:center;margin:-6px 0 16px}
/* recommendation list: results header, cards with a match receipt, inline analysis, taste shaping */
.rhead{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 16px;margin-bottom:14px;background:var(--panel);border:1px solid var(--line);border-radius:16px;backdrop-filter:blur(8px)}
.rhead .t{font-size:13px;font-weight:600;color:var(--text)}.rhead .n{font-size:15px;font-weight:700;color:#fff}
.lbl{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--mute)}
.rhead .lbl span{margin-left:8px;padding:3px 9px;border:1px solid #2f5670;border-radius:6px;background:var(--btn);color:var(--accent);letter-spacing:0;text-transform:none;font-size:13px}
.rec{padding:12px;background:var(--panel);border:1px solid var(--line);border-radius:16px 16px 0 0;backdrop-filter:blur(8px)}
.rec .top{display:grid;grid-template-columns:150px 1fr auto;gap:14px;align-items:start}
.rec .cap{width:150px;aspect-ratio:460/215;border-radius:10px;background:#0b1520 center/cover no-repeat;border:1px solid var(--line)}
.rec h3{margin:0 0 6px;padding:0;font-size:18px;font-weight:700}
.rec h3 .pct{margin-left:10px;font-size:13px;font-weight:700;color:var(--accent);white-space:nowrap}
.rec .mi{font-size:13px;margin-left:8px}
.rec .rev{min-width:170px;text-align:right;font-size:13px;color:var(--mute)}.rec .rev b{color:#fff}
.rec .rev .bar{height:5px;margin:6px 0 5px}
.badge{display:inline-block;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;background:rgba(250,204,21,.14);border:1px solid rgba(250,204,21,.5);color:#fde68a;margin:2px 3px 2px 0}
.shots{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px}
.shots img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:10px;border:1px solid var(--line);background:#0b1520}
.rec>.lbl{margin:14px 0 6px}
.receipt{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.receipt>div{padding:8px 10px;border:1px solid var(--line);border-radius:10px;background:rgba(11,21,32,.55)}
.receipt .lbl{display:flex;justify-content:space-between;margin-bottom:4px}.receipt .lbl b{letter-spacing:0;text-transform:none;color:var(--text)}
.why{color:var(--mute);font-size:13px;margin-top:4px}
[class*="st-key-rec_"]{margin-bottom:6px}
[class*="st-key-rec_"] [data-testid=stExpander] details{border-radius:0 0 16px 16px;border-top:0!important}
[class*="st-key-rec_"] [data-testid=stExpander] summary p{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--mute)}
[class*="st-key-view_"] button p{font-size:13px;color:var(--accent2)}
.ana{display:grid;grid-template-columns:250px 1fr;gap:12px}
.ana>div{padding:12px;border:1px solid var(--line);border-radius:12px;background:rgba(11,21,32,.55)}
.ana .lbl{color:var(--accent);margin-bottom:10px}
.ringrow{display:flex;gap:12px;align-items:center}
.ring{flex:none;width:78px;height:78px;border-radius:50%;display:grid;place-items:center}
.ring b{width:56px;height:56px;border-radius:50%;display:grid;place-items:center;background:var(--field);color:#fff;font-size:15px}
.leg{display:flex;justify-content:space-between;gap:10px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:5px 0}
.leg b{color:var(--text)}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}
.ana .mode{margin:0 0 10px}
/* quick taste shaping panel */
.st-key-shape{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:14px;backdrop-filter:blur(8px)}
.st-key-shape button{justify-content:flex-start;border-radius:12px;text-align:left}
.st-key-shape .pd{font-size:12px;color:var(--mute);margin:-12px 0 2px 4px;line-height:1.4}
.match{padding:4px 10px;border-radius:999px;font-weight:700;font-size:13px;color:#06121c;white-space:nowrap}
.price{font-weight:700;font-size:17px;color:#fff;white-space:nowrap}
@media(max-width:640px){.rec .top{grid-template-columns:1fr}.rec .cap{width:100%}.rec .rev{text-align:left}.receipt,.ana{grid-template-columns:1fr}}
/* hidden gem: corner card on wide screens */
.gem{position:fixed;right:22px;bottom:22px;width:260px;z-index:5;display:none;background:var(--field);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 20px 52px rgba(0,0,0,.5)}
@media(min-width:1600px){.gem{display:block}}
.gem img{width:100%;display:block;aspect-ratio:460/215;object-fit:cover}
.gem .gb{padding:10px 14px 12px;font-size:12px;color:var(--mute);line-height:1.5}
.gem .pill{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.14em;padding:2px 8px;border:1px solid var(--line2);border-radius:99px;color:var(--accent2);margin-right:6px}
.gem a{display:block;margin:6px 0 2px;color:#fff!important;font-weight:700;font-size:15px;text-decoration:none}
/* category worlds */
.catcard{border-radius:16px;overflow:hidden;margin:4px 0 6px;background:var(--cp);border:1px solid var(--cl);box-shadow:0 14px 32px -16px var(--ca)}
.scene{position:relative;height:100px;overflow:hidden}
.scene::after{content:'';position:absolute;inset:0;z-index:1;background:linear-gradient(transparent 35%,rgba(0,0,0,.72))}
.scene .ttl{position:absolute;z-index:2;left:14px;right:14px;bottom:9px}
.scene .ttl h3{margin:0;padding:0;font-family:var(--cd);font-size:25px;line-height:1.1;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.85)}
.scene .realm{font-family:var(--cb);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--ca2)}
.cbody{padding:12px 14px 14px;font-family:var(--cb)}
.empty{color:var(--mute);padding:28px;text-align:center;border:1px dashed var(--line2);border-radius:16px;background:var(--panel);backdrop-filter:blur(8px)}
.note{font-size:12px;color:var(--mute);margin-top:12px}
.mode{margin:12px 0 16px}.mh{display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px}.mh.sm{font-size:12px;color:var(--mute);margin-top:6px}
.todo{display:flex;justify-content:space-between;gap:10px;font-size:13px;padding:6px 0;border-bottom:1px dashed var(--line)}
table.t{width:100%;border-collapse:collapse;font-size:13px}
table.t td,table.t th{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}
table.t th{color:var(--mute);font-weight:600;font-size:12px}
svg text{fill:var(--text);font-size:11px}
</style>
"""

# gamepad mark used in the top bar and the hero
MARK = ('<svg viewBox="0 0 64 44" aria-hidden="true"><path d="M17 4h30c9 0 15 9 16 22 1 10-3 16-9 16-4 0-7-3-10-8H20'
        'c-3 5-6 8-10 8-6 0-10-6-9-16C2 13 8 4 17 4z" fill="#1b374a" stroke="#b8e6fe" stroke-width="2.5"/>'
        '<path d="M15 20h4v-4h4v4h4v4h-4v4h-4v-4h-4z" fill="#b8e6fe"/><circle cx="44" cy="18" r="3" fill="#7dd3fc"/>'
        '<circle cx="50" cy="25" r="3" fill="#b8e6fe"/></svg>')


def html(s: str):
    # strip leading whitespace so markdown doesn't treat indented HTML as a code block
    st.markdown(re.sub(r"(?m)^\s+", "", s), unsafe_allow_html=True)


def fmt(p: float) -> str:
    return "Free" if p == 0 else f"${p:.2f}"


def modes_for(genres):
    """Which of story / co-op / pvp this game supports, from its tags (story is the fallback)."""
    s = {str(x).strip().lower() for x in genres}
    coop = bool(s & COOP_T)
    has = {"story": bool(s & STORY_T), "coop": coop, "pvp": bool(s & PVP_T or (s & MULTI_T and not coop))}
    return [m for m in MODES if has[m]] or ["story"]


@st.cache_data(ttl=3600)
def fetch(name: str) -> pd.DataFrame:
    r = requests.get(API_URL, params={"sql_name": name}, timeout=90)
    r.raise_for_status()
    return pd.DataFrame(r.json()["rows"])


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_catalog() -> pd.DataFrame:
    """The games the recommender works over. Row position is the game id used across the app (G.loc[gid])."""
    if FULL_CATALOG:
        df = db.build_catalog(db.fetch_games(GAMES_URL, GAMES_KEY), MIN_REVIEWS, extra_tags=gd.csv_tags())
    else:  # old source: the top 3,000 games by review count, from the Modal API
        df = fetch("catalog")
        df["genres"] = df["tags"].str.split(",")
        df["price"] = df["price"].astype(float)
        df["rating"] = df["rating"].astype(float)
        df["label"] = df["name"] + "  (" + df["app_id"].astype(str) + ")"
        df = df.reset_index(drop=True)
    df["modes"] = df.genres.apply(modes_for)
    return df


# ---------- profile math ----------
def profile(G, played, feats):
    aff, tot, wp = {}, 0.0, 0.0
    for gid, h in played.items():
        g = G.loc[gid]
        tot += h
        wp += math.log1p(g.price) * h
        for x in g.genres:
            aff[x] = aff.get(x, 0) + h / len(g.genres)
    aff = {k: v / (tot or 1) for k, v in aff.items()}
    lp = wp / tot if tot else 0
    # play style: a game's hours are split across its ticked modes by their time share
    modes = {}
    for gid, h in played.items():
        for m, share in (feats.get(gid) or {}).items():
            modes[m] = modes.get(m, 0) + h * share
    return dict(tot=tot, aff=aff, lp=lp, avg_price=math.exp(lp) - 1, n=len(played), modes=modes)


@st.cache_resource(show_spinner="Loading the EASE-safe model (~330 MB, first time only)...")
def ease_model():
    """Juan's EASE-safe recommender (ease/recommender.py), loaded once per server. None when its files are missing."""
    return None if E.missing_files(STEAMREC_ARTIFACTS, STEAMREC_DATA) else E.Recommender(STEAMREC_ARTIFACTS, STEAMREC_DATA)


@st.cache_data(ttl=3600, show_spinner="Finding games players like you went on to enjoy...")
def _ease_recs(library: tuple, owned: tuple, budget, n: int):
    return ease_model().recommend(list(library), owned=list(owned), n=n,
                                  max_price=None if budget >= 999 else budget)


def recommend(hours, budget=999, n=8):
    """EASE-safe picks for a library {catalog row: hours}: a list of card dicts (ease/recommender.py), best first,
    or None when none of the games are known to the model. Every library game counts (EASE input is played or
    not), and the under-2-hour ones also feed the like-quit flag. Results are cached: picks call the Steam store."""
    library = tuple(sorted((int(G.loc[gid].app_id), int(round(h * 60))) for gid, h in hours.items()))
    out = _ease_recs(library, tuple(a for a, _ in library), budget, n)
    return None if out is None else out["for_you"]


def radar(entries):
    n, R, cx, cy = len(entries), 120, 170, 150

    def pt(i, r):
        a = -math.pi / 2 + i * 2 * math.pi / n
        return cx + math.cos(a) * r, cy + math.sin(a) * r

    line = 'style="fill:none;stroke:var(--line)"'
    web = "".join(
        f'<polygon points="{" ".join("%.1f,%.1f" % pt(i, R * f) for i in range(n))}" {line}/>'
        for f in (.25, .5, .75, 1))
    axes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{pt(i, R)[0]:.1f}" y2="{pt(i, R)[1]:.1f}" {line}/>' for i in range(n))
    mx = entries[0][1]
    poly = " ".join("%.1f,%.1f" % pt(i, R * max(.08, e[1] / mx)) for i, e in enumerate(entries))
    labs = ""
    for i, e in enumerate(entries):
        x, y = pt(i, R + 18)
        anchor = "end" if x < cx - 5 else "start" if x > cx + 5 else "middle"
        labs += f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle">{e[0]}</text>'
    return (f'<svg viewBox="-40 0 420 300" width="100%">{web}{axes}<polygon points="{poly}" '
            f'style="fill:var(--accent);fill-opacity:.3;stroke:var(--accent);stroke-width:2"/>{labs}</svg>')


def bar(pct):
    return f'<div class="bar"><i style="width:{pct:.0f}%"></i></div>'


def capsule(app_id) -> str:
    """Steam's store header image for a game."""
    return f"https://cdn.akamai.steamstatic.com/steam/apps/{int(app_id)}/header.jpg"


@st.cache_resource
def _shot_store() -> dict:
    """app_id -> screenshot thumbnail URLs, shared by every session for the life of the server."""
    return {}


def _fetch_shots(app_id: int):
    """Up to three store screenshots from Steam's public store API. None when Steam didn't answer (so it's retried)."""
    try:
        r = requests.get("https://store.steampowered.com/api/appdetails",
                         params={"appids": app_id, "filters": "screenshots"}, timeout=6)
        r.raise_for_status()
        d = r.json()[str(app_id)]
        return [s["path_thumbnail"] for s in ((d.get("data") or {}).get("screenshots") or [])[:3]]
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        return None


def screenshots(app_ids) -> dict:
    """app_id -> screenshot URLs for the given games, fetching the ones not seen yet in parallel."""
    store = _shot_store()
    missing = [a for a in app_ids if a not in store]
    if missing:
        with ThreadPoolExecutor(8) as pool:
            for a, urls in zip(missing, pool.map(_fetch_shots, missing)):
                if urls is not None:
                    store[a] = urls
    return {a: store.get(a, []) for a in app_ids}


# ---------- page ----------
html(CSS + T.backdrop_html())  # styled before the catalog loads, so the wait isn't on a blank page
if not (FULL_CATALOG or API_URL):
    st.error("Set GAMES_SUPABASE_URL and GAMES_SUPABASE_KEY (full Steam catalog), or MODAL_API_URL, "
             "in .streamlit/secrets.toml.")
    st.stop()

with st.spinner("Stocking the shelves... (first load pulls the full Steam catalog, about 30 seconds)"
                if FULL_CATALOG else "Stocking the shelves..."):
    try:
        G = load_catalog()
    except requests.RequestException as e:
        st.error(f"Couldn't load the games catalog: {e}")
        st.stop()
ss = st.session_state
ss.setdefault("picked", [])
ss.setdefault("view", None)  # app_id of the game whose stats page is open
ss.setdefault("view_why", None)
ss.setdefault("mode", "Simple")  # Simple: just pick games. Advanced: per-game hours / modes and recommender tuning
ss.setdefault("budget", 60)
# Streamlit forgets a widget's value on any run where the widget isn't drawn. Simple mode hides the per-game and
# tuning controls, so re-assign their values every run to keep them (Streamlit's documented workaround).
for k in list(ss.keys()):
    if str(k).startswith(("h_", "m_", "s_")) or k == "budget":
        ss[k] = ss[k]


def open_game(app_id, why):
    ss.view, ss.view_why = app_id, why


def close_game():
    ss.view = ss.view_why = None


def load_demo():
    """A fresh random profile every click: random games, hours, modes and time split."""
    picks = []
    for gid in random.sample(range(len(G)), random.randint(4, 10)):
        lab = G.loc[gid].label
        picks.append(lab)
        ss[f"h_{lab}"] = float(random.choice([random.randint(3, 30), random.randint(20, 150), random.randint(100, 600)]))
        have = modes_for(G.loc[gid].genres)
        for mode in MODES:
            ss[f"m_{lab}_{mode}"] = mode in have
            ss[f"s_{lab}_{mode}"] = random.randint(10, 90)
    ss.picked = picks


def reset_game_state(lab):
    """Forget a game's mode ticks / time split so they re-default from its Steam tags."""
    for mode in MODES:
        ss.pop(f"m_{lab}_{mode}", None)
        ss.pop(f"s_{lab}_{mode}", None)


def catalog_matches(games):
    """Every owned game that's in the catalog, as (catalog row, hours), most hours first."""
    by_app = dict(zip(G.app_id.astype(int), G.index))
    return [(int(by_app[g["appid"]]), min(9999.0, round(g["hours"], 1)))
            for g in sorted(games, key=lambda g: -g["hours"]) if g["appid"] in by_app]


def default_feats(gid):
    """Mode split when we only know hours (other players): even across the modes the game's tags suggest."""
    have = modes_for(G.loc[gid].genres)
    return {m: 1 / len(have) for m in have}


def load_rival(source):
    """Fetch another player's library for the Compare tab, from the friends dropdown or the typed profile."""
    ss.rival_msg = None
    try:
        if source == "friend":
            sid = ss.get("rival_pick")
            if not sid:
                raise S.SteamError("Pick a friend first.")
        else:
            sid = S.resolve_steamid(STEAM_KEY, ss.get("rival_user", ""))
        if sid == ss.get("steam_id"):
            raise S.SteamError("That's you. Pick someone else to compare with.")
        games = S.owned_games(STEAM_KEY, sid)
        name = S.player_name(STEAM_KEY, sid)
    except S.SteamError as e:
        ss.rival_msg = str(e)
        return
    except requests.RequestException as e:
        ss.rival_msg = f"Couldn't reach the Steam API: {e}"
        return
    matched = catalog_matches(games)
    their_played = {gid: h for gid, h in matched if h >= MIN_HOURS}
    if not their_played:
        ss.rival_msg = (f"{name} owns {len(games)} games, but none of the ones in the catalog have "
                        f"{MIN_HOURS:g}+ hours played.")
        return
    ss.rival = dict(sid=sid, name=name, played=their_played, owned=[gid for gid, _ in matched], hours=dict(matched),
                    n_played=sum(g["hours"] > 0 for g in games), n_owned=len(games))


def load_friends():
    try:
        ss.friends = S.friends(STEAM_KEY, ss.steam_id)
        ss.friends_msg = None if ss.friends else "Your friends list is empty."
    except S.SteamError as e:
        ss.friends, ss.friends_msg = [], str(e)
    except requests.RequestException as e:
        ss.friends, ss.friends_msg = [], f"Couldn't reach the Steam API: {e}"


def import_steam(sid=None):
    """Replace the played list with every owned game that's in the catalog (most hours first).
    Uses the signed-in Steam ID if given, otherwise whatever is typed in the profile box."""
    ss.steam_msg = None
    try:
        sid = sid or S.resolve_steamid(STEAM_KEY, ss.get("steam_user", ""))
        games = S.owned_games(STEAM_KEY, sid)
    except S.SteamError as e:
        ss.steam_msg = ("error", str(e))
        return
    except requests.RequestException as e:
        ss.steam_msg = ("error", f"Couldn't reach the Steam API: {e}")
        return
    matched = catalog_matches(games)
    if not matched:
        ss.steam_msg = ("warning", f"Found {len(games)} owned games, but none of them are in the catalog yet.")
        return
    picks = []
    for gid, h in matched:
        lab = G.loc[gid].label
        picks.append(lab)
        ss[f"h_{lab}"] = h
        reset_game_state(lab)
    ss.picked = picks
    skipped = len(games) - len(matched)
    counted = sum(h >= MIN_HOURS for _, h in matched)
    msg = (f"Imported {len(picks)} of your {len(games)} owned games; the {counted} with {MIN_HOURS:g}+ hours shape "
           f"your recommendations")
    if skipped:
        msg += f"; {skipped} {'wasn' if skipped == 1 else 'weren'}'t in the catalog"
    ss.steam_msg = ("success", msg + ". Adjust hours and modes in Advanced mode.")


def steam_sign_out():
    for k in ("steam_id", "steam_name", "friends", "friends_msg"):
        ss.pop(k, None)
    ss.steam_msg = None


# Steam's sign-in page redirects back here with openid.* query params: verify them and import right away.
# This must run before the search box is drawn, because it fills the played-games list.
if STEAM_KEY and "openid.mode" in st.query_params:
    reply = st.query_params.to_dict()
    st.query_params.clear()  # so a refresh doesn't re-submit the (one-time) reply
    try:
        ss.steam_id = S.verify_login(reply, APP_URL)
        ss.steam_name = S.player_name(STEAM_KEY, ss.steam_id)
        import_steam(ss.steam_id)
    except S.SteamError as e:
        ss.steam_msg = ("error", str(e))
    except requests.RequestException as e:
        ss.steam_msg = ("error", f"Couldn't reach Steam to confirm the sign-in: {e}")


def steam_menu():
    """Top-right Steam pill: sign in through Steam, or import from a typed profile."""
    signed_in = ss.get("steam_id")
    with st.popover(f"🎮  {ss.get('steam_name') or 'Steam'}" if signed_in else "🎮  Import from Steam"):
        if not STEAM_KEY:
            st.info("Add STEAM_API_KEY to .streamlit/secrets.toml to import your games from Steam. "
                    "Get a key at steamcommunity.com/dev/apikey.")
            return
        if signed_in:
            st.markdown(f"Signed in as **{ss.get('steam_name') or ss.steam_id}**")
            st.button("Re-import my games", type="primary", on_click=import_steam, args=(ss.steam_id,),
                      use_container_width=True)
            st.button("Sign out", on_click=steam_sign_out, use_container_width=True)
        else:
            # plain link with target=_self so Steam returns to this tab (st.link_button opens a new one)
            st.markdown(f'<a href="{S.login_url(APP_URL)}" target="_self" class="steam-login">'
                        '<img src="https://community.fastly.steamstatic.com/public/images/signinthroughsteam/sits_01.png" '
                        'alt="Sign in through Steam"></a>', unsafe_allow_html=True)
            st.text_input("Or enter a profile", key="steam_user",
                          placeholder="Custom URL name, profile URL or SteamID64")
            st.button("Import my library", on_click=import_steam, use_container_width=True)
        st.caption("Your Steam profile and its Game details must be set to Public. Every owned game that's in the "
                   f"catalog is imported with its lifetime hours; games under {MIN_HOURS:g} hours don't count "
                   "toward your taste profile.")


def game_inputs(lab, gid, show):
    """(hours, {mode: share of hours}) for one played game. The values live in session state, defaulted from the
    game's Steam tags, so Simple mode can use them without drawing anything; with `show` the controls are drawn."""
    ss[f"h_{lab}"] = float(ss.get(f"h_{lab}", 20))  # float, so Steam's fractional hours survive the 2.5h cutoff
    have = modes_for(G.loc[gid].genres)
    for mode in MODES:
        ss.setdefault(f"m_{lab}_{mode}", mode in have)
    on = [m for m in MODES if ss[f"m_{lab}_{m}"]]
    solo = len(on) == 1  # the only mode played is all of the time played
    for m in on:
        if solo:
            ss[f"s_{lab}_{m}"] = 100
        else:
            ss.setdefault(f"s_{lab}_{m}", 50)
    if show:
        st.number_input("Hours played", min_value=0.0, max_value=9999.0, step=1.0, format="%.1f", key=f"h_{lab}",
                        help=f"Games under {MIN_HOURS:g} hours are left out of your taste profile.")
        for mode, (ic, name) in MODES.items():
            if st.checkbox(f"{ic} {name}", key=f"m_{lab}_{mode}"):
                st.slider("Share of hours", 0, 100, key=f"s_{lab}_{mode}", format="%d%%", disabled=solo,
                          help="Locked at 100% while this is the only mode ticked." if solo else
                          "What percentage of your hours on this game went into this mode.")
    raw = {m: ss[f"s_{lab}_{m}"] for m in on}
    tot = sum(raw.values())
    return ss[f"h_{lab}"], {m: s / tot if tot else 1 / len(raw) for m, s in raw.items()}


# ---- top bar: brand on the left, Steam import and the mode switch on the right
left, right = st.columns([1, 2], vertical_alignment="center")
with left:
    html(f'<div class="brand">{MARK}<span>Taste<b>Forge</b></span></div>')
with right, st.container(horizontal=True, horizontal_alignment="right", key="topbar"):
    steam_menu()
    with st.popover(f"Mode: {ss.mode}"):
        st.radio("Mode", ["Simple", "Advanced"], key="mode", label_visibility="collapsed",
                 captions=["Pick your games, get recommendations", "Hours, play modes, weights, budget and filters"])
adv = ss.mode == "Advanced"

# ---- hero: title and one big search box
html(f"""<div class="hero"><div class="ttl">{MARK}<h1>Find what to play next</h1></div>
<p>Add the games you've played. TasteForge learns what you spend your hours on (genres, prices, play styles)
and finds what fits you next.</p></div>""")
with st.container(key="heromid"):
    with st.container(key="search"):
        st.multiselect("Games you've played", G.label.tolist(), key="picked", label_visibility="collapsed",
                       placeholder="Search a game you've played...")
    with st.container(horizontal=True, horizontal_alignment="center"):
        st.button("Try a demo profile", on_click=load_demo)
        if ss.picked:
            st.button("Clear", on_click=lambda: ss.update(picked=[]))
    msg = ss.get("steam_msg")
    if msg:
        getattr(st, msg[0])(msg[1])
    with st.container(key="why"), st.expander("How the recommender works"):
        st.markdown(
            "Recommendations come from **EASE-safe**, a collaborative-filtering model trained on the libraries of "
            "thousands of Steam players. It recommends games that **players who played the same games as you went "
            "on to play**, and names which of your games pushed each pick up.\n\n"
            "**EASE** (Embarrassingly Shallow Autoencoder) learns how strongly each game predicts every other game. "
            "Your scores are the sum of those links from every game you've played. The **safe** step then re-ranks "
            "the top 50 so likely misses move down (they aren't removed): games whose tags look more like the games "
            "you quit in under 2 hours than the ones you kept playing, games most people finish in 2 hours or less, "
            "and games with negative Steam reviews.\n\n"
            "The model only knows games that 100+ players in its training data played (about 13,000), mostly from "
            "2017 to 2023, so very new or niche games won't be recommended yet.\n\n"
            "Your **Player Profile** (genres, prices, play styles) is still built from your hours. Switch to "
            "**Advanced** (top right) to set hours per game or cap the budget. "
            "Use **Import from Steam** to fill the list from your library.")
SOURCE = (f"{len(G):,} Steam games with {MIN_REVIEWS}+ reviews, from the full Steam catalog in Supabase" if FULL_CATALOG
          else f"{len(G):,} well-reviewed Steam games from Supabase")
html(f'<div class="src">Live data · {SOURCE}</div>')

# ---- played games: Advanced draws each game's hours and modes, Simple uses the stored / tag-based defaults
owned, feats = {}, {}  # every picked game: none of them is ever recommended back
row_of = dict(zip(G.label, G.index))
picked = [(lab, int(row_of[lab])) for lab in ss.picked]
if adv and picked:
    with st.container(key="mygames"):
        st.markdown("##### Your games · hours and play modes")
        cols = st.columns(3)
        for i, (lab, gid) in enumerate(picked):
            with cols[i % 3], st.expander(lab.rsplit("  (", 1)[0]):
                owned[gid], feats[gid] = game_inputs(lab, gid, True)
        st.caption("Set each game's hours, which modes you play (story, co-op, PvP) and what percentage of your "
                   "hours went into each (locked to 100% when only one is ticked). Modes are pre-ticked from the "
                   "game's Steam tags.")
else:
    for lab, gid in picked:
        owned[gid], feats[gid] = game_inputs(lab, gid, False)

# only games with real time in them shape the taste profile; barely-touched ones would just add noise
played = {gid: h for gid, h in owned.items() if h >= MIN_HOURS}
P = profile(G, played, feats)

# ---- world for the animated scene on the open game page
viewed = G[G.app_id == ss.view] if ss.view else G.iloc[:0]
scenes = set()
if ss.view and gd.has(ss.view):
    scenes.add(T.theme_for(gd.tags_of(ss.view)))
elif len(viewed):  # games only in the new catalog, not in games_slim.csv
    scenes.add(T.theme_for(viewed.iloc[0].genres))
html(T.scene_css(scenes))

# ---- hidden gem: a well-loved, lesser-known game in the bottom-right corner (wide screens only)
if "gem" not in ss:
    pool = G[(G.rating >= 92) & G.reviews.between(300, 5000)] if "reviews" in G else G.iloc[:0]
    ss.gem = int(pool.sample(1).index[0]) if len(pool) else None
if ss.gem is not None:
    g = G.loc[ss.gem]
    html(f'<div class="gem fx-host"><img src="{capsule(g.app_id)}" alt=""><div class="gb">'
         f'<span class="pill">HIDDEN GEM</span>{g.rating:.0f}% positive'
         f'<a href="https://store.steampowered.com/app/{int(g.app_id)}/" target="_blank">{escape(g["name"])} ↗</a>'
         f'{int(g.reviews):,} reviews · {fmt(g.price)}</div></div>')

tabs = st.tabs(["Recommendations", "Player Profile", "Compare"])
NEED = (f'<div class="empty">None of your games have {MIN_HOURS:g}+ hours yet, so there\'s nothing to build a taste '
        'profile from. Add a game you\'ve spent more time in, or raise the hours in Advanced mode.</div>' if owned else
        '<div class="empty">Search for a few games you\'ve played above (or hit <b>Try a demo profile</b>) to build '
        'your player profile.</div>')

# ----- Player Profile -----
with tabs[1]:
    if not played:
        html(NEED)
    else:
        top = sorted(P["aff"].items(), key=lambda kv: -kv[1])
        rad = top[:8]
        while len(rad) < 3:
            rad.append(("—", 0.0001))
        buckets = [("Free", 0, 0), ("Under $10", .01, 9.99), ("$10–20", 10, 20), ("$20–40", 20.01, 40), ("$40+", 40.01, 999)]
        pb = [(l, sum(h for gid, h in played.items() if a <= G.loc[gid].price <= b)) for l, a, b in buckets]
        mx = max(max(h for _, h in pb), 1)
        ap = P["avg_price"]
        arche = f"{top[0][0]} " + ("Bargain Hunter" if ap < 15 else "Value Seeker" if ap < 35 else "Premium Collector")
        html(f"""<div class="kpi"><div><b>{P['n']}</b><span>games tracked</span></div>
        <div><b>{round(P['tot'])}h</b><span>total hours</span></div>
        <div><b>{fmt(round(ap, 2))}</b><span>hour-weighted price</span></div>
        <div><b>{MODES[max(P['modes'], key=P['modes'].get)][1].split(' ')[0] if P['modes'] else '—'}</b><span>main mode</span></div>
        <div><b style="font-size:16px">{arche}</b><span>your archetype</span></div></div>""")
        a, b = st.columns(2)
        with a:
            html(f'<div class="card"><h2>Genre radar</h2>{radar(rad)}</div>')
        with b:
            hours = "".join(
                f'<div style="margin:7px 0"><div style="display:flex;justify-content:space-between;font-size:13px">'
                f'<span>{g}</span><span>{round(v * 100)}%</span></div>{bar(v / top[0][1] * 100)}</div>' for g, v in top[:7])
            price = "".join(
                f'<div style="display:grid;grid-template-columns:90px 1fr 44px;gap:8px;align-items:center;font-size:13px;margin:5px 0">'
                f'<span>{l}</span>{bar(h / mx * 100)}<span>{round(h)}h</span></div>' for l, h in pb)
            html(f'<div class="card"><h2>Where your hours go</h2>{hours}<h2 style="margin-top:18px">Price comfort zone</h2>{price}</div>')

        # play style: how hours split across story / co-op / pvp
        th = sum(P["modes"].values())
        rows = ""
        for m, (ic, name) in MODES.items():
            hrs = P["modes"].get(m)
            if hrs and th:
                rows += (f'<div class="mode"><div class="mh"><span>{ic} {name}</span>'
                         f'<span>{round(hrs)}h · {round(hrs / th * 100)}% of your time</span></div>{bar(hrs / th * 100)}</div>')
        big = sorted(played.items(), key=lambda kv: -kv[1])[:5]
        big_html = "".join(
            f'<div class="todo"><span>{G.loc[g]["name"]}</span><span>{h:g}h · '
            + " ".join(f'{MODES[m][0]} {round(s * 100)}%' for m, s in feats[g].items()) + '</span></div>' for g, h in big)
        c, d = st.columns(2)
        with c:
            html(f'<div class="card"><h2>Play style</h2>{rows or "<div class=why>Tick a mode on a game to see this.</div>"}</div>')
        with d:
            html(f'<div class="card"><h2>Your biggest games</h2>{big_html}'
                 f'<div class="note">Hours and how each game\'s time splits between story, co-op and PvP.</div></div>')

# ----- Recommendations -----
PRESETS = [  # quick shaping: (title, what it does, budget it sets)
    ("Any price", "No budget cap", 60),
    ("Under $20", "Hide anything pricier than $20", 20),
    ("Under $10", "Hide anything pricier than $10", 10),
    ("Free only", "Only free-to-play games", 0),
]
FLAG_HELP = {"quit": "its tags look more like the games you quit in under 2 hours than the ones you kept playing",
             "short": "most players finish it in 2 hours or less",
             "neg": "its Steam reviews are Mostly Negative or worse"}


def shape(key, value):
    ss[key] = value


def short(n) -> str:
    n = int(n)
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e4 else f"{n / 1e3:.1f}k" if n >= 1e3 else str(n)


def chips(tags, sel=False) -> str:
    return "".join(f'<span class="chip {"sel" if sel else ""}">{escape(str(x))}</span>' for x in tags)


def price_html(c) -> str:
    if c["price_text"] is None:
        return '<span class="why">Price unknown</span>'
    sale = (f'<span class="why"> was ${c["price_initial"]:.2f} (-{c["discount"]}%)</span>'
            if c.get("discount") and c.get("price_initial") else "")
    return f'<span class="chip sel">{escape(c["price_text"])}</span>{sale}'


def analysis_html(c) -> str:
    """Why EASE picked this game: how much each of the player's games pushed it up, plus the safe re-rank's flags."""
    contrib = c["contrib"]
    mx = max((v for _, v in contrib), default=1) or 1
    bars = "".join(
        f'<div class="mode"><div class="mh"><span>{escape(t)}</span><span>{round(v / mx * 100)}%</span></div>'
        f'{bar(v / mx * 100)}</div>' for t, v in contrib) or '<div class="why">No single game stands out.</div>'
    flags = "".join(f'<div class="why">⚠️ <b>{E.FLAG_NAMES[f]}</b>: {FLAG_HELP[f]}, so it was moved down.</div>'
                    for f in c["flags"]) or '<div class="why">✅ No soft-fail flags: not like the games you quit, '\
                                            'not a 2-hour game, and not negatively reviewed.</div>'
    return (f'<div class="ana"><div><div class="lbl">Your games behind this pick</div>{bars}'
            f'<div class="note">Relative pull from each game you played, strongest = 100%.</div></div>'
            f'<div><div class="lbl">Safe check</div>{flags}</div></div>')


EASE_MISSING = E.missing_files(STEAMREC_ARTIFACTS, STEAMREC_DATA)
MISSING_HTML = (f'<div class="empty">The EASE-safe model files are missing: '
                f'{"<br>".join(f"<code>{escape(p)}</code>" for p in EASE_MISSING)}<br>See <code>ease/README.md</code> '
                f'to download them from Supabase, or set STEAMREC_ARTIFACTS / STEAMREC_DATA.</div>')

with tabs[0]:
    if ss.view:
        gd.show(ss.view, ss.view_why, close_game, basic=viewed.iloc[0] if len(viewed) else None)
    elif not played:
        html(NEED)
    elif EASE_MISSING:
        html(MISSING_HTML)
    else:
        main, side = st.columns([3.2, 1], gap="medium")
        with side, st.container(key="shape"):
            st.markdown("##### Budget")
            for title, desc, val in PRESETS:
                st.button(title, key=f"shape_{title}", use_container_width=True, on_click=shape, args=("budget", val),
                          type="primary" if ss.budget == val else "secondary")
                html(f'<div class="pd">{desc}</div>')
        with main:
            if adv:
                with st.container(key="tune"):
                    st.markdown("##### Tune the recommender")
                    st.slider("Max budget ($)", 0, 60, step=5, key="budget",
                              help="Checked against the current Steam store price. 60 means no limit.")
            budget = 999 if ss.budget >= 60 else ss.budget
            R = recommend(owned, budget, n=8)
            if R is None:
                html('<div class="empty">None of your games are known to the EASE model yet (it learned from games '
                     '100+ players in its data played, mostly 2017 to 2023). Add a few more popular games.</div>')
                R = []
            html(f'<div class="rhead"><div><div class="t">Recommendations</div>'
                 f'<div class="n">Top {len(R)} of {ease_model().n_candidates:,} games the EASE-safe model can recommend</div></div>'
                 f'<div class="lbl">Sorted by<span>EASE-safe rank</span></div></div>')
            if not R and budget < 999:
                html('<div class="empty">Nothing fits that budget. Raise the max budget.</div>')
            aff = P["aff"]
            shots = screenshots([c["app_id"] for c in R])
            for i, c in enumerate(R):
                aid = c["app_id"]
                gw = T.THEMES[T.theme_for(c["tags"])]
                mine = [t for t in c["tags"] if t in aff]
                fresh = [t for t in c["tags"] if t not in aff]
                flags = [E.FLAG_NAMES[f] for f in c["flags"]]
                strip = "".join(f'<img src="{escape(u)}" loading="lazy" alt="">' for u in shots.get(aid, []))
                rev = (f'Steam reviews <b>{c["rating"]}% positive</b>{bar(c["rating"])}{short(c["reviews"])} total'
                       if c["rating"] is not None else "No Steam rating yet")
                with st.container(key=f"rec_{aid}"):
                    html(f"""<div class="rec"><div class="top">
                    <div class="cap" style="background-image:url('{escape(c["image"] or capsule(aid))}')"></div>
                    <div><h3><a href="{c['store_url']}" target="_blank" style="color:inherit;text-decoration:none">{escape(c['title'])}</a>
                    <span class="pct">#{i + 1} pick</span>
                    <span class="mi" title="{gw['name']}">{gw['icon']}</span></h3>
                    <div>{'<span class="badge">Best match</span>' if i == 0 else ""}</div></div>
                    <div class="rev">{rev}</div></div>
                    {f'<div class="shots">{strip}</div>' if strip else ""}
                    <div class="lbl">Match receipt</div>
                    <div class="receipt">
                    <div><div class="lbl"><span>Because you played</span></div>
                    {chips(c["because"], True) or '<span class="why">Your library as a whole</span>'}</div>
                    <div><div class="lbl"><span>Tags</span><b>{len(mine)} you play</b></div>
                    {chips(mine, True)}{chips(fresh) if fresh else ""}{'' if c["tags"] else '<span class="why">No tags</span>'}</div>
                    <div><div class="lbl"><span>Price</span></div>{price_html(c)}</div>
                    <div><div class="lbl"><span>Safe check</span><b>{len(flags)} flag{"" if len(flags) == 1 else "s"}</b></div>
                    {chips(flags) or '<span class="chip sel">✅ No flags</span>'}</div>
                    </div></div>""")
                    with st.expander("Why this pick"):
                        html(analysis_html(c))
                        st.button(f"📊  See full stats for {c['title']}  →", key=f"view_{aid}", use_container_width=True,
                                  on_click=open_game, args=(aid, dict(rank=i + 1, because=c["because"], flags=flags)))

# ----- Compare -----
YOU_C, THEM_C = "var(--accent)", "#b48cff"


def two_bar(you, them):
    """Your bar over theirs, both scaled 0-100."""
    return (f'<div class="bar" style="margin-bottom:3px"><i style="width:{you:.0f}%"></i></div>'
            f'<div class="bar"><i style="width:{them:.0f}%;--ca:{THEM_C};--ca2:#d6c2ff"></i></div>')


def taste_match(a, b):
    """Cosine similarity of two genre-affinity profiles, 0-1."""
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0


def rec_list(cards, other_ids, who):
    """One player's EASE-safe picks (card dicts), flagging the ones the other player also got."""
    out = ""
    for i, c in enumerate(cards or []):
        tag = '<span class="chip sel">for both of you</span>' if c["app_id"] in other_ids else ""
        out += (f'<div class="todo"><span>#{i + 1} {escape(c["title"])} {tag}</span>'
                f'<span>{escape(c["price_text"] or "")}</span></div>')
    return f'<div class="card"><h2>{who}</h2>{out or "<div class=why>No recommendations.</div>"}</div>'


def fav_list(title, src, other, n=6):
    rows = [(g, h) for g, h in sorted(src.items(), key=lambda kv: -kv[1]) if g not in other][:n]
    body = "".join(f'<div class="todo"><span>{G.loc[g]["name"]}</span><span>{h:g}h · {fmt(G.loc[g].price)}</span></div>'
                   for g, h in rows)
    return f'<div class="card"><h2>{title}</h2>{body or "<div class=why>Nothing here: you have the same favorites.</div>"}</div>'


with tabs[2]:
    if not STEAM_KEY:
        st.info("Add STEAM_API_KEY to .streamlit/secrets.toml to compare libraries with other Steam players.")
    else:
        st.markdown("##### COMPARE WITH ANOTHER PLAYER")
        a, b = st.columns(2)
        with a:
            if ss.get("steam_id"):
                if "friends" not in ss:
                    load_friends()
                if ss.friends:
                    names = dict(ss.friends)
                    st.selectbox("Your Steam friends", list(names), key="rival_pick", format_func=names.get,
                                 index=None, placeholder="Pick a friend...")
                    st.button("Compare with friend", type="primary", on_click=load_rival, args=("friend",))
                else:
                    st.caption(ss.friends_msg)
            else:
                st.caption("Sign in through Steam (Import from Steam, top right) to pick from your friends list.")
        with b:
            st.text_input("Their Steam profile", key="rival_user",
                          placeholder="Custom URL name, profile URL or SteamID64")
            st.button("Compare with this profile", on_click=load_rival, args=("typed",))
        if ss.get("rival_msg"):
            st.error(ss.rival_msg)

        rv = ss.get("rival")
        if not rv:
            html('<div class="empty">Pick a friend or enter someone\'s Steam profile to compare your libraries and '
                 'recommendations. Their profile\'s Game details must be public.</div>')
        elif not played:
            html(NEED)
        else:
            them = rv["played"]
            their_owned = set(rv.get("owned", them))
            P2 = profile(G, them, {g: default_feats(g) for g in them})
            shared = [g for g in played if g in them]
            match = taste_match(P["aff"], P2["aff"])
            html(f"""<div class="kpi"><div><b>{round(match * 100)}%</b><span>taste match (genre profile)</span></div>
            <div><b>{len(shared)}</b><span>games you both play</span></div>
            <div><b>{P['n']} · {round(P['tot'])}h</b><span>you: games · hours</span></div>
            <div><b style="color:{THEM_C}">{P2['n']} · {round(P2['tot'])}h</b><span>{rv['name']}: games · hours</span></div></div>""")
            legend = (f'<div class="why" style="margin-bottom:8px"><b style="color:var(--accent2)">■ You</b> &nbsp; '
                      f'<b style="color:{THEM_C}">■ {rv["name"]}</b></div>')
            c, d = st.columns(2)
            with c:
                top = sorted(set(P["aff"]) | set(P2["aff"]), key=lambda k: -(P["aff"].get(k, 0) + P2["aff"].get(k, 0)))[:8]
                mx = max([P["aff"].get(k, 0) for k in top] + [P2["aff"].get(k, 0) for k in top] + [1e-9])
                rows = "".join(
                    f'<div style="margin:8px 0"><div class="mh"><span>{k}</span><span>{round(P["aff"].get(k, 0) * 100)}% · '
                    f'{round(P2["aff"].get(k, 0) * 100)}%</span></div>'
                    f'{two_bar(P["aff"].get(k, 0) / mx * 100, P2["aff"].get(k, 0) / mx * 100)}</div>' for k in top)
                html(f'<div class="card"><h2>Genres: share of hours</h2>{legend}{rows}</div>')
            with d:
                if shared:
                    hm = max(max(played[g], them[g]) for g in shared)
                    body = "".join(
                        f'<div style="margin:8px 0"><div class="mh"><span>{G.loc[g]["name"]}</span>'
                        f'<span>{played[g]:g}h · {them[g]:g}h</span></div>{two_bar(played[g] / hm * 100, them[g] / hm * 100)}</div>'
                        for g in sorted(shared, key=lambda g: -(played[g] + them[g]))[:10])
                else:
                    body = f'<div class="why">No games in common (with {MIN_HOURS:g}+ hours each).</div>'
                html(f'<div class="card"><h2>Games you both play</h2>{legend}{body}</div>')
            c, d = st.columns(2)
            with c:
                html(fav_list(f"{rv['name']}'s favorites you don't own", them, owned))
            with d:
                html(fav_list(f"Your favorites {rv['name']} doesn't own", played, their_owned))
            if EASE_MISSING:
                html(MISSING_HTML)
            else:
                mine = recommend(owned, n=8) or []
                theirs = recommend(rv.get("hours") or {g: them.get(g, 0) for g in their_owned}, n=8) or []
                mine_ids, their_ids = {c["app_id"] for c in mine}, {c["app_id"] for c in theirs}
                c, d = st.columns(2)
                with c:
                    html(rec_list(mine, their_ids, "Recommended for you"))
                with d:
                    html(rec_list(theirs, mine_ids, f"Recommended for {rv['name']}"))
            html(f'<div class="note">{rv["name"]}: {rv["n_played"]} played of {rv["n_owned"]} owned; compared on their '
                 f'{len(them)} catalog games with {MIN_HOURS:g}+ hours. Recommendations come from the EASE-safe model '
                 f'over each full library, with no budget limit.</div>')
