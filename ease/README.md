# EASE-safe recommender (Juan's model)

TasteForge's recommendations come from **EASE-safe**, taken from
[RShea42/DTSC3602_Models](https://github.com/RShea42/DTSC3602_Models/tree/main/Steam_EASE_Safe_Recommender)
(commit `82bf4bc`). The model, the safe re-rank and its settings are unchanged. See that folder's README for
how it was trained and evaluated.

- **EASE** learns one item-to-item weight matrix from which games players played together. A player's scores are
  the sum of the rows for the games they played.
- **Safe re-rank:** EASE's top 50 are re-scored as
  `z(score) − 0.5 × like_quit − 1 × short_game − 10 × negative_reviews` (`rerank_choice.json`).

| File | What |
|---|---|
| `recommender.py` | Model loading, EASE scores, safe re-rank, budget filter, live Steam prices, per-pick explanation |
| `flags.py` | The team's flag definitions (`NEG`, `tag_matrix`), copied from `team_eval/evaluate.py` |
| `rerank_choice.json` | Re-rank weights, copied from `team_eval/rerank_choice.json` |

## Data files (not in git)

The app reads two folders, set like Juan's app (in `.streamlit/secrets.toml` or as environment variables).
Both default to `ease/artifacts/`, so the simplest setup is to put all four files there:

```
STEAMREC_ARTIFACTS/ease.npz                  trained EASE weights, ~335 MB   (model/build_ease.py)
STEAMREC_ARTIFACTS/items.parquet             per-game playtime quantiles     (model/build_model.py)
STEAMREC_DATA/games.parquet                  Juan's cleaned catalog
STEAMREC_DATA/team_eval/games.parquet        shared team catalog for the soft-fail flags
```

### Downloading them from Supabase

They're in the team Supabase project: **Storage → `team-eval` bucket**.

- `ease_safe/`: the model split into 8 parts (Supabase's 50 MB upload limit), plus the other files and a
  `README.txt` with the command to rejoin the parts, a checksum to verify, and where each file goes.
- `games.parquet` at the top of the bucket: the shared team catalog. It goes in `STEAMREC_DATA/team_eval/`.

Follow `ease_safe/README.txt`, then check the rejoined `ease.npz` against the checksum it lists
(PowerShell: `Get-FileHash ease.npz`). For reference, the `ease.npz` in Juan's `EASE_safe_data.zip` (Nov 12, 2026)
has SHA-256 `11888b3f7308960c41d38d12e59b830e0afd73fe82041a58542c4c888c8aeb8b`.

If you unzipped Juan's `EASE_safe_data.zip` instead, either move the files into `ease/artifacts/` as above, or
point the settings at it:

```
STEAMREC_ARTIFACTS = "<unzip folder>/model/artifacts"
STEAMREC_DATA      = "<unzip folder>/data_clean"
```

Without the files the app still runs: the Recommendations tab and the Compare tab's recommendations list the
missing paths, and the Player Profile still works. The model takes ~330 MB of memory and loads once per server.
