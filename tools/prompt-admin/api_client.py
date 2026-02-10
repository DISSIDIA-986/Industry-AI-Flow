"""Prompt admin API client."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class PromptApiError(RuntimeError):
    """Raised when prompt-admin API request fails."""


class PromptApiClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method=method, url=url, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise PromptApiError(f"{method} {path} failed: {exc}") from exc

        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError as exc:
            raise PromptApiError(f"{method} {path} returned non-JSON payload") from exc

    def list_prompts(
        self,
        *,
        page: int = 1,
        size: int = 20,
        category: Optional[str] = None,
        is_active: Optional[bool] = True,
        is_latest: Optional[bool] = True,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "page": page,
            "size": size,
            "is_active": is_active,
            "is_latest": is_latest,
        }
        if category:
            params["category"] = category
        return self._request("GET", "/api/prompts/", params=params)

    def get_prompt(self, prompt_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/prompts/{prompt_id}")

    def create_prompt(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/prompts/", json=payload)

    def update_prompt(self, prompt_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"/api/prompts/{prompt_id}", json=payload)

    def delete_prompt(self, prompt_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/api/prompts/{prompt_id}")

    def test_prompt(
        self, prompt_id: str, variables: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"variables": variables}
        if context is not None:
            payload["context"] = context
        return self._request("POST", f"/api/prompts/{prompt_id}/test", json=payload)

    def list_categories(self) -> list[str]:
        data = self._request("GET", "/api/prompts/categories/list")
        return data if isinstance(data, list) else []

    def list_tags(self) -> list[Dict[str, Any]]:
        data = self._request("GET", "/api/prompts/tags/list")
        return data if isinstance(data, list) else []

    def get_metrics_summary(
        self, *, days: int = 7, category: Optional[str] = None, top_limit: int = 10
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"days": days, "top_limit": top_limit}
        if category:
            params["category"] = category
        return self._request("GET", "/api/prompts/metrics/summary", params=params)

    def list_experiments(
        self,
        *,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "size": size}
        if status:
            params["status"] = status
        if category:
            params["category"] = category
        return self._request("GET", "/api/prompts/experiments", params=params)

    def get_experiment(self, experiment_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/prompts/experiments/{experiment_id}")

    def create_experiment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/prompts/experiments", json=payload)

    def update_experiment_traffic(self, experiment_id: str, traffic_split: float) -> Dict[str, Any]:
        return self._request(
            "PATCH",
            f"/api/prompts/experiments/{experiment_id}/traffic",
            json={"traffic_split": traffic_split},
        )

    def update_experiment_status(self, experiment_id: str, status: str) -> Dict[str, Any]:
        return self._request(
            "PATCH",
            f"/api/prompts/experiments/{experiment_id}/status",
            json={"status": status},
        )
