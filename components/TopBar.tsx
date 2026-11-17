"use client";
// Brand on the left; Steam import and the Simple / Advanced switch on the right (app.py top bar).
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { MIN_HOURS } from "@/lib/profile";
import { useStore } from "@/lib/store";
import { Mark, Msg } from "./ui";

function Popover({ label, solid, children }: { label: string; solid?: boolean; children: (close: () => void) => React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", off);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", off);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  return (
    <div className="pop" ref={ref}>
      <button className={`pill ${solid ? "solid" : ""}`} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {label}
      </button>
      {open && <div className="pop-body">{children(() => setOpen(false))}</div>}
    </div>
  );
}

/** Import a Steam library into the store: every owned game that's in the catalog, most hours first. */
export function useSteamImport() {
  const { replace } = useStore();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<["error" | "success" | "warning", string] | null>(null);
  async function run(q: string) {
    if (!q.trim()) return setMsg(["error", "Enter a custom URL name, profile link or SteamID64."]);
    setBusy(true);
    setMsg(null);
    try {
      const p = await api.player(q.trim());
      const matched = p.games.filter((g) => g.in_catalog).slice(0, 500);
      if (!matched.length) {
        setMsg(["warning", `Found ${p.n_owned} owned games, but none of them are in the catalog yet.`]);
        return;
      }
      replace(matched.map((g) => ({ ...g, hours: Math.min(9999, Math.round(g.hours * 10) / 10) })));
      const counted = matched.filter((g) => g.hours >= MIN_HOURS).length;
      const skipped = p.n_owned - matched.length;
      setMsg([
        "success",
        `Imported ${matched.length} of ${p.name ? `${p.name}'s` : "your"} ${p.n_owned} owned games; the ${counted} with ${MIN_HOURS}+ hours shape your profile` +
          (skipped ? `; ${skipped} ${skipped === 1 ? "wasn't" : "weren't"} in the catalog` : "") +
          ". Adjust hours and modes in Advanced mode.",
      ]);
    } catch (e) {
      setMsg(["error", e instanceof ApiError ? e.message : "Import failed."]);
    } finally {
      setBusy(false);
    }
  }
  return { run, busy, msg };
}

/** Steam's official "Sign in through Steam" button. Plain link so Steam returns to this tab. */
export function SteamSignIn() {
  return (
    <a href="/api/auth/steam" className="steam-login" title="Sign in through Steam to import your library">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="https://community.fastly.steamstatic.com/public/images/signinthroughsteam/sits_01.png" alt="Sign in through Steam" width={180} height={35} />
    </a>
  );
}

function SteamImport() {
  const [q, setQ] = useState("");
  const { run, busy, msg } = useSteamImport();
  return (
    <>
      <div className="steam-primary">
        <SteamSignIn />
      </div>
      <div className="or">or paste your profile link</div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(q);
        }}
      >
        <input id="steam-q" aria-label="Your Steam profile" className="input" style={{ margin: "0 0 10px" }} value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Custom URL name, profile URL or SteamID64" autoComplete="off" />
        <button className="btn ghost block" disabled={busy}>
          {busy ? "Importing..." : "Import my library"}
        </button>
      </form>
      {msg && <Msg kind={msg[0]}>{msg[1]}</Msg>}
      <p style={{ marginTop: 10 }}>
        Your Steam profile and its Game details must be set to Public. Every owned game that&apos;s in the catalog is imported
        with its lifetime hours; games under {MIN_HOURS} hours don&apos;t count toward your taste profile. Signing in only
        tells this site your Steam ID (never your password), and it&apos;s only used for this lookup and isn&apos;t stored.
      </p>
    </>
  );
}

export default function TopBar() {
  const { settings, set } = useStore();
  return (
    <div className="topbar">
      <Link href="/" className="brand">
        <Mark />
        <span>
          Taste<b>Forge</b>
        </span>
      </Link>
      <div className="tb-right">
        <Popover label="🎮  Import from Steam">{() => <SteamImport />}</Popover>
        <Popover label={`Mode: ${settings.mode}`} solid>
          {(close) =>
            (["Simple", "Advanced"] as const).map((m) => (
              <label key={m} className="check" style={{ alignItems: "flex-start" }}>
                <input type="radio" name="mode" checked={settings.mode === m} onChange={() => (set({ mode: m }), close())} />
                <span>
                  <b>{m}</b>
                  <div className="why" style={{ marginTop: 0 }}>
                    {m === "Simple" ? "Pick your games, get recommendations" : "Hours, play modes, budget and filters"}
                  </div>
                </span>
              </label>
            ))
          }
        </Popover>
      </div>
    </div>
  );
}
