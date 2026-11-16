// Up to three store screenshots per game from Steam's public store API (it has no CORS, so the server asks).
// GET /api/shots?ids=620,400  ->  { "620": [url, url, url], "400": [...] }
import { NextRequest } from "next/server";

export const runtime = "nodejs";

async function shots(appId: number): Promise<string[] | null> {
  try {
    const r = await fetch(
      `https://store.steampowered.com/api/appdetails?appids=${appId}&filters=screenshots`,
      { next: { revalidate: 86400 }, signal: AbortSignal.timeout(6000) },
    );
    if (!r.ok) return null;
    const j = await r.json();
    const list = j?.[String(appId)]?.data?.screenshots ?? [];
    return list.slice(0, 3).map((s: { path_thumbnail: string }) => s.path_thumbnail);
  } catch {
    return null;
  }
}

export async function GET(req: NextRequest) {
  const ids = (req.nextUrl.searchParams.get("ids") ?? "")
    .split(",")
    .filter((x) => /^\d+$/.test(x))
    .slice(0, 24)
    .map(Number);
  const res = await Promise.all(ids.map(shots));
  const out: Record<string, string[]> = {};
  ids.forEach((a, i) => (out[a] = res[i] ?? []));
  const allOk = res.every((x) => x !== null);
  return Response.json(out, {
    headers: { "Cache-Control": allOk ? "public, s-maxage=86400, stale-while-revalidate=86400" : "no-store" },
  });
}
