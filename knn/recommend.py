"""Recommend games from the catalog for one Steam library.

  python recommend.py <steamid or profile URL>
  python recommend.py --library libraries/<steamid>.json      # a saved {appid: minutes} file

Taste comes from the most-played games ("liked") and the least-played games that were still
launched ("disliked"; unplayed games are ignored). Every catalog game is scored by tag similarity
to the liked games, minus similarity to the disliked ones, plus a little review quality.
All knobs are in RecConfig.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .features import Features, is_same_game, load_features

HERE = Path(__file__).parent
LIBRARIES = HERE / "libraries"


@dataclass
class RecConfig:
    n: int = 15
    # Taste profile
    liked_count: int = 15            # most-played games (or franchises) that define what the user likes
    # Several games of one franchise = one taste entry with combined playtime. OFF for now (idea for
    # later): it broadened the profile (12 -> 15 franchises on a real library) but cost blind-test
    # hits on recently played games, 1/1/3 -> 0/0/0 @10/15/50 (tune.py, 2026-11-09).
    collapse_franchises: bool = False
    disliked_count: int = 10         # least-played (but launched) games
    min_disliked_minutes: int = 5    # launched for less than this = probably a crash or a misclick
    max_disliked_minutes: int = 120  # played more than this = not really a dislike, even at the bottom
    playtime_measure: str = "raw"    # "raw" minutes, or "relative" to the game's median playtime
    # Recency (Steam gives a last-played date and two-week playtime per game, nothing longer)
    recency_half_life_days: float = 180   # a game's playtime counts half after this long; 0 = off
    recency_floor: float = 0.25           # ...but never less than this share
    recent_2weeks_boost: float = 10.0     # each minute in the last two weeks counts this many times
    # Scoring
    method: str = "knn"              # "knn": match any one liked game; "centroid": match the average
    knn_k: int = 3                   # knn: average of the k best matches among liked games
    dislike_weight: float = 0.5
    # Share of the score from quality = half review score, half review volume (log scale). Proven
    # games are a safer bet than near-identical obscure clones with the same tags. 0.5 nearly
    # doubled blind-test hits over 0.3 (tune.py, 2026-11-09); above ~0.6 lists turn generic.
    quality_weight: float = 0.5
    # Variety: picks take turns between the liked games they resemble, this many per liked game per
    # round, so one dense genre (e.g. deckbuilders) can't fill the whole list.
    max_per_anchor: int = 2
    # Explanations ("why we picked this")
    explain_max: int = 3             # library games named per pick
    explain_min_ratio: float = 0.6   # only name games at least this close, relative to the closest
    # Filters
    min_reviews: int = 50
    allow_adult: bool = False
    allow_sequels_of_owned: bool = True   # own Hades -> Hades II may be recommended
    max_franchise_picks: int = 3          # ...but at most this many from series the user owns
    max_per_family: int = 1               # editions/sequels of one game in the final list
    # First look (see first_look / refine)
    pool_size: int = 40              # games generated before the swipe step; the final list comes from these
    deck_size: int = 5               # cards shown
    # 1 = just the best matches, 0 = just the most different. 0.6 let one near-duplicate pair
    # through (e.g. two multiplayer FPS); 0.4 keeps cards distinct while staying in the top ~30.
    deck_relevance: float = 0.4
    deck_recognisability: float = 0.3  # share of a card's value from review volume (well-known games)


def normalize_library(lib: dict) -> dict[int, dict]:
    """Libraries are {appid: {"minutes", "minutes_2weeks", "last_played"}}. Older saved files are
    {appid: minutes}; those load with no recency information (treated as not played recently)."""
    out = {}
    for appid, v in lib.items():
        v = v if isinstance(v, dict) else {"minutes": v}
        out[int(appid)] = {"minutes": int(v.get("minutes", 0)),
                           "minutes_2weeks": int(v.get("minutes_2weeks", 0)),
                           "last_played": int(v.get("last_played", 0))}
    return out


def minutes(library: dict[int, dict]) -> dict[int, int]:
    return {a: v["minutes"] for a, v in library.items()}


def recency_factor(last_played: np.ndarray, cfg: RecConfig, now: float | None = None) -> np.ndarray:
    """1.0 for a game played today, halving every recency_half_life_days, never below
    recency_floor (so an old favourite still counts for something). Unknown dates get the floor."""
    if not cfg.recency_half_life_days:
        return np.ones(len(last_played))
    now = now or time.time()
    age_days = np.where(last_played > 0, (now - last_played) / 86400, np.inf)
    decay = 0.5 ** (np.maximum(age_days, 0) / cfg.recency_half_life_days)
    return cfg.recency_floor + (1 - cfg.recency_floor) * decay


def series_label(names: list[str]) -> str:
    """'Fallout 4', 'Fallout: New Vegas' -> 'the Fallout series'; a lone game keeps its name."""
    if len(names) == 1:
        return names[0]
    prefix = os.path.commonprefix([n.replace("’", "'") for n in names])   # Civ titles mix ' and ’
    prefix = re.sub(r"[\s:\-–—]+$", "", prefix)           # 'Fallout ' / 'Borderlands:' -> clean
    prefix = re.sub(r"\s+([IVX]+|\d+)$", "", prefix)       # 'Civilization® V' (V / VI) -> 'Civilization®'
    return f"the {prefix} series" if len(prefix) >= 3 else f"the {names[0]} series"


def collapse_by_family(played: pd.DataFrame) -> pd.DataFrame:
    """One taste entry per franchise/family: playtime and recency-weighted measure are summed, so a
    devoted fan's franchise still counts strongly but takes one slot instead of three. The
    franchise's most-played game stands in for its tag profile."""
    played = played.sort_values("measure", ascending=False)
    out = played.groupby("family", sort=False).agg(
        appid=("appid", "first"), row=("row", "first"), name=("name", "first"),
        minutes=("minutes", "sum"), minutes_2weeks=("minutes_2weeks", "sum"),
        last_played=("last_played", "max"), measure=("measure", "sum"), members=("name", list))
    out["label"] = out.members.apply(series_label)
    return out.reset_index()


def taste(f: Features, library: dict[int, dict], cfg: RecConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pick the liked and disliked games from a library."""
    library = normalize_library(library)
    played = pd.DataFrame([{"appid": a, **v} for a, v in library.items()],
                          columns=["appid", "minutes", "minutes_2weeks", "last_played"])
    played = played[played.minutes > 0]
    played = played[played.appid.isin(f.row_of.keys())]
    played["row"] = played.appid.map(f.row_of)
    g = f.games.iloc[played.row]
    played = played[g.has_features.to_numpy()].copy()
    played["name"] = f.games.name.iloc[played.row].to_numpy()

    if cfg.playtime_measure == "relative":
        median = f.games.median_playtime_hours.iloc[played.row].to_numpy() * 60
        typical = np.nanmedian(f.games.median_playtime_hours) * 60
        played["measure"] = played.minutes / np.where(np.isnan(median), typical, np.maximum(median, 30))
    else:
        played["measure"] = played.minutes.astype(float)
    # Recency: what someone plays now says more about what they want next than what they played
    # years ago. Total playtime fades with time since last played; the last two weeks add a boost.
    played["measure"] = (played.measure * recency_factor(played.last_played.to_numpy(), cfg)
                         + cfg.recent_2weeks_boost * played.minutes_2weeks)

    played["family"] = f.games.family_id.iloc[played.row].to_numpy()
    if cfg.collapse_franchises:
        liked = collapse_by_family(played).nlargest(cfg.liked_count, "measure")
        # A barely-played game from a franchise the player loves isn't a dislike of the franchise.
        rest = played[~played.family.isin(liked.family)]
    else:
        liked = played.nlargest(cfg.liked_count, "measure").assign(label=lambda d: d.name)
        rest = played.drop(liked.index)
    rest = rest[rest.minutes.between(cfg.min_disliked_minutes, cfg.max_disliked_minutes)]
    rest = rest[rest.minutes_2weeks == 0]           # still being tried out: not a dislike (yet)
    disliked = rest.nsmallest(cfg.disliked_count, "measure")
    liked["weight"] = np.log1p(liked.measure / 60) + 0.1      # recency-adjusted
    liked["source"] = "library"
    disliked["weight"] = np.log1p(disliked.minutes / 60) + 0.1
    return liked, disliked


def similarity(f: Features, rows: np.ndarray, ref: pd.DataFrame, cfg: RecConfig):
    """Similarity of each candidate row to a set of reference games.
    Returns (score, S, Sw): the score, raw similarities and play-weighted similarities
    (candidates x reference games)."""
    if ref.empty:
        z = np.zeros((len(rows), 0))
        return np.zeros(len(rows)), z, z
    S = (f.X[rows] @ f.X[ref.row.to_numpy()].T).toarray()          # candidates x reference games
    w = ref.weight.to_numpy() / ref.weight.max()
    Sw = S * w
    if cfg.method == "centroid":
        profile = (f.X[ref.row.to_numpy()].T @ w).ravel()
        profile /= np.linalg.norm(profile) or 1
        return np.asarray(f.X[rows] @ profile).ravel(), S, Sw
    k = min(cfg.knn_k, Sw.shape[1])
    return np.sort(Sw, axis=1)[:, -k:].mean(axis=1), S, Sw


def explain(S: np.ndarray, Sw: np.ndarray, ref: pd.DataFrame, cfg: RecConfig):
    """For each candidate, up to cfg.explain_max entries from the player's own library that drive
    its score most (by play-weighted similarity), keeping only close matches: raw similarity at
    least cfg.explain_min_ratio of the best match's. An entry is a game, or a whole franchise
    ('the Fallout series') when franchises are collapsed. Games liked via a first-look swipe are
    left out; the app mentions those separately.
    Returns (labels, appids): display labels, and the appid standing in for each (for tags)."""
    from_library = (ref.source == "library").to_numpy()
    labels, appids = ref.label.to_numpy(), ref.appid.to_numpy()
    order = np.argsort(-np.where(from_library, Sw, -np.inf), axis=1)[:, :cfg.explain_max]
    out_labels, out_ids = [], []
    for i, idx in enumerate(order):
        idx = idx[from_library[idx]]
        keep = [j for j in idx if S[i, j] >= cfg.explain_min_ratio * S[i, idx].max()] if len(idx) else []
        out_labels.append(tuple(labels[j] for j in keep))
        out_ids.append(tuple(int(appids[j]) for j in keep))
    return out_labels, out_ids


def exclusion_reasons(f: Features, owned: set[int], cfg: RecConfig) -> pd.Series:
    """Why each catalog game can't be recommended ('' = it can)."""
    g = f.games
    reason = pd.Series("", index=g.index, dtype=object)
    owned_rows = g.appid.isin(owned)
    owned_families = set(g.family_id[owned_rows])
    in_family = g.family_id.isin(owned_families) & ~owned_rows
    same_game = pd.Series(False, index=g.index)
    for i in g.index[in_family]:
        same_game.at[i] = any(is_same_game(g.loc[i], g.loc[j])
                              for j in g.index[owned_rows & (g.family_id == g.family_id.at[i])])
    sequel = in_family & ~same_game
    checks = [  # first matching reason wins
        (~g.has_features, "no tags or genres"),
        (owned_rows, "already owned"),
        (same_game, "edition/expansion of an owned game"),
        (sequel & (not cfg.allow_sequels_of_owned), "sequel of an owned game"),
        (~g.is_released, "not released"),
        (g.is_software, "software, not a game"),
        (g.is_non_game, "demo/soundtrack/playtest/benchmark"),
        (g.is_duplicate_listing, "duplicate listing (usually a DLC)"),
        (g.is_adult & (not cfg.allow_adult), "adult content"),
        (g.total_reviews < cfg.min_reviews, f"fewer than {cfg.min_reviews} reviews"),
    ]
    for mask, why in reversed(checks):
        reason[mask.to_numpy()] = why
    return reason


def add_reactions(f: Features, liked: pd.DataFrame, disliked: pd.DataFrame,
                  interested=(), not_interested=()) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fold first-look swipes into the taste profile. 'Interested' counts like a typical liked game;
    'not interested' counts as a strong dislike, since it's said outright rather than guessed from
    low playtime."""
    def rows_for(appids, weight):
        r = f.rows(appids)
        return pd.DataFrame({"appid": f.games.appid.iloc[r].to_numpy(), "row": r,
                             "name": f.games.name.iloc[r].to_numpy(), "weight": weight,
                             "source": "swipe", "label": f.games.name.iloc[r].to_numpy()})
    liked = pd.concat([liked, rows_for(interested, liked.weight.median())], ignore_index=True)
    strong = liked.weight.max()
    disliked = pd.concat([disliked, rows_for(not_interested, strong)], ignore_index=True)
    return liked, disliked


def score_candidates(f: Features, library: dict[int, int], cfg: RecConfig,
                     interested=(), not_interested=()) -> pd.DataFrame:
    """Every recommendable game with its score, best first (no list-shaping caps yet)."""
    liked, disliked = taste(f, library, cfg)
    if liked.empty:
        raise ValueError("None of this library's played games are in the catalog.")
    liked, disliked = add_reactions(f, liked, disliked, interested, not_interested)
    reasons = exclusion_reasons(f, set(library) | set(not_interested), cfg)
    rows = np.flatnonzero(reasons.eq("").to_numpy())

    like, S, Sw = similarity(f, rows, liked, cfg)
    dislike, _, _ = similarity(f, rows, disliked, cfg)
    g = f.games.iloc[rows]
    aligned_labels, aligned_ids = explain(S, Sw, liked, cfg)
    out = pd.DataFrame({
        "appid": g.appid.to_numpy(), "name": g.name.to_numpy(),
        "like": like, "dislike": dislike, "review_score": g.review_score.to_numpy(),
        "total_reviews": g.total_reviews.to_numpy(), "family_id": g.family_id.to_numpy(),
        # The closest liked game (library or swipe); drives the variety round-robin. (Raw
        # similarity here tested better than play-weighted; the display uses aligned_with.)
        "because": liked.name.to_numpy()[S.argmax(axis=1)],
        # Up to 3 games from the player's library that justify the pick (for display).
        "aligned_with": aligned_labels,
        "aligned_appids": aligned_ids,
    })
    volume = g.log_reviews.to_numpy() / max(g.log_reviews.max(), 1)
    out["quality"] = 0.5 * out.review_score + 0.5 * volume
    sim = out.like - cfg.dislike_weight * out.dislike
    out["score"] = (1 - cfg.quality_weight) * sim + cfg.quality_weight * out.quality

    # Expansions are never recommended themselves; the base game inherits the expansion's score
    # if that is higher (expansions without a recommendable base are simply dropped).
    is_exp = g.is_expansion.to_numpy()
    if is_exp.any():
        to_base = out[is_exp].assign(base=g.base_appid.to_numpy()[is_exp]).groupby("base").score.max()
        out = out[~is_exp]
        out["score"] = np.fmax(out.score, out.appid.map(to_base).to_numpy())
    return out.sort_values("score", ascending=False, ignore_index=True)


def arrange(out: pd.DataFrame, f: Features, library: dict[int, int], cfg: RecConfig) -> pd.DataFrame:
    """Shape scored games into list order: family cap, variety round-robin, franchise cap."""
    # Family cap: keep the best-scoring editions/sequels of each game.
    out = out[out.groupby("family_id").cumcount() < cfg.max_per_family]
    # Variety: round-robin across the liked games each pick resembles.
    out = out.assign(_round=out.groupby("because").cumcount() // cfg.max_per_anchor)
    out = out.sort_values(["_round", "score"], ascending=[True, False], ignore_index=True)
    # Franchise cap: past the first few picks from series the user already owns, the rest are moved
    # out of the top n (to just after it, in score order, so the litmus top-50/100 stay meaningful).
    owned_families = set(f.games.family_id[f.games.appid.isin(library)])
    franchise = out.family_id.isin(owned_families)
    over = franchise & (franchise.cumsum() > cfg.max_franchise_picks)
    kept = out[~over]
    out = pd.concat([kept.iloc[:cfg.n], pd.concat([kept.iloc[cfg.n:], out[over]]).sort_index()],
                    ignore_index=True)
    return out.drop(columns="_round").assign(rank=np.arange(1, len(out) + 1))


def recommend(f: Features, library: dict[int, int], cfg: RecConfig | None = None,
              full: bool = False) -> pd.DataFrame:
    """Top cfg.n games, or with full=True every recommendable game in final list order."""
    cfg = cfg or RecConfig()
    out = arrange(score_candidates(f, library, cfg), f, library, cfg)
    return out if full else out.head(cfg.n)


# ---- First look: a 5-card deck, then a refined list -------------------------------------------


def first_look(f: Features, library: dict[int, int], cfg: RecConfig | None = None):
    """Returns (pool, deck). pool: the top cfg.pool_size recommendations, in list order (its first
    cfg.n are the unrefined top list). deck: cfg.deck_size games from the pool that together show
    the range of the user's taste.

    Cards are picked by maximal marginal relevance: each next card is the best balance of 'strong
    match' and 'unlike the cards already picked'. Cards only come from the pool, so variety is
    never forced: a library of nothing but shooters gets five different kinds of shooter, not a
    farming sim. Recognisable games are slightly preferred, since a card is only useful if the
    player can judge the game at a glance."""
    cfg = cfg or RecConfig()
    pool = recommend(f, library, cfg, full=True).head(cfg.pool_size).reset_index(drop=True)
    s = pool.score.to_numpy()
    rel = (s - s.min()) / ((s.max() - s.min()) or 1)
    rows = np.array(f.rows(pool.appid))
    volume = f.games.log_reviews.iloc[rows].to_numpy()
    volume = volume / (volume.max() or 1)
    value = (1 - cfg.deck_recognisability) * rel + cfg.deck_recognisability * volume
    sims = (f.X[rows] @ f.X[rows].T).toarray()

    picked: list[int] = []
    for _ in range(min(cfg.deck_size, len(pool))):
        overlap = sims[:, picked].max(axis=1) if picked else np.zeros(len(pool))
        mmr = cfg.deck_relevance * value - (1 - cfg.deck_relevance) * overlap
        mmr[picked] = -np.inf
        picked.append(int(mmr.argmax()))
    return pool, pool.iloc[picked].reset_index(drop=True)


def refine(f: Features, library: dict[int, int], pool: pd.DataFrame, deck: pd.DataFrame,
           reactions: dict[int, bool], cfg: RecConfig | None = None) -> pd.DataFrame:
    """The final list after the first look. reactions: {appid: True (interested) / False}.

    - The list is re-scored with the swipes folded into the taste profile, from the pool only.
    - 'Not interested' cards never appear.
    - A card appears only if it was already in the unrefined top list; if it was and the user
      swiped it up, it is guaranteed a place."""
    cfg = cfg or RecConfig()
    interested = [a for a, yes in reactions.items() if yes]
    not_interested = [a for a, yes in reactions.items() if not yes]
    original_top = set(pool.appid.head(cfg.n))
    blocked = (set(deck.appid) - original_top) | set(not_interested)
    allowed = set(pool.appid) - blocked

    scored = score_candidates(f, library, cfg, interested, not_interested)
    ranked = arrange(scored[scored.appid.isin(allowed)].reset_index(drop=True), f, library, cfg)
    pinned = ranked.appid.isin(set(interested) & original_top)
    final = pd.concat([ranked[pinned], ranked[~pinned].head(cfg.n - int(pinned.sum()))])
    return final.sort_values("rank").reset_index(drop=True).assign(rank=lambda d: range(1, len(d) + 1))


def get_library(user: str | None, path: Path | None, save: bool = True) -> dict[int, dict]:
    """Load a saved library, or fetch it from Steam and save a copy to libraries/."""
    if path:
        return normalize_library(json.loads(path.read_text(encoding="utf-8")))
    from steam_api import owned_games, resolve_steamid
    steamid = resolve_steamid(user)
    lib = owned_games(steamid)
    if save:
        LIBRARIES.mkdir(exist_ok=True)
        (LIBRARIES / f"{steamid}.json").write_text(json.dumps(lib), encoding="utf-8")
    return lib


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("user", nargs="?", help="SteamID64, profile URL or custom URL name")
    ap.add_argument("--library", type=Path, help="saved {appid: minutes} JSON instead of fetching")
    ap.add_argument("--method", choices=["knn", "centroid"], default="knn")
    args = ap.parse_args()
    if not (args.user or args.library):
        ap.error("give a Steam user or --library")
    f = load_features()
    recs = recommend(f, get_library(args.user, args.library), RecConfig(method=args.method))
    with pd.option_context("display.width", 200, "display.max_colwidth", 45):
        print(recs[["name", "score", "like", "dislike", "review_score", "because"]].round(3))


if __name__ == "__main__":
    sys.exit(main())
