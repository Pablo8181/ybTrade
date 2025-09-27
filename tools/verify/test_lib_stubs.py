#!/usr/bin/env python3
"""Lightweight harness to ensure stub helpers expose docstrings."""

from __future__ import annotations

import inspect
import sys
from importlib import import_module
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_docstrings(module_name: str, attribute_names: Iterable[str]) -> Tuple[int, int]:
    """Return (pass_count, fail_count) while logging docstring presence."""
    module = import_module(module_name)
    passed = 0
    failed = 0
    for attr in attribute_names:
        obj = getattr(module, attr)
        if inspect.getdoc(obj):
            print(f"[verify] PASS {module_name}.{attr} docstring present")
            passed += 1
        else:
            print(f"[verify] FAIL {module_name}.{attr} docstring missing")
            failed += 1
    return passed, failed


def main() -> int:
    """Run docstring checks across stub modules."""
    checks: List[Tuple[str, Iterable[str]]] = [
        ("lib.py.bq", ("get_client", "load_dataframe", "insert_json")),
        ("lib.py.sheets", ("ensure_header", "replace_rows")),
        ("lib.py.binance", ("get_klines_daily_binance",)),
        (
            "lib.py.indicators",
            (
                "sma",
                "ema",
                "rma",
                "atr",
                "rsi",
                "macd",
                "macd_signal",
                "macd_histogram",
                "roc",
                "vwap",
                "vwma",
                "delta",
                "cumulative_delta",
                "taker_buy_ratio",
                "relative_volume",
                "average_trade_size",
                "on_balance_volume",
                "accumulation_distribution",
                "chaikin_money_flow",
                "money_flow_index",
                "bollinger_bands",
                "keltner_channels",
                "directional_index",
                "donchian_channels",
                "swing_points",
                "divergence_flags",
                "fibonacci_levels",
            ),
        ),
    ]

    total_pass = 0
    total_fail = 0
    for module_name, attrs in checks:
        try:
            passed, failed = check_docstrings(module_name, attrs)
        except Exception as exc:  # pragma: no cover - harness logging only
            print(f"[verify] FAIL {module_name} import/docstring error: {exc}")
            total_fail += 1
            continue
        total_pass += passed
        total_fail += failed

    summary = f"[verify] PASS summary: {total_pass} passed, {total_fail} failed"
    if total_fail:
        print(summary.replace("PASS", "FAIL"))
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
