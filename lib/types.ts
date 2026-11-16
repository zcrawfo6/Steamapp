// Shapes returned by the EASE-safe Modal API (Juan_EASE/modal_api.py).

export type GameSummary = {
  app_id: number;
  title: string;
  tags: string[]; // up to 5 taste tags (format tags like "Singleplayer" removed)
  raw_tags: string[]; // full user tags, used for worlds and play-style modes
  genres: string[];
  image: string | null;
  price: number | null;
  rating: number | null;
  reviews: number | null;
  in_catalog: boolean;
  in_model: boolean;
  recommendable?: boolean;
  explicit?: boolean;
  store_url?: string;
};

export type Mode = "story" | "coop" | "pvp";

/** One game in the player's library, as kept in the browser. */
export type LibGame = GameSummary & {
  hours: number;
  modes: Partial<Record<Mode, number>>; // ticked modes -> share of hours (0-100)
};

export type Card = {
  app_id: number;
  title: string;
  score: number;
  because: string[];
  contrib: [string, number][];
  flags: ("quit" | "short" | "neg")[];
  tags: string[];
  raw_tags?: string[];
  genres?: string[];
  price: number | null;
  price_initial: number | null;
  discount: number;
  price_text: string | null;
  rating: number | null;
  reviews: number;
  image: string | null;
  store_url: string;
  new_tag?: string | null;
};

export type RecResult = {
  for_you: Card[];
  try_new: Card[];
  top_tags: string[];
  favorites: string[];
  n_owned: number;
  n_used: number;
  n_candidates: number;
};

export type PlayerGame = GameSummary & { playtime_min: number; hours: number };

export type Player = {
  steamid: string;
  name: string | null;
  avatar: string | null;
  url: string | null;
  cc: string;
  n_owned: number;
  n_played: number;
  games: PlayerGame[];
};

export type Metric = {
  value: number | null;
  genre_avg: number | null;
  all_avg: number | null;
  genre_pct_below: number | null;
  all_pct_below: number | null;
};

export type GameDetail = GameSummary & {
  release_date: string | null;
  developer: string | null;
  publisher: string | null;
  description: string | null;
  steam_rating_label: string | null;
  positive: number | null;
  negative: number | null;
  owners_lo: number | null;
  owners_hi: number | null;
  primary_genre: string;
  n_genre: number;
  n_all: number;
  metrics: Record<
    "price" | "rating" | "reviews" | "owners" | "hours" | "median_hours" | "peak_ccu" | "achievements",
    Metric
  >;
};
