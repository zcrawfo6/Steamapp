"""TasteForge: Streamlit dashboard over the Steam games table in Supabase, read directly via the Supabase REST API.
Run: streamlit run app.py   (SUPABASE_URL and SUPABASE_KEY in .streamlit/secrets.toml or the environment)
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

def _setting(name: str) -> str:
    try:
        return str(st.secrets[name])
    except Exception:
        return os.environ.get(name, "")


SUPABASE_URL = _setting("SUPABASE_URL").rstrip("/")
SUPABASE_KEY = _setting("SUPABASE_KEY")  # publishable (anon) key only; never put a secret/service key here
STEAM_API_KEY = _setting("STEAM_API_KEY")  # optional: lets "Sign in with Steam" also import your owned games
APP_URL = (_setting("APP_URL") or "http://localhost:8501").rstrip("/")  # where Steam sends you back after login
STEAM_OPENID = "https://steamcommunity.com/openid/login"
OPENID_NS = "http://specs.openid.net/auth/2.0"

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
/* the sidebar ignores the page theme: it redefines every theme variable with fixed Steam-style values */
section[data-testid=stSidebar]{--bg:#171a21;--panel:#1b2838;--panel2:#2a475e;--line:#3d5a73;--text:#c7d5e0;--mute:#8f98a0;
--accent:#66c0f4;--accent2:#a4d7f5;--disp:'DM Sans',system-ui,sans-serif;--body:'DM Sans',system-ui,sans-serif;
background:#171a21!important;backdrop-filter:none!important;border-right:1px solid #2a3547!important;color:var(--text)}
section[data-testid=stSidebar] :is(p,label,li,small,h1,h2,h3,h4,h5,h6,[data-testid=stCaptionContainer]){color:var(--text)}
section[data-testid=stSidebar] [data-testid=stCaptionContainer]{color:var(--mute)}
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
.price{font-family:var(--disp);font-weight:700;font-size:18px;color:var(--accent2);white-space:nowrap;text-align:right}
.steam-link{display:block;margin-top:4px;font-family:var(--body);font-weight:600;font-size:12px;letter-spacing:.04em;color:var(--mute);text-decoration:none}
.steam-link:hover{color:var(--accent2);text-decoration:underline}
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
@keyframes radin{from{transform:scale(.1);opacity:0}to{transform:scale(1);opacity:1}}
.rmq{container-type:inline-size;overflow:hidden;white-space:nowrap;height:28px;line-height:28px;
-webkit-mask-image:linear-gradient(90deg,transparent,#000 10px,#000 calc(100% - 10px),transparent);
mask-image:linear-gradient(90deg,transparent,#000 10px,#000 calc(100% - 10px),transparent)}
.rmq>span{display:inline-block;padding:0 10px;animation:rmqa 9s ease-in-out 1 both}
@keyframes rmqa{0%,20%{transform:translateX(0)}50%,62%{transform:translateX(min(0px,calc(100cqw - 100%)))}92%,100%{transform:translateX(0)}}
@keyframes rmqb{0%,20%{transform:translateX(0)}50%,62%{transform:translateX(min(0px,calc(100cqw - 100%)))}92%,100%{transform:translateX(0)}}
@media (prefers-reduced-motion:reduce){.rmq>span{animation:none;max-width:100%;overflow:hidden;text-overflow:ellipsis;vertical-align:top}}
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


CATALOG_SIZE = 3000   # most-reviewed games pulled from Supabase
MIN_REVIEWS = 1000    # same "well-reviewed" cut-off as the Modal version
WINDOW = 100_000      # app_id range per request; the anon role has a ~3s statement timeout, and sorting by
                      # a non-indexed column (user_reviews) times out, so we scan the primary key in windows
                      # in parallel and rank in pandas instead.


def _get(params: dict, tries: int = 3) -> list:
    import time
    for i in range(tries):  # retry transient 5xx / statement timeouts
        r = requests.get(f"{SUPABASE_URL}/rest/v1/games", headers={"apikey": SUPABASE_KEY}, params=params, timeout=60)
        if r.status_code < 500:
            r.raise_for_status()
            return r.json()
        time.sleep(0.5 * (i + 1))
    r.raise_for_status()


def _id_window(lo: int, size: int = WINDOW) -> list:
    """Light query (ids + review counts only) over one app_id range, so it stays under the timeout.
    If a range still times out, split it in half and retry each half."""
    try:
        rows = _get({"select": "app_id,user_reviews", "user_reviews": f"gte.{MIN_REVIEWS}",
                     "positive_ratio": "not.is.null", "and": f"(app_id.gte.{lo},app_id.lt.{lo + size})",
                     "order": "app_id.asc", "limit": 1000}, tries=2)
    except requests.HTTPError:
        if size <= 5000:
            raise
        half = size // 2
        return _id_window(lo, half) + _id_window(lo + half, size - half)
    if len(rows) >= 1000 and size > 5000:  # hit the row cap: split so nothing is silently cut off
        half = size // 2
        return _id_window(lo, half) + _id_window(lo + half, size - half)
    return rows


def _details(ids: list) -> list:
    return _get({"select": "app_id,title,price_regular,positive_ratio,user_reviews,tags,explicit,content_level",
                 "app_id": f"in.({','.join(map(str, ids))})", "limit": len(ids)})


@st.cache_data(ttl=3600)
def load_catalog() -> pd.DataFrame:
    """Pull the catalog straight from the Supabase REST API (public.games) and map it to the columns the app uses."""
    from concurrent.futures import ThreadPoolExecutor
    max_id = _get({"select": "app_id", "order": "app_id.desc", "limit": 1})[0]["app_id"]
    with ThreadPoolExecutor(max_workers=4) as ex:
        # step 1: find the most-reviewed games (scan the primary key in windows, rank in pandas)
        ranked = pd.DataFrame([r for b in ex.map(_id_window, range(0, max_id + 1, WINDOW)) for r in b])
        ids = ranked.sort_values(["user_reviews", "app_id"], ascending=[False, True]).head(CATALOG_SIZE).app_id.tolist()
        # step 2: fetch the full rows for just those ids, in small chunks
        chunks = [ids[i:i + 150] for i in range(0, len(ids), 150)]
        df = pd.DataFrame([r for b in ex.map(_details, chunks) for r in b])
    df = df.sort_values(["user_reviews", "app_id"], ascending=[False, True])
    # tags arrive as an array (or a delimited string); keep the first 5 as the game's "genres"
    df["genres"] = df["tags"].apply(
        lambda t: [x.strip() for x in (t if isinstance(t, list) else str(t or "").split(",")) if x.strip()][:5])
    df = df[df.genres.str.len() > 0]
    df["name"] = df["title"]
    df["price"] = df["price_regular"].fillna(0).astype(float)
    df["rating"] = df["positive_ratio"].astype(float)
    df["owners"] = df["user_reviews"].astype(float)  # no owners column in this dataset; review count is the popularity proxy
    df["label"] = df["name"] + "  (" + df["app_id"].astype(str) + ")"
    # 18+ = flagged explicit or sexual themes in the data ('mature' is mostly violence, so it stays visible)
    df["adult"] = df["explicit"].fillna(False).astype(bool) | df["content_level"].isin(["explicit", "sexual_themes"])
    return df.drop(columns=["tags"]).reset_index(drop=True)


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


def recommend(G, P, played, w_genre, budget):
    pool = G[~G.index.isin(played) & (G.price <= budget)]
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


def radar(entries, flip=0):
    """Genre radar: entries = [(genre, share of hours), ...] sorted high to low (padded with '—' placeholders).
    `flip` (0/1) picks which of two identical marquee keyframes the labels use. Streamlit reuses the page's elements
    when the radar redraws, so a CSS animation would only ever play once per page load; changing the animation
    name each time the data/theme changes makes the browser restart the scroll."""
    from html import escape as esc
    n, R, cx, cy, W, H = len(entries), 135, 300, 218, 600, 440
    ang = lambda i: -math.pi / 2 + i * 2 * math.pi / n
    pt = lambda i, r: (cx + math.cos(ang(i)) * r, cy + math.sin(ang(i)) * r)
    ring = lambda f: " ".join("%.1f,%.1f" % pt(i, R * f) for i in range(n))

    # background web: banded rings (outer first so inner bands sit on top), spokes and a centre dot
    web = ""
    for k, f in enumerate((1, .8, .6, .4, .2)):
        web += (f'<polygon points="{ring(f)}" style="fill:var(--panel2);fill-opacity:{.45 if k % 2 == 0 else .15};'
                f'stroke:var(--line);stroke-width:{1.6 if f == 1 else 1};'
                f'{"" if f == 1 else "stroke-dasharray:2 6;"}stroke-opacity:.9"/>')
    web += "".join(f'<line x1="{cx}" y1="{cy}" x2="{pt(i, R)[0]:.1f}" y2="{pt(i, R)[1]:.1f}" '
                   f'style="stroke:var(--line);stroke-width:1"/>' for i in range(n))

    # the player's shape
    mx = max(e[1] for e in entries) or 1
    spots = [pt(i, R * max(.07, e[1] / mx)) for i, e in enumerate(entries)]
    poly = " ".join("%.1f,%.1f" % p for p in spots)
    dots = ""
    for i, ((x, y), e) in enumerate(zip(spots, entries)):
        if e[0] == "—":
            continue
        big = i == 0
        dots += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{9 if big else 6.5}" style="fill:var(--accent2);fill-opacity:.25"/>'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.6 if big else 3.4}" style="fill:var(--accent2);stroke:var(--bg,#000);'
                 f'stroke-width:1.5"><title>{esc(str(e[0]))}: {round(e[1] * 100)}% of your hours</title></circle>')

    # labels: genre name over its share of hours, pushed away from the web, top/bottom ones nudged clear
    labs = ""
    for i, e in enumerate(entries):
        if e[0] == "—":
            continue
        x, y = pt(i, R + 20)
        anchor = "end" if x < cx - 8 else "start" if x > cx + 8 else "middle"
        y += -14 if y < cy - R * .85 else 4 if y > cy + R * .85 else -6
        top = i == 0
        # the name gets the room between its anchor point and the edge of the graphic; if it is wider than that,
        # the .rmq marquee (CSS only) scrolls it right-to-left to reveal the rest, otherwise it stays put
        room = (x - 8) if anchor == "end" else (W - x - 8) if anchor == "start" else 2 * min(x, W - x) - 16
        pad = 10  # soft-fade zone at each end of the window; the box grows by this much so resting text doesn't move
        fx = x - room if anchor == "end" else x - pad if anchor == "start" else x - room / 2 - pad
        room = room + pad if anchor != "middle" else room + 2 * pad
        align = {"end": "right", "start": "left", "middle": "center"}[anchor]
        labs += (f'<foreignObject x="{fx:.1f}" y="{y - 20:.1f}" width="{room:.1f}" height="28">'
                 f'<div class="rmq" title="{esc(str(e[0]))}" style="text-align:{align};font-family:var(--disp);font-size:17px;'
                 f'letter-spacing:.07em;text-transform:uppercase;font-weight:{800 if top else 600};'
                 f'color:{"var(--accent2)" if top else "var(--text)"}"><span style="animation-name:rmq{"ab"[flip]}">'
                 f'{esc(str(e[0]))}</span></div></foreignObject>'
                 f'<text x="{x:.1f}" y="{y + 17:.1f}" text-anchor="{anchor}" style="font-family:var(--body);font-size:13px;'
                 f'fill:var(--mute)">{round(e[1] * 100)}% of hours</text>')

    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Genre radar">'
            '<defs><linearGradient id="rdg" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" style="stop-color:var(--accent);stop-opacity:.75"/>'
            '<stop offset="1" style="stop-color:var(--accent2);stop-opacity:.25"/></linearGradient>'
            '<linearGradient id="rds" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--accent)"/>'
            '<stop offset="1" style="stop-color:var(--accent2)"/></linearGradient>'
            '<filter id="rdf" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
            f'{web}<g style="transform-box:view-box;transform-origin:{cx}px {cy}px;'
            f'animation:radin .9s cubic-bezier(.2,.8,.2,1) both">'
            f'<polygon points="{poly}" style="fill:url(#rdg);stroke:url(#rds);stroke-width:2.6;stroke-linejoin:round;'
            f'filter:url(#rdf)"/>{dots}</g>{labs}'
            f'<circle cx="{cx}" cy="{cy}" r="2.5" style="fill:var(--mute)"/></svg>')


def bar(pct):
    return f'<div class="bar"><i style="width:{pct:.0f}%"></i></div>'


# ---------- page ----------
if not (SUPABASE_URL and SUPABASE_KEY):
    html(CSS + T.theme_css(T.DEFAULT) + T.fx_html(T.DEFAULT))
    st.error("Set SUPABASE_URL and SUPABASE_KEY (publishable key) in .streamlit/secrets.toml or the environment.")
    st.stop()

with st.spinner("Heating the forge..."):
    G_ALL = load_catalog()
G = G_ALL  # narrowed below if the 18+ switch is off
ss = st.session_state
ss.setdefault("picked", [])
ss.setdefault("adult_ok", False)  # 18+ content is hidden until the sidebar switch is turned on
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


# ---------- Steam sign-in (OpenID 2.0) + library import ----------
def steam_login_url() -> str:
    from urllib.parse import urlencode
    return STEAM_OPENID + "?" + urlencode({
        "openid.ns": OPENID_NS, "openid.mode": "checkid_setup", "openid.return_to": APP_URL, "openid.realm": APP_URL,
        "openid.identity": f"{OPENID_NS}/identifier_select", "openid.claimed_id": f"{OPENID_NS}/identifier_select"})


def verify_steam_login(params: dict):
    """Ask Steam to confirm the signed response is genuine; returns the 17-digit SteamID64, or None."""
    claimed = re.fullmatch(r"https://steamcommunity\.com/openid/id/(\d{17})", params.get("openid.claimed_id", ""))
    if not claimed or params.get("openid.mode") != "id_res":
        return None
    try:
        r = requests.post(STEAM_OPENID, data={**params, "openid.mode": "check_authentication"}, timeout=15)
    except requests.RequestException:
        return None
    return claimed.group(1) if re.search(r"^is_valid:true\s*$", r.text, re.M) else None


@st.cache_data(ttl=600, show_spinner=False)
def steam_library(steam_id: str, key: str) -> dict:
    """Owned games with playtime via the Steam Web API. Errors are swallowed on purpose: the URL carries the key."""
    try:
        g = requests.get("https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/", timeout=20,
                         params={"key": key, "steamid": steam_id, "include_played_free_games": 1, "format": "json"})
        p = requests.get("https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/", timeout=20,
                         params={"key": key, "steamids": steam_id})
        if g.status_code != 200:
            return {"error": "Steam rejected the request (check STEAM_API_KEY)."}
        games = g.json().get("response", {}).get("games", [])
        who = (p.json().get("response", {}).get("players") or [{}])[0].get("personaname", "")
        return {"games": {x["appid"]: x.get("playtime_forever", 0) for x in games}, "name": who}
    except Exception:
        return {"error": "Could not reach the Steam Web API."}


def import_steam_library():
    lib = steam_library(ss.steam_id, STEAM_API_KEY)
    owned = lib.get("games", {})
    mine = G[G.app_id.isin(owned)].copy()
    mine["hrs"] = mine.app_id.map(lambda a: max(1, min(9999, round(owned[a] / 60))))
    mine = mine[mine.app_id.map(owned) > 0].sort_values("hrs", ascending=False).head(25)  # played games only
    ss.steam_note = (f"Imported {len(mine)} played games ({len(owned)} owned; only games in this catalog can be matched)."
                     if len(mine) else "No played games matched this catalog. Is your Steam game list set to public?")
    for lab, h, gen in zip(mine.label, mine.hrs, mine.genres):
        ss[f"h_{lab}"] = int(h)
        have = modes_for(gen)
        for mode in MODES:
            ss[f"m_{lab}_{mode}"] = mode in have
            ss[f"s_{lab}_{mode}"] = 50
    ss.picked = mine.label.tolist()


def steam_sign_out():
    ss.pop("steam_id", None)
    ss.pop("steam_note", None)


# Steam redirects back here with openid.* in the URL: verify it once, then clean the URL
if "openid.mode" in st.query_params and not ss.get("steam_id"):
    sid = verify_steam_login(dict(st.query_params))
    if sid:
        ss.steam_id = sid
    else:
        ss.steam_note = "Steam sign-in could not be verified. Please try again."
    st.query_params.clear()

with st.sidebar:
    st.markdown("##### 1 · YOUR PLAYED GAMES")
    if ss.get("steam_id"):
        who = steam_library(ss.steam_id, STEAM_API_KEY).get("name", "") if STEAM_API_KEY else ""
        st.success(f"Signed in to Steam as **{who or ss.steam_id}**")
        if STEAM_API_KEY:
            st.button("Import my Steam library", on_click=import_steam_library, use_container_width=True)
        else:
            st.caption("Signed in, but importing games needs a Steam Web API key. Add STEAM_API_KEY to "
                       ".streamlit/secrets.toml (free at steamcommunity.com/dev/apikey).")
        st.button("Sign out of Steam", on_click=steam_sign_out, use_container_width=True)
    else:
        # small Steam-style mark (circle, linked rings): drawn inline so it takes the text colour and needs no image file
        logo = ('<svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true" style="flex:none" fill="none" '
                'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="12" r="10.6"/>'
                '<circle cx="15.4" cy="9.4" r="3.3"/><circle cx="8.6" cy="15.6" r="2.1" fill="currentColor" stroke="none"/>'
                '<path d="M10.2 14.5 13 11.6M7 14.9 3.2 13.3"/></svg>')
        html(f'<a href="{steam_login_url()}" target="_self" style="display:flex;align-items:center;justify-content:center;'
             f'gap:9px;padding:9px 12px;border-radius:8px;border:1px solid var(--line);background:var(--panel2);'
             f'color:var(--text);text-decoration:none;font-weight:700;letter-spacing:.04em">{logo}<span>Sign in with Steam</span></a>')
    if ss.get("steam_note"):
        st.caption(ss.steam_note)
    st.toggle("Show 18+ content", key="adult_ok",
              help="Off (default) hides games the data flags as explicit or sexual-themed, everywhere in the app: "
                   "search, imports, recommendations and stats.")
    if not ss.adult_ok:
        G = G_ALL[~G_ALL.adult].reset_index(drop=True)
        keep = set(G.label)
        ss.picked = [lab for lab in ss.picked if lab in keep]  # drop any 18+ games already picked
        if ss.view and ss.view not in set(G.app_id):
            close_game()
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
html(CSS + T.theme_css(world) + T.fx_html(world))

html("""<div class="hero"><div><div class="logo"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2c.6 3.6 4.6 5.4 4.6 10.2A4.6 4.6 0 0 1 12 17a4.6 4.6 0 0 1-4.6-4.8c0-1.9.9-3.1 1.9-4 .1 1.7.9 2.6 1.9 2.8C10.9 8 11.2 5 12 2z"/><rect x="5" y="19" width="14" height="3" rx="1" fill="currentColor" opacity=".7"/></svg>
<h1 class="tf">TASTE<span>FORGE</span></h1></div>
<div class="sub">Pick games you've played and the app builds your Player Profile from genre, price and play-style habits,
then recommends what to play next.</div></div></div>""")
html(f'<div class="sub" style="text-align:right;margin:4px 0 6px">Live data · {len(G):,} well-reviewed Steam games from Supabase</div>')

tabs = st.tabs(["Player Profile", "Recommendations", "Genre Success"])
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
            sig = (tuple((g, round(v, 4)) for g, v in rad), world)  # replay the label scroll when data or theme changes
            if ss.get("rad_sig") != sig:
                ss.rad_sig, ss.rad_n = sig, ss.get("rad_n", 0) + 1
            html(f'<div class="card"><h2>Genre radar</h2>{radar(rad, ss.rad_n % 2)}</div>')
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
        R = recommend(G, P, played, w, 999 if budget >= 60 else budget)[:8]
        if not R:
            html('<div class="empty">Nothing matches that budget. Raise it to see more games.</div>')
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
            <div class="price">{fmt(g.price)}<a class="steam-link" href="https://store.steampowered.com/app/{int(g.app_id)}"
            target="_blank" rel="noopener noreferrer">View on Steam ↗</a></div></div>""")
            st.button(f"See full stats for {g['name']}  →", key=f"view_{int(g.app_id)}", use_container_width=True,
                      on_click=open_game, args=(int(g.app_id), dict(score=score, gm=gm, pm=pm, mf=mf, best=best)))

# ----- Genre Success -----
with tabs[2]:
    # computed from the loaded catalog (the Modal version ran this as a SQL group-by)
    ex = G.explode("genres").rename(columns={"genres": "genre"})
    gs = (ex.groupby("genre").agg(n=("app_id", "count"), rating=("rating", "mean"), price=("price", "mean"),
                                  owners=("owners", "sum")).reset_index())
    gs = gs[gs.n >= 30]
    gs["idx"] = (gs.rating - 70).clip(lower=0) * gs.owners.apply(lambda o: math.log10(1 + o)) * 10
    gs = gs.sort_values("idx", ascending=False)
    mx = gs.idx.max() or 1
    rows = "".join(
        f"<tr><td>{r.genre}</td><td>{int(r.n):,}</td><td>{r.rating:.1f}%</td><td>{fmt(r.price)}</td><td>{bar(r.idx / mx * 100)}</td></tr>"
        for r in gs.itertuples())
    html(f"""<div class="card"><h2>Research question: which genres actually succeed, and does price explain it?</h2>
    <div class="why" style="margin-bottom:10px">Success Index = avg. positive-review % (above a 70% baseline) × log of combined owners,
    computed over the most-reviewed games loaded from Supabase (owners = review count in this dataset).</div>
    <table class="t"><tr><th>Genre</th><th>Games</th><th>Avg rating</th><th>Avg price</th><th style="width:38%">Success index</th></tr>{rows}</table></div>""")
