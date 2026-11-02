"""TasteForge: Streamlit dashboard over the Steam games table in Supabase, served via the Modal app.
Run: streamlit run app.py   (MODAL_API_URL in .streamlit/secrets.toml or the environment)
The page re-themes itself to the games you pick (see themes.py).
"""
import math
import os
import random
import re

import pandas as pd
import requests
import streamlit as st

import game_detail as gd
import themes as T

st.set_page_config(page_title="TasteForge - Steam Category Tracker", page_icon="🔥", layout="wide")

try:
    API_URL = st.secrets["MODAL_API_URL"]
except Exception:
    API_URL = os.environ.get("MODAL_API_URL", "")

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
.stApp{isolation:isolate;font-family:var(--body);color:var(--text)}
[data-testid=stAppViewContainer],[data-testid=stMain],[data-testid=stHeader],[data-testid=stBottom],[data-testid=stBottom]>div{background:transparent!important}
div[data-testid=stElementContainer]:has(.fx-host){position:absolute;width:0;height:0;overflow:visible}
.stApp p,.stApp label,.stApp li,.stApp input,.stApp textarea,.stApp button,.stApp [data-baseweb]{font-family:var(--body)}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6{font-family:var(--disp);letter-spacing:.05em}
.stApp h5{text-transform:uppercase;letter-spacing:.14em;font-size:15px;color:var(--accent2)}
section[data-testid=stSidebar]{background:var(--panel)!important;backdrop-filter:blur(10px);border-right:1px solid var(--line)}
section[data-testid=stSidebar]>div{background:transparent!important}
.stTabs [data-baseweb=tab] p{font-family:var(--disp);letter-spacing:.1em;text-transform:uppercase;font-size:15px}
.stTabs [aria-selected=true] p{color:var(--accent2)}
.stTabs [data-baseweb=tab-highlight]{background:linear-gradient(90deg,var(--accent),var(--accent2))!important;height:3px}
.stTabs [data-baseweb=tab-border]{background:var(--line)!important}
[data-baseweb=select]>div,[data-baseweb=base-input],[data-baseweb=input]>div,textarea{background:var(--panel2)!important;border-color:var(--line)!important}
[data-testid=stBaseButton-primary]{background:linear-gradient(135deg,var(--accent),var(--accent2))!important;color:#140c07!important;border:0!important;font-weight:700;box-shadow:0 6px 20px -8px var(--accent)}
[data-testid=stBaseButton-primary] p{color:#140c07!important;font-family:var(--disp);letter-spacing:.1em;text-transform:uppercase}
[data-testid=stBaseButton-secondary]{background:var(--panel2);border:1px solid var(--line);color:var(--text)}
[data-testid=stBaseButton-secondary]:hover{border-color:var(--accent);color:var(--accent2)}
span[data-baseweb=tag]{background:var(--accent)!important}
span[data-baseweb=tag] span,span[data-baseweb=tag] svg{color:#140c07!important;fill:#140c07!important}
[data-testid=stSlider] [role=slider]{background:var(--accent2)!important;box-shadow:0 0 12px var(--accent)}
[data-testid=stSliderThumbValue]{color:var(--accent2)!important}
[data-testid=stExpander]{background:var(--panel);border:1px solid var(--line)!important;border-radius:12px}
.hero{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin:0 0 4px}
.logo{display:flex;align-items:center;gap:12px}
.logo svg{width:50px;height:50px;color:var(--accent2);filter:drop-shadow(0 0 10px var(--accent));animation:flame 2.4s ease-in-out infinite}
@keyframes flame{50%{transform:scale(1.07) translateY(-2px);filter:drop-shadow(0 0 18px var(--accent2))}}
h1.tf{font-family:'Big Shoulders Display',Impact,sans-serif!important;font-weight:900;font-size:58px;letter-spacing:5px;line-height:1;margin:0;padding:0}
h1.tf span{color:var(--accent2);text-shadow:0 0 24px var(--accent)}
.sub{color:var(--mute);font-size:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:12px;backdrop-filter:blur(6px)}
.card h2{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:.18em;color:var(--mute)}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.kpi div{flex:1;min-width:120px;background:var(--panel);border:1px solid var(--line);padding:10px 12px;border-radius:10px;backdrop-filter:blur(6px)}
.kpi b{display:block;font-family:var(--disp);font-size:24px;color:var(--accent2)}.kpi span{font-size:12px;color:var(--mute)}
.bar{height:9px;border-radius:5px;background:var(--panel2);overflow:hidden}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--ca,var(--accent)),var(--ca2,var(--accent2)));box-shadow:0 0 10px var(--ca,var(--accent))}
.chip{display:inline-block;padding:3px 9px;border-radius:99px;font-size:12px;background:var(--panel2);border:1px solid var(--line);margin:2px 3px 2px 0}
.chip.sel{background:var(--ca2,var(--accent2));color:#10130a;border-color:var(--ca2,var(--accent2))}
.rec{display:grid;grid-template-columns:54px 1fr auto;gap:12px;align-items:center;padding:12px;background:var(--panel);border:1px solid var(--line);border-radius:12px 12px 0 0;margin-bottom:0;backdrop-filter:blur(6px)}
[class*="st-key-view_"]{margin:-14px 0 8px}
[class*="st-key-view_"] button{border-radius:0 0 12px 12px;background:var(--panel2);border:1px solid var(--line);border-top:0;min-height:34px}
[class*="st-key-view_"] button:hover{border-color:var(--accent)}
[class*="st-key-view_"] button p{font-size:13px;color:var(--accent2);letter-spacing:.04em}
.match{width:54px;height:54px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:15px;color:#0a1119}
.rec h3{margin:0;font-size:18px}.rec .mi{font-size:13px;margin-left:8px;letter-spacing:3px}.why{color:var(--mute);font-size:13px}
.price{font-family:var(--disp);font-weight:700;font-size:18px;color:var(--accent2);white-space:nowrap}
.catcard{border-radius:14px;overflow:hidden;margin:4px 0 6px;background:var(--cp);border:1px solid var(--cl);box-shadow:0 14px 32px -16px var(--ca)}
.scene{position:relative;height:100px;overflow:hidden}
.scene::after{content:'';position:absolute;inset:0;z-index:1;background:linear-gradient(transparent 35%,rgba(0,0,0,.72))}
.scene .ttl{position:absolute;z-index:2;left:14px;right:14px;bottom:9px}
.scene .ttl h3{margin:0;padding:0;font-family:var(--cd);font-size:25px;line-height:1.1;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.85)}
.scene .realm{font-family:var(--cb);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--ca2)}
.cbody{padding:12px 14px 14px;font-family:var(--cb)}
.empty{color:var(--mute);padding:28px;text-align:center;border:1px dashed var(--line);border-radius:12px;background:var(--panel)}
.note{font-size:12px;color:var(--mute);margin-top:12px}
.mode{margin:12px 0 16px}.mh{display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px}.mh.sm{font-size:12px;color:var(--mute);margin-top:6px}
.todo{display:flex;justify-content:space-between;font-size:13px;padding:5px 0;border-bottom:1px dashed var(--line)}
table.t{width:100%;border-collapse:collapse;font-size:13px}
table.t td,table.t th{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}
table.t th{color:var(--mute);font-weight:600;font-size:12px}
svg text{fill:var(--text);font-size:11px}
</style>
"""


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


@st.cache_data(ttl=3600)
def load_catalog() -> pd.DataFrame:
    df = fetch("catalog")
    df["genres"] = df["tags"].str.split(",")
    df["price"] = df["price"].astype(float)
    df["rating"] = df["rating"].astype(float)
    df["owners"] = df["owners"].astype(float)
    df["label"] = df["name"] + "  (" + df["app_id"].astype(str) + ")"
    return df.reset_index(drop=True)


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


def recommend(G, P, played, w_genre, budget, focus_genres):
    pool = G[~G.index.isin(played) & (G.price <= budget)]
    if focus_genres:
        pool = pool[pool.genres.apply(lambda gs: any(x in focus_genres for x in gs))]
    max_a = max(P["aff"].values(), default=0.0001)
    w_g = w_genre / 100
    th = sum(P["modes"].values())
    share = {m: v / th for m, v in P["modes"].items()} if th else {}
    rows = []
    for gid, g in pool.iterrows():
        gm = sum(P["aff"].get(x, 0) for x in g.genres) / len(g.genres) / max_a
        d = math.log1p(g.price) - P["lp"]
        pm = math.exp(-(d * d) / (2 * 1.1 * 1.1))
        q = (g.rating - 70) / 30
        mf = min(1, sum(share.get(m, 0) for m in modes_for(g.genres))) if share else .5
        score = max(0, min(1, (w_g * gm + (1 - w_g) * pm) * 0.8 + q * 0.1 + mf * 0.1))
        best = max(g.genres, key=lambda x: P["aff"].get(x, 0))
        rows.append((score, gm, pm, best, g, mf))
    return sorted(rows, key=lambda r: -r[0])


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


def world_card(title, genres, body, key=None):
    """Category card: a small animated world built from the category's genres, with `body` underneath."""
    key = key or T.theme_for(genres)
    return (f'<div class="catcard" style="{T.card_vars(key)}">{T.scene_html(key, title)}'
            f'<div class="cbody">{body}</div></div>')


# ---------- page ----------
if not API_URL:
    html(CSS + T.theme_css(T.DEFAULT) + T.fx_html(T.DEFAULT))
    st.error("Set MODAL_API_URL (your deployed Modal endpoint URL) in .streamlit/secrets.toml.")
    st.stop()

with st.spinner("Heating the forge..."):
    G = load_catalog()
ss = st.session_state
ss.setdefault("picked", [])
ss.setdefault("cats", [{"name": "Cozy Grind", "genres": ["Cozy", "Farming Sim", "Simulation"]}])
ss.setdefault("view", None)  # app_id of the game whose stats page is open
ss.setdefault("view_why", None)


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
        ss[f"h_{lab}"] = int(random.choice([random.randint(2, 30), random.randint(20, 150), random.randint(100, 600)]))
        have = modes_for(G.loc[gid].genres)
        for mode in MODES:
            ss[f"m_{lab}_{mode}"] = mode in have
            ss[f"s_{lab}_{mode}"] = random.randint(10, 90)
    ss.picked = picks


with st.sidebar:
    st.markdown("##### 1 · YOUR PLAYED GAMES")
    st.multiselect("Search games", G.label.tolist(), key="picked", label_visibility="collapsed",
                   placeholder="Search games...")
    c1, c2 = st.columns([3, 1])
    c1.button("Load demo profile", type="primary", on_click=load_demo, use_container_width=True)
    c2.button("Clear", on_click=lambda: ss.update(picked=[]), use_container_width=True)
    played, feats = {}, {}
    for lab in ss.picked:
        gid = int(G.index[G.label == lab][0])
        ss.setdefault(f"h_{lab}", 20)
        with st.expander(lab.rsplit("  (", 1)[0]):
            played[gid] = st.number_input("Hours played", min_value=1, max_value=9999, key=f"h_{lab}")
            have = modes_for(G.loc[gid].genres)
            for mode in MODES:
                ss.setdefault(f"m_{lab}_{mode}", mode in have)
            on = [m for m in MODES if ss[f"m_{lab}_{m}"]]
            solo = len(on) == 1  # the only mode played is all of the time played
            raw = {}
            for mode, (ic, name) in MODES.items():
                if not st.checkbox(f"{ic} {name}", key=f"m_{lab}_{mode}"):
                    continue
                if solo:
                    ss[f"s_{lab}_{mode}"] = 100
                else:
                    ss.setdefault(f"s_{lab}_{mode}", 50)
                raw[mode] = st.slider("Share of hours", 0, 100, key=f"s_{lab}_{mode}", format="%d%%", disabled=solo,
                                      help="Locked at 100% while this is the only mode ticked." if solo else
                                      "What percentage of your hours on this game went into this mode.")
            tot = sum(raw.values())
            feats[gid] = {m: s / tot if tot else 1 / len(raw) for m, s in raw.items()}
    st.caption("Open a game to set its hours, which modes you play (story, co-op, PvP) and what percentage of your "
               "hours went into each (locked to 100% when only one is ticked). Modes are pre-ticked from the game's "
               "Steam tags. In the full app this list would come from the Steam Web API (GetOwnedGames) after a "
               "Steam login.")

P = profile(G, played, feats)

# ---- the world is fixed by the chosen games (hours-weighted)
world, drivers = T.theme_for_library([
    (G.loc[g]["name"], G.loc[g].genres, h) for g, h in played.items()])
if ss.view and gd.has(ss.view):  # a game's stats page takes on that game's own world
    world, drivers = T.theme_for(gd.tags_of(ss.view)), [gd.name_of(ss.view)]
cat_worlds = {T.theme_for(c["genres"]) for c in ss.cats} | {T.theme_for(ss.get("new_picks", []))}
html(CSS + T.theme_css(world, cat_worlds) + T.fx_html(world))

html("""<div class="hero"><div><div class="logo"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2c.6 3.6 4.6 5.4 4.6 10.2A4.6 4.6 0 0 1 12 17a4.6 4.6 0 0 1-4.6-4.8c0-1.9.9-3.1 1.9-4 .1 1.7.9 2.6 1.9 2.8C10.9 8 11.2 5 12 2z"/><rect x="5" y="19" width="14" height="3" rx="1" fill="currentColor" opacity=".7"/></svg>
<h1 class="tf">TASTE<span>FORGE</span></h1></div>
<div class="sub">Pick games you've played and the app builds your Player Profile from genre, price and play-style habits,
lets you forge your own custom categories, then recommends what to play next.</div></div></div>""")
html(f'<div class="sub" style="text-align:right;margin:4px 0 6px">Live data · {len(G):,} well-reviewed Steam games from Supabase</div>')

tabs = st.tabs(["Player Profile", "Recommendations", "Custom Categories", "Genre Success"])
NEED = '<div class="empty">Add some games on the left (or hit <b>Load demo profile</b>) to build your Player Profile.</div>'

# ----- Player Profile -----
with tabs[0]:
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
            f'<div class="todo"><span>{G.loc[g]["name"]}</span><span>{h}h · '
            + " ".join(f'{MODES[m][0]} {round(s * 100)}%' for m, s in feats[g].items()) + '</span></div>' for g, h in big)
        c, d = st.columns(2)
        with c:
            html(f'<div class="card"><h2>Play style</h2>{rows or "<div class=why>Tick a mode on a game to see this.</div>"}</div>')
        with d:
            html(f'<div class="card"><h2>Your biggest games</h2>{big_html}'
                 f'<div class="note">Hours and how each game\'s time splits between story, co-op and PvP.</div></div>')

# ----- Recommendations -----
with tabs[1]:
    if ss.view:
        gd.show(ss.view, ss.view_why, close_game)
    elif not played:
        html(NEED)
    else:
        st.markdown("##### TUNE THE RECOMMENDER")
        w = st.slider("Genre ↔ Price  (left = price habits, right = genre taste)", 0, 100, 70)
        budget = st.slider("Max budget ($)", 0, 60, 60, step=5)
        names = [c["name"] for c in ss.cats]
        focus = st.selectbox("Focus category", ["All genres"] + names)
        fg = next((c["genres"] for c in ss.cats if c["name"] == focus), None)
        R = recommend(G, P, played, w, 999 if budget >= 60 else budget, fg)[:8]
        if not R:
            html('<div class="empty">Nothing matches those filters. Raise the budget or change the focus category.</div>')
        top_mode = max(P["modes"], key=P["modes"].get) if P["modes"] else None
        for score, gm, pm, best, g, mf in R:
            gw = T.THEMES[T.theme_for(g.genres)]
            gmodes = modes_for(g.genres)
            icons = gw["icon"] + "  " + " ".join(MODES[m][0] for m in gmodes)
            chips = "".join(f'<span class="chip {"sel" if x in P["aff"] else ""}">{x}</span>' for x in g.genres)
            fit = f" · fits your {MODES[top_mode][1]} play" if top_mode in gmodes else ""
            html(f"""<div class="rec" style="border-left:4px solid {gw['c']['accent']}"><div class="match" style="background:hsl({round(score * 120)},80%,60%)">{round(score * 100)}%</div>
            <div><h3>{g['name']}<span class="mi" title="{gw['name']}">{icons}</span></h3><div>{chips}</div>
            <div class="why">Genre fit {round(gm * 100)}% (you play lots of <b>{best}</b>) · price fit {round(pm * 100)}% · {g.rating:.0f}% positive{fit}</div></div>
            <div class="price">{fmt(g.price)}</div></div>""")
            st.button(f"📊  See full stats for {g['name']}  →", key=f"view_{int(g.app_id)}", use_container_width=True,
                      on_click=open_game, args=(int(g.app_id), dict(score=score, gm=gm, pm=pm, mf=mf, best=best)))

# ----- Custom Categories -----
with tabs[2]:
    all_genres = sorted({x for gs in G.genres for x in gs})

    def create_cat():
        n, p = ss.new_name.strip(), ss.new_picks
        if n and p:
            ss.cats.append({"name": n, "genres": list(p)})
            realm = T.THEMES[T.theme_for(p)]
            st.toast(f"{n} forged. Welcome to {realm['name']}.", icon=realm["icon"])
            ss.new_name, ss.new_picks = "", []
        else:
            st.toast("Give it a name and pick at least one genre.", icon="⚠️")

    a, b = st.columns(2)
    with a:
        st.markdown("##### FORGE A CATEGORY")
        name = st.text_input("Name it", placeholder="e.g. 'Rage Quit Club'", key="new_name")
        picks = st.multiselect("Genres / tags", all_genres, key="new_picks")
        st.button("Create category", type="primary", on_click=create_cat)
        if picks:
            html(world_card(name.strip() or "Your new category", picks,
                            '<div class="why">Live preview. This is the world your category will live in; '
                            'it is built from the genres you pick.</div>'))
        html('<div class="note">Steam\'s built-in tags are broad. Combine genres into your own buckets, then track how much of '
             'your playtime each one owns and use them as a recommendation filter. Every category gets a world of its own.</div>')
    with b:
        st.markdown("##### YOUR CATEGORIES")
        for i, c in enumerate(ss.cats):
            hit = [gid for gid in played if any(x in c["genres"] for x in G.loc[gid].genres)]
            hrs = sum(played[g] for g in hit)
            share = round(hrs / P["tot"] * 100) if P["tot"] else 0
            un = G[~G.index.isin(played) & G.genres.apply(lambda gs: any(x in c["genres"] for x in gs))]
            un = un.sort_values("rating", ascending=False).head(3)
            chips = "".join(f'<span class="chip sel">{x}</span>' for x in c["genres"])
            txt = f"<b>{share}%</b> of your playtime ({round(hrs)}h across {len(hit)} games)" if P["tot"] else "Add games to see your playtime share"
            tu = " · ".join(f"{r['name']} ({fmt(r.price)})" for _, r in un.iterrows()) or "none"
            html(world_card(c["name"], c["genres"],
                            f'<div>{chips}</div><div class="why" style="margin:6px 0">{txt}</div>'
                            f'{bar(share)}<div class="why" style="margin-top:8px">Top unplayed: {tu}</div>'))
            st.button("Delete", key=f"del{i}", on_click=lambda i=i: ss.cats.pop(i))

# ----- Genre Success -----
with tabs[3]:
    gs = fetch("genre_success")
    for col in ("n", "rating", "price", "owners"):
        gs[col] = gs[col].astype(float)
    gs["idx"] = (gs.rating - 70).clip(lower=0) * gs.owners.apply(lambda o: math.log10(1 + o)) * 10
    gs = gs.sort_values("idx", ascending=False)
    mx = gs.idx.max() or 1
    rows = "".join(
        f"<tr><td>{r.genre}</td><td>{int(r.n):,}</td><td>{r.rating:.1f}%</td><td>{fmt(r.price)}</td><td>{bar(r.idx / mx * 100)}</td></tr>"
        for r in gs.itertuples())
    html(f"""<div class="card"><h2>Research question: which genres actually succeed, and does price explain it?</h2>
    <div class="why" style="margin-bottom:10px">Success Index = avg. positive-review % (above a 70% baseline) × log of combined owners,
    computed over every game in the database with 50+ reviews.</div>
    <table class="t"><tr><th>Genre</th><th>Games</th><th>Avg rating</th><th>Avg price</th><th style="width:38%">Success index</th></tr>{rows}</table></div>""")
