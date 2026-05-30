"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, CandleStatus, ExperimentDetail, ExperimentSummary, RunPayload } from "../lib/api";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0
});

const percent = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2
});

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric"
  }).format(new Date(value));
}

function EquityChart({ points }: { points: ExperimentDetail["equity_points"] }) {
  const path = useMemo(() => {
    if (points.length < 2) return "";
    const width = 720;
    const height = 220;
    const padding = 14;
    const equities = points.map((point) => point.equity);
    const min = Math.min(...equities);
    const max = Math.max(...equities);
    const span = max - min || 1;

    return points
      .map((point, index) => {
        const x = padding + (index / (points.length - 1)) * (width - padding * 2);
        const y = height - padding - ((point.equity - min) / span) * (height - padding * 2);
        return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");
  }, [points]);

  if (points.length < 2) {
    return <div className="empty-chart">Run an experiment to draw an equity curve.</div>;
  }

  const first = points[0].equity;
  const last = points[points.length - 1].equity;

  return (
    <div className="chart-wrap">
      <svg viewBox="0 0 720 220" role="img" aria-label="Equity curve">
        <line x1="14" y1="206" x2="706" y2="206" className="axis" />
        <path d={path} className={last >= first ? "chart-line positive" : "chart-line negative"} />
      </svg>
      <div className="chart-labels">
        <span>{formatDate(points[0].time)}</span>
        <span>{formatDate(points[points.length - 1].time)}</span>
      </div>
    </div>
  );
}

export default function Home() {
  const [status, setStatus] = useState<CandleStatus | null>(null);
  const [runs, setRuns] = useState<ExperimentSummary[]>([]);
  const [selected, setSelected] = useState<ExperimentDetail | null>(null);
  const [form, setForm] = useState<RunPayload>({
    fast_window: 20,
    slow_window: 50,
    initial_cash: 10000,
    fee_bps: 5
  });
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh(selectId?: string) {
    const [nextStatus, nextRuns] = await Promise.all([api.status(), api.listExperiments()]);
    setStatus(nextStatus);
    setRuns(nextRuns);
    const id = selectId ?? selected?.id ?? nextRuns[0]?.id;
    if (id) {
      setSelected(await api.getExperiment(id));
    } else {
      setSelected(null);
    }
  }

  useEffect(() => {
    refresh()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setRunning(true);
    try {
      const experiment = await api.runExperiment(form);
      await refresh(experiment.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run experiment");
    } finally {
      setRunning(false);
    }
  }

  async function selectRun(id: string) {
    setError(null);
    try {
      setSelected(await api.getExperiment(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load experiment");
    }
  }

  return (
    <main className="page">
      <section className="topbar">
        <div>
          <p className="eyebrow">BTC-USD daily backtesting</p>
          <h1>Moving-average experiment bench</h1>
        </div>
        <div className="status-box">
          <span>
            {status?.candle_count ?? 0} {status?.granularity === "ONE_DAY" ? "daily" : status?.granularity ?? ""} candles
          </span>
          <strong>{status ? `${formatDate(status.first_time)} to ${formatDate(status.last_time)}` : "Loading data status"}</strong>
        </div>
      </section>

      {error && <div className="alert">{error}</div>}

      <section className="workspace">
        <aside className="panel controls">
          <h2>Run backtest</h2>
          <form onSubmit={submit}>
            <label>
              Fast SMA window
              <input
                type="number"
                min="2"
                max="500"
                value={form.fast_window}
                onChange={(event) => setForm({ ...form, fast_window: Number(event.target.value) })}
              />
            </label>
            <label>
              Slow SMA window
              <input
                type="number"
                min="3"
                max="1000"
                value={form.slow_window}
                onChange={(event) => setForm({ ...form, slow_window: Number(event.target.value) })}
              />
            </label>
            <label>
              Initial cash
              <input
                type="number"
                min="100"
                step="100"
                value={form.initial_cash}
                onChange={(event) => setForm({ ...form, initial_cash: Number(event.target.value) })}
              />
            </label>
            <label>
              Fee bps
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={form.fee_bps}
                onChange={(event) => setForm({ ...form, fee_bps: Number(event.target.value) })}
              />
            </label>
            <button type="submit" disabled={running || loading}>
              {running ? "Running..." : "Run experiment"}
            </button>
          </form>
        </aside>

        <section className="panel detail">
          <div className="section-header">
            <div>
              <p className="eyebrow">Selected run</p>
              <h2>{selected ? `${selected.fast_window}/${selected.slow_window} SMA` : "No experiment yet"}</h2>
            </div>
            {selected && <span className="run-date">{formatDate(selected.created_at)}</span>}
          </div>

          {selected ? (
            <>
              <div className="metrics">
                <div>
                  <span>Total return</span>
                  <strong className={selected.total_return_pct >= 0 ? "gain" : "loss"}>
                    {percent.format(selected.total_return_pct)}%
                  </strong>
                </div>
                <div>
                  <span>Final equity</span>
                  <strong>{currency.format(selected.final_equity)}</strong>
                </div>
                <div>
                  <span>Max drawdown</span>
                  <strong className="loss">{percent.format(selected.max_drawdown_pct)}%</strong>
                </div>
                <div>
                  <span>Win rate</span>
                  <strong>{percent.format(selected.win_rate_pct)}%</strong>
                </div>
              </div>
              <EquityChart points={selected.equity_points} />
            </>
          ) : (
            <div className="empty-state">Run a strategy to populate metrics, trades, and an equity curve.</div>
          )}
        </section>
      </section>

      <section className="panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">History</p>
            <h2>Previous experiments</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Params</th>
                <th>Return</th>
                <th>Drawdown</th>
                <th>Trades</th>
                <th>Win rate</th>
                <th>Final equity</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className={selected?.id === run.id ? "selected-row" : ""}
                  onClick={() => selectRun(run.id)}
                >
                  <td>{formatDate(run.created_at)}</td>
                  <td>
                    {run.fast_window}/{run.slow_window}, {run.fee_bps} bps
                  </td>
                  <td className={run.total_return_pct >= 0 ? "gain" : "loss"}>{percent.format(run.total_return_pct)}%</td>
                  <td className="loss">{percent.format(run.max_drawdown_pct)}%</td>
                  <td>{run.trade_count}</td>
                  <td>{percent.format(run.win_rate_pct)}%</td>
                  <td>{currency.format(run.final_equity)}</td>
                </tr>
              ))}
              {!runs.length && (
                <tr>
                  <td colSpan={7} className="empty-cell">
                    No experiments saved yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Trades</p>
            <h2>Trade log</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Entry</th>
                <th>Exit</th>
                <th>Entry price</th>
                <th>Exit price</th>
                <th>Qty</th>
                <th>PnL</th>
                <th>Return</th>
              </tr>
            </thead>
            <tbody>
              {selected?.trades.map((trade) => (
                <tr key={`${trade.entry_time}-${trade.exit_time}`}>
                  <td>{formatDate(trade.entry_time)}</td>
                  <td>{formatDate(trade.exit_time)}</td>
                  <td>{currency.format(trade.entry_price)}</td>
                  <td>{currency.format(trade.exit_price)}</td>
                  <td>{trade.quantity.toFixed(6)}</td>
                  <td className={trade.pnl >= 0 ? "gain" : "loss"}>{currency.format(trade.pnl)}</td>
                  <td className={trade.return_pct >= 0 ? "gain" : "loss"}>{percent.format(trade.return_pct)}%</td>
                </tr>
              ))}
              {!selected?.trades.length && (
                <tr>
                  <td colSpan={7} className="empty-cell">
                    No trades for this run.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
