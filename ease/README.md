# EASE-safe recommender (Juan's model)

TasteForge's recommendations come from **EASE-safe**, taken from
[RShea42/DTSC3602_Models](https://github.com/RShea42/DTSC3602_Models/tree/main/Steam_EASE_Safe_Recommender)
(commit `e8f7531`). The model, the safe re-rank and its settings are unchanged. See that folder's README for
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

Put these in `ease/artifacts/` (ignored by git), or point `EASE_DATA_DIR` in `.streamlit/secrets.toml` at
another folder with the same layout:

```
ease.npz                  trained EASE weights, ~330 MB      (model/build_ease.py)
items.parquet             per-game playtime quantiles        (model/build_model.py)
games.parquet             Juan's cleaned catalog             (data_clean/games.parquet)
team_eval/games.parquet   shared team catalog for the flags  (Supabase bucket "team-eval")
```

Without them the app still runs: the Recommendations tab and the Compare tab's recommendations show which files are
missing, and the Player Profile still works. The model takes ~330 MB of memory and loads once per server.
