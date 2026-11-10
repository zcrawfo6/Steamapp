"""Full Steam catalog from the shared Supabase project (table `games`, ~111k active Steam games).

Read through Supabase's REST API (PostgREST) with GAMES_SUPABASE_URL + GAMES_SUPABASE_KEY from
.streamlit/secrets.toml. The API returns at most 1,000 rows per request and filtering/counting on unindexed
columns times out, so the table is read in app_id ranges (primary key, indexed) on parallel threads and
filtered here instead.

Returns the same columns the app's old Modal "catalog" query did: app_id, name, price, rating, tags, genres, label
(plus reviews and release_date).
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import time

import pandas as pd
import requests

COLS = "app_id,title,release_date,item_type,tags,positive_ratio,user_reviews,price_regular,explicit"
PAGE = 1000  # PostgREST's max rows per request on this project
SLICES = 32  # app_id ranges read in parallel
WORKERS = 8
SPARSE_TAGS = 6  # games with fewer tags than this get their tag list from games_slim.csv when it has more


def _headers(key: str) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _get(s: requests.Session, url: str, key: str, params) -> list[dict]:
    """GET with a few retries: the API occasionally answers 500/503 when a query hits its statement timeout."""
    for attempt in range(4):
        r = s.get(f"{url}/rest/v1/games", params=params, headers=_headers(key), timeout=60)
        if r.status_code < 500 or attempt == 3:
            r.raise_for_status()
            return r.json()
        time.sleep(1 + attempt * 2)


def _read_range(url: str, key: str, lo: int, hi: int) -> list[dict]:
    """Every row with lo <= app_id < hi, paging by primary key. (Filtering on user_reviews server-side times
    out: that column has no index. Rows are filtered in build_catalog instead.)"""
    rows, last = [], lo - 1
    with requests.Session() as s:
        while True:
            params = [("select", COLS), ("app_id", f"gt.{last}"), ("app_id", f"lt.{hi}"),
                      ("order", "app_id"), ("limit", PAGE)]
            batch = _get(s, url, key, params)
            rows += batch
            if len(batch) < PAGE:
                return rows
            last = batch[-1]["app_id"]


def fetch_games(url: str, key: str) -> pd.DataFrame:
    """All raw rows of the `games` table (the catalog columns only)."""
    url = url.strip().rstrip("/")
    key = key.strip()
    with requests.Session() as s:
        top = _get(s, url, key, {"select": "app_id", "order": "app_id.desc", "limit": 1})[0]["app_id"] + 1
    step = -(-top // SLICES)
    with ThreadPoolExecutor(WORKERS) as pool:
        parts = pool.map(lambda i: _read_range(url, key, i * step, min((i + 1) * step, top)),
                         range(SLICES))
        rows = [row for part in parts for row in part]
    return pd.DataFrame(rows, columns=COLS.split(","))


def _canonical_tags(tag_lists: pd.Series) -> dict:
    """lowercased tag -> its most common spelling, so 'Free to Play' and 'Free To Play' become one tag."""
    counts = Counter(t.strip() for ts in tag_lists for t in ts if t and t.strip())
    best = {}
    for t, n in counts.most_common():
        best.setdefault(t.lower(), t)
    return best


def build_catalog(raw: pd.DataFrame, min_reviews: int = 10, include_explicit: bool = False,
                  extra_tags: dict | None = None) -> pd.DataFrame:
    """Clean raw rows into the app's catalog shape.

    extra_tags: app_id -> fuller tag list (from games_slim.csv) used where this table's tags are sparse.
    """
    d = raw[(raw.item_type == "game") & raw.title.notna() & raw.positive_ratio.notna()
            & (raw.user_reviews >= min_reviews)].copy()
    if not include_explicit:
        d = d[~d.explicit.fillna(False).astype(bool)]
    d["tags"] = d.tags.apply(lambda ts: [t for t in ts if t] if isinstance(ts, list) else [])
    if extra_tags:
        d["tags"] = [extra_tags[a] if len(ts) < SPARSE_TAGS and len(extra_tags.get(a, ())) > len(ts) else ts
                     for a, ts in zip(d.app_id, d.tags)]
    canon = _canonical_tags(d.tags)
    d["genres"] = d.tags.apply(lambda ts: list(dict.fromkeys(canon[t.strip().lower()] for t in ts if t.strip())))
    d = d[d.genres.str.len() > 0]
    out = pd.DataFrame({
        "app_id": d.app_id.astype(int),
        "name": d.title.str.strip(),
        "price": d.price_regular.astype(float).fillna(0.0),
        "rating": d.positive_ratio.astype(float),
        "reviews": d.user_reviews.astype(int),
        "release_date": d.release_date,
        "genres": d.genres,
    })
    out["tags"] = out.genres.str.join(",")
    out["label"] = out["name"] + "  (" + out["app_id"].astype(str) + ")"
    # most-reviewed first, like the old catalog, so the search box lists well-known games first
    return out.drop_duplicates("app_id").sort_values("reviews", ascending=False).reset_index(drop=True)
