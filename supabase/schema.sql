create extension if not exists pgcrypto;

create table if not exists candles (
  id uuid primary key default gen_random_uuid(),
  product_id text not null,
  granularity text not null,
  time timestamptz not null,
  open numeric not null,
  high numeric not null,
  low numeric not null,
  close numeric not null,
  volume numeric not null,
  inserted_at timestamptz not null default now(),
  unique (product_id, granularity, time)
);

create index if not exists candles_product_granularity_time_idx
  on candles (product_id, granularity, time);

create table if not exists experiments (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  product_id text not null,
  granularity text not null,
  fast_window integer not null,
  slow_window integer not null,
  initial_cash numeric not null,
  fee_bps numeric not null,
  final_equity numeric not null,
  total_return_pct numeric not null,
  max_drawdown_pct numeric not null,
  trade_count integer not null,
  win_rate_pct numeric not null,
  avg_trade_return_pct numeric not null
);

create index if not exists experiments_created_at_idx
  on experiments (created_at desc);

create table if not exists trades (
  id uuid primary key default gen_random_uuid(),
  experiment_id uuid not null references experiments(id) on delete cascade,
  entry_time timestamptz not null,
  exit_time timestamptz not null,
  entry_price numeric not null,
  exit_price numeric not null,
  quantity numeric not null,
  pnl numeric not null,
  return_pct numeric not null
);

create index if not exists trades_experiment_entry_idx
  on trades (experiment_id, entry_time);

create table if not exists equity_points (
  id uuid primary key default gen_random_uuid(),
  experiment_id uuid not null references experiments(id) on delete cascade,
  time timestamptz not null,
  equity numeric not null,
  cash numeric not null,
  position_qty numeric not null,
  close_price numeric not null
);

create index if not exists equity_points_experiment_time_idx
  on equity_points (experiment_id, time);

