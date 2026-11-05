"""Atmosphere engine for TasteForge.

Every game tag can pull the page toward a "world" (medieval, cyberpunk, horror ...). A world is a palette,
a font pairing, a drifting particle effect (embers, neon rain, stars ...), and a skyline silhouette drawn as SVG.
Pure Python, no pandas: app.py hands in plain lists.
"""
import math
import random
import zlib
from functools import lru_cache
from urllib.parse import quote

FONT_URL = ("https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;900&family=DM+Sans:wght@400;500;700"
            "&family=Cinzel:wght@600;800&family=EB+Garamond:wght@400;600&family=Orbitron:wght@600;900"
            "&family=Rajdhani:wght@500;700&family=Audiowide&family=Exo+2:wght@400;600&family=Creepster"
            "&family=Lora:wght@400;600&family=Fredoka:wght@500;700&family=Nunito:wght@400;700&family=Press+Start+2P"
            "&family=Space+Mono:wght@400;700&family=Black+Ops+One&family=Saira+Condensed:wght@400;600"
            "&family=Mochiy+Pop+One&family=Zen+Maru+Gothic:wght@400;700&family=Russo+One&family=Chakra+Petch:wght@400;600"
            "&family=Playfair+Display:wght@700;900&family=Libre+Franklin:wght@400;600&display=swap")

DEFAULT = "forge"

# ---------------------------------------------------------------- worlds
THEMES = {
    "forge": dict(
        name="The Forge", icon="🔥", tag="Hammer your taste into shape.",
        disp="'Big Shoulders Display',Impact,sans-serif", body="'DM Sans',system-ui,sans-serif",
        c=dict(bg="#100c0a", panel="rgba(30,22,17,.82)", panel2="rgba(48,34,25,.9)", line="#4a3526",
               text="#f3e9df", mute="#b39a85", accent="#ff7a2f", accent2="#ffc857"),
        bg="radial-gradient(1000px 500px at 85% -10%,rgba(255,120,40,.16),transparent 60%),"
           "radial-gradient(900px 400px at 10% 110%,rgba(255,90,20,.18),transparent 60%)",
        ov="radial-gradient(900px 260px at 50% 108%,rgba(255,110,30,.35),transparent 70%),"
           "radial-gradient(ellipse at center,transparent 60%,rgba(0,0,0,.45) 100%)",
        grad="linear-gradient(180deg,#2a140a,#6a2c0e)", sil="#0c0605", skyk="foundry",
        part=("ember", "#ffb347", 26), flick=True, tags={},
        deco=""),
    "medieval": dict(
        name="Age of Steel", icon="⚔️", tag="Torchlight, stone halls and sharpened steel.",
        disp="'Cinzel',Georgia,serif", body="'EB Garamond',Georgia,serif",
        c=dict(bg="#12100c", panel="rgba(30,24,17,.84)", panel2="rgba(46,37,25,.92)", line="#5a4a2c",
               text="#efe6d2", mute="#b3a381", accent="#d0584a", accent2="#f0c75e"),
        bg="radial-gradient(1100px 600px at 50% -15%,rgba(120,80,30,.35),transparent 65%),"
           "radial-gradient(700px 500px at 0% 100%,rgba(255,140,40,.2),transparent 60%),"
           "radial-gradient(700px 500px at 100% 100%,rgba(255,140,40,.2),transparent 60%)",
        ov="radial-gradient(ellipse at center,transparent 50%,rgba(0,0,0,.6) 100%)",
        grad="linear-gradient(180deg,#1d1a2a,#6b3b1a)", sil="#080604", skyk="castle",
        part=("ember", "#ffa94d", 26), flick=True,
        tags={"medieval": 3, "dark fantasy": 2.5, "fantasy": 1.5, "souls-like": 2, "historical": 1.5,
              "hack and slash": 1, "dungeon crawler": 1.5, "party-based rpg": 1, "tactical rpg": 1,
              "swordplay": 2, "grand strategy": 1},
        deco=".fx .deco{left:9vw;top:8vh;width:92px;height:92px;border-radius:50%;"
             "background:radial-gradient(circle at 40% 40%,#fff8e0,#d9c48a);"
             "box-shadow:0 0 60px 16px rgba(240,200,120,.18);opacity:.75}"),
    "cyber": dict(
        name="Neon Sprawl", icon="🌃", tag="Neon rain. Chrome nerves. Static in the sky.",
        disp="'Chakra Petch','Rajdhani',sans-serif", body="'Rajdhani',sans-serif",
        c=dict(bg="#05060f", panel="rgba(10,12,30,.82)", panel2="rgba(22,22,52,.9)", line="#2c2f6e",
               text="#e6f1ff", mute="#8a96cf", accent="#19d3ff", accent2="#ff3fb8"),
        bg="radial-gradient(1000px 520px at 20% -10%,rgba(255,63,184,.16),transparent 60%),"
           "radial-gradient(900px 500px at 90% 0%,rgba(25,211,255,.14),transparent 60%),"
           "linear-gradient(180deg,#05060f 0%,#0b0a22 55%,#1a0c30 100%)",
        # no CRT scanlines (that was the arcade look): a smoggy horizon glow and a vignette instead
        ov="radial-gradient(ellipse 80% 40% at 50% 100%,rgba(255,63,184,.22),transparent 70%),"
           "linear-gradient(180deg,transparent 55%,rgba(25,211,255,.07)),"
           "radial-gradient(ellipse at center,transparent 55%,rgba(0,0,0,.5) 100%)",
        grad="linear-gradient(180deg,#0b0a22,#4a1466)", sil="#04040c", skyk="neon",
        part=("rain", "#8fe8ff", 60),
        tags={"cyberpunk": 3, "robots": 1.5, "mechs": 1.2, "immersive sim": 1, "futuristic": 2,
              "transhumanism": 2, "hacking": 2, "sci-fi": 0.8},
        # tall megacity skyline, faint searchlight beams, and two flying-car light streaks crossing the sky
        deco=".fx .sky{height:46vh}.fx .deco{inset:0;"
             "background:linear-gradient(104deg,transparent 30%,rgba(25,211,255,.07) 31%,transparent 36%),"
             "linear-gradient(76deg,transparent 64%,rgba(255,63,184,.06) 65%,transparent 70%)}"
             ".fx .deco::before,.fx .deco::after{content:'';position:absolute;top:22vh;left:-12%;width:70px;height:3px;"
             "border-radius:3px;background:linear-gradient(90deg,transparent,#fff,#ff3fb8);"
             "box-shadow:0 0 12px 3px rgba(255,63,184,.7);animation:carpass 14s linear infinite}"
             ".fx .deco::after{top:31vh;width:46px;background:linear-gradient(90deg,transparent,#fff,#19d3ff);"
             "box-shadow:0 0 12px 3px rgba(25,211,255,.7);animation-duration:21s;animation-delay:-8s;"
             "animation-direction:reverse}@keyframes carpass{from{left:-12%}to{left:112%}}"
             # type two notches smaller for this theme only, in the main area (not the sidebar, which stays fixed)
             "[data-testid=stMain] :is(p,li,label){font-size:.875rem}.stApp .sub{font-size:12px}.stApp .why,.stApp .mh,.stApp .todo,.stApp table.t{font-size:11px}"
             ".stApp .mh.sm,.stApp .kpi span,.stApp .chip,.stApp .note{font-size:10px}.stApp .card h2{font-size:11px}"
             ".stApp .rec h3,.stApp .price{font-size:16px}.stApp .kpi b{font-size:22px}"
             ".stApp h5{font-size:13px}.stTabs [data-baseweb=tab] p{font-size:13px}"),
    "space": dict(
        name="Deep Void", icon="🪐", tag="Silence, starlight and a long way from home.",
        disp="'Audiowide',sans-serif", body="'Exo 2',sans-serif",
        c=dict(bg="#05070f", panel="rgba(10,16,36,.8)", panel2="rgba(20,28,62,.9)", line="#28407a",
               text="#e6eeff", mute="#8da2d6", accent="#7aa2ff", accent2="#b388ff"),
        bg="radial-gradient(900px 600px at 20% 10%,rgba(120,80,255,.28),transparent 60%),"
           "radial-gradient(800px 600px at 85% 70%,rgba(40,120,255,.22),transparent 60%),"
           "radial-gradient(500px 400px at 55% 40%,rgba(255,80,180,.12),transparent 60%)",
        ov="none",
        grad="linear-gradient(180deg,#05061a,#2a1a6a)", sil="#040612", skyk="peaks",
        part=("stars", "#dfe8ff", 70),
        tags={"sci-fi": 2, "space": 3, "4x": 1.5, "flight": 1, "space sim": 3, "aliens": 2, "colony sim": 0.5,
              "futuristic": 0.5},
        deco=".fx .deco{right:-5vw;bottom:14vh;width:30vw;max-width:460px;aspect-ratio:1;border-radius:50%;"
             "background:radial-gradient(circle at 35% 35%,#8a6cff 0,#32207f 55%,#0a0a2a 100%);opacity:.8}"
             ".fx .deco::after{content:'';position:absolute;inset:-14% -38%;border:3px solid rgba(190,170,255,.4);"
             "border-radius:50%;transform:rotate(-18deg) scaleY(.26)}"),
    "horror": dict(
        name="The Haunting", icon="🕯️", tag="Something is watching. Keep playing.",
        disp="'Creepster',cursive", body="'Lora',Georgia,serif",
        c=dict(bg="#0b0809", panel="rgba(22,12,14,.84)", panel2="rgba(40,18,22,.92)", line="#4d1d22",
               text="#eadcd8", mute="#a58a86", accent="#c0242f", accent2="#e0cfa8"),
        bg="radial-gradient(1000px 600px at 50% 0%,rgba(120,15,25,.28),transparent 65%)",
        ov="radial-gradient(ellipse at center,transparent 35%,rgba(0,0,0,.78) 100%)",
        grad="linear-gradient(180deg,#1a0508,#4a0f16)", sil="#050304", skyk="tombs",
        part=("fog", "#8c7f86", 7), flick=True,
        tags={"horror": 3, "psychological horror": 3, "survival horror": 3, "zombies": 2, "gore": 1.5,
              "lovecraftian": 3, "dark": 1.2, "thriller": 1.5, "supernatural": 2, "atmospheric": 0.3},
        deco=".fx .deco{right:12vw;top:9vh;width:150px;height:150px;border-radius:50%;"
             "background:radial-gradient(circle at 40% 40%,#d9442f,#7a1117 70%);"
             "box-shadow:0 0 90px 24px rgba(200,30,40,.28);opacity:.7}"),
    "cozy": dict(
        name="Lantern Hollow", icon="🏡", tag="Warm lanterns, soft light, no rush.",
        disp="'Fredoka',sans-serif", body="'Nunito',sans-serif",
        c=dict(bg="#17131f", panel="rgba(36,28,50,.8)", panel2="rgba(54,42,72,.9)", line="#5a4a78",
               text="#f6ecf5", mute="#b9a6c9", accent="#ff9eb5", accent2="#ffd98a"),
        bg="radial-gradient(1100px 600px at 50% 110%,rgba(255,150,100,.28),transparent 60%),"
           "radial-gradient(900px 500px at 80% -10%,rgba(140,100,220,.28),transparent 60%)",
        ov="none",
        grad="linear-gradient(180deg,#2a2050,#e07a6a)", sil="#120d1c", skyk="hills",
        part=("firefly", "#ffe38a", 22),
        tags={"cozy": 3, "farming sim": 2.5, "relaxing": 2.5, "cute": 2, "life sim": 2, "casual": 1,
              "family friendly": 1.5, "wholesome": 3, "crafting": 0.4, "building": 0.4},
        deco=".fx .deco{left:12vw;top:10vh;width:100px;height:100px;border-radius:50%;background:#ffe9b0;"
             "box-shadow:0 0 70px 14px rgba(255,220,140,.3);opacity:.8}"),
    "retro": dict(
        name="Arcade Wave", icon="👾", tag="Insert coin. High scores forever.",
        disp="'Press Start 2P',monospace", body="'Space Mono',monospace",
        c=dict(bg="#0d0221", panel="rgba(26,8,52,.82)", panel2="rgba(44,14,84,.9)", line="#5b2a9e",
               text="#fdf1ff", mute="#c19be0", accent="#ff4fa3", accent2="#3df5ff"),
        bg="linear-gradient(180deg,rgba(255,79,163,0) 0,rgba(255,79,163,.18) 70%,rgba(61,245,255,.15) 100%),"
           "radial-gradient(900px 500px at 50% 0%,rgba(120,40,200,.35),transparent 65%)",
        ov="repeating-linear-gradient(0deg,rgba(0,0,0,.2) 0 1px,transparent 1px 3px)",
        grad="linear-gradient(180deg,#1a0540,#ff4fa3)", sil="#14052e", skyk="pixel",
        part=("pixel", "#3df5ff", 30),
        tags={"pixel graphics": 2, "retro": 3, "arcade": 3, "classic": 1.5, "platformer": 1.2, "shoot 'em up": 2,
              "bullet hell": 2, "2d platformer": 1.5, "side scroller": 1, "beat 'em up": 1.5, "rhythm": 1.5,
              "metroidvania": 1, "pinball": 2},
        deco=".fx .deco{left:50%;bottom:20vh;width:26vw;max-width:360px;aspect-ratio:1;transform:translateX(-50%);"
             "border-radius:50%;background:linear-gradient(#ffe66d,#ff4fa3);opacity:.55;"
             "-webkit-mask-image:linear-gradient(#000 0 50%,transparent 50% 54%,#000 54% 66%,transparent 66% 71%,"
             "#000 71% 81%,transparent 81% 87%,#000 87%);"
             "mask-image:linear-gradient(#000 0 50%,transparent 50% 54%,#000 54% 66%,transparent 66% 71%,"
             "#000 71% 81%,transparent 81% 87%,#000 87%)}"),
    "war": dict(
        name="Ashfall", icon="🪖", tag="Smoke on the horizon. Hold the line.",
        disp="'Black Ops One',sans-serif", body="'Saira Condensed',sans-serif",
        c=dict(bg="#0e100c", panel="rgba(24,27,20,.84)", panel2="rgba(38,43,30,.92)", line="#4a5238",
               text="#e4e6d8", mute="#9ea58a", accent="#9aa84a", accent2="#e0a030"),
        bg="radial-gradient(1000px 500px at 50% 110%,rgba(255,140,40,.2),transparent 60%),"
           "radial-gradient(900px 500px at 20% -10%,rgba(120,130,90,.18),transparent 60%)",
        ov="radial-gradient(ellipse at center,transparent 45%,rgba(0,0,0,.55) 100%),"
           "repeating-linear-gradient(0deg,rgba(0,0,0,.08) 0 2px,transparent 2px 5px)",
        grad="linear-gradient(180deg,#2a2a1a,#8a5a20)", sil="#080905", skyk="ruins",
        part=("ash", "#b9b9a8", 34),
        tags={"post-apocalyptic": 3, "war": 3, "world war ii": 3, "military": 2.5, "wargame": 2.5,
              "survival": 0.8, "open world survival craft": 0.8, "tactical": 1, "fps": 0.5, "shooter": 0.4,
              "real time tactics": 1.5, "turn-based tactics": 1},
        deco=".fx .deco{left:50%;top:-14vh;width:60vw;height:50vh;transform:translateX(-50%);"
             "background:radial-gradient(closest-side,rgba(255,179,71,.5),rgba(255,140,40,.2) 45%,transparent 75%)}"),
    "anime": dict(
        name="Sakura Dreams", icon="🌸", tag="Petals drift. Every story is a love letter.",
        disp="'Mochiy Pop One',sans-serif", body="'Zen Maru Gothic',sans-serif",
        c=dict(bg="#1a1020", panel="rgba(42,24,54,.8)", panel2="rgba(62,36,78,.9)", line="#7a4a96",
               text="#fff0f8", mute="#d3a9d9", accent="#ff7fb0", accent2="#8fd7ff"),
        bg="radial-gradient(1000px 600px at 80% -10%,rgba(255,127,176,.3),transparent 60%),"
           "radial-gradient(900px 600px at 0% 100%,rgba(143,215,255,.2),transparent 60%)",
        ov="none",
        grad="linear-gradient(180deg,#3a2060,#ff9cc6)", sil="#1a0f24", skyk="fuji",
        part=("petal", "#ffb7d5", 26),
        tags={"anime": 3, "visual novel": 2.5, "dating sim": 2.5, "romance": 2, "jrpg": 2, "manga": 3,
              "otome": 3, "female protagonist": 0.3},
        deco=".fx .deco{right:8vw;top:9vh;width:14vw;max-width:200px;aspect-ratio:1;border-radius:50%;"
             "background:radial-gradient(circle at 35% 35%,#fff,#ffd6ea 60%,#ff9cc6);"
             "box-shadow:0 0 80px 20px rgba(255,150,200,.35);opacity:.85}"),
    "racing": dict(
        name="Redline", icon="🏁", tag="Redline everything.",
        disp="'Russo One',sans-serif", body="'Chakra Petch',sans-serif",
        c=dict(bg="#0a0c10", panel="rgba(18,22,30,.84)", panel2="rgba(30,36,50,.92)", line="#3a4660",
               text="#f0f4fa", mute="#98a6c0", accent="#ff3b30", accent2="#ffd60a"),
        bg="radial-gradient(900px 500px at 100% 0%,rgba(255,59,48,.25),transparent 60%),"
           "linear-gradient(115deg,rgba(255,214,10,.06),transparent 40%)",
        ov="repeating-linear-gradient(115deg,rgba(255,255,255,.025) 0 2px,transparent 2px 36px)",
        grad="linear-gradient(180deg,#10141c,#b8281f)", sil="#07090d", skyk="road",
        part=("streak", "#ffd60a", 18),
        tags={"racing": 3, "driving": 2.5, "sports": 1.5, "automobile sim": 3, "parkour": 1, "fast-paced": 0.8,
              "football": 2, "basketball": 2, "soccer": 2},
        deco=""),
    "noir": dict(
        name="Midnight Case", icon="🕵️", tag="Rain on the glass. Every case has a secret.",
        disp="'Playfair Display',Georgia,serif", body="'Libre Franklin',sans-serif",
        c=dict(bg="#0c0c0e", panel="rgba(22,22,26,.84)", panel2="rgba(36,36,42,.92)", line="#46464f",
               text="#ece8df", mute="#a09c92", accent="#9a9aa6", accent2="#e5c07b"),
        bg="radial-gradient(1000px 600px at 20% -10%,rgba(230,200,140,.14),transparent 60%)",
        ov="radial-gradient(ellipse at center,transparent 50%,rgba(0,0,0,.6) 100%)",
        grad="linear-gradient(180deg,#141416,#3c3c44)", sil="#060607", skyk="noir",
        part=("rain", "#a8a8b4", 40),
        tags={"detective": 3, "crime": 2.5, "mystery": 2.5, "stealth": 1.2, "noir": 3, "point & click": 0.8,
              "interactive fiction": 0.8, "investigation": 3},
        deco=".fx .deco{inset:0;background:repeating-linear-gradient(115deg,rgba(255,240,200,.07) 0 38px,"
             "transparent 38px 90px);-webkit-mask-image:linear-gradient(120deg,#000 0,transparent 60%);"
             "mask-image:linear-gradient(120deg,#000 0,transparent 60%)}"),
}

# ---------------------------------------------------------------- picking a world
def tag_scores(genres):
    s = {}
    for g in genres:
        k = str(g).strip().lower()
        for tk, t in THEMES.items():
            w = t["tags"].get(k)
            if w:
                s[tk] = s.get(tk, 0) + w
    return s


def theme_for(genres):
    """World for one game or one custom category (list of tags)."""
    s = tag_scores(genres)
    return max(s, key=s.get) if s else DEFAULT


# worlds that feel alike back each other up when games are compared
RELATED = {frozenset(p) for p in (("cyber", "noir"), ("cyber", "space"), ("cyber", "retro"), ("medieval", "horror"),
                                  ("cozy", "anime"))}


def theme_for_library(games):
    """games: [(name, genres, hours)] -> (world, names of the games that decided it).

    Each game votes for its best world, weighted by its hours; related worlds lend each other half their votes so a
    cluster of similar games beats a few stray ones. Inside the winning cluster the world of the game with the
    most hours wins.
    """
    direct, drivers = {}, {}
    for name, genres, hours in games:
        s = tag_scores(genres)
        if not s:
            continue
        best = max(s, key=s.get)
        w = hours * (.75 + .25 * min(s[best], 3) / 3)
        direct[best] = direct.get(best, 0) + w
        drivers.setdefault(best, []).append((w, name))
    if not direct:
        return DEFAULT, []
    total = {t: direct[t] + .5 * sum(v for u, v in direct.items() if frozenset((t, u)) in RELATED) for t in direct}
    key = max(direct, key=lambda t: (total[t], max(drivers[t])[0], direct[t]))
    return key, [n for _, n in sorted(drivers[key], reverse=True)[:3]]


# ---------------------------------------------------------------- skylines (SVG silhouettes)
def _poly(pts, fill):
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'


def _castle(fill, lit):
    r = random.Random(7)
    o = f'<rect x="0" y="140" width="1200" height="60" fill="{fill}"/>'
    o += "".join(f'<rect x="{x}" y="130" width="12" height="12" fill="{fill}"/>' for x in range(0, 1200, 24))
    x = 30
    while x < 1160:
        w, h = r.choice([46, 56, 66]), r.randint(70, 150)
        y = 200 - h
        o += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'
        o += "".join(f'<rect x="{x + k}" y="{y - 10}" width="7" height="11" fill="{fill}"/>' for k in range(0, w - 6, 13))
        if r.random() < .55:
            o += _poly([f"{x - 5},{y - 9}", f"{x + w / 2},{y - 58}", f"{x + w + 5},{y - 9}"], fill)
        o += f'<rect x="{x + w / 2 - 3}" y="{y + 22}" width="6" height="14" fill="{lit}"/>'
        x += w + r.randint(60, 150)
    return o


def _city(fill, wins, seed, density=.5, maxh=170, broken=False, antenna=False):
    r = random.Random(seed)
    x, o = 0, ""
    while x < 1200:
        w, h = r.randint(36, 90), r.randint(50, maxh)
        y = 200 - h
        if broken:
            pts = ["%d,200" % x, "%d,%d" % (x, y)]
            pts += ["%d,%d" % (x + w * k / 4, y + r.randint(0, 28)) for k in range(1, 4)]
            pts += ["%d,%d" % (x + w, y + r.randint(0, 20)), "%d,200" % (x + w)]
            o += _poly(pts, fill)
        else:
            o += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'
            if antenna and r.random() < .3:
                o += f'<rect x="{x + w // 2}" y="{y - 26}" width="2" height="26" fill="{fill}"/>'
        for wy in range(y + 10, 190, 14):
            for wx in range(x + 6, x + w - 8, 12):
                if wins and r.random() < density:
                    o += f'<rect x="{wx}" y="{wy}" width="5" height="7" fill="{r.choice(wins)}" opacity=".85"/>'
        x += w + r.randint(-6, 6)
    return o


def _megacity(fill, a, a2, seed=21):
    """Cyberpunk skyline in three depth layers: hazy far towers, lit mid towers with neon signs,
    and dark foreground towers with billboards and red aircraft lights; a horizon glow sits behind them."""
    r = random.Random(seed)
    lit = ["#ffd9a0", "#ffd9a0", "#ffd9a0", a, a2]
    o = (f'<defs><linearGradient id="hz" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{a2}" stop-opacity=".5"/>'
         f'<stop offset=".6" stop-color="{a2}" stop-opacity=".1"/><stop offset="1" stop-color="{a2}" stop-opacity="0"/>'
         '</linearGradient></defs><rect x="0" y="0" width="1200" height="200" fill="url(#hz)"/>')
    x = -10  # far layer: tall, pale and hazy
    while x < 1200:
        w, h = r.randint(18, 44), r.randint(100, 192)
        o += f'<rect x="{x}" y="{200 - h}" width="{w}" height="{h}" fill="#3a2a78" opacity=".5"/>'
        if r.random() < .3:
            o += f'<rect x="{x + w // 2}" y="{200 - h - 22}" width="2" height="22" fill="#3a2a78" opacity=".5"/>'
        x += w + r.randint(2, 10)
    x = 0  # mid layer: lit windows, setbacks, vertical neon signs
    while x < 1200:
        w, h = r.randint(30, 66), r.randint(70, 165)
        y = 200 - h
        o += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#110a2e"/>'
        if r.random() < .4:
            o += f'<rect x="{x + w * .2:.0f}" y="{y - 14}" width="{w * .6:.0f}" height="15" fill="#110a2e"/>'
        if r.random() < .2:
            o += (f'<rect x="{x + w - 6}" y="{y + 8}" width="3" height="{r.randint(24, 48)}" '
                  f'fill="{r.choice([a, a2])}" opacity=".95"/>')
        for wy in range(y + 8, 196, 9):
            for wx in range(x + 5, x + w - 6, 7):
                if r.random() < .22:
                    o += f'<rect x="{wx}" y="{wy}" width="3" height="5" fill="{r.choice(lit)}" opacity=".8"/>'
        x += w + r.randint(-4, 8)
    x = r.randint(-30, 20)  # near layer: big dark towers with gaps so the mid layer shows through
    while x < 1200:
        w, h = r.randint(70, 130), r.randint(95, 175)
        y = 200 - h
        o += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'
        ax = x + int(w * .3)
        o += f'<rect x="{ax}" y="{y - 24}" width="2" height="24" fill="{fill}"/><circle cx="{ax + 1}" cy="{y - 26}" r="2" fill="#ff3355"/>'
        if r.random() < .5:
            bw, bh = r.randint(22, 40), r.randint(16, 26)
            bx, by = x + r.randint(6, max(7, w - bw - 6)), y + r.randint(14, 40)
            c = r.choice([a, a2])
            o += (f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{c}" opacity=".9"/>'
                  f'<rect x="{bx + 3}" y="{by + 3}" width="{bw - 6}" height="{bh - 6}" fill="{fill}" opacity=".35"/>')
        for wy in range(y + 12, 196, 11):
            for wx in range(x + 8, x + w - 8, 9):
                if r.random() < .07:
                    o += f'<rect x="{wx}" y="{wy}" width="3" height="5" fill="{r.choice(lit)}" opacity=".85"/>'
        x += w + r.randint(25, 70)
    return o


def _ground(x):
    return 150 + 25 * math.sin(x / 170) + 14 * math.sin(x / 57)


def _hills(fill, glow):
    pts = ["%d,%.1f" % (x, _ground(x)) for x in range(0, 1201, 20)]
    o = _poly(["0,200"] + pts + ["1200,200"], fill)
    r = random.Random(3)
    for _ in range(18):
        x = r.randint(10, 1190)
        yb, h = _ground(x) + 4, r.randint(26, 52)
        for k in range(3):
            w = 16 + k * 7
            o += _poly(["%d,%.1f" % (x - w / 2, yb - k * h / 3.2), "%d,%.1f" % (x, yb - h / 2.2 - k * h / 3.2),
                        "%d,%.1f" % (x + w / 2, yb - k * h / 3.2)], fill)
    for x in (260, 830):
        yb = _ground(x) + 3
        o += f'<rect x="{x - 17}" y="{yb - 24:.1f}" width="34" height="26" fill="{fill}"/>'
        o += _poly(["%d,%.1f" % (x - 23, yb - 23), "%d,%.1f" % (x, yb - 46), "%d,%.1f" % (x + 23, yb - 23)], fill)
        o += f'<rect x="{x - 5}" y="{yb - 16:.1f}" width="9" height="9" fill="{glow}"/>'
    return o


def _tombs(fill):
    pts = ["%d,%.1f" % (x, 168 + 8 * math.sin(x / 90)) for x in range(0, 1201, 20)]
    o = _poly(["0,200"] + pts + ["1200,200"], fill)
    r = random.Random(11)
    for _ in range(22):
        x, h = r.randint(10, 1180), r.randint(20, 40)
        o += f'<rect x="{x}" y="{170 - h + 6}" width="16" height="{h}" rx="8" fill="{fill}"/>'
    for x in (150, 700, 1050):
        o += (f'<path d="M{x},175 L{x},110 L{x - 22},80 M{x},135 L{x + 26},100 M{x},120 L{x - 12},95 '
              f'M{x + 26},100 L{x + 34},80" stroke="{fill}" stroke-width="6" fill="none" stroke-linecap="round"/>')
    return o


def _peaks(fill, seed):
    r = random.Random(seed)
    pts, x = ["0,200"], 0
    while x < 1200:
        pts.append("%d,%d" % (x, r.randint(70, 175)))
        x += r.randint(50, 110)
    return _poly(pts + ["1200,175", "1200,200"], fill)


def _pixel(fill, seed):
    r = random.Random(seed)
    pts, x, y = ["0,200"], 0, 140
    while x < 1200:
        w = r.choice([40, 60, 80, 100])
        pts += [f"{x},{y}", f"{x + w},{y}"]
        x += w
        y = max(90, min(180, y + r.choice([-30, -20, 20, 30])))
    return _poly(pts + ["1200,200"], fill)


def _fuji(fill, blossom):
    o = (f'<path d="M0,200 L0,182 C300,172 420,112 520,84 C560,72 640,72 680,84 C780,112 900,172 1200,182 L1200,200Z" '
         f'fill="{fill}"/>')
    for x, s in ((120, 1), (330, .8), (930, 1.1), (1090, .9)):
        o += f'<rect x="{x - 3}" y="{150 - 10 * s:.0f}" width="6" height="{50 + 10 * s:.0f}" fill="{fill}"/>'
        for dx, dy, rr in ((0, -32, 24), (-18, -16, 18), (18, -16, 18)):
            o += f'<circle cx="{x + dx * s:.0f}" cy="{150 + dy * s:.0f}" r="{rr * s:.0f}" fill="{blossom}" opacity=".85"/>'
    return o


def _road(fill, accent, seed):
    o = _city("#0a0d14", None, seed, maxh=70)
    o += _poly(["0,200", "1200,200", "690,62", "510,62"], fill)
    o += f'<path d="M0,200 L510,62 M1200,200 L690,62" stroke="{accent}" stroke-width="3" fill="none"/>'
    for i in range(6):
        t0, t1 = i / 6, (i + .55) / 6
        y0, y1 = 200 - 138 * t0, 200 - 138 * t1
        w0, w1 = 14 - 12 * t0, 14 - 12 * t1
        o += _poly([f"{600 - w0},{y0}", f"{600 + w0},{y0}", f"{600 + w1},{y1}", f"{600 - w1},{y1}"], "#ffd60a")
    return o


def _sky_svg(key):
    t = THEMES[key]
    f, k, a, a2 = t["sil"], t["skyk"], t["c"]["accent"], t["c"]["accent2"]
    inner = {
        "castle": lambda: _castle(f, "#ffb347"),
        "foundry": lambda: _city(f, ["#ff8a3d"], 5, density=.12, maxh=120, antenna=True),
        "neon": lambda: _megacity(f, a, a2),
        "noir": lambda: _city(f, ["#e5c07b"], 33, density=.12),
        "ruins": lambda: _city(f, None, 9, broken=True, maxh=140),
        "tombs": lambda: _tombs(f),
        "hills": lambda: _hills(f, "#ffd98a"),
        "peaks": lambda: _peaks(f, 4),
        "pixel": lambda: _pixel(f, 8),
        "fuji": lambda: _fuji(f, "#ff9cc6"),
        "road": lambda: _road(f, a, 12),
    }[k]()
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 200" preserveAspectRatio="none">{inner}</svg>'


@lru_cache(maxsize=None)
def _sky_uri(key):
    return "data:image/svg+xml;utf8," + quote(_sky_svg(key))


# ---------------------------------------------------------------- particles
# kind: (size min, size max, seconds min, seconds max, horizontal drift px, y min %, y max %)
PART = {
    "ember": (2, 5, 8, 18, 80, 0, 0), "pixel": (4, 8, 7, 16, 0, 0, 0), "ash": (2, 4, 12, 24, 60, 0, 0),
    "stars": (1, 3, 2, 6, 0, 0, 78), "rain": (1, 2.2, .8, 1.7, 22, 0, 0), "petal": (8, 14, 9, 17, 140, 0, 0),
    "firefly": (3, 5, 5, 11, 60, 15, 92), "streak": (2, 6, 1.2, 3, 0, 4, 96), "fog": (16, 30, 14, 30, 0, 6, 78),
}


def _parts(kind, n, seed, mini=False):
    r = random.Random(seed)
    smin, smax, tmin, tmax, xmax, ymin, ymax = PART[kind]
    k = (.4 if kind == "fog" else .65) if mini else 1
    out = []
    for _ in range(n):
        s = r.uniform(smin, smax) * k
        out.append('<i style="--l:%.1f%%;--y:%.1f%%;--s:%.1fpx;--t:%.1fs;--d:-%.1fs;--x:%dpx"></i>' % (
            r.uniform(0, 100), r.uniform(ymin, ymax), s, r.uniform(tmin, tmax) * (.7 if mini else 1),
            r.uniform(0, tmax), r.randint(-xmax, xmax) if xmax else 0))
    return "".join(out)


FX_CSS = """
.fx{position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden;animation:fxin 1.4s ease both}
.fx .ov,.fx .deco{position:absolute;pointer-events:none}.fx .ov{inset:0}
.fx .sky,.scene .sky{position:absolute;left:0;right:0;bottom:0;background-size:100% 100%;background-repeat:no-repeat}
.fx .sky{height:24vh;opacity:.96}.scene .sky{height:58%}
.fx i,.scene i{position:absolute;display:block;left:var(--l);width:var(--s);height:var(--s);border-radius:50%;
background:var(--pc);opacity:0;animation:linear infinite;animation-duration:var(--t);animation-delay:var(--d)}
.p-ember i{bottom:-5%;box-shadow:0 0 6px 1px var(--pc);animation-name:rise}
.p-pixel i{bottom:-5%;border-radius:0;box-shadow:0 0 6px var(--pc);animation-name:rise;animation-timing-function:steps(22)}
.p-ash i{top:-5%;animation-name:fall}
.p-stars i{top:var(--y);box-shadow:0 0 5px var(--pc);animation-name:twinkle}
.p-rain i{top:-10%;width:1px;height:calc(var(--s)*14);border-radius:0;transform:rotate(12deg);
background:linear-gradient(transparent,var(--pc));animation-name:fall}
.p-petal i{top:-5%;height:calc(var(--s)*.7);border-radius:100% 0 100% 0;animation-name:fallspin}
.p-firefly i{top:var(--y);box-shadow:0 0 10px 3px var(--pc);animation-name:glow}
.p-streak i{top:var(--y);left:-20%;width:calc(var(--s)*14);height:2px;border-radius:2px;
background:linear-gradient(90deg,transparent,var(--pc));animation-name:dash}
.p-fog i{top:var(--y);left:-35%;width:calc(var(--s)*14);height:calc(var(--s)*8);filter:blur(36px);animation-name:drift}
.scene.p-fog i{filter:blur(18px)}
@keyframes rise{0%{bottom:-5%;opacity:0;margin-left:0}12%{opacity:.9}85%{opacity:.5}100%{bottom:105%;opacity:0;margin-left:var(--x)}}
@keyframes fall{0%{top:-8%;opacity:0;margin-left:0}10%{opacity:.8}90%{opacity:.8}100%{top:104%;opacity:0;margin-left:var(--x)}}
@keyframes fallspin{0%{top:-6%;opacity:0;margin-left:0;transform:rotate(0)}10%{opacity:.9}90%{opacity:.9}
100%{top:104%;opacity:0;margin-left:var(--x);transform:rotate(540deg)}}
@keyframes twinkle{0%,100%{opacity:.1;transform:scale(.6)}50%{opacity:1;transform:scale(1.25)}}
@keyframes glow{0%{opacity:0;margin:0}25%{opacity:1}50%{opacity:.25;margin-left:var(--x);margin-top:-22px}75%{opacity:1}100%{opacity:0;margin:0}}
@keyframes dash{0%{left:-20%;opacity:0}10%{opacity:.85}100%{left:115%;opacity:0}}
@keyframes drift{0%{left:-35%;opacity:0}20%,80%{opacity:.17}100%{left:105%;opacity:0}}
@keyframes flick{0%,100%{opacity:1}42%{opacity:.82}48%{opacity:.96}66%{opacity:.88}}
@keyframes fxin{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){.fx i,.scene i{display:none}.fx,.fx .ov{animation:none!important}}
"""


# ---------------------------------------------------------------- public: page + card pieces
def theme_css(key, extra=()):
    """<style> block: palette, fonts, page backdrop, particle keyframes and the skyline images in use."""
    t = THEMES[key]
    root = ":root{" + "".join(f"--{k}:{v};" for k, v in t["c"].items()) + f"--disp:{t['disp']};--body:{t['body']}}}"
    css = f"@import url('{FONT_URL}');{root}{FX_CSS}.stApp{{background:{t['bg']},var(--bg)}}"
    css += f".fx .ov{{background:{t['ov']}}}"
    if t.get("flick"):
        css += ".fx .ov{animation:flick 4.5s ease-in-out infinite}"
    css += t["deco"]
    for k in {key, *extra}:
        css += f'.sk-{k}{{background-image:url("{_sky_uri(k)}")}}'
    return f"<style>{css}</style>"


def fx_html(key):
    """Fixed, click-through backdrop: overlay, deco (moon/planet/sun), skyline and drifting particles."""
    t = THEMES[key]
    kind, color, n = t["part"]
    return (f'<div class="fx fx-host p-{kind}" style="--pc:{color}"><div class="ov"></div><div class="deco"></div>'
            f'<div class="sky sk-{key}"></div>{_parts(kind, n, zlib.crc32(key.encode()))}</div>')


def scene_html(key, title, n=11):
    """Mini animated world used as a category card header."""
    t = THEMES[key]
    kind, color, _ = t["part"]
    return (f'<div class="scene p-{kind}" style="--pc:{color};background:{t["grad"]}"><div class="sky sk-{key}"></div>'
            f'{_parts(kind, n, zlib.crc32((key + title).encode()), mini=True)}'
            f'<div class="ttl"><div class="realm">{t["icon"]} {t["name"]}</div><h3>{title}</h3></div></div>')


def card_vars(key):
    t = THEMES[key]
    c = t["c"]
    return f'--ca:{c["accent"]};--ca2:{c["accent2"]};--cl:{c["line"]};--cp:{c["panel2"]};--cd:{t["disp"]};--cb:{t["body"]}'
