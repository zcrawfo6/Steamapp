"""TasteForge: Streamlit dashboard over the Steam games table in Supabase, served via the Modal app.
Run: streamlit run app.py   (MODAL_API_URL in .streamlit/secrets.toml or the environment)
"""
import math
import os
import re

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="TasteForge - Steam Category Tracker", layout="wide")

try:
    API_URL = st.secrets["MODAL_API_URL"]
except Exception:
    API_URL = os.environ.get("MODAL_API_URL", "")

DEMO = [("Stardew Valley", 120), ("Terraria", 90), ("Hades", 60), ("Slay the Spire", 75),
        ("Balatro", 40), ("Hollow Knight", 35), ("Valheim", 50), ("Portal 2", 12),
        ("Vampire Survivors", 20), ("Dave the Diver", 18)]

CSS = """
<style>
:root{--bg:#0e141b;--panel:#16202b;--panel2:#1c2937;--line:#2a3b4d;--text:#e6edf3;--mute:#8fa3b8;--accent:#66c0f4;--accent2:#c6ff4d}
.stApp{background:radial-gradient(1200px 600px at 80% -10%,#1b3350 0,transparent 60%),var(--bg)}
section[data-testid=stSidebar]{background:var(--panel);border-right:1px solid var(--line)}
h1.tf{margin:0;font-size:26px;letter-spacing:.5px}h1.tf span{color:var(--accent2)}
.sub{color:var(--mute);font-size:13px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:12px}
.card h2{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:1.5px;color:var(--mute)}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.kpi div{flex:1;min-width:120px;background:var(--panel2);padding:10px 12px;border-radius:10px}
.kpi b{display:block;font-size:22px;color:var(--accent2)}.kpi span{font-size:12px;color:var(--mute)}
.bar{height:9px;border-radius:5px;background:var(--panel2);overflow:hidden}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.chip{display:inline-block;padding:3px 9px;border-radius:99px;font-size:12px;background:var(--panel2);border:1px solid var(--line);margin:2px 3px 2px 0}
.chip.sel{background:var(--accent2);color:#10200a;border-color:var(--accent2)}
.rec{display:grid;grid-template-columns:54px 1fr auto;gap:12px;align-items:center;padding:12px;background:var(--panel2);border-radius:12px;margin-bottom:9px}
.match{width:54px;height:54px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:15px;color:#0a1119}
.rec h3{margin:0;font-size:16px}.why{color:var(--mute);font-size:13px}
.price{font-weight:700;color:var(--accent2);white-space:nowrap}
.catcard{background:var(--panel2);border-radius:12px;padding:12px;margin-bottom:10px;border-left:4px solid var(--accent2)}
.catcard h3{margin:0 0 4px}
.empty{color:var(--mute);padding:28px;text-align:center;border:1px dashed var(--line);border-radius:12px}
.note{font-size:12px;color:var(--mute);margin-top:12px}
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


# ---------- profile math (same model as the prototype) ----------
def profile(G, played):
    aff, tot, wp = {}, 0.0, 0.0
    for gid, h in played.items():
        g = G.loc[gid]
        tot += h
        wp += math.log1p(g.price) * h
        for x in g.genres:
            aff[x] = aff.get(x, 0) + h / len(g.genres)
    aff = {k: v / (tot or 1) for k, v in aff.items()}
    lp = wp / tot if tot else 0
    return dict(tot=tot, aff=aff, lp=lp, avg_price=math.exp(lp) - 1, n=len(played))


def recommend(G, P, played, w_genre, budget, focus_genres):
    pool = G[~G.index.isin(played) & (G.price <= budget)]
    if focus_genres:
        pool = pool[pool.genres.apply(lambda gs: any(x in focus_genres for x in gs))]
    max_a = max(P["aff"].values(), default=0.0001)
    w_g = w_genre / 100
    rows = []
    for gid, g in pool.iterrows():
        gm = sum(P["aff"].get(x, 0) for x in g.genres) / len(g.genres) / max_a
        d = math.log1p(g.price) - P["lp"]
        pm = math.exp(-(d * d) / (2 * 1.1 * 1.1))
        q = (g.rating - 70) / 30
        score = max(0, min(1, (w_g * gm + (1 - w_g) * pm) * 0.9 + q * 0.1))
        best = max(g.genres, key=lambda x: P["aff"].get(x, 0))
        rows.append((score, gm, pm, best, g))
    return sorted(rows, key=lambda r: -r[0])


def radar(entries):
    n, R, cx, cy = len(entries), 120, 170, 150

    def pt(i, r):
        a = -math.pi / 2 + i * 2 * math.pi / n
        return cx + math.cos(a) * r, cy + math.sin(a) * r

    web = "".join(
        f'<polygon points="{" ".join("%.1f,%.1f" % pt(i, R * f) for i in range(n))}" fill="none" stroke="#2a3b4d"/>'
        for f in (.25, .5, .75, 1))
    axes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{pt(i, R)[0]:.1f}" y2="{pt(i, R)[1]:.1f}" stroke="#2a3b4d"/>' for i in range(n))
    mx = entries[0][1]
    poly = " ".join("%.1f,%.1f" % pt(i, R * max(.08, e[1] / mx)) for i, e in enumerate(entries))
    labs = ""
    for i, e in enumerate(entries):
        x, y = pt(i, R + 18)
        anchor = "end" if x < cx - 5 else "start" if x > cx + 5 else "middle"
        labs += f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle">{e[0]}</text>'
    return (f'<svg viewBox="0 0 340 300" width="100%">{web}{axes}<polygon points="{poly}" '
            f'fill="rgba(102,192,244,.35)" stroke="#66c0f4" stroke-width="2"/>{labs}</svg>')


def bar(pct):
    return f'<div class="bar"><i style="width:{pct:.0f}%"></i></div>'


# ---------- page ----------
st.markdown(CSS, unsafe_allow_html=True)
html("""<h1 class="tf">TASTE<span>FORGE</span></h1>
<div class="sub">Pick games you've played, and the app builds your Player Profile from genre and price habits,
lets you forge your own custom categories, then recommends what to play next.</div>""")

if not API_URL:
    st.error("Set MODAL_API_URL (your deployed Modal endpoint URL) in .streamlit/secrets.toml.")
    st.stop()

G = load_catalog()
ss = st.session_state
ss.setdefault("picked", [])
ss.setdefault("cats", [{"name": "Cozy Grind", "genres": ["Cozy", "Farming Sim", "Simulation"]}])


def load_demo():
    picks, hours = [], {}
    for name, h in DEMO:
        m = G[G.name.str.lower() == name.lower()]
        if len(m):
            picks.append(m.iloc[0].label)
            hours[m.iloc[0].label] = h
    ss.picked = picks
    for lab, h in hours.items():
        ss[f"h_{lab}"] = h


with st.sidebar:
    st.markdown("##### 1 · YOUR PLAYED GAMES")
    st.multiselect("Search games", G.label.tolist(), key="picked", label_visibility="collapsed",
                   placeholder="Search games...")
    c1, c2 = st.columns([3, 1])
    c1.button("Load demo profile", type="primary", on_click=load_demo, use_container_width=True)
    c2.button("Clear", on_click=lambda: ss.update(picked=[]), use_container_width=True)
    played = {}
    for lab in ss.picked:
        gid = int(G.index[G.label == lab][0])
        ss.setdefault(f"h_{lab}", 20)
        h = st.number_input(lab.rsplit("  (", 1)[0], min_value=1, max_value=9999, key=f"h_{lab}")
        played[gid] = h
    st.caption("Tick a game and enter your hours. In the full app this list would come from the Steam Web API "
               "(GetOwnedGames) after a Steam login.")

P = profile(G, played)
html(f'<div class="sub" style="text-align:right">Live data · {len(G):,} well-reviewed Steam games from Supabase</div>')
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
        <div><b style="font-size:15px">{arche}</b><span>your archetype</span></div></div>""")
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

# ----- Recommendations -----
with tabs[1]:
    if not played:
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
        for score, gm, pm, best, g in R:
            chips = "".join(f'<span class="chip {"sel" if x in P["aff"] else ""}">{x}</span>' for x in g.genres)
            html(f"""<div class="rec"><div class="match" style="background:hsl({round(score * 120)},80%,60%)">{round(score * 100)}%</div>
            <div><h3>{g['name']}</h3><div>{chips}</div>
            <div class="why">Genre fit {round(gm * 100)}% (you play lots of <b>{best}</b>) · price fit {round(pm * 100)}% · {g.rating:.0f}% positive</div></div>
            <div class="price">{fmt(g.price)}</div></div>""")

# ----- Custom Categories -----
with tabs[2]:
    all_genres = sorted({x for gs in G.genres for x in gs})
    a, b = st.columns(2)
    with a:
        st.markdown("##### FORGE A CATEGORY")
        name = st.text_input("Name it", placeholder="e.g. 'Rage Quit Club'")
        picks = st.multiselect("Genres / tags", all_genres)
        if st.button("Create category", type="primary"):
            if name.strip() and picks:
                ss.cats.append({"name": name.strip(), "genres": picks})
                st.rerun()
            else:
                st.warning("Give it a name and pick at least one genre.")
        html('<div class="note">Steam\'s built-in tags are broad. Combine genres into your own buckets, then track how much of '
             'your playtime each one owns and use them as a recommendation filter.</div>')
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
            html(f'<div class="catcard"><h3>{c["name"]}</h3><div>{chips}</div><div class="why" style="margin:6px 0">{txt}</div>'
                 f'{bar(share)}<div class="why" style="margin-top:8px">Top unplayed: {tu}</div></div>')
            if st.button("Delete", key=f"del{i}"):
                ss.cats.pop(i)
                st.rerun()

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
