"""GitHub REST API client with rate limiting and disk caching."""

import logging
import time
from pathlib import Path
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

from hackathon_analyzer.utils.cache import DiskCache


class GitHubClient:
    _BASE = "https://api.github.com"

    def __init__(self, token: str, cache: DiskCache, rate_limit_per_minute: int = 30):
        self._token = token
        self._cache = cache
        self._interval = 60.0 / max(rate_limit_per_minute, 1)
        self._last_call: float = 0.0

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _rate_limit_wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_call = time.monotonic()

    def _get(self, url: str, params: Optional[dict] = None, timeout: int = 15) -> Optional[dict]:
        self._rate_limit_wait()
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=timeout)
            if resp.status_code == 403:
                reset_at = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                sleep_for = max(0, reset_at - time.time()) + 2
                time.sleep(min(sleep_for, 120))
                return None
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException as exc:
            logger.warning("GitHub API request failed (%s): %s", url, exc)
        return None

    def search_code(self, query: str, language: str = "") -> list[dict]:
        """Search GitHub code. Results are cached by query+language."""
        cache_key = f"search_code:{query}:{language}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params: dict[str, Any] = {"q": query, "per_page": 10}
        if language:
            params["q"] = f"{query} language:{language}"

        data = self._get(f"{self._BASE}/search/code", params=params)
        results: list[dict] = []
        if data and "items" in data:
            results = [
                {
                    "repo": item["repository"]["full_name"],
                    "url": item["html_url"],
                    "path": item["path"],
                }
                for item in data["items"]
            ]

        self._cache.set(cache_key, results)
        return results

    def get_repo_info(self, owner: str, name: str) -> Optional[dict]:
        """Fetch basic repo metadata (size, language, stars, etc.)."""
        cache_key = f"repo_info:{owner}/{name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        data = self._get(f"{self._BASE}/repos/{owner}/{name}")
        if data:
            self._cache.set(cache_key, data)
        return data
