"""Pull a player's played games from the Steam Web API.

Needs a Steam Web API key (https://steamcommunity.com/dev/apikey) as STEAM_API_KEY in
.streamlit/secrets.toml or the environment. The player's profile and "Game details" must be public.
"""
import re
from urllib.parse import urlencode

import requests

API = "https://api.steampowered.com"
OPENID = "https://steamcommunity.com/openid/login"
OPENID_NS = "http://specs.openid.net/auth/2.0"


def login_url(return_to: str) -> str:
    """Steam's "Sign in through Steam" page; Steam sends the user back to `return_to` afterwards."""
    return OPENID + "?" + urlencode({
        "openid.ns": OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": return_to,
        "openid.identity": OPENID_NS + "/identifier_select",
        "openid.claimed_id": OPENID_NS + "/identifier_select",
    })


def verify_login(params: dict, return_to: str) -> str:
    """Check the reply Steam redirected back with and return the signed-in SteamID64.

    Steam signs its reply; posting it back with mode=check_authentication makes Steam confirm the
    signature, so a hand-crafted URL can't log someone in as another account.
    """
    if params.get("openid.mode") != "id_res":
        raise SteamError("Steam sign-in was cancelled.")
    if params.get("openid.op_endpoint") != OPENID or not params.get("openid.return_to", "").startswith(return_to):
        raise SteamError("Steam sign-in reply didn't match this app. Try signing in again.")
    m = re.fullmatch(r"https://steamcommunity\.com/openid/id/(\d{17})", params.get("openid.claimed_id", ""))
    if not m:
        raise SteamError("Steam sign-in reply had no Steam ID. Try signing in again.")
    r = requests.post(OPENID, data={**params, "openid.mode": "check_authentication"}, timeout=20)
    r.raise_for_status()
    if "is_valid:true" not in r.text:
        raise SteamError("Steam couldn't confirm this sign-in (it may have expired). Try signing in again.")
    return m.group(1)


def player_name(key: str, steamid: str) -> str:
    """The account's current display name (falls back to the ID)."""
    r = requests.get(f"{API}/ISteamUser/GetPlayerSummaries/v2/", params={"key": key, "steamids": steamid}, timeout=20)
    r.raise_for_status()
    players = r.json().get("response", {}).get("players", [])
    return players[0].get("personaname", steamid) if players else steamid


class SteamError(Exception):
    """A problem worth showing to the user as-is."""


def resolve_steamid(key: str, text: str) -> str:
    """Turn a SteamID64, a profile URL, or a custom (vanity) profile name into a SteamID64."""
    s = text.strip().rstrip("/")
    if not s:
        raise SteamError("Enter a Steam profile name, profile URL, or SteamID64.")
    m = re.search(r"steamcommunity\.com/profiles/(\d{17})", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d{17}", s):
        return s
    m = re.search(r"steamcommunity\.com/id/([^/?#]+)", s)
    vanity = m.group(1) if m else s
    r = requests.get(f"{API}/ISteamUser/ResolveVanityURL/v1/", params={"key": key, "vanityurl": vanity}, timeout=20)
    if r.status_code == 403:
        raise SteamError("Steam rejected the API key. Check STEAM_API_KEY.")
    r.raise_for_status()
    res = r.json().get("response", {})
    if res.get("success") != 1:
        raise SteamError(f"No Steam profile found with the custom URL name '{vanity}'. "
                         "Try the full profile URL or your SteamID64.")
    return res["steamid"]


def owned_games(key: str, steamid: str) -> list[dict]:
    """Every game the account owns, with `appid`, `name` and `hours` (lifetime playtime)."""
    r = requests.get(f"{API}/IPlayerService/GetOwnedGames/v1/", timeout=30, params={
        "key": key, "steamid": steamid, "include_appinfo": 1, "include_played_free_games": 1})
    if r.status_code == 403:
        raise SteamError("Steam rejected the API key. Check STEAM_API_KEY.")
    r.raise_for_status()
    res = r.json().get("response", {})
    if "games" not in res:
        # Steam returns an empty response (not an error) when the game list is private
        raise SteamError("Couldn't read this profile's games. In Steam, set Privacy Settings -> "
                         "'Game details' to Public, then try again.")
    return [{"appid": g["appid"], "name": g.get("name", str(g["appid"])),
             "hours": g.get("playtime_forever", 0) / 60} for g in res["games"]]
