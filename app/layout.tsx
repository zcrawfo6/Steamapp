import type { CSSProperties } from "react";
import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import TopBar from "@/components/TopBar";
import { FONT_URL, particles, skyUri } from "@/lib/themes";
import { StoreProvider } from "@/lib/store";
import "./globals.css";

export const metadata: Metadata = {
  title: "TasteForge · Find what to play next",
  description: "Steam game recommendations from the EASE-safe collaborative-filtering model.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href={FONT_URL} />
      </head>
      <body>
        <div className="forge-bg" aria-hidden>
          <div className="sky" style={{ backgroundImage: skyUri("forge") }} />
          <div className="embers" style={{ "--pc": "#ffb000" } as CSSProperties}>
            {particles("ember", 36, 7).map((p, i) => (
              <i key={i} style={p as CSSProperties} />
            ))}
          </div>
        </div>
        <StoreProvider>
          <div className="wrap">
            <TopBar />
            {children}
          </div>
        </StoreProvider>
        <Analytics />
      </body>
    </html>
  );
}
