"""Modal app: serves Supabase game data as JSON endpoints for the Streamlit dashboard.
Setup:  modal secret create supabase-secret SUPABASE_DB_URL=postgresql://...
Deploy: modal deploy modal_app.py
"""
import modal

app = modal.App("steam-games-api")
image = modal.Image.debian_slim().pip_install("psycopg2-binary", "fastapi[standard]")


@app.function(image=image, secrets=[modal.Secret.from_name("supabase-secret")])
@modal.fastapi_endpoint(method="GET")
def query(sql_name: str = "genres"):
    import os
    import psycopg2
    import psycopg2.extras

    queries = {
        "genres": "select primary_genre, count(*) n, round(avg(price),2) avg_price from games where primary_genre is not null group by 1 order by n desc limit 20",
        "by_year": "select extract(year from release_date)::int yr, count(*) n, round(avg(price),2) avg_price from games where release_date is not null group by 1 order by 1",
        "top_rated": "select name, positive, negative, price from games where positive + negative >= 1000 order by positive::float/(positive+negative) desc limit 25",
        "deals": "select name, primary_genre, price, discount, positive, negative, median_playtime_forever, round(100.0*positive/(positive+negative),1) as pct_positive, round((100.0*positive/(positive+negative))/price,1) as value_score from games where discount > 0 and price > 0 and positive + negative >= 200 order by value_score desc limit 400",
        "playtime_by_genre": "select primary_genre, round(avg(median_playtime_forever)) median_playtime, count(*) n from games where primary_genre is not null and median_playtime_forever > 0 group by 1 having count(*) >= 50 order by 2 desc limit 20",
        "catalog": "select app_id, name, price, round(100.0*positive/(positive+negative),1) as rating, (owners_min+owners_max)/2 as owners, array_to_string((string_to_array(coalesce(nullif(tags,''), genres), ','))[1:5], ',') as tags from games where positive + negative >= 1000 and release_date is not null and (tags <> '' or genres <> '') order by positive + negative desc limit 3000",
        "genre_success": "select t as genre, count(*) n, round(avg(100.0*positive/(positive+negative)),1) rating, round(avg(price),2) price, sum((owners_min+owners_max)/2) owners from (select unnest((string_to_array(tags, ','))[1:5]) t, positive, negative, price, owners_min, owners_max from games where positive + negative >= 50 and tags <> '') s group by t having count(*) >= 100 order by sum((owners_min+owners_max)/2) desc limit 60",
    }
    if sql_name not in queries:
        return {"error": f"unknown query; choose from {list(queries)}"}
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"])
    with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(queries[sql_name])
        return {"rows": cur.fetchall()}
