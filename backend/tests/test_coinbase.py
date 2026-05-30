from datetime import datetime, timezone

import pytest

from app import coinbase


class FakeResponse:
    def __init__(self, candles):
        self._candles = candles

    def raise_for_status(self):
        return None

    def json(self):
        return {"candles": self._candles}


class FakeAsyncClient:
    requests = []

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def get(self, url, params):
        self.requests.append({"url": url, "params": params})
        if len(self.requests) == 1:
            return FakeResponse(
                [
                    {
                        "start": "1735704000",
                        "open": "100",
                        "high": "110",
                        "low": "90",
                        "close": "105",
                        "volume": "2.5",
                    },
                    {
                        "start": "1735700400",
                        "open": "95",
                        "high": "100",
                        "low": "90",
                        "close": "98",
                        "volume": "1.2",
                    },
                ]
            )
        return FakeResponse(
            [
                {
                    "start": "1735704000",
                    "open": "101",
                    "high": "111",
                    "low": "91",
                    "close": "106",
                    "volume": "2.6",
                }
            ]
        )


@pytest.mark.anyio
async def test_fetch_candles_chunks_sorts_and_deduplicates(monkeypatch) -> None:
    FakeAsyncClient.requests = []
    monkeypatch.setattr(coinbase.httpx, "AsyncClient", FakeAsyncClient)

    rows = await coinbase.fetch_candles(
        product_id="BTC-USD",
        granularity="ONE_HOUR",
        days=13,
        end_time=datetime(2025, 1, 14, tzinfo=timezone.utc),
    )

    assert len(FakeAsyncClient.requests) == 2
    assert [row["time"] for row in rows] == [
        "2025-01-01T03:00:00+00:00",
        "2025-01-01T04:00:00+00:00",
    ]
    assert rows[1]["close"] == 106.0
    assert rows[1]["product_id"] == "BTC-USD"


@pytest.mark.anyio
async def test_fetch_candles_rejects_unknown_granularity() -> None:
    with pytest.raises(ValueError, match="Unsupported granularity"):
        await coinbase.fetch_candles("BTC-USD", "ONE_WEEK", 1)
