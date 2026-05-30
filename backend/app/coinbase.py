from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx


COINBASE_PUBLIC_API = "https://api.coinbase.com/api/v3/brokerage/market/products"
GRANULARITY_SECONDS = {
    "ONE_MINUTE": 60,
    "FIVE_MINUTE": 300,
    "FIFTEEN_MINUTE": 900,
    "THIRTY_MINUTE": 1800,
    "ONE_HOUR": 3600,
    "TWO_HOUR": 7200,
    "SIX_HOUR": 21600,
    "ONE_DAY": 86400,
}


async def fetch_candles(
    product_id: str,
    granularity: str,
    days: int,
    end_time: datetime | None = None,
) -> List[Dict[str, Any]]:
    if granularity not in GRANULARITY_SECONDS:
        raise ValueError(f"Unsupported granularity: {granularity}")

    end = (end_time or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    step = timedelta(seconds=GRANULARITY_SECONDS[granularity] * 300)
    rows: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30) as client:
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + step, end)
            response = await client.get(
                f"{COINBASE_PUBLIC_API}/{product_id}/candles",
                params={
                    "start": str(int(cursor.timestamp())),
                    "end": str(int(chunk_end.timestamp())),
                    "granularity": granularity,
                },
            )
            response.raise_for_status()
            candles = response.json().get("candles", [])
            for candle in candles:
                candle_time = datetime.fromtimestamp(int(candle["start"]), tz=timezone.utc)
                rows.append(
                    {
                        "product_id": product_id,
                        "granularity": granularity,
                        "time": candle_time.isoformat(),
                        "open": float(candle["open"]),
                        "high": float(candle["high"]),
                        "low": float(candle["low"]),
                        "close": float(candle["close"]),
                        "volume": float(candle["volume"]),
                    }
                )
            cursor = chunk_end

    unique = {row["time"]: row for row in rows}
    return [unique[key] for key in sorted(unique.keys())]
