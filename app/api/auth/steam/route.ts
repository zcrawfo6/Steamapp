// Start "Sign in through Steam": send the browser to Steam's OpenID page.
import { NextRequest, NextResponse } from "next/server";
import { loginUrl } from "@/lib/steamAuth";

export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  return NextResponse.redirect(loginUrl(req.nextUrl.origin), 303);
}
