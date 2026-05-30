from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.backtester import Candle
from app.main import app, get_repo


class FakeRepo:
    def __init__(self) -> None:
        self.experiment = None
        self.trades = []
        self.equity_points = []

    def list_candles(self):
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        closes = [10, 9, 8, 9, 10, 11, 12, 11, 10, 9, 8]
        return [
            Candle(
                time=start + timedelta(hours=index),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1,
            )
            for index, close in enumerate(closes)
        ]

    def candle_status(self):
        return {
            "product_id": "BTC-USD",
            "granularity": "ONE_HOUR",
            "candle_count": 11,
            "first_time": "2025-01-01T00:00:00+00:00",
            "last_time": "2025-01-01T10:00:00+00:00",
        }

    def upsert_candles(self, rows):
        self.loaded_rows = rows
        return len(rows)

    def create_experiment(self, params, metrics, trades, equity_points):
        self.experiment = {
            "id": "00000000-0000-0000-0000-000000000001",
            "created_at": datetime(2025, 1, 2, tzinfo=timezone.utc).isoformat(),
            **params,
            **metrics,
        }
        self.trades = trades
        self.equity_points = equity_points
        return self.experiment

    def get_experiment(self, experiment_id):
        if self.experiment is None:
            return None
        return {
            **self.experiment,
            "trades": self.trades,
            "equity_points": self.equity_points,
        }

    def list_experiments(self):
        return [self.experiment] if self.experiment else []


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_experiment_validation() -> None:
    app.dependency_overrides[get_repo] = lambda: FakeRepo()
    client = TestClient(app)
    response = client.post(
        "/experiments/run",
        json={"fast_window": 50, "slow_window": 20, "initial_cash": 1000, "fee_bps": 0},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_run_experiment_with_fake_repo() -> None:
    fake_repo = FakeRepo()
    app.dependency_overrides[get_repo] = lambda: fake_repo
    client = TestClient(app)

    response = client.post(
        "/experiments/run",
        json={"fast_window": 2, "slow_window": 3, "initial_cash": 1000, "fee_bps": 0},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["trade_count"] == 1
    assert len(body["trades"]) == 1
    assert len(body["equity_points"]) == 11


def test_candle_status_uses_repository() -> None:
    app.dependency_overrides[get_repo] = lambda: FakeRepo()
    client = TestClient(app)

    response = client.get("/candles/status")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["candle_count"] == 11


def test_get_experiment_returns_404_when_missing() -> None:
    app.dependency_overrides[get_repo] = lambda: FakeRepo()
    client = TestClient(app)

    response = client.get("/experiments/00000000-0000-0000-0000-000000000404")

    app.dependency_overrides.clear()

    assert response.status_code == 404


def test_load_data_persists_fetched_candles(monkeypatch) -> None:
    fake_repo = FakeRepo()

    async def fake_fetch_candles(product_id, granularity, days):
        assert product_id == "BTC-USD"
        assert granularity == "ONE_HOUR"
        assert days == 1
        return [
            {
                "product_id": "BTC-USD",
                "granularity": "ONE_HOUR",
                "time": "2025-01-01T00:00:00+00:00",
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 10.0,
            }
        ]

    monkeypatch.setattr("app.main.fetch_candles", fake_fetch_candles)
    app.dependency_overrides[get_repo] = lambda: fake_repo
    client = TestClient(app)

    response = client.post("/admin/load-data", json={"days": 1})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["candles_upserted"] == 1
    assert fake_repo.loaded_rows[0]["close"] == 1.5
