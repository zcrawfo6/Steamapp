# KNN recommender (by RShea42)

Copied from [RShea42/DTSC3602_Models](https://github.com/RShea42/DTSC3602_Models) `Steam_KNN_Recommender/`
at commit `b20face8422c7b968e4c18f9466f515fc5bdec37`.

- `features.py`: catalog features (TF-IDF tag vectors, game families, adult/software/non-game flags) and `load_features()`.
- `recommend.py`: content-based KNN. Liked = most-played games (recency weighted), disliked = briefly played games;
  score = tag similarity minus dislike similarity, blended with review quality. Settings live in `RecConfig`.
- `artifacts/`: prebuilt features (`games.parquet`, `tag_matrix.npz`, `vocab.json`, `build_info.json`).

Only change from upstream: `recommend.py` imports `.features` (package-relative) instead of `features`.
To refresh, rebuild `artifacts/` in Rob's repo (`python features.py --csv games_cleaned.csv`) and copy them here.
