"""BigQuery helper stubs for the staged data platform."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence


def get_client() -> "bigquery.Client":
    """Return a BigQuery client authenticated via Application Default Credentials."""
    raise NotImplementedError("Implement BigQuery client acquisition.")


def load_dataframe(table_id: str, df: "DataFrame", *, write_disposition: str = "WRITE_APPEND") -> None:
    """Load a pandas DataFrame into the specified BigQuery table."""
    raise NotImplementedError("Implement DataFrame load to BigQuery.")


def insert_json(table_id: str, rows: Sequence[Mapping[str, object]], *, retry: int = 3) -> None:
    """Insert JSON payload rows into a BigQuery table using streaming inserts."""
    raise NotImplementedError("Implement JSON row insertion to BigQuery.")


__all__: Iterable[str] = ("get_client", "load_dataframe", "insert_json")
