// Server-side proxy to the EASE-safe Modal API. The browser only ever talks to /api/m/*; the Modal URL and the
// bearer token stay on the server (MODAL_API_URL, MODAL_API_TOKEN).
import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60; // first request after the Modal container scales to zero can take a while

// path pattern -> seconds a successful GET may be cached by Vercel's CDN (0 = never; these carry Steam IDs)
const ROUTES: [RegExp, number][] = [
  [/^search$/, 3600],
  [/^games$/, 3600],
  [/^game\/\d+$/, 86400],
  [/^gem$/, 0],
  [/^demo$/, 0],
  [/^player$/, 0],
  [/^recommend$/, 0],
  [/^recommend\/profile$/, 0],
];

async function forward(req: NextRequest, path: string[]) {
  const p = path.join("/");
  const route = ROUTES.find(([re]) => re.test(p));
  if (!route) return Response.json({ error: "not found" }, { status: 404 });
  const base = process.env.MODAL_API_URL;
  const token = process.env.MODAL_API_TOKEN;
  if (!base || !token) return Response.json({ error: "MODAL_API_URL / MODAL_API_TOKEN are not set" }, { status: 500 });

  const url = `${base.replace(/\/$/, "")}/${p}${req.nextUrl.search}`;
  const init: RequestInit = {
    method: req.method,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    cache: "no-store",
    signal: AbortSignal.timeout(55_000),
  };
  if (req.method === "POST") {
    const body = await req.text();
    if (body.length > 200_000) return Response.json({ error: "request too large" }, { status: 413 });
    init.body = body;
  }
  try {
    const r = await fetch(url, init);
    const text = await r.text();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    headers["Cache-Control"] =
      r.ok && req.method === "GET" && route[1] > 0
        ? `public, s-maxage=${route[1]}, stale-while-revalidate=${route[1]}`
        : "no-store";
    return new Response(text, { status: r.status, headers });
  } catch {
    return Response.json({ error: "The recommender didn't answer in time. Try again in a moment." }, { status: 504 });
  }
}

type Ctx = { params: Promise<{ path: string[] }> };
export async function GET(req: NextRequest, ctx: Ctx) {
  return forward(req, (await ctx.params).path);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return forward(req, (await ctx.params).path);
}
