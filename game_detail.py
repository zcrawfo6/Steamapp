"""Game detail view for TasteForge: one game's stats, read straight from the cleaned dataset (games_slim.csv).

The cleaned data has review *counts* (positive / negative) but no review text, so the review section shows the
rating, its Steam-style label and the positive/negative split.
"""
import os
import re
from html import escape

import pandas as pd
import streamlit as st

import themes as T

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "games_slim.csv")
MIN_REVIEWS = 50  # same cut-off as the Genre Success tab, so averages are not dragged down by unreviewed games

# label, column, formatter, treat 0 as "no data" when averaging
METRICS = [
    ("Price", "price", lambda v: "Free" if v == 0 else f"${v:.2f}", False),
    ("Positive reviews", "rating", lambda v: f"{v:.1f}%", False),
    ("Total reviews", "reviews", lambda v: num(v), False),
    ("Estimated owners", "owners", lambda v: num(v), False),
    ("Avg. playtime", "hours", lambda v: f"{v:.1f}h", True),
    ("Median playtime", "median_hours", lambda v: f"{v:.1f}h", True),
    ("Peak concurrent players", "peak_ccu", lambda v: num(v), True),
    ("Achievements", "achievements", lambda v: num(v), True),
]

CSS = ("<style>.split{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--panel2)}"
       ".split i{display:block;height:100%}.split .pos{background:var(--accent2)}.split .neg{background:#c0392b}"
       ".b2{margin-top:4px;height:5px}.b2 i{background:var(--mute);box-shadow:none}"
       ".up{color:var(--accent2)}.down{color:var(--mute)}"
       ".gd-big{font-family:var(--disp);font-size:30px;color:var(--accent2);line-height:1.1}"
       ".fact{display:inline-block;margin:3px 8px 3px 0;font-size:13px;color:var(--mute)}.fact b{color:var(--text)}"
       ".gd-pct{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}"
       ".gd-pct div{flex:1;min-width:150px;background:var(--panel2);border-radius:10px;padding:10px 12px;font-size:13px}"
       ".gd-pct b{display:block;font-family:var(--disp);font-size:22px;color:var(--accent2)}</style>")


def num(v: float) -> str:
    v = float(v)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= div:
            return f"{v / div:.1f}{suf}".replace(".0", "")
    return f"{v:,.0f}"


def _html(s: str):
    st.markdown(re.sub(r"(?m)^\s+", "", s), unsafe_allow_html=True)


def _bar(pct: float, cls: str = "") -> str:
    return f'<div class="bar {cls}"><i style="width:{max(0, min(100, pct)):.0f}%"></i></div>'


@st.cache_resource
def load_full() -> pd.DataFrame:
    d = pd.read_csv(CSV).drop_duplicates("app_id")
    d["reviews"] = d.positive + d.negative
    d["rating"] = (100 * d.positive / d.reviews.where(d.reviews > 0)).round(1)
    d["owners"] = (d.owners_min + d.owners_max) / 2
    d["hours"] = d.avg_playtime_forever / 60  # the dataset stores minutes
    d["median_hours"] = d.median_playtime_forever / 60
    return d.set_index("app_id", drop=False)


@st.cache_resource
def _reviewed() -> pd.DataFrame:
    d = load_full()
    return d[d.reviews >= MIN_REVIEWS]


def _text(v) -> str:
    return v.strip() if isinstance(v, str) and v.strip() and v != "nan" else ""


def has(app_id) -> bool:
    return app_id in load_full().index


def name_of(app_id) -> str:
    return _text(load_full().loc[app_id, "name"]) or "Unknown game"


def tags_of(app_id) -> list:
    """Full tag list from the cleaned data (falls back to genres)."""
    if not has(app_id):
        return []
    r = load_full().loc[app_id]
    return [t.strip() for t in (_text(r.tags) or _text(r.genres)).split(",") if t.strip()]


def review_label(rating: float, reviews: int) -> str:
    if reviews < 10:
        return "Not enough reviews"
    for floor, label in ((95, "Overwhelmingly Positive"), (80, "Very Positive"), (70, "Mostly Positive"),
                         (40, "Mixed"), (20, "Mostly Negative")):
        if rating >= floor:
            return label if not (floor == 95 and reviews < 500) else "Very Positive"
    return "Overwhelmingly Negative" if reviews >= 500 else "Very Negative"


def _avg(df: pd.DataFrame, col: str, skip_zero: bool):
    s = df[col].dropna()
    s = s[s > 0] if skip_zero else s
    return float(s.mean()) if len(s) else None


def _pct_below(df: pd.DataFrame, col: str, v: float, skip_zero: bool):
    s = df[col].dropna()
    s = s[s > 0] if skip_zero else s
    return float((s < v).mean() * 100) if len(s) else None


def _delta(v: float, avg) -> str:
    if not avg:
        return '<span class="down">–</span>'
    r = v / avg
    txt = f"{r:.1f}×" if r >= 3 else f"{(r - 1) * 100:+.0f}%"
    return f'<span class="{"up" if r >= 1 else "down"}">{txt}</span>'


def show(app_id: int, why: dict | None, on_back):
    """Render the detail view in place. `why` is the recommender's breakdown for this game (or None)."""
    st.button("← Back to recommendations", on_click=on_back, key="gd_back")
    if not has(app_id):
        st.warning("That game is not in the cleaned dataset.")
        return
    g = load_full().loc[app_id]
    tags = tags_of(app_id)
    world = T.theme_for(tags)
    genre = _text(g.primary_genre)
    q = _reviewed()
    peers = q[q.primary_genre == genre] if genre else q
    pname = genre or "all"

    # ---- hero: the game's own world + the facts about it
    chips = "".join(f'<span class="chip sel">{escape(t)}</span>' for t in tags[:14]) or '<span class="why">No tags in the data</span>'
    plats = " · ".join(n for n, on in (("Windows", g.windows), ("macOS", g.mac), ("Linux", g.linux)) if on) or "n/a"
    facts = [f"<b>Developer</b> {escape(_text(g.developers) or 'n/a')}", f"<b>Publisher</b> {escape(_text(g.publishers) or 'n/a')}",
             f"<b>Released</b> {escape(_text(g.release_date) or 'n/a')}", f"<b>Platforms</b> {plats}"]
    if g.required_age:
        facts.append(f"<b>Age</b> {g.required_age}+")
    if g.metacritic_score:
        facts.append(f"<b>Metacritic</b> {g.metacritic_score}")
    if g.dlc_count:
        facts.append(f"<b>DLC</b> {g.dlc_count}")
    if g.discount:
        facts.append(f"<b>On sale</b> {g.discount}% off")
    fact_html = "".join(f'<span class="fact">{f}</span>' for f in facts)
    why_html = ""
    if why:
        why_html = (f'<div class="why" style="margin-top:10px"><b>Why it was recommended:</b> {round(why["score"] * 100)}% match · '
                    f'genre fit {round(why["gm"] * 100)}% (you play lots of <b>{escape(str(why["best"]))}</b>) · '
                    f'price fit {round(why["pm"] * 100)}% · play-style fit {round(why["mf"] * 100)}%</div>')
    _html(CSS + f'<div class="catcard" style="{T.card_vars(world)}">{T.scene_html(world, escape(name_of(app_id)), 16)}'
          f'<div class="cbody"><div>{chips}</div><div style="margin-top:8px">{fact_html}</div>{why_html}</div></div>')

    # ---- headline numbers
    price = "Free" if g.price == 0 else f"${g.price:.2f}"
    hrs = f"{g.hours:.0f}h" if g.hours > 0 else "n/a"
    _html(f"""<div class="kpi"><div><b>{g.rating:.0f}%</b><span>positive reviews</span></div>
    <div><b>{num(g.reviews)}</b><span>total reviews</span></div>
    <div><b>{num(g.owners_min)}–{num(g.owners_max)}</b><span>estimated owners</span></div>
    <div><b>{num(g.peak_ccu)}</b><span>peak concurrent players</span></div>
    <div><b>{hrs}</b><span>average playtime</span></div>
    <div><b>{price}</b><span>price</span></div></div>""" if g.reviews else
          f'<div class="kpi"><div><b>{price}</b><span>price</span></div><div><b>0</b><span>reviews yet</span></div></div>')

    a, b = st.columns(2)
    with a:
        # ---- reviews: counts only, the dataset has no review text
        tot = max(int(g.reviews), 1)
        pos = g.positive / tot * 100
        _html(f"""<div class="card"><h2>Player reviews</h2>
        <div class="gd-big">{review_label(g.rating if g.reviews else 0, int(g.reviews))}</div>
        <div class="why" style="margin:4px 0 12px">{g.rating:.1f}% of {int(g.reviews):,} reviews are positive</div>
        <div class="split"><i class="pos" style="width:{pos:.1f}%"></i><i class="neg" style="width:{100 - pos:.1f}%"></i></div>
        <div class="mh sm"><span>👍 {int(g.positive):,} positive</span><span>👎 {int(g.negative):,} negative</span></div>
        <div class="note">The cleaned dataset keeps review counts, not review text. Steam recommendations: {int(g.recommendations):,}.</div></div>"""
              if g.reviews else '<div class="card"><h2>Player reviews</h2><div class="why">No reviews in the dataset yet.</div></div>')
    with b:
        # ---- where it ranks among its genre
        rows = ""
        for label, col, skip in (("Rated higher than", "rating", False), ("More owners than", "owners", False),
                                 ("Longer playtime than", "hours", True)):
            v = g[col]
            p = _pct_below(peers, col, v, skip) if v == v and (v > 0 or not skip) else None
            rows += (f'<div><b>{p:.0f}%</b>{label} of {escape(pname)} games</div>' if p is not None
                     else f'<div><b>n/a</b>{label} (no data)</div>')
        _html(f'<div class="card"><h2>Standing in {escape(pname)}</h2><div class="gd-pct">{rows}</div>'
              f'<div class="note">Ranked against {len(peers):,} {escape(pname)} games with {MIN_REVIEWS}+ reviews.</div></div>')

    # ---- this game vs the averages
    trs = ""
    for label, col, fmt_, skip in METRICS:
        v = g[col]
        gavg, aavg = _avg(peers, col, skip), _avg(q, col, skip)
        shown = fmt_(v) if v == v and (v > 0 or not skip) else '<span class="down">n/a</span>'
        top = max(x for x in (v if v == v else 0, gavg or 0) if x is not None) or 1
        bars = _bar((v if v == v else 0) / top * 100) + (_bar((gavg or 0) / top * 100, "b2") if gavg else "")
        trs += (f"<tr><td>{label}</td><td><b>{shown}</b></td><td>{fmt_(gavg) if gavg is not None else 'n/a'}</td>"
                f"<td>{fmt_(aavg) if aavg is not None else 'n/a'}</td>"
                f"<td>{_delta(v, gavg) if v == v and (v > 0 or not skip) else ''}</td><td style='width:26%'>{bars}</td></tr>")
    _html(f"""<div class="card"><h2>This game vs. the averages</h2>
    <table class="t"><tr><th>Statistic</th><th>This game</th><th>{escape(pname)} avg.</th><th>All games avg.</th><th>vs. {escape(pname)}</th><th>Compared</th></tr>{trs}</table>
    <div class="note">Averages cover games with {MIN_REVIEWS}+ reviews in games_slim.csv ({len(q):,} games, {len(peers):,} in {escape(pname)}).
    Playtime, peak players and achievements ignore games with no data (0). In the bars, the bright one is this game and the grey one is the {escape(pname)} average.</div></div>""")
