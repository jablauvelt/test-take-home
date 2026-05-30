# BTC-USD Backtesting Experiment Platform

A tiny internal-tool style backtesting app for BTC-USD moving-average crossover experiments. It uses real Coinbase public market data, stores candles and experiment results in Supabase, exposes a FastAPI backend, and provides a Next.js UI for running and comparing backtests.

## What Works

- Loads 1 year of hourly BTC-USD candles from Coinbase public market data.
- Runs a long-only moving-average crossover strategy from the web UI.
- Lets users configure fast SMA window, slow SMA window, initial cash, and fee bps.
- Persists experiment summaries, trade-level results, and equity curves in Supabase.
- Shows previous runs, key metrics, a trade log, and an SVG equity curve.
- Includes backend unit/API tests and deployment-ready Vercel config.

## Repo Layout

- `backend/`: FastAPI app, Coinbase loader, Supabase repository, backtester, tests.
- `frontend/`: Next.js app-router frontend.
- `supabase/schema.sql`: Postgres schema for candles, experiments, trades, and equity points.

## Local Setup

Create a free Supabase project and run `supabase/schema.sql` in the SQL editor.

Backend:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Set these backend env vars:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
CORS_ORIGINS=http://localhost:3000
```

Load data:

```bash
curl -X POST http://localhost:8000/admin/load-data \
  -H "Content-Type: application/json" \
  -d '{"product_id":"BTC-USD","granularity":"ONE_HOUR","days":365}'
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Set:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Deployment

Live frontend URL: `TODO after Vercel deploy`

Live backend/API URL: `TODO after Vercel deploy`

Recommended free deployment:

1. Push this repo to GitHub.
2. Create a Supabase project and run `supabase/schema.sql`.
3. Create a Vercel project for `backend/`.
   - Framework preset: Other.
   - Root directory: `backend`.
   - Env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `CORS_ORIGINS`.
4. Create a Vercel project for `frontend/`.
   - Framework preset: Next.js.
   - Root directory: `frontend`.
   - Env var: `NEXT_PUBLIC_API_BASE_URL=https://your-backend.vercel.app`.
5. Update backend `CORS_ORIGINS` to include the deployed frontend URL.
6. Call deployed `/admin/load-data` once to preload Supabase before sharing the app.

## Data Loading

The backend calls Coinbase's public Advanced Trade candles endpoint in chunks of up to 300 candles, deduplicates by timestamp, and upserts into Supabase on `(product_id, granularity, time)`. No Coinbase account or exchange keys are required.

## Strategy

The strategy is intentionally simple:

- Compute fast and slow SMAs on hourly close prices.
- Buy with all available cash when fast SMA crosses above slow SMA.
- Sell the full position when fast SMA crosses below slow SMA.
- Charge configurable fee bps on entries and exits.
- Mark equity at each candle close.
- Close any open position at the final candle for reporting.

Metrics include final equity, total return, max drawdown, trade count, win rate, and average trade return.

## Shortcuts And Tradeoffs

- No auth, by design for the prompt.
- The admin data-load endpoint is public; for a real system it should be protected or moved to a job.
- Backtests use all-in/all-out sizing and candle close prices only.
- The frontend chart is a lightweight SVG instead of a charting dependency.
- Supabase is accessed only by the backend using the service-role key.

## What I Would Improve Next

- Add server-side pagination for large equity/trade histories.
- Add benchmark buy-and-hold comparison and Sharpe/volatility metrics.
- Add more strategy templates and parameter presets.
- Add background data refresh jobs and API protection for admin endpoints.
- Add Playwright end-to-end tests against a seeded test database.

## Tests

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```
