"""EASE-safe recommender (Juan's model), adapted for TasteForge.

Source: RShea42/DTSC3602_Models @ e8f7531, Steam_EASE_Safe_Recommender/model/recommender.py. The model, the
safe re-rank and its settings are unchanged. Changes for this app:
- Steam lookups and .env reading removed (app.py / steam_import.py already do that).
- Data files are read from one folder (EASE_DATA_DIR, default ease/artifacts) instead of C:/Users/juant/...
- The "Try something new" row is not built.
- Each pick also carries its soft-fail flags and how much each of the player's games pushed it up.

Model: EASE (Steck 2019) item-to-item weights B learned from which games players played together. A player's
scores = sum of B's rows for the games they played. "Safe" re-rank of EASE's top 50:
    z(score) - a x like_quit - b x short_game - c x negative_reviews     (a, b, c in rerank_choice.json)

Files needed in the data folder (not in git; ease.npz alone is ~330 MB):
    ease.npz                 B (float16) + app_ids                    model/build_ease.py
    items.parquet            per-game playtime quantiles (q)           model/build_model.py
    games.parquet            Juan's cleaned catalog (data_clean/)      main project's cleaning scripts
    team_eval/games.parquet  shared team catalog for the flags         Supabase bucket "team-eval"
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .flags import NEG, tag_matrix

HERE = Path(__file__).resolve().parent
SAFE = json.loads((HERE / "rerank_choice.json").read_text())  # a_quit, b_short, c_negative
FILES = ("ease.npz", "items.parquet", "games.parquet", "team_eval/games.parquet")
FLAG_NAMES = {"quit": "Like games you quit", "short": "Short (median 2h or less)", "neg": "Negative Steam reviews"}

# tags that describe format or business model, not taste: not shown as a pick's tags
BROAD = {t.lower() for t in (
    "Singleplayer", "Multiplayer", "Indie", "Free to Play", "Early Access", "Great Soundtrack", "Co-op", "Online Co-Op",
    "PvP", "Massively Multiplayer", "Controller", "Moddable", "Classic", "Remake", "Remaster", "Female Protagonist",
    "Steam Achievements", "Family Friendly", "Masterpiece", "Addictive", "Replay Value", "Difficult", "Short",
    "Beautiful", "Funny", "Cute", "Colorful", "Relaxing", "Utilities", "Software")}


def missing_files(data_dir) -> list[str]:
    d = Path(data_dir)
    return [f for f in FILES if not (d / f).exists()]


def live_prices(app_ids, cc="us"):
    """Current Steam store price for each app, 50 per request. {app_id: {final, initial, discount, text}}."""
    out = {}
    for k in range(0, len(app_ids), 50):
        chunk = [str(a) for a in app_ids[k:k + 50]]
        try:
            r = requests.get("https://store.steampowered.com/api/appdetails",
                             params={"appids": ",".join(chunk), "filters": "price_overview", "cc": cc}, timeout=15).json()
        except (requests.RequestException, ValueError):
            continue
        for a in chunk:
            v = (r or {}).get(a) or {}
            if not v.get("success"):
                continue
            p = v.get("data") or {}
            po = p.get("price_overview") if isinstance(p, dict) else None
            out[int(a)] = ({"final": po["final"] / 100, "initial": po["initial"] / 100, "discount": po.get("discount_percent", 0),
                            "text": po.get("final_formatted")} if po else {"final": None, "initial": None, "discount": 0, "text": None})
    return out


class Recommender:
    def __init__(self, data_dir):
        D = Path(data_dir)
        z = np.load(D / "ease.npz")
        self.B = z["B"]                                   # float16, rows = played game, columns = candidate game
        self.app_ids = z["app_ids"]
        self.idx = {int(a): i for i, a in enumerate(self.app_ids)}
        it = pd.read_parquet(D / "items.parquet")
        self.q = {int(a): np.asarray(q) for a, q in zip(it.app_id, it.q) if q is not None}
        g = pd.read_parquet(D / "games.parquet", columns=["app_id", "title", "tags", "genres", "price_regular", "recommendable",
                                                          "header_image", "steam_positive", "steam_negative", "positive_ratio",
                                                          "user_reviews", "kaggle_price_regular", "price_source", "explicit"])
        g = g.set_index("app_id")
        self.games = g
        pos, neg = g.steam_positive.fillna(0), g.steam_negative.fillna(0)
        n = pos + neg
        self.rating = ((pos / n.where(n > 0)).fillna(g.positive_ratio / 100)).reindex(self.app_ids).to_numpy()
        self.n_reviews = n.where(n > 0, g.user_reviews).reindex(self.app_ids).fillna(0).to_numpy()
        # regular-price estimate for when the store can't be reached: Steam regular price, else the older sources
        self.est_price = g.price_regular.where(g.price_source.eq("itad_steam_regular"),
                                               g[["price_regular", "kaggle_price_regular"]].max(axis=1)).reindex(self.app_ids).to_numpy(float)
        rec = g.recommendable.reindex(self.app_ids).fillna(False).to_numpy(bool)
        # actionable picks only: on sale in the store, not adult, and not poorly rated
        self.candidate = rec & ~((self.rating < 0.65) & (self.n_reviews >= 50)) & (self.n_reviews >= 20)
        self.explicit = g.explicit.reindex(self.app_ids).fillna(False).to_numpy(bool)
        self.tags = {int(a): [x for x in (list(t) if t is not None and len(t) else list(ge) if ge is not None else [])
                              if x.lower() not in BROAD][:5] for a, t, ge in zip(g.index, g.tags, g.genres)}
        self.titles = g.title.to_dict()
        # EASE-safe flags, built exactly as the team scoring builds them
        fg = pd.read_parquet(D / "team_eval" / "games.parquet", columns=["app_id", "tags", "genres", "rating", "median_playtime_min"])
        self.T = tag_matrix(fg).tocsr()
        self.tpos = {int(a): i for i, a in enumerate(fg.app_id)}
        self.trow = np.array([self.tpos.get(int(a), -1) for a in self.app_ids])
        fl = fg.set_index("app_id").reindex(self.app_ids)
        self.flag_short = (fl.median_playtime_min <= 120).to_numpy()          # unknown median -> not flagged
        self.flag_neg = fl.rating.isin(NEG).to_numpy()

    @property
    def n_candidates(self) -> int:
        return int((self.candidate & ~self.explicit).sum())

    def knows(self, app_id) -> bool:
        return int(app_id) in self.idx

    # ---- EASE-safe: push flagged games down within EASE's top k (team_eval/rerank.py, same rule)
    def safe_rerank(self, order, s, library, k=50):
        """Returns (new order, {candidate column: set of flag names})."""
        head = list(order[:k])
        flags = {}
        if len(head) < 2:
            return list(order), flags
        sc = s[head].astype(np.float64)
        z = (sc - sc.mean()) / (sc.std(ddof=1) + 1e-9)
        played = [(self.tpos[a], pt) for a, pt in library if pt > 0 and a in self.tpos]
        quit = np.zeros(len(head), bool)
        short_ix = [i for i, pt in played if pt < 120]
        kept_ix = [i for i, pt in played if pt >= 120]
        if short_ix and kept_ix:                   # like quit: closer to the under-2-hour games than to the kept ones
            def prof(ix):
                p = np.asarray(self.T[ix].sum(0)).ravel()
                n = np.linalg.norm(p)
                return p / n if n else p
            rows = self.trow[head]
            G = self.T[np.maximum(rows, 0)]
            has_tags = (rows >= 0) & (np.asarray(G.sum(1)).ravel() > 0)
            quit = has_tags & (G @ prof(short_ix) > G @ prof(kept_ix))
        short, neg = self.flag_short[head], self.flag_neg[head]
        new = z - SAFE["a_quit"] * quit - SAFE["b_short"] * short - SAFE["c_negative"] * neg
        for i, j in enumerate(head):
            flags[j] = {n for n, on in (("quit", quit[i]), ("short", short[i]), ("neg", neg[i])) if on}
        return [head[i] for i in np.argsort(-new, kind="stable")] + list(order[k:]), flags

    def taste(self, library):
        """library: (app_id, playtime_min) pairs. EASE input is binary (played or not), as in the evaluation.
        Returns (scores over app_ids, [(row in B, app_id)]) or (None, [])."""
        rows = [(self.idx[a], a) for a, pt in library if pt > 0 and a in self.idx]
        if not rows:
            return None, []
        return self.B[[r[0] for r in rows]].astype(np.float32).sum(0), rows

    def _contrib(self, j, rows, n=4):
        """The played games that pushed pick j up most: [(title, weight)], largest first, positive only."""
        c = self.B[[r[0] for r in rows], j].astype(np.float32)
        return [(self.titles.get(rows[k][1], str(rows[k][1])), float(c[k])) for k in np.argsort(-c)[:n] if c[k] > 0]

    def _card(self, j, score, rows, prices, flags):
        a = int(self.app_ids[j])
        g = self.games.loc[a] if a in self.games.index else None
        lp = prices.get(a)
        if lp and lp["final"] is not None:
            price = {"price": lp["final"], "price_initial": lp["initial"], "discount": lp["discount"], "price_text": lp["text"]}
        elif lp:                                    # store lists no price: free if our catalog says so, else check the store
            free = self.est_price[j] == 0
            price = {"price": 0.0 if free else None, "price_initial": None, "discount": 0, "price_text": "Free" if free else "See store"}
        else:                                       # store unreachable: last known regular price, marked approximate
            est = None if np.isnan(self.est_price[j]) else float(self.est_price[j])
            price = {"price": est, "price_initial": est, "discount": 0,
                     "price_text": None if est is None else ("Free" if est == 0 else f"~${est:.2f}")}
        contrib = self._contrib(j, rows)
        return {"app_id": a, "title": self.titles.get(a, str(a)), "score": float(score),
                "because": [t for t, _ in contrib[:2]], "contrib": contrib, "tags": self.tags.get(a, [])[:4], **price,
                "rating": None if np.isnan(self.rating[j]) else round(float(self.rating[j]) * 100),
                "reviews": int(self.n_reviews[j]),
                "image": None if g is None or pd.isna(g.header_image) else g.header_image,
                "flags": sorted(flags.get(j, ())),
                "store_url": f"https://store.steampowered.com/app/{a}/"}

    def recommend(self, library, owned=None, n=10, max_price=None, cc="us", include_explicit=False):
        """library: (app_id, playtime_min) pairs; owned: every owned app_id (never recommended).
        max_price is checked against the live store price. Returns None when no played game is known to EASE."""
        s, rows = self.taste(library)
        if s is None:
            return None
        mask = self.candidate.copy()
        if not include_explicit:
            mask &= ~self.explicit
        for a in set(owned or []) | {a for a, _ in library}:
            i = self.idx.get(a)
            if i is not None:
                mask[i] = False
        s = np.where(mask, s, -np.inf)
        order = [j for j in np.argsort(-s)[:600] if np.isfinite(s[j])]
        order, flags = self.safe_rerank(order, s, library)
        prices = {}
        if max_price is not None:
            head = order[:150]
            prices = live_prices([int(self.app_ids[j]) for j in head], cc)
            def ok(j):
                lp = prices.get(int(self.app_ids[j]))
                v = lp["final"] if lp and lp["final"] is not None else self.est_price[j]
                return not (v > max_price)
            order = [j for j in head if ok(j)] + [j for j in order[150:] if not (self.est_price[j] > max_price)]
        top = order[:n + 10]                        # spares, in case some turn out not to be on sale
        prices.update(live_prices([int(self.app_ids[j]) for j in top if int(self.app_ids[j]) not in prices], cc))
        if prices:                                  # drop delisted / unbuyable games (only when the store answered)
            def buyable(j):
                lp = prices.get(int(self.app_ids[j]))
                return lp is not None and (lp["final"] is not None or self.est_price[j] == 0)
            top = [j for j in top if buyable(j)]
        return {"for_you": [self._card(j, s[j], rows, prices, flags) for j in top[:n]],
                "n_used": len(rows), "n_candidates": self.n_candidates}
