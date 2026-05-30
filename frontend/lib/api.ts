export type ExperimentSummary = {
  id: string;
  created_at: string;
  product_id: string;
  granularity: string;
  fast_window: number;
  slow_window: number;
  initial_cash: number;
  fee_bps: number;
  final_equity: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  trade_count: number;
  win_rate_pct: number;
  avg_trade_return_pct: number;
};

export type Trade = {
  id?: string;
  experiment_id?: string;
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  return_pct: number;
};

export type EquityPoint = {
  id?: string;
  experiment_id?: string;
  time: string;
  equity: number;
  cash: number;
  position_qty: number;
  close_price: number;
};

export type ExperimentDetail = ExperimentSummary & {
  trades: Trade[];
  equity_points: EquityPoint[];
};

export type CandleStatus = {
  product_id: string;
  granularity: string;
  candle_count: number;
  first_time: string | null;
  last_time: string | null;
};

export type RunPayload = {
  fast_window: number;
  slow_window: number;
  initial_cash: number;
  fee_bps: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // Keep the status text when the response is not JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  status: () => request<CandleStatus>("/candles/status"),
  listExperiments: () => request<ExperimentSummary[]>("/experiments"),
  getExperiment: (id: string) => request<ExperimentDetail>(`/experiments/${id}`),
  runExperiment: (payload: RunPayload) =>
    request<ExperimentDetail>("/experiments/run", {
      method: "POST",
      body: JSON.stringify(payload)
    })
};

