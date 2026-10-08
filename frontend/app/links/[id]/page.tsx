"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import CopyButton from "@/components/CopyButton";
import { api, ApiError, type Link as ShortLink, type LinkStats } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

const WINDOWS = [7, 30, 90];

function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
}

export default function StatsPage() {
  const ready = useRequireAuth();
  const { id } = useParams<{ id: string }>();
  const [days, setDays] = useState(30);
  const [link, setLink] = useState<ShortLink | null>(null);
  const [stats, setStats] = useState<LinkStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    setError(null);
    Promise.all([api.getLink(id), api.stats(id, days)])
      .then(([l, s]) => {
        setLink(l);
        setStats(s);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load stats. Please try again."));
  }, [ready, id, days]);

  if (!ready) return null;
  if (error)
    return (
      <main className="page">
        <p role="alert" className="error">{error}</p>
        <Link href="/">Back to your links</Link>
      </main>
    );
  if (!link || !stats) return <main className="page"><p className="muted">Loading stats…</p></main>;

  // Presentation only: bar heights are scaled to the tallest bar. All counts come from the backend.
  const tallest = Math.max(1, ...stats.daily.map((d) => d.clicks));

  return (
    <main className="page">
      <Link href="/" className="back">Your links</Link>
      <header className="stats-head">
        <div>
          <h1 className="code code-xl">/r/{link.code}</h1>
          <a className="target" href={link.target_url} target="_blank" rel="noopener noreferrer">{link.target_url}</a>
        </div>
        <CopyButton text={link.short_url} />
      </header>

      <p className="totals">
        <strong>{stats.total_clicks}</strong> clicks all time, <strong>{stats.window_clicks}</strong> in the last {stats.days} days.
      </p>

      <div className="windows" role="group" aria-label="Time range">
        {WINDOWS.map((w) => (
          <button key={w} type="button" aria-pressed={w === days} className="chip" onClick={() => setDays(w)}>
            {w} days
          </button>
        ))}
      </div>

      <section aria-label="Clicks per day" className="chart">
        <div className="bars">
          {stats.daily.map((d) => (
            <div key={d.date} className="bar-slot" title={`${shortDate(d.date)}: ${d.clicks}`}>
              <div className="bar" style={{ height: `${(d.clicks / tallest) * 100}%` }} />
            </div>
          ))}
        </div>
        <div className="chart-axis">
          <span>{shortDate(stats.daily[0].date)}</span>
          <span>{shortDate(stats.daily[stats.daily.length - 1].date)} (UTC)</span>
        </div>
      </section>

      <section>
        <h2>Where clicks came from</h2>
        {stats.top_referrers.length === 0 ? (
          <p className="muted">No clicks in this period yet. Share {link.short_url} to start counting.</p>
        ) : (
          <table className="referrers">
            <thead><tr><th scope="col">Source</th><th scope="col">Clicks</th></tr></thead>
            <tbody>
              {stats.top_referrers.map((r) => (
                <tr key={r.referrer}>
                  <td>{r.referrer === "direct" ? "Direct or unknown" : r.referrer}</td>
                  <td>{r.clicks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
