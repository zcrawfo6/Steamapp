# TasteForge - Steam Game Recommender Dashboard

Team 3 Billion (DTSC 3602). Streamlit dashboard over a Supabase (Postgres) database of ~125k Steam games, served through a Modal API.

## Architecture
Kaggle Steam games CSV -> `upload_to_supabase.py` -> Supabase `games` table -> `modal_app.py` (read-only query endpoint) -> `app.py` (Streamlit)

## Run the dashboard
1. `git clone https://github.com/zcrawfo6/Steamapp.git` and `cd Steamapp`
2. `pip install -r requirements.txt`
3. Create `.streamlit/secrets.toml` containing: `MODAL_API_URL = "https://zcrawfo6--steam-games-api-query.us-east.modal.run"`
4. `streamlit run app.py`

## Rebuild the data / backend (only if needed)
- `games_slim.csv` (31 MB, cleaned from the Kaggle Steam games dataset: merged "Discount"/"DLC count" header fixed, large text columns dropped) is included in the repo.
- Set `SUPABASE_DB_URL` (Session pooler URI), then `python upload_to_supabase.py`.
- `modal secret create supabase-secret SUPABASE_DB_URL=...` then `modal deploy modal_app.py`.

Never commit database passwords. The API only runs a fixed set of read-only queries.

## Contributors

- zcrawfo6
- Peyton
