"""Tiny JSON HTTP client on the standard library, with retries for rate limits and server errors."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

USER_AGENT = "job-scraper/1.0 (personal job search)"
RETRY_STATUSES = {429, 500, 502, 503, 504}


class FetchError(Exception):
    pass


def request_json(url: str, *, body: dict | None = None, timeout: float = 30, retries: int = 3):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUSES and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise FetchError(f"HTTP {e.code} from {url}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise FetchError(f"could not reach {url}: {e}") from e
        except json.JSONDecodeError as e:
            raise FetchError(f"{url} did not return JSON") from e
    raise FetchError(f"gave up on {url}")
