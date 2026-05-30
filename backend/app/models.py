from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class LoadDataRequest(BaseModel):
    product_id: Literal["BTC-USD"] = "BTC-USD"
    granularity: Literal["ONE_DAY"] = "ONE_DAY"
    days: int = Field(default=730, ge=1, le=1825)


class LoadDataResponse(BaseModel):
    product_id: str
    granularity: str
    candles_upserted: int
    start_time: datetime
    end_time: datetime


class CandleStatus(BaseModel):
    product_id: str = "BTC-USD"
    granularity: str = "ONE_DAY"
    candle_count: int
    first_time: Optional[datetime] = None
    last_time: Optional[datetime] = None


class RunExperimentRequest(BaseModel):
    fast_window: int = Field(default=20, ge=2, le=500)
    slow_window: int = Field(default=50, ge=3, le=1000)
    initial_cash: float = Field(default=10_000.0, gt=0, le=10_000_000)
    fee_bps: float = Field(default=5.0, ge=0, le=100)

    @model_validator(mode="after")
    def validate_windows(self) -> "RunExperimentRequest":
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window")
        return self


class ExperimentSummary(BaseModel):
    id: str
    created_at: datetime
    product_id: str
    granularity: str
    fast_window: int
    slow_window: int
    initial_cash: float
    fee_bps: float
    final_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    win_rate_pct: float
    avg_trade_return_pct: float


class Trade(BaseModel):
    id: Optional[str] = None
    experiment_id: Optional[str] = None
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float


class EquityPoint(BaseModel):
    id: Optional[str] = None
    experiment_id: Optional[str] = None
    time: datetime
    equity: float
    cash: float
    position_qty: float
    close_price: float


class ExperimentDetail(ExperimentSummary):
    trades: List[Trade]
    equity_points: List[EquityPoint]
