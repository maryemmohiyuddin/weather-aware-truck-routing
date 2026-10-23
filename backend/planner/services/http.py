import time

import requests

from planner.services.errors import UpstreamError

USER_AGENT = "WeatherAwareTruckRouting/1.0 (educational demo)"


def get_json(url: str, params: dict | None = None, timeout: float = 40, service: str = "service"):
    last_error: UpstreamError | None = None
    for attempt in range(2):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_error = UpstreamError(f"The {service} did not respond. Try again in a moment.")
            last_error.__cause__ = exc
            if attempt == 0:
                time.sleep(0.4)
                continue
            raise last_error from exc
        if response.status_code >= 500 and attempt == 0:
            time.sleep(0.4)
            continue
        if response.status_code >= 400:
            message = _message(response)
            raise UpstreamError(message or f"The {service} returned {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise UpstreamError(f"The {service} returned something that was not JSON.") from exc
    raise last_error or UpstreamError(f"The {service} did not respond. Try again in a moment.")


def _message(response: requests.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    if isinstance(body, dict):
        reason = body.get("message") or body.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return None
