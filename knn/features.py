"""Build the features the recommender uses from the games_cleaned catalog.

Run once after each monthly catalog refresh:
  python features.py                          # read from Supabase (SUPABASE_DB_URL)
  python features.py --csv games_cleaned.csv  # or from the local CSV
  python features.py --csv games_cleaned.csv --similar "Hades"   # sanity check: 10 nearest games

Writes to artifacts/:
  games.parquet    one row per game: metadata, filter flags, numeric ranker features
  tag_matrix.npz   sparse TF-IDF matrix, row i <-> games.parquet row i, rows L2-normalised
  vocab.json       column names of tag_matrix ("tag:Roguelike", "genre:RPG", ...)
  build_info.json  when/how the artifacts were built

Other code loads them with `features.load_features()`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"

# ---- Tunable settings -------------------------------------------------------------------------


@dataclass
class FeatureConfig:
    # Steam lists a game's tags most-voted first. Tag at position i (0-based) gets weight
    # 1 / (1 + tag_position_decay * i): with 0.1 the top tag counts 1.0 and the 20th ~0.34,
    # which also softens joke tags that sit at the bottom of the list. 0 = all tags equal.
    tag_position_decay: float = 0.1
    # Genres mostly repeat what tags say, so they get a smaller share of the vector.
    genre_weight: float = 0.5
    # Adult flag: a strong tag in the top-k tags, or two adult tags in the top-k,
    # or an adult genre (genres are set by the developer, tags are voted by players).
    adult_top_k: int = 10
    # A multiplayer tag only counts when it is in the top-k tags (categories always count).
    multiplayer_tag_top_k: int = 10
    # Bayesian smoothing for review score: behaves as if every game had this many extra
    # reviews at the catalog's typical positive rate, so 3/3 positive doesn't beat 9,000/10,000.
    review_prior_weight: int = 50
    # Tag pairs the EDA lift analysis showed are near-duplicates. Merged before vectorising so one
    # idea isn't counted twice. key -> value.
    tag_synonyms: dict[str, str] = field(default_factory=lambda: {
        "Naval Combat": "Naval",
        "Politics": "Political",
        "Political Sim": "Political",
        "Party Game": "Party",
        "Mini Golf": "Golf",
        "Wholesome": "Cozy",
        "Rogue-like": "Rogue-lite",
        "Snowboarding": "Skiing",
        "Motocross": "Motorbike",
    })
    # Tags that describe quality, hype or business model rather than what the game is like.
    drop_tags: set[str] = field(default_factory=lambda: {
        "Great Soundtrack", "Masterpiece", "Addictive", "Classic", "Cult Classic",
        "Early Access", "Free to Play",
    })
    drop_genres: set[str] = field(default_factory=lambda: {"Early Access", "Free To Play"})


ADULT_STRONG_TAGS = {"NSFW", "Hentai"}
ADULT_TAGS = ADULT_STRONG_TAGS | {"Sexual Content", "Nudity"}
ADULT_GENRES = {"Sexual Content", "Nudity"}

SOFTWARE_GENRES = {
    "Utilities", "Design & Illustration", "Animation & Modeling", "Video Production",
    "Game Development", "Education", "Audio Production", "Software Training", "Photo Editing",
    "Web Publishing", "Accounting", "Movie",
}
NON_GAME_NAME = re.compile(r"soundtrack|\bOST\b|playtest|\bdemo\b|dedicated server|\bSDK\b|benchmark|"
                           r"[:\-–]\s*prologue\b", re.IGNORECASE)

# Multiplayer modes: (categories that imply it, tags that imply it). Categories are developer-set.
MULTIPLAYER_MODES = {
    "online_coop": ({"Online Co-op"}, {"Online Co-Op"}),
    "local_coop": ({"Shared/Split Screen Co-op"}, {"Local Co-Op"}),
    "online_pvp": ({"Online PvP"}, set()),
    "local_pvp": ({"Shared/Split Screen PvP"}, set()),
    "lan": ({"LAN Co-op", "LAN PvP"}, {"LAN"}),
    "any_multiplayer": (
        {"Multi-player", "Co-op", "PvP", "Online Co-op", "Online PvP", "Shared/Split Screen",
         "Shared/Split Screen Co-op", "Shared/Split Screen PvP", "LAN Co-op", "LAN PvP",
         "Cross-Platform Multiplayer", "MMO"},
        {"Multiplayer", "Co-op", "Online Co-Op", "Local Co-Op", "Local Multiplayer", "PvP",
         "Massively Multiplayer", "Co-op Campaign", "4 Player Local"},
    ),
}

# Words that mark a re-release of the same game rather than a different one.
EDITION_WORDS = re.compile(
    r"\b(remastered|remaster|remake|definitive|special|enhanced|complete|ultimate|deluxe|goty|"
    r"game of the year|anniversary|director'?s cut|legacy|gold|platinum|collection|hd|vr|edition|"
    r"redux|reloaded|plus|classic|bundle|trilogy)\b")
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9,
         "x": 10, "xi": 11, "xii": 12}

EXPANSION_TEXT = re.compile(r"\bis (?:the|an|a) (?:[\w-]+ ){0,2}expansion(?: pack)? (?:for|to)\b",
                            re.IGNORECASE)
STANDALONE = re.compile(r"stand[- ]?alone", re.IGNORECASE)

COLUMNS = ["appid", "name", "release_date", "release_year", "price", "price_type", "positive",
           "negative", "total_reviews", "positive_review_pct", "median_playtime_forever",
           "dlc_count", "achievements", "genres", "tags", "categories", "windows", "mac", "linux",
           "header_image", "developers", "publishers"]
OPTIONAL_ABOUT = "about_the_game"

# ---- Loading the catalog ----------------------------------------------------------------------


def snake(name: str) -> str:
    """'Positive review %' -> 'positive_review_pct' (same rule upload_games_cleaned.py uses)."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower().replace("%", "pct")).strip("_")


def db_url() -> str:
    if os.environ.get("SUPABASE_DB_URL"):
        return os.environ["SUPABASE_DB_URL"]
    secrets = HERE / ".streamlit" / "secrets.toml"
    if secrets.exists():
        url = tomllib.loads(secrets.read_text(encoding="utf-8-sig")).get("SUPABASE_DB_URL")
        if url:
            return url
    sys.exit("Set SUPABASE_DB_URL in the environment or .streamlit/secrets.toml, or pass --csv.")


def load_catalog(csv: Path | None = None) -> pd.DataFrame:
    wanted = COLUMNS + [OPTIONAL_ABOUT]   # the description is only used to spot expansions
    if csv:
        df = pd.read_csv(csv, usecols=lambda c: snake(c) in wanted)
        df.columns = [snake(c) for c in df.columns]
    else:
        import psycopg2  # only needed for the Supabase path
        with psycopg2.connect(db_url()) as conn, conn.cursor() as cur:
            cur.execute("select column_name from information_schema.columns "
                        "where table_schema = 'public' and table_name = 'games_cleaned'")
            available = {r[0] for r in cur.fetchall()}
            cur.execute(f"select {', '.join(c for c in wanted if c in available)} from public.games_cleaned")
            df = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    df = df.dropna(subset=["appid"]).astype({"appid": "int64"})
    dupes = df.appid.duplicated().sum()
    if dupes:
        print(f"warning: dropping {dupes} duplicate appids")
        df = df.drop_duplicates("appid")
    return df.reset_index(drop=True)


# ---- Feature building -------------------------------------------------------------------------


def split_list(s) -> list[str]:
    if not isinstance(s, str):
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def clean_tags(tags: list[str], cfg: FeatureConfig) -> list[str]:
    """Apply synonyms, drop non-descriptive tags, keep first occurrence (best vote rank)."""
    out, seen = [], set()
    for t in tags:
        t = cfg.tag_synonyms.get(t, t)
        if t in cfg.drop_tags or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def is_adult(tags: list[str], genres: list[str], cfg: FeatureConfig) -> bool:
    top = tags[:cfg.adult_top_k]
    return (bool(ADULT_GENRES.intersection(genres))
            or bool(ADULT_STRONG_TAGS.intersection(top))
            or len(ADULT_TAGS.intersection(top)) >= 2)


def add_flags(df: pd.DataFrame, raw_tags: pd.Series, genres: pd.Series, cats: pd.Series,
              cfg: FeatureConfig, today: pd.Timestamp) -> None:
    df["has_features"] = df.tag_list.str.len().gt(0) | genres.str.len().gt(0)
    # Adult and multiplayer flags use the raw vote-ordered tags, before synonyms/drops.
    df["is_adult"] = [is_adult(t, g, cfg) for t, g in zip(raw_tags, genres)]
    df["is_software"] = genres.apply(lambda g: bool(g) and set(g) <= SOFTWARE_GENRES)
    df["is_non_game"] = df.name.fillna("").str.contains(NON_GAME_NAME)
    df["is_released"] = pd.to_datetime(df.release_date, errors="coerce").le(today)
    k = cfg.multiplayer_tag_top_k
    for mode, (mode_cats, mode_tags) in MULTIPLAYER_MODES.items():
        df[mode] = [bool(mode_cats.intersection(c)) or bool(mode_tags.intersection(t[:k]))
                    for c, t in zip(cats, raw_tags)]


def _clean_subtitle(s: str) -> str:
    s = EDITION_WORDS.sub(" ", re.sub(r"\(.*?\)|\[.*?\]", " ", s))
    return " ".join(re.sub(r"[^\w' ]+", " ", s).split())


def family_name(name) -> tuple[str, int, str]:
    """'DARK SOULS™ II: Scholar of the First Sin' -> ('dark souls', 2, 'scholar of the first sin');
    'The Binding of Isaac: Rebirth' -> ('binding of isaac', 1, 'rebirth'). The part after ':' or
    ' - ' is the subtitle, so expansions, remasters and editions share a base name with the
    original; the series number separates sequels; the subtitle (minus edition words) is kept so
    'Black Ops' and 'Black Ops III' can be told apart."""
    if not isinstance(name, str):
        return "", 1, ""
    s = re.sub(r"[™®©]", "", name)                    # before NFKC, which turns ™ into "TM"
    s = unicodedata.normalize("NFKC", s).lower().replace("’", "'")
    parts = re.split(r":| - | – | — ", s, maxsplit=1)
    s, subtitle = parts[0], _clean_subtitle(parts[1]) if len(parts) > 1 else ""
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)
    s = EDITION_WORDS.sub(" ", s)
    s = re.sub(r"^\w+ \w+'s ", "", s.strip())        # "sid meier's civilization" -> "civilization"
    s = re.sub(r"^the ", "", s)
    s = re.sub(r"[^\w' ]+", " ", s)
    words = s.split()
    number = 1
    if len(words) > 1 and (words[-1] in ROMAN or re.fullmatch(r"\d{1,2}", words[-1])):
        last = words.pop()
        number = ROMAN.get(last) or int(last)
    return " ".join(words), number, subtitle


def add_families(df: pd.DataFrame) -> None:
    """family_id groups re-releases, editions, expansions and sequels of one game: same base name
    AND at least one shared developer or publisher (so two unrelated games called 'Survival' stay
    apart). series_number tells sequels apart (Hades = 1, Hades II = 2)."""
    parsed = df.name.apply(family_name)
    df["series_number"] = parsed.str[1]
    df["subtitle"] = parsed.str[2]
    base = parsed.str[0]
    makers = (df.developers.fillna("") + "," + df.publishers.fillna("")).apply(
        lambda s: {x.strip().lower().rstrip(".").replace(", inc", "").replace(" inc", "")
                   for x in s.split(",") if x.strip() and x.strip().lower() not in {"inc", "inc.", "llc", "ltd"}})
    parent = list(range(len(df)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for _, idx in base[base.ne("")].groupby(base).groups.items():
        idx = list(idx)
        for a_pos, a in enumerate(idx):
            for b in idx[a_pos + 1:]:
                if makers[a] & makers[b]:
                    parent[find(a)] = find(b)
    df["family_id"] = [int(df.appid.iat[find(i)]) for i in range(len(df))]

    # The same name listed more than once in a family is a DLC that inherited its base game's
    # data (e.g. 20 "Shadow of the Tomb Raider: Definitive Edition" rows are its DLC packs) or a
    # regional/duplicate listing. Keep the one with the most reviews, lowest appid on ties.
    key = df.name.fillna("").str.lower().str.strip() + "|" + df.family_id.astype(str)
    keep = (df.assign(_key=key).sort_values(["total_reviews", "appid"], ascending=[False, True])
            .drop_duplicates("_key").index)
    df["is_duplicate_listing"] = ~df.index.isin(keep) & df.name.notna()


def is_same_game(a: pd.Series, b: pd.Series) -> bool:
    """Two games of one family are the same game (edition, remaster, expansion, remake) when they
    have the same series number and either the same subtitle (Skyrim / Skyrim Special Edition) or
    one has no subtitle and came out first (Isaac 2011 -> Isaac: Rebirth 2014). A plain title that
    is NEWER than the subtitled one is a different game (the 2022 'Call of Duty' hub app is not an
    edition of 'Call of Duty: Black Ops')."""
    if a.series_number != b.series_number:
        return False
    if a.subtitle == b.subtitle:
        return True
    if a.subtitle and b.subtitle:
        return False
    plain, subtitled = (a, b) if not a.subtitle else (b, a)
    return str(plain.release_date) <= str(subtitled.release_date)


def add_expansions(df: pd.DataFrame, about: pd.Series | None) -> None:
    """is_expansion: the store text says the game IS an expansion for another game ('...is the
    second expansion pack for Civilization IV'), and isn't standalone. base_appid: the plain-titled
    original it expands (Civ IV: Beyond the Sword -> Civilization IV), or 0 if not in the catalog."""
    df["base_appid"] = 0
    if about is None:
        df["is_expansion"] = False
        print("warning: no 'About the game' text, so expansions can't be detected "
              "(use --csv, or upload the catalog with --keep-big-columns)")
        return
    text = about.fillna("")
    df["is_expansion"] = (text.str.contains(EXPANSION_TEXT) & ~text.str.contains(STANDALONE)).to_numpy()
    for i in df.index[df.is_expansion]:
        sibs = df[(df.family_id == df.family_id.at[i]) & ~df.is_expansion & df.subtitle.eq("")
                  & ~df.is_duplicate_listing]
        bases = [j for j in sibs.index if is_same_game(df.loc[j], df.loc[i])]
        if bases:
            df.at[i, "base_appid"] = int(df.loc[bases].sort_values("total_reviews").appid.iat[-1])


def add_numeric(df: pd.DataFrame, cfg: FeatureConfig, today: pd.Timestamp) -> float:
    """Ranker inputs. Returns the review prior used, for build_info."""
    reviewed = df.total_reviews >= 50
    prior = float(df.loc[reviewed, "positive_review_pct"].median() / 100) if reviewed.any() else 0.75
    m = cfg.review_prior_weight
    df["review_score"] = (df.positive + m * prior) / (df.total_reviews + m)
    df["log_reviews"] = np.log1p(df.total_reviews)
    df["age_years"] = today.year - df.release_year
    # 0 means "no data" for ~29% of reviewed games, not "nobody plays it"
    df["median_playtime_hours"] = df.median_playtime_forever.where(df.median_playtime_forever > 0) / 60
    return prior


def build_matrix(tag_lists: pd.Series, genre_lists: pd.Series, cfg: FeatureConfig):
    """TF-IDF over tags (weighted by vote position) + genres (scaled), rows L2-normalised."""
    vocab: dict[str, int] = {}
    rows, cols, vals = [], [], []
    for r, (tags, genres) in enumerate(zip(tag_lists, genre_lists)):
        for i, t in enumerate(tags):
            rows.append(r); cols.append(vocab.setdefault(f"tag:{t}", len(vocab)))
            vals.append(1.0 / (1.0 + cfg.tag_position_decay * i))
        for g in genres:
            if g in cfg.drop_genres:
                continue
            rows.append(r); cols.append(vocab.setdefault(f"genre:{g}", len(vocab)))
            vals.append(cfg.genre_weight)
    X = sp.csr_matrix((vals, (rows, cols)), shape=(len(tag_lists), len(vocab)), dtype=np.float32)

    # Smooth IDF (same formula as scikit-learn), counted over games that have any features.
    n_docs = int((X.getnnz(axis=1) > 0).sum())
    df_counts = np.bincount(X.indices, minlength=X.shape[1])
    idf = np.log((1 + n_docs) / (1 + df_counts)) + 1
    X = X @ sp.diags(idf.astype(np.float32))

    norms = np.sqrt(np.asarray(X.multiply(X).sum(axis=1)).ravel())
    norms[norms == 0] = 1
    X = sp.diags((1 / norms).astype(np.float32)) @ X
    names = sorted(vocab, key=vocab.get)
    return X.tocsr(), names


def build(df: pd.DataFrame, cfg: FeatureConfig | None = None):
    cfg = cfg or FeatureConfig()
    today = pd.Timestamp.today().normalize()
    raw_tags = df.tags.apply(split_list)
    genres = df.genres.apply(split_list)
    cats = df.categories.apply(split_list)

    df = df.copy()
    about = df.pop(OPTIONAL_ABOUT) if OPTIONAL_ABOUT in df else None
    df["tag_list"] = raw_tags.apply(lambda t: clean_tags(t, cfg))
    add_flags(df, raw_tags, genres, cats, cfg, today)
    add_families(df)
    add_expansions(df, about)
    prior = add_numeric(df, cfg, today)
    X, vocab = build_matrix(df.tag_list, genres, cfg)

    games = df.drop(columns=["tags", "categories"]).assign(
        tag_list=df.tag_list.str.join(","))
    info = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": len(games), "with_features": int(games.has_features.sum()),
        "vocab_size": len(vocab), "review_prior": round(prior, 4),
        "flag_counts": {c: int(games[c].sum()) for c in
                        ["is_adult", "is_software", "is_non_game", "is_duplicate_listing", "is_expansion",
                         "is_released",
                         *MULTIPLAYER_MODES]},
        "config": {k: sorted(v) if isinstance(v, set) else v for k, v in asdict(cfg).items()},
    }
    return games, X, vocab, info


# ---- Saving and loading -----------------------------------------------------------------------


def save(games: pd.DataFrame, X, vocab: list[str], info: dict, out: Path = ARTIFACTS) -> None:
    out.mkdir(exist_ok=True)
    games.to_parquet(out / "games.parquet", index=False)
    sp.save_npz(out / "tag_matrix.npz", X)
    (out / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
    (out / "build_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")


@dataclass
class Features:
    games: pd.DataFrame          # row i describes tag_matrix row i
    X: sp.csr_matrix
    vocab: list[str]
    info: dict
    row_of: dict[int, int]       # appid -> row

    def rows(self, appids) -> list[int]:
        """Rows for the appids that are in the catalog (others are silently skipped)."""
        return [self.row_of[a] for a in appids if a in self.row_of]


def load_features(path: Path = ARTIFACTS) -> Features:
    games = pd.read_parquet(path / "games.parquet")
    return Features(
        games=games,
        X=sp.load_npz(path / "tag_matrix.npz").tocsr(),
        vocab=json.loads((path / "vocab.json").read_text(encoding="utf-8")),
        info=json.loads((path / "build_info.json").read_text(encoding="utf-8")),
        row_of=dict(zip(games.appid.tolist(), range(len(games)))),
    )


def most_similar(f: Features, name: str, n: int = 10, min_reviews: int = 50) -> pd.DataFrame:
    """Debug helper: nearest games to one title by cosine similarity."""
    hits = f.games.index[f.games.name.str.lower() == name.lower()]
    if hits.empty:
        sys.exit(f"No game named {name!r}")
    r = hits[0]
    sims = (f.X @ f.X[r].T).toarray().ravel()
    g = f.games.assign(similarity=sims)
    ok = (g.total_reviews >= min_reviews) & ~g.is_adult & ~g.is_software & ~g.is_non_game
    ok.iloc[r] = False
    return g[ok].nlargest(n, "similarity")[["name", "similarity", "total_reviews", "tag_list"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, help="read the catalog from this CSV instead of Supabase")
    ap.add_argument("--out", type=Path, default=ARTIFACTS)
    ap.add_argument("--similar", metavar="NAME", help="after building, print the 10 nearest games")
    args = ap.parse_args()

    games, X, vocab, info = build(load_catalog(args.csv))
    save(games, X, vocab, info, args.out)
    print(json.dumps({k: v for k, v in info.items() if k != "config"}, indent=2))
    if args.similar:
        with pd.option_context("display.width", 200, "display.max_colwidth", 90):
            print(most_similar(load_features(args.out), args.similar))


if __name__ == "__main__":
    main()
