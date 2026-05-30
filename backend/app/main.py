from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .backtester import run_ma_crossover
from .coinbase import fetch_candles
from .config import Settings, get_settings
from .models import (
    CandleStatus,
    ExperimentDetail,
    ExperimentSummary,
    LoadDataRequest,
    LoadDataResponse,
    RunExperimentRequest,
)
from .repository import Repository, get_supabase


app = FastAPI(title="BTC-USD Backtesting API", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_repo(settings: Settings = Depends(get_settings)) -> Repository:
    return Repository(get_supabase(settings))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/supabase")
def supabase_health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "status": "checking",
        "supabase_url_configured": bool(settings.supabase_url),
        "supabase_key_configured": bool(settings.supabase_service_role_key),
        "supabase_key_type": "unknown",
    }

    if settings.supabase_service_role_key.startswith("sb_secret_"):
        diagnostics["supabase_key_type"] = "secret"
    elif settings.supabase_service_role_key.startswith("sb_publishable_"):
        diagnostics["supabase_key_type"] = "publishable"
    elif settings.supabase_service_role_key.startswith("eyJ"):
        diagnostics["supabase_key_type"] = "legacy_jwt"

    try:
        repo = Repository(get_supabase(settings))
        status = repo.candle_status()
    except Exception as exc:
        diagnostics["status"] = "error"
        diagnostics["error_type"] = type(exc).__name__
        diagnostics["error"] = str(exc)
        return diagnostics

    diagnostics["status"] = "ok"
    diagnostics["candle_count"] = status["candle_count"]
    return diagnostics


@app.post("/admin/load-data", response_model=LoadDataResponse)
async def load_data(payload: LoadDataRequest, repo: Repository = Depends(get_repo)) -> LoadDataResponse:
    candles = await fetch_candles(payload.product_id, payload.granularity, payload.days)
    count = repo.upsert_candles(candles)
    if not candles:
        now = datetime.now(timezone.utc)
        return LoadDataResponse(
            product_id=payload.product_id,
            granularity=payload.granularity,
            candles_upserted=0,
            start_time=now,
            end_time=now,
        )

    return LoadDataResponse(
        product_id=payload.product_id,
        granularity=payload.granularity,
        candles_upserted=count,
        start_time=candles[0]["time"],
        end_time=candles[-1]["time"],
    )


@app.get("/candles/status", response_model=CandleStatus)
def candle_status(repo: Repository = Depends(get_repo)) -> CandleStatus:
    return CandleStatus(**repo.candle_status())


@app.post("/experiments/run", response_model=ExperimentDetail)
def run_experiment(payload: RunExperimentRequest, repo: Repository = Depends(get_repo)) -> ExperimentDetail:
    candles = repo.list_candles()
    if not candles:
        raise HTTPException(status_code=400, detail="No candle data loaded. Run /admin/load-data first.")

    try:
        result = run_ma_crossover(
            candles=candles,
            fast_window=payload.fast_window,
            slow_window=payload.slow_window,
            initial_cash=payload.initial_cash,
            fee_bps=payload.fee_bps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    experiment = repo.create_experiment(
        params={
            "product_id": "BTC-USD",
            "granularity": "ONE_HOUR",
            "fast_window": payload.fast_window,
            "slow_window": payload.slow_window,
            "initial_cash": payload.initial_cash,
            "fee_bps": payload.fee_bps,
        },
        metrics=result["metrics"],
        trades=result["trades"],
        equity_points=result["equity_points"],
    )
    detail = repo.get_experiment(experiment["id"])
    if detail is None:
        raise HTTPException(status_code=500, detail="Experiment saved but could not be read back")
    return ExperimentDetail(**detail)


@app.get("/experiments", response_model=list[ExperimentSummary])
def list_experiments(repo: Repository = Depends(get_repo)) -> list[ExperimentSummary]:
    return [ExperimentSummary(**row) for row in repo.list_experiments()]


@app.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
def get_experiment(experiment_id: str, repo: Repository = Depends(get_repo)) -> ExperimentDetail:
    detail = repo.get_experiment(experiment_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentDetail(**detail)


handler = app
