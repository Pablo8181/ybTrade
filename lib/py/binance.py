"""Binance data access stubs for ingest pipelines."""

from __future__ import annotations

from datetime import date
from typing import Iterable, List, Mapping


def get_klines_daily_binance(symbol: str, since_date: date) -> List[Mapping[str, object]]:
    """Fetch daily kline data for a symbol from Binance starting at the given date."""
    raise NotImplementedError("Implement Binance kline retrieval.")


__all__: Iterable[str] = ("get_klines_daily_binance",)
