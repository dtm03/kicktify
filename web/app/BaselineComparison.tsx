import styles from "./page.module.css";

type BaselineStrategy = {
  id: string;
  label: string;
  kicktipp_points: number;
  kicktipp_points_max: number;
  kicktipp_points_avg: number;
  games: number;
  coverage_pct: number;
};

export type BaselineComparison = {
  total_games: number;
  strategies: BaselineStrategy[];
  cumulative_by_matchday?: unknown[];
};

export function BaselineComparisonPanel({ data }: { data: BaselineComparison }) {
  const sorted = [...data.strategies].sort((a, b) => b.kicktipp_points_avg - a.kicktipp_points_avg);
  const maxAvg = Math.max(...sorted.map((s) => s.kicktipp_points_avg), 0.01);

  return (
    <section className={styles.baselinePanel} aria-labelledby="baseline-heading">
      <div className={styles.baselineHead}>
        <h2 id="baseline-heading">Modell vs. Baselines</h2>
        <span className={styles.muted}>{data.total_games} Spiele · Ø Punkte</span>
      </div>
      <ul className={styles.baselineList}>
        {sorted.map((s) => (
          <li
            key={s.id}
            className={`${styles.baselineRow} ${s.id === "model" ? styles.baselineRowModel : ""}`}
          >
            <span className={styles.baselineLabel}>
              {s.label}
              {s.id === "bookmaker" && s.coverage_pct < 100 ? (
                <span className={styles.baselineCov}> · {s.coverage_pct}% mit Kurs</span>
              ) : null}
            </span>
            <span className={styles.baselineTrack} aria-hidden>
              <span
                className={`${styles.baselineFill} ${s.id === "model" ? styles.baselineFillModel : ""}`}
                style={{ width: `${(s.kicktipp_points_avg / maxAvg) * 100}%` }}
              />
            </span>
            <span className={styles.baselineValue}>Ø {s.kicktipp_points_avg}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}