import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

from fuel_route.application.plan_trip import ExternalServiceError


def get_json(service: str, url: str) -> Any:
    """GET a JSON document; any network, HTTP or decoding failure becomes ExternalServiceError."""
    request = Request(url, headers={"User-Agent": settings.HTTP_USER_AGENT})
    try:
        with urlopen(request, timeout=settings.EXTERNAL_TIMEOUT_SECONDS) as response:
            return json.load(response)
    except (URLError, TimeoutError, ValueError) as error:
        raise ExternalServiceError(f"{service} request failed: {error}") from error
