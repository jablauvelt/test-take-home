from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from .backtester import Candle
from .config import Settings

PAGE_SIZE = 1000


def get_supabase(settings: Settings) -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


class Repository:
    def __init__(self, client: Client):
        self.client = client

    def _execute_all(self, query: Any) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        start = 0
        while True:
            page = query.range(start, start + PAGE_SIZE - 1).execute().data
            rows.extend(page)
            if len(page) < PAGE_SIZE:
                return rows
            start += PAGE_SIZE

    def _serialize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in row.items()
        }

    def upsert_candles(self, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0
        for index in range(0, len(rows), 500):
            self.client.table("candles").upsert(
                rows[index : index + 500],
                on_conflict="product_id,granularity,time",
            ).execute()
        return len(rows)

    def candle_status(self, product_id: str = "BTC-USD", granularity: str = "ONE_HOUR") -> Dict[str, Any]:
        rows = self._execute_all(
            self.client.table("candles")
            .select("time")
            .eq("product_id", product_id)
            .eq("granularity", granularity)
            .order("time")
        )
        times = [row["time"] for row in rows]
        return {
            "product_id": product_id,
            "granularity": granularity,
            "candle_count": len(times),
            "first_time": times[0] if times else None,
            "last_time": times[-1] if times else None,
        }

    def list_candles(self, product_id: str = "BTC-USD", granularity: str = "ONE_HOUR") -> List[Candle]:
        rows = self._execute_all(
            self.client.table("candles")
            .select("time,open,high,low,close,volume")
            .eq("product_id", product_id)
            .eq("granularity", granularity)
            .order("time")
        )
        return [
            Candle(
                time=datetime.fromisoformat(row["time"].replace("Z", "+00:00")),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for row in rows
        ]

    def create_experiment(
        self,
        params: Dict[str, Any],
        metrics: Dict[str, Any],
        trades: List[Dict[str, Any]],
        equity_points: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        experiment_row = {**params, **metrics}
        experiment = self.client.table("experiments").insert(experiment_row).execute().data[0]
        experiment_id = experiment["id"]

        if trades:
            self.client.table("trades").insert(
                [self._serialize_row({**trade, "experiment_id": experiment_id}) for trade in trades]
            ).execute()

        if equity_points:
            for index in range(0, len(equity_points), 500):
                self.client.table("equity_points").insert(
                    [
                        self._serialize_row({**point, "experiment_id": experiment_id})
                        for point in equity_points[index : index + 500]
                    ]
                ).execute()

        return experiment

    def list_experiments(self) -> List[Dict[str, Any]]:
        return (
            self.client.table("experiments")
            .select("*")
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        experiment_result = self.client.table("experiments").select("*").eq("id", experiment_id).maybe_single().execute()
        if experiment_result.data is None:
            return None

        trades = self._execute_all(
            self.client.table("trades")
            .select("*")
            .eq("experiment_id", experiment_id)
            .order("entry_time")
        )
        equity_points = self._execute_all(
            self.client.table("equity_points")
            .select("*")
            .eq("experiment_id", experiment_id)
            .order("time")
        )
        return {**experiment_result.data, "trades": trades, "equity_points": equity_points}
