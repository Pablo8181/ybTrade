"""Google Sheets helper stubs for deterministic exports."""

from __future__ import annotations

from typing import Iterable, Sequence


def ensure_header(sheet_id: str, tab: str, header: Sequence[str]) -> None:
    """Ensure the target sheet tab has the expected header row."""
    raise NotImplementedError("Implement Sheets header synchronization.")


def replace_rows(sheet_id: str, tab: str, matrix: Sequence[Sequence[object]]) -> None:
    """Replace all data rows in the target sheet tab with the provided matrix."""
    raise NotImplementedError("Implement Sheets row replacement.")


__all__: Iterable[str] = ("ensure_header", "replace_rows")
