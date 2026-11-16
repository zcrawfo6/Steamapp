# TasteForge (Vercel)

A Next.js port of the TasteForge Streamlit dashboard (`Steamapp_Juan_Model`). Recommendations come from Juan's
**EASE-safe** model, served as an API on Modal (`../Juan_EASE/modal_api.py`).

```
browser ──> Next.js on Vercel ──/api/m/*──> Modal API (EASE-safe, FastAPI) ──> Steam Web API (profiles)
                       └──/api/shots──> Steam store (screenshots)
```

The browser only talks to this site. The Modal URL and its bearer token stay on the server (`app/api/m/[...path]/route.ts`).
That route only forwards a fixed list of paths.

## Features
- **Recommendations**: search games and add them, or import a public Steam library, or try a demo profile. You get the
  EASE-safe "For you" picks plus "Try something new". Each pick shows a match receipt (because you played, tags, price,
  soft-fail flags), screenshots, a "Why this pick" breakdown, and budget presets.
- **Player Profile**: genre radar, where your hours go, price comfort zone, play style (story / co-op / PvP),
  archetype, and the library's "world".
- **Compare**: another public Steam profile's taste match, genre shares, shared games, each other's favorites, and
  both recommendation lists.
- **Game page** (`/game/[appid]`): an animated world header (ported from `themes.py`), reviews, standing in its genre,
  and stats vs genre and catalog averages.
- **Advanced mode**: per-game hours, play modes and their share of hours, a budget slider, and an adult-games toggle.
  The library is kept in this browser only (localStorage).

## Run locally
```
npm install
# .env.local (not committed)
MODAL_API_URL=https://sirjacket42--steam-ease-api-api-web.us-east.modal.run
MODAL_API_TOKEN=<API_TOKEN from the Modal secret steam-ease-api>
npm run dev        # http://localhost:3000
```

## Deploy to Vercel
1. Push this folder to its own GitHub repo, then import it in Vercel (framework preset: Next.js).
2. Under Project → Settings → Environment Variables, set `MODAL_API_URL` and `MODAL_API_TOKEN`.
3. Deploy. The first request after the Modal API has been idle can take a few seconds while it wakes up.

| Path | What |
|---|---|
| `app/page.tsx` | Home: hero, search, tabs |
| `app/game/[appid]/` + `components/GameView.tsx` | Game stats page |
| `app/api/m/[...path]/route.ts` | Proxy to Modal (adds the token) |
| `app/api/shots/route.ts` | Steam store screenshots |
| `lib/themes.ts` | Worlds, skylines, particles, shelf backdrop (port of `themes.py`) |
| `lib/profile.ts` | Profile math (port of `app.py`'s `profile`, `modes_for`, `taste_match`) |
| `lib/store.tsx` | Library and settings state (localStorage) |
