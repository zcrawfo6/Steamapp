import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import TopBar from "@/components/TopBar";
import { FONT_URL, shelfUri } from "@/lib/themes";
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
        <div className="shelves" style={{ backgroundImage: shelfUri() }} aria-hidden />
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
