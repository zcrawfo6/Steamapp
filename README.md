# TasteForge - Steam Game Recommender Dashboard

Team 3 Billion (DTSC 3602). Streamlit dashboard over a Supabase (Postgres) database of ~125k Steam games, served through a Modal API.

## Architecture
Kaggle Steam games CSV -> `upload_to_supabase.py` -> Supabase `games` table -> `modal_app.py` (read-only query endpoint) -> `app.py` (Streamlit)

## Run the dashboard
1. `git clone https://github.com/zcrawfo6/Steamapp.git` and `cd Steamapp`
2. `pip install -r requirements.txt`
3. Create `.streamlit/secrets.toml` containing: `MODAL_API_URL = "https://zcrawfo6--steam-games-api-query.us-east.modal.run"`
4. Optional, for **Import from Steam**: get a Steam Web API key at https://steamcommunity.com/dev/apikey and add `STEAM_API_KEY = "..."` to the same `secrets.toml`
5. `streamlit run app.py`

## Recommender (KNN model by RShea42)
Recommendations come from the KNN recommender in [RShea42/DTSC3602_Models](https://github.com/RShea42/DTSC3602_Models),
copied into `knn/` with its prebuilt `knn/artifacts/` (see `knn/README.md`). A player's most-played games
(recency weighted when imported from Steam) define their taste, and briefly played games count as dislikes. Every
unowned game is scored by tag similarity to the liked games, minus similarity to the dislikes, blended with review
quality. `app.py` keeps the cards, Player Profile and Compare UI and filters the model's list to the catalog and budget.
Advanced mode exposes the review-quality weight, dislike strength and minimum reviews.

## Import from Steam
Click **Sign in through Steam** in the sidebar. Steam's own login page (OpenID) sends you back with your Steam ID, which the app verifies with Steam, then it pulls your library with `GetOwnedGames` (`steam_import.py`) and loads your most-played games that are in the catalog (up to 40) with their lifetime hours. The app never sees your Steam password. Your profile's "Game details" must be public.

As a fallback you can type a custom URL name, profile URL, or SteamID64 instead (resolved with `ResolveVanityURL`).

## Compare with another player
The **Compare** tab loads another player's library (pick from your Steam friends when signed in, or type their profile) and shows a taste-match score, games you both play, genre shares side by side, each other's favorites the other hasn't played, and both players' recommendations, flagging picks you'd both get. Their "Game details" must be public; picking from friends also needs your friends list to be public.

If the app runs anywhere other than `http://localhost:8501/`, set `APP_URL = "https://your-app-address/"` in `secrets.toml` so Steam redirects back to the right place.

## Rebuild the data / backend (only if needed)
- `games_slim.csv` (31 MB, cleaned from the Kaggle Steam games dataset: merged "Discount"/"DLC count" header fixed, large text columns dropped) is included in the repo.
- Set `SUPABASE_DB_URL` (Session pooler URI), then `python upload_to_supabase.py`.
- `modal secret create supabase-secret SUPABASE_DB_URL=...` then `modal deploy modal_app.py`.

Never commit database passwords. The API only runs a fixed set of read-only queries.

## Contributors

- zcrawfo6
- Peyton
