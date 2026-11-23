"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  BaselineComparisonPanel,
  type BaselineComparison,
} from "./BaselineComparison";
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
  baseline_comparison?: BaselineComparison;
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

type FeedItem =
  | { kind: "backtest"; block: MatchdayBlock }
  | { kind: "predicted"; payload: LivePayload };

function feedPanes(feed: HTMLElement) {
  return Array.from(
    feed.querySelectorAll<HTMLElement>("article[data-matchday]"),
  );
}

function feedIndexAtScroll(feed: HTMLElement, count: number) {
  const panes = feedPanes(feed);
  if (!panes.length) return 0;
  const anchor = feed.scrollTop + Math.min(80, feed.clientHeight * 0.2);
  let idx = 0;
  let best = Number.POSITIVE_INFINITY;
  panes.forEach((pane, i) => {
    const d = Math.abs(pane.offsetTop - anchor);
    if (d < best) {
      best = d;
      idx = i;
    }
  });
  return Math.max(0, Math.min(count - 1, idx));
}

function scrollFeedToPane(
  feed: HTMLElement,
  index: number,
  behavior: ScrollBehavior,
) {
  const pane = feedPanes(feed)[index];
  if (!pane) return;
  feed.scrollTo({ top: pane.offsetTop, behavior });
}

function isMobileStage() {
  return window.matchMedia("(max-width: 1000px)").matches;
}

function StatCard({
  title,
  stats,
  field,
}: {
  title: string;
  stats: Stats;
  field: "exact" | "tendency" | "margin";
}) {
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

function Logo() {
  return <div className={styles.logo}>kicktify</div>;
}

function PredictedMatchdayPane({ payload }: { payload: LivePayload }) {
  const md = payload.matchday ?? 0;
  return (
    <article
      className={`${styles.matchdayPane} ${styles.matchdayPanePredicted}`}
      id={`md-predicted-${md}`}
      data-matchday={md}
      data-predicted="true"
    >
      <span className={styles.mdNum} aria-hidden="true">
        {String(md).padStart(2, "0")}
      </span>
      <div className={styles.slideBody} data-md-body>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Zeit</th>
              <th>Spiel</th>
              <th>Tipp</th>
              <th>xG</th>
            </tr>
          </thead>
          <tbody>
            {payload.matches.map((m, i) => (
              <tr
                key={`${m.home}-${m.away}-${m.kickoff}`}
                style={{ "--i": i } as React.CSSProperties}
              >
                <td>{m.kickoff}</td>
                <td>
                  {m.home} – {m.away}
                </td>
                <td className={styles.pickCell}>{m.pick}</td>
                <td className={styles.muted}>{m.expected_xg}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function MatchdayPane({ block }: { block: MatchdayBlock }) {
  return (
    <article
      className={styles.matchdayPane}
      id={`md-${block.matchday}`}
      data-matchday={block.matchday}
    >
      <span className={styles.mdNum} aria-hidden="true">
        {String(block.matchday).padStart(2, "0")}
      </span>
      <header className={styles.slideHead}>
        <div className={styles.matchdayStats}>
          <span>Exakt {block.stats.exact_pct}%</span>
          <span>Tendenz {block.stats.tendency_pct}%</span>
          <span>Abstand {block.stats.margin_pct}%</span>
          <span className={styles.pointsBadge}>
            {block.stats.kicktipp_points} Pkt
          </span>
        </div>
      </header>
      <div className={styles.slideBody} data-md-body>
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
            {block.matches.map((m, i) => (
              <tr
                key={`${m.home}-${m.kickoff}`}
                className={m.kicktipp_points > 0 ? styles.ok : styles.miss}
                style={{ "--i": i } as React.CSSProperties}
              >
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

  const [activeIdx, setActiveIdx] = useState(0);
  const railRef = useRef<HTMLElement>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLElement>(null);
  const sideRef = useRef<HTMLElement>(null);
  const pairHeightRef = useRef(0);
  const scrollRafRef = useRef(0);
  const scrollToPredictionRef = useRef(false);

  const days = useMemo(
    () =>
      history
        ? [...history.matchdays].sort((a, b) => b.matchday - a.matchday)
        : [],
    [history],
  );

  const feedItems = useMemo((): FeedItem[] => {
    const historical = days.map((block) => ({
      kind: "backtest" as const,
      block,
    }));
    if (!live?.matchday || !live.matches.length) return historical;
    const withoutDup = historical.filter(
      (item) => item.block.matchday !== live.matchday,
    );
    return [{ kind: "predicted", payload: live }, ...withoutDup];
  }, [days, live]);

  useEffect(() => {
    const loads: Promise<void>[] = [
      fetch("/data/season_backtest.json")
        .then((r) => {
          if (!r.ok)
            throw new Error(
              "Backtest-Daten fehlen (export_web_data ausführen).",
            );
          return r.json();
        })
        .then((data: BacktestData) => setHistory(data)),
      fetch("/data/prediction_gate.json")
        .then((r) => (r.ok ? r.json() : null))
        .then((data: PredictionGate | null) => {
          if (data) setGate(data);
        })
        .catch(() =>
          fetch("/api/status")
            .then((r) => r.json())
            .then(setGate),
        ),
    ];
    Promise.all(loads).catch((e: Error) => setLoadError(e.message));
  }, []);

  const go = useCallback(
    (to: number, behavior: ScrollBehavior = "smooth") => {
      if (to < 0 || to >= feedItems.length) return;
      const feed = feedRef.current;
      if (!feed) {
        setActiveIdx(to);
        return;
      }
      if (isMobileStage()) {
        scrollFeedToPane(feed, to, behavior);
        setActiveIdx(to);
        return;
      }
      const paneH = feed.clientHeight;
      if (paneH < 1) {
        setActiveIdx(to);
        return;
      }
      feed.scrollTo({ top: to * paneH, behavior });
      setActiveIdx(to);
    },
    [feedItems.length],
  );

  useEffect(() => {
    if (!live || !scrollToPredictionRef.current) return;
    scrollToPredictionRef.current = false;
    const t = requestAnimationFrame(() => go(0, "smooth"));
    return () => cancelAnimationFrame(t);
  }, [live, go]);

  useLayoutEffect(() => {
    const side = sideRef.current;
    const stage = stageRef.current;
    const feed = feedRef.current;
    if (!side || !stage || !history) return;

    const mq = window.matchMedia("(min-width: 1001px)");
    const rail = railRef.current;

    const applyHeights = (h: number) => {
      pairHeightRef.current = h;
      side.style.height = `${h}px`;
      side.style.minHeight = `${h}px`;
      stage.style.height = `${h}px`;
      stage.style.minHeight = `${h}px`;
      if (feed) {
        feed.style.height = `${h}px`;
        feed.style.maxHeight = `${h}px`;
        feed.style.setProperty("--pane-h", `${h}px`);
      }
      if (rail) rail.style.maxHeight = `${h}px`;
    };

    const syncMobileFeed = () => {
      if (!feed || !stage) return;
      const prevScroll = feed.scrollTop;

      side.style.height = "";
      side.style.minHeight = "";
      stage.style.height = "";
      stage.style.minHeight = "";
      rail?.style.removeProperty("max-height");
      feed.style.removeProperty("--pane-h");

      feed.style.removeProperty("height");
      feed.style.removeProperty("max-height");
      const viewportH = Math.ceil(feed.clientHeight);
      if (viewportH < 120) return;

      if (
        viewportH === pairHeightRef.current &&
        feed.style.height === `${viewportH}px`
      ) {
        if (prevScroll > 0) feed.scrollTop = prevScroll;
        return;
      }

      pairHeightRef.current = viewportH;
      feed.style.height = `${viewportH}px`;
      feed.style.maxHeight = `${viewportH}px`;
      if (prevScroll > 0) feed.scrollTop = prevScroll;
    };

    const syncPairHeight = () => {
      if (!feed) return;

      if (!mq.matches) {
        syncMobileFeed();
        return;
      }

      const tail = side.querySelector<HTMLElement>("[data-side-tail]");
      const tailVis = tail?.style.visibility;
      if (tail) tail.style.visibility = "hidden";
      side.style.height = "";
      side.style.minHeight = "";
      stage.style.height = "";
      stage.style.minHeight = "";
      feed.style.height = `${pairHeightRef.current || 1}px`;
      feed.style.maxHeight = `${pairHeightRef.current || 1}px`;
      if (pairHeightRef.current > 0) {
        feed.style.setProperty("--pane-h", `${pairHeightRef.current}px`);
      }

      const h = Math.ceil(side.offsetHeight);
      if (tail) tail.style.visibility = tailVis ?? "";
      if (h < 1) return;
      if (h === pairHeightRef.current) {
        feed.style.height = `${h}px`;
        feed.style.maxHeight = `${h}px`;
        feed.style.setProperty("--pane-h", `${h}px`);
        return;
      }
      applyHeights(h);
    };

    syncPairHeight();
    const t = window.setTimeout(syncPairHeight, 50);
    const t2 = window.setTimeout(syncPairHeight, 280);
    const ro = new ResizeObserver(() => requestAnimationFrame(syncPairHeight));
    ro.observe(side);
    ro.observe(stage);
    mq.addEventListener("change", syncPairHeight);
    window.addEventListener("resize", syncPairHeight);
    return () => {
      window.clearTimeout(t);
      window.clearTimeout(t2);
      ro.disconnect();
      mq.removeEventListener("change", syncPairHeight);
      window.removeEventListener("resize", syncPairHeight);
    };
  }, [history, live, feedItems.length]);

  useEffect(() => {
    const feed = feedRef.current;
    const stage = stageRef.current;
    if (!feed || !stage) return;

    const FEED_WHEEL_GAIN = 0.52;

    const onScroll = () => {
      if (scrollRafRef.current) return;
      scrollRafRef.current = requestAnimationFrame(() => {
        scrollRafRef.current = 0;
        const clamped = isMobileStage()
          ? feedIndexAtScroll(feed, feedItems.length)
          : (() => {
              const paneH = feed.clientHeight;
              if (paneH < 1) return 0;
              return Math.round(feed.scrollTop / paneH);
            })();
        const bound = Math.max(0, Math.min(feedItems.length - 1, clamped));
        setActiveIdx((prev) => (prev === bound ? prev : bound));
      });
    };

    const onWheel = (e: WheelEvent) => {
      if (window.matchMedia("(max-width: 1000px)").matches) return;
      if (Math.abs(e.deltaY) < 2) return;
      const body = (e.target as HTMLElement).closest<HTMLElement>(
        "[data-md-body]",
      );
      if (body) {
        const canDown =
          body.scrollTop + body.clientHeight < body.scrollHeight - 2;
        const canUp = body.scrollTop > 2;
        if ((e.deltaY > 0 && canDown) || (e.deltaY < 0 && canUp)) return;
      }
      const atTop = feed.scrollTop <= 0;
      const atBottom =
        feed.scrollTop + feed.clientHeight >= feed.scrollHeight - 2;
      if ((e.deltaY < 0 && atTop) || (e.deltaY > 0 && atBottom)) return;

      e.preventDefault();
      feed.scrollTop += e.deltaY * FEED_WHEEL_GAIN;
    };

    feed.addEventListener("scroll", onScroll, { passive: true });
    stage.addEventListener("wheel", onWheel, { passive: false });
    onScroll();
    return () => {
      feed.removeEventListener("scroll", onScroll);
      stage.removeEventListener("wheel", onWheel);
      if (scrollRafRef.current) cancelAnimationFrame(scrollRafRef.current);
    };
  }, [feedItems.length, history]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const next =
        e.key === "ArrowDown" || e.key === "ArrowRight" || e.key === "PageDown";
      const prev =
        e.key === "ArrowUp" || e.key === "ArrowLeft" || e.key === "PageUp";
      if (!next && !prev) return;
      const to = activeIdx + (next ? 1 : -1);
      if (to < 0 || to >= feedItems.length) return;
      e.preventDefault();
      go(to, "smooth");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeIdx, feedItems.length, go]);

  useEffect(() => {
    const rail = railRef.current;
    const btn = document.getElementById(`rail-${activeIdx}`);
    if (!rail || !btn) return;
    rail.scrollTo({
      top: btn.offsetTop - rail.clientHeight / 2 + btn.clientHeight / 2,
      left: btn.offsetLeft - rail.clientWidth / 2 + btn.clientWidth / 2,
      behavior: "smooth",
    });
  }, [activeIdx, feedItems.length]);

  const predictNext = useCallback(async () => {
    setPredicting(true);
    setPredictError(null);
    const minMs = 5000;
    const started = Date.now();
    try {
      const params = new URLSearchParams(window.location.search);
      const trainLive =
        params.get("train") === "1" && process.env.NODE_ENV === "development";

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

      setLive(data);
      scrollToPredictionRef.current = true;
    } catch (e) {
      setPredictError(e instanceof Error ? e.message : "Prediction failed");
    } finally {
      setPredicting(false);
    }
  }, []);

  const label = gate?.upcoming
    ? `Spieltag ${gate.upcoming.matchday} predicten`
    : "Nächsten Spieltag predicten";

  return (
    <>
      <main className={styles.layout}>
        {loadError && <p className={styles.error}>{loadError}</p>}
        {history && (
          <>
            <div className={styles.topBar}>
              <Logo />
              <button
                type="button"
                className={styles.cta}
                onClick={predictNext}
                disabled={predicting}
                title={
                  gate?.upcoming
                    ? `Erster Anpfiff ${gate.upcoming.first_kickoff_display}${gate.allowed === false ? ` · ${gate.message}` : ""}`
                    : undefined
                }
              >
                {predicting ? "Vorhersage wird geladen…" : label}
              </button>
              {predictError && (
                <p className={styles.errorInline}>{predictError}</p>
              )}
            </div>
            <section className={styles.stage} ref={stageRef}>
              <nav className={styles.rail} ref={railRef} aria-label="Spieltage">
                {feedItems.map((item, i) => {
                  const isPredicted = item.kind === "predicted";
                  const md =
                    item.kind === "predicted"
                      ? item.payload.matchday
                      : item.block.matchday;
                  return (
                    <button
                      key={
                        isPredicted
                          ? `predicted-${md}`
                          : `backtest-${md}`
                      }
                      id={`rail-${i}`}
                      type="button"
                      className={[
                        styles.railBtn,
                        isPredicted ? styles.railPredicted : "",
                        i === activeIdx ? styles.railActive : "",
                        isPredicted && i === activeIdx
                          ? styles.railActivePredicted
                          : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      onClick={() => go(i)}
                      title={
                        isPredicted ? "Vorhersage (noch keine Ergebnisse)" : undefined
                      }
                    >
                      {md}
                    </button>
                  );
                })}
              </nav>
              <div className={styles.feed} ref={feedRef}>
                {feedItems.map((item) =>
                  item.kind === "predicted" ? (
                    <PredictedMatchdayPane
                      key={`predicted-${item.payload.matchday}`}
                      payload={item.payload}
                    />
                  ) : (
                    <MatchdayPane
                      key={item.block.matchday}
                      block={item.block}
                    />
                  ),
                )}
              </div>
            </section>

            <aside className={styles.side} ref={sideRef}>
              <p className={styles.muted}>
                Saison {history.season}
                {history.generated_at
                  ? ` · Stand ${new Date(history.generated_at).toLocaleString("de-DE")}`
                  : ""}
              </p>
              <article className={styles.pointsHero}>
                <div className={styles.pointsTitle}>
                  Kicktipp-Punkte (Saison)
                </div>
                <div
                  className={styles.pointsScore}
                  aria-label={`${history.season_stats.kicktipp_points} von ${history.season_stats.kicktipp_points_max} Punkten`}
                >
                  <span className={styles.pointsValue}>
                    {history.season_stats.kicktipp_points}
                  </span>
                  <span className={styles.pointsSlash} aria-hidden>
                    /
                  </span>
                  <span className={styles.pointsMax}>
                    {history.season_stats.kicktipp_points_max}
                  </span>
                </div>
                <p className={styles.pointsSub}>
                  Ø {history.season_stats.kicktipp_points_avg} Punkte pro Spiel
                  · 4 exakt · 3 Abstand · 2 Tendenz
                </p>
              </article>
              <div className={styles.statRow}>
                <StatCard
                  title="Exaktes Ergebnis"
                  stats={history.season_stats}
                  field="exact"
                />
                <StatCard
                  title="Tendenz (Sieger)"
                  stats={history.season_stats}
                  field="tendency"
                />
                <StatCard
                  title="Torabstand"
                  stats={history.season_stats}
                  field="margin"
                />
              </div>
              {history.baseline_comparison && (
                <BaselineComparisonPanel data={history.baseline_comparison} />
              )}
              <div className={styles.sideTail} data-side-tail aria-hidden />
            </aside>
          </>
        )}
      </main>
    </>
  );
}
