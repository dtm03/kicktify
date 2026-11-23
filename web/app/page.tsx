"use client";

import { useCallback, useEffect, useState } from "react";
import styles from "./page.module.css";

type Stats = {
  total: number;
  exact: number;
  tendency: number;
  margin: number;
  exact_pct: number;
  tendency_pct: number;
  margin_pct: number;
  kicktipp_points: number;
  kicktipp_points_max: number;
  kicktipp_points_avg: number;
};

type BacktestMatch = {
  home: string;
  away: string;
  pick: string;
  actual: string;
  kickoff: string;
  expected_xg: string;
  exact: boolean;
  tendency: boolean;
  margin: boolean;
  kicktipp_points: number;
};

type MatchdayBlock = {
  matchday: number;
  stats: Stats;
  matches: BacktestMatch[];
};

type BacktestData = {
  season: number;
  generated_at?: string;
  season_stats: Stats;
  matchdays: MatchdayBlock[];
};

type LiveMatch = {
  home: string;
  away: string;
  pick: string;
  kickoff: string;
  expected_xg: string;
  injuries?: string;
};

type LivePayload = {
  season: number;
  matchday: number | null;
  predicted_at?: string;
  matches: LiveMatch[];
};

type PredictionGate = {
  allowed: boolean;
  message: string;
  upcoming?: {
    season: number;
    matchday: number;
    first_kickoff_display: string;
    first_kickoff?: string;
  };
};

function StatCard({ title, stats, field }: { title: string; stats: Stats; field: "exact" | "tendency" | "margin" }) {
  const count = stats[field];
  const pct = stats[`${field}_pct` as const];
  return (
    <article className={styles.statCard}>
      <div className={styles.statTitle}>{title}</div>
      <div className={styles.statPct}>{pct}%</div>
      <div className={styles.statSub}>
        {count}/{stats.total} Spiele
      </div>
    </article>
  );
}

export default function HomePage() {
  const [history, setHistory] = useState<BacktestData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [live, setLive] = useState<LivePayload | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictError, setPredictError] = useState<string | null>(null);
  const [gate, setGate] = useState<PredictionGate | null>(null);

  useEffect(() => {
    const loads: Promise<void>[] = [
      fetch("/data/season_backtest.json")
        .then((r) => {
          if (!r.ok) throw new Error("Backtest-Daten fehlen (export_web_data ausführen).");
          return r.json();
        })
        .then((data: BacktestData) => setHistory(data)),
      fetch("/data/prediction_gate.json")
        .then((r) => (r.ok ? r.json() : null))
        .then((data: PredictionGate | null) => {
          if (data) setGate(data);
        })
        .catch(() => fetch("/api/status").then((r) => r.json()).then(setGate)),
    ];
    Promise.all(loads).catch((e: Error) => setLoadError(e.message));
  }, []);

  const showLive = (data: LivePayload) => {
    setLive(data);
  };

  const predictNext = useCallback(async () => {
    setPredicting(true);
    setPredictError(null);
    const minMs = 5000;
    const started = Date.now();
    try {
      const params = new URLSearchParams(window.location.search);
      const trainLive = params.get("train") === "1" && process.env.NODE_ENV === "development";

      let data: LivePayload;
      if (trainLive) {
        const res = await fetch("/api/predict");
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || res.statusText);
        data = json as LivePayload;
      } else {
        const res = await fetch(`/data/live_prediction.json?ts=${Date.now()}`);
        if (!res.ok) {
          throw new Error(
            "Keine live_prediction.json — GitHub Action abwarten oder lokal predict_and_save.py ausführen und pushen.",
          );
        }
        data = (await res.json()) as LivePayload;
      }

      const wait = minMs - (Date.now() - started);
      if (wait > 0) await new Promise((r) => setTimeout(r, wait));

      showLive(data);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setPredictError(e instanceof Error ? e.message : "Prediction failed");
    } finally {
      setPredicting(false);
    }
  }, []);

  return (
    <>
      <header className={styles.stickyBar}>
        <button
          type="button"
          className={styles.cta}
          onClick={predictNext}
          disabled={predicting}
        >
          {predicting ? "Vorhersage wird geladen…" : "Nächsten Spieltag predicten"}
        </button>
        {gate?.upcoming && (
          <p className={styles.hint}>
            Spieltag {gate.upcoming.matchday} · erster Anpfiff {gate.upcoming.first_kickoff_display}
            {gate.allowed === false ? ` · ${gate.message}` : ""}
          </p>
        )}
        <p className={styles.hint}>
          Nach jedem Reload nur die History — oben Tipps erst nach Klick (lädt ~5 s aus dem Repo, bereits von der GitHub
          Action berechnet).
        </p>
        {predictError && <p className={styles.error}>{predictError}</p>}
      </header>

      {live && (
        <section className={styles.livePanel}>
          <h2>
            Vorhersage · Spieltag {live.matchday ?? "—"} ({live.season})
            {live.predicted_at
              ? ` · ${new Date(live.predicted_at).toLocaleString("de-DE")}`
              : ""}
          </h2>
          <ul className={styles.matchList}>
            {live.matches.map((m) => (
              <li key={`${m.home}-${m.away}-${m.kickoff}`}>
                <span className={styles.time}>{m.kickoff}</span>
                <span className={styles.teams}>
                  {m.home} – {m.away}
                </span>
                <span className={styles.pick}>{m.pick}</span>
                <span className={styles.muted}>xG {m.expected_xg}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <main className={styles.main}>
        <h1>Bundesliga · Saison-Backtest</h1>
        {loadError && <p className={styles.error}>{loadError}</p>}
        {history && (
          <>
            <p className={styles.muted}>
              Saison {history.season}
              {history.generated_at
                ? ` · Stand ${new Date(history.generated_at).toLocaleString("de-DE")}`
                : ""}
            </p>

            <article className={styles.pointsHero}>
              <div className={styles.pointsTitle}>Kicktipp-Punkte (Saison)</div>
              <div className={styles.pointsValue}>
                {history.season_stats.kicktipp_points}
                <span className={styles.pointsMax}>
                  {" "}
                  / {history.season_stats.kicktipp_points_max}
                </span>
              </div>
              <p className={styles.pointsSub}>
                Ø {history.season_stats.kicktipp_points_avg} Punkte pro Spiel · 4 exakt · 3 Abstand · 2
                Tendenz
              </p>
            </article>

            <div className={styles.statRow}>
              <StatCard title="Exaktes Ergebnis" stats={history.season_stats} field="exact" />
              <StatCard title="Tendenz (Sieger)" stats={history.season_stats} field="tendency" />
              <StatCard title="Torabstand" stats={history.season_stats} field="margin" />
            </div>

            {history.matchdays.map((block) => (
              <section key={block.matchday} className={styles.matchdayCard}>
                <header className={styles.matchdayHead}>
                  <h2>Spieltag {block.matchday}</h2>
                  <div className={styles.matchdayStats}>
                    <span>Exakt {block.stats.exact_pct}%</span>
                    <span>Tendenz {block.stats.tendency_pct}%</span>
                    <span>Abstand {block.stats.margin_pct}%</span>
                    <span className={styles.pointsBadge}>
                      {block.stats.kicktipp_points} Pkt
                    </span>
                  </div>
                </header>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Zeit</th>
                      <th>Spiel</th>
                      <th>Tipp</th>
                      <th>Ergebnis</th>
                      <th>Ex</th>
                      <th>Td</th>
                      <th>Ab</th>
                      <th>Pkt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {block.matches.map((m) => (
                      <tr key={`${m.home}-${m.kickoff}`}>
                        <td>{m.kickoff}</td>
                        <td>
                          {m.home} – {m.away}
                        </td>
                        <td>{m.pick}</td>
                        <td>{m.actual}</td>
                        <td>{m.exact ? "✓" : "✗"}</td>
                        <td>{m.tendency ? "✓" : "✗"}</td>
                        <td>{m.margin ? "✓" : "✗"}</td>
                        <td>{m.kicktipp_points}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            ))}
          </>
        )}
      </main>
    </>
  );
}