from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
import requests
import requests_cache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DEFAULT_TIMEOUT = 30

class NBUApiError(RuntimeError):
    pass

@dataclass(frozen=True)
class NBUOpenDataClient:
    base_url: str
    timeout: int = DEFAULT_TIMEOUT
    use_cache: bool = True

    def __post_init__(self):
        if self.use_cache:
            # SQLite cache in .cache folder (safe default)
            requests_cache.install_cache(cache_name=".cache/nbu_opendata", backend="sqlite", expire_after=3600)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, NBUApiError)),
    )
    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        params = dict(params or {})
        params["json"] = ""  # API uses ?json as JSON switch; empty value is fine
        try:
            r = requests.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
        except requests.RequestException as e:
            raise NBUApiError(f"HTTP error: {e}") from e

        # NBU returns JSON arrays/objects
        try:
            return r.json()
        except Exception as e:
            raise NBUApiError(f"Failed to parse JSON: {e}") from e

    # ---------- Catalog ----------
    def list_datasets(self) -> list[dict]:
        """Entry point: lists all OpenData datasets (apikod + metadata)."""
        url = f"{self.base_url}"
        return self._get_json(url, params={})

    def list_dimensions(self) -> list[dict]:
        """Lists all dimensions (dimensionkod + name)."""
        url = f"{self.base_url}/dimension"
        return self._get_json(url, params={})

    def dimension_values(self, dimensionkod: str, date: Optional[str] = None) -> list[dict]:
        """Gets values of a dimension, optionally at a given date (yyyyMMdd)."""
        url = f"{self.base_url}/dimension/{dimensionkod}"
        params: Dict[str, Any] = {}
        if date:
            params["date"] = date
        return self._get_json(url, params=params)

    # ---------- Data fetching ----------
    def fetch_dataset_page(self, apikod: str, params: Dict[str, Any]) -> list[dict]:
        url = f"{self.base_url}/{apikod}"
        return self._get_json(url, params=params)

    def fetch_dataset_all(self, apikod: str, params: Dict[str, Any], page_size: int = 10_000) -> list[dict]:
        """Fetches all rows using offset/limit pagination (safe for large blocks)."""
        offset = 0
        out: list[dict] = []
        while True:
            page_params = dict(params)
            page_params.update({"offset": offset, "limit": page_size})
            chunk = self.fetch_dataset_page(apikod, page_params)
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < page_size:
                break
            offset += page_size
        return out
