"""Load games_slim.csv into Supabase Postgres. Usage: set SUPABASE_DB_URL, then python upload_to_supabase.py"""
import io, os
import pandas as pd
import psycopg2

df = pd.read_csv("games_slim.csv").dropna(subset=["name"])
conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"])
with conn, conn.cursor() as cur:
    cur.execute(open("schema.sql", encoding="utf-8-sig").read())
    cur.execute("truncate public.games")
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cur.copy_expert(f"copy public.games ({','.join(df.columns)}) from stdin with csv", buf)
    cur.execute("select count(*) from public.games")
    print("rows loaded:", cur.fetchone()[0])
