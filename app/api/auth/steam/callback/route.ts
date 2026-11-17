// Steam redirects here after sign-in. Verify the reply with Steam, then hand the SteamID64 to the home page,
// which imports that library once and strips it from the URL. Nothing is stored server-side.
import { NextRequest, NextResponse } from "next/server";
import { verifyLogin } from "@/lib/steamAuth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const origin = req.nextUrl.origin;
  try {
    const id = await verifyLogin(req.nextUrl.searchParams, origin);
    return NextResponse.redirect(`${origin}/?steam=${id}`, 303);
  } catch (e) {
    const msg = e instanceof Error && e.message ? e.message : "Steam sign-in failed.";
    return NextResponse.redirect(`${origin}/?steam_error=${encodeURIComponent(msg)}`, 303);
  }
}
