// Small shared pieces: the gamepad mark, bars, chips, the radar chart, a world scene header.
import type { CSSProperties, ReactNode } from "react";
import { THEMES, cardVars, hash, particles, skyUri } from "@/lib/themes";

export function Mark() {
  return (
    <svg viewBox="0 0 64 44" aria-hidden="true">
      <path d="M17 4h30c9 0 15 9 16 22 1 10-3 16-9 16-4 0-7-3-10-8H20c-3 5-6 8-10 8-6 0-10-6-9-16C2 13 8 4 17 4z" fill="#26282c" stroke="#ff5a1f" strokeWidth="2.5" />
      <path d="M15 20h4v-4h4v4h4v4h-4v4h-4v-4h-4z" fill="#ff5a1f" />
      <circle cx="44" cy="18" r="3" fill="#ffb000" />
      <circle cx="50" cy="25" r="3" fill="#ff5a1f" />
    </svg>
  );
}

const clamp = (p: number) => Math.max(0, Math.min(100, p || 0));

export function Bar({ pct, them, className = "", style }: { pct: number; them?: boolean; className?: string; style?: CSSProperties }) {
  return (
    <div className={`bar ${them ? "them" : ""} ${className}`} style={style}>
      <i style={{ width: `${clamp(pct)}%` }} />
    </div>
  );
}

export function TwoBar({ you, them }: { you: number; them: number }) {
  return (
    <>
      <Bar pct={you} style={{ marginBottom: 3 }} />
      <Bar pct={them} them />
    </>
  );
}

export function Chips({ items, sel }: { items: string[]; sel?: boolean }) {
  return (
    <>
      {items.map((x) => (
        <span key={x} className={`chip ${sel ? "sel" : ""}`}>
          {x}
        </span>
      ))}
    </>
  );
}

export const Spinner = ({ children }: { children: ReactNode }) => <div className="spinner">{children}</div>;
export const Empty = ({ children }: { children: ReactNode }) => <div className="empty">{children}</div>;
export const Msg = ({ kind, children }: { kind: "error" | "success" | "warning" | "info"; children: ReactNode }) => (
  <div className={`msg ${kind}`}>{children}</div>
);

/** Spider chart of the top genres (app.py radar). entries: [label, value], largest first. */
export function Radar({ entries }: { entries: [string, number][] }) {
  const n = entries.length;
  const R = 120;
  const cx = 170;
  const cy = 150;
  const pt = (i: number, r: number): [number, number] => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const pts = (f: (i: number) => number) =>
    Array.from({ length: n }, (_, i) => pt(i, f(i)).map((v) => v.toFixed(1)).join(",")).join(" ");
  const mx = entries[0][1] || 1;
  const line = { fill: "none", stroke: "var(--line)" };
  return (
    <svg viewBox="-40 0 420 300" width="100%" role="img" aria-label="Genre radar">
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <polygon key={f} points={pts(() => R * f)} style={line} />
      ))}
      {entries.map((_, i) => {
        const [x, y] = pt(i, R);
        return <line key={i} x1={cx} y1={cy} x2={x.toFixed(1)} y2={y.toFixed(1)} style={line} />;
      })}
      <polygon points={pts((i) => R * Math.max(0.08, entries[i][1] / mx))} style={{ fill: "var(--accent)", fillOpacity: 0.3, stroke: "var(--accent)", strokeWidth: 2 }} />
      {entries.map(([label], i) => {
        const [x, y] = pt(i, R + 18);
        const anchor = x < cx - 5 ? "end" : x > cx + 5 ? "start" : "middle";
        return (
          <text key={i} x={x.toFixed(1)} y={y.toFixed(1)} textAnchor={anchor} dominantBaseline="middle">
            {label}
          </text>
        );
      })}
    </svg>
  );
}

/** Animated world header for a game page (themes.py scene_html inside a catcard). */
export function WorldCard({ world, title, children }: { world: string; title: string; children?: ReactNode }) {
  const t = THEMES[world];
  const [kind, color] = t.part;
  return (
    <div className="catcard" style={cardVars(world) as CSSProperties}>
      <div className={`scene p-${kind}`} style={{ "--pc": color, background: t.grad } as CSSProperties}>
        <div className="sky" style={{ backgroundImage: skyUri(world) }} />
        {particles(kind, 16, hash(world + title), true).map((p, i) => (
          <i key={i} style={p as CSSProperties} />
        ))}
        <div className="ttl">
          <div className="realm">
            {t.name}
          </div>
          <h3>{title}</h3>
        </div>
      </div>
      {children && <div className="cbody">{children}</div>}
    </div>
  );
}
