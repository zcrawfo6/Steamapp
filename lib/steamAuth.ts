// "Sign in through Steam" (OpenID 2.0), ported from Steamapp_Juan_Model/steam_import.py (login_url, verify_login).
// Server-only: used by app/api/auth/steam/*.
export const OPENID = "https://steamcommunity.com/openid/login";
const NS = "http://specs.openid.net/auth/2.0";

export const callbackPath = "/api/auth/steam/callback";

/** Steam's sign-in page; Steam sends the user back to `returnTo` afterwards. */
export function loginUrl(origin: string): string {
  const returnTo = origin + callbackPath;
  return (
    OPENID +
    "?" +
    new URLSearchParams({
      "openid.ns": NS,
      "openid.mode": "checkid_setup",
      "openid.return_to": returnTo,
      "openid.realm": origin,
      "openid.identity": `${NS}/identifier_select`,
      "openid.claimed_id": `${NS}/identifier_select`,
    })
  );
}

/**
 * Check the reply Steam redirected back with and return the signed-in SteamID64.
 * Steam signs its reply; posting it back with mode=check_authentication makes Steam confirm the signature,
 * so a hand-crafted URL can't sign someone in as another account.
 */
export async function verifyLogin(params: URLSearchParams, origin: string): Promise<string> {
  if (params.get("openid.mode") !== "id_res") throw new Error("Steam sign-in was cancelled.");
  if (params.get("openid.op_endpoint") !== OPENID || !(params.get("openid.return_to") ?? "").startsWith(origin + callbackPath))
    throw new Error("Steam sign-in reply didn't match this site. Try signing in again.");
  const m = /^https:\/\/steamcommunity\.com\/openid\/id\/(\d{17})$/.exec(params.get("openid.claimed_id") ?? "");
  if (!m) throw new Error("Steam sign-in reply had no Steam ID. Try signing in again.");

  const body = new URLSearchParams(params);
  body.set("openid.mode", "check_authentication");
  let text: string;
  try {
    const r = await fetch(OPENID, { method: "POST", body, cache: "no-store", signal: AbortSignal.timeout(20_000) });
    text = await r.text();
    if (!r.ok) throw new Error();
  } catch {
    throw new Error("Couldn't reach Steam to confirm the sign-in. Try again in a moment.");
  }
  if (!text.includes("is_valid:true"))
    throw new Error("Steam couldn't confirm this sign-in (it may have expired). Try signing in again.");
  return m[1];
}
