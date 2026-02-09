from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
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
            requests_cache.install_cache(
                cache_name=".cache/nbu_opendata",
                backend="sqlite",
                expire_after=3600,
            )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, NBUApiError)),
    )
    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        params = dict(params or {})
        params["json"] = ""
        try:
            r = requests.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
        except requests.RequestException as e:
            raise NBUApiError(f"HTTP error: {e}") from e

        try:
            return r.json()
        except Exception as e:
            raise NBUApiError(f"Failed to parse JSON: {e}") from e

    def list_datasets(self) -> list[dict]:
        return self._get_json(f"{self.base_url}", params={})

    def list_dimensions(self) -> list[dict]:
        return self._get_json(f"{self.base_url}/dimension", params={})

    def dimension_values(self, dimensionkod: str, date: Optional[str] = None) -> list[dict]:
        params: Dict[str, Any] = {}
        if date:
            params["date"] = date
        return self._get_json(f"{self.base_url}/dimension/{dimensionkod}", params=params)

    def fetch_dataset_page(self, apikod: str, params: Dict[str, Any]) -> list[dict]:
        return self._get_json(f"{self.base_url}/{apikod}", params=params)

    def fetch_dataset_all(self, apikod: str, params: Dict[str, Any], page_size: int = 10_000, hard_cap_rows: int = 250_000) -> list[dict]:
        offset = 0
        out: list[dict] = []
        while True:
            page_params = dict(params)
            page_params.update({"offset": offset, "limit": page_size})
            chunk = self.fetch_dataset_page(apikod, page_params)
            if not chunk:
                break
            out.extend(chunk)
            if len(out) >= hard_cap_rows:
                break
            if len(chunk) < page_size:
                break
            offset += page_size
        return out
