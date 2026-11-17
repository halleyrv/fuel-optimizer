import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from fuel_route.application.plan_trip import ExternalServiceError


def get_json(service: str, url: str, client_error_body: bool = False) -> Any:
    """GET a JSON document; any network, HTTP or decoding failure becomes ExternalServiceError.

    With `client_error_body`, a 4xx response returns its JSON body so the caller can read
    the provider's error code (OSRM answers "NoRoute" with HTTP 400).
    """
    request = Request(url, headers={"User-Agent": settings.HTTP_USER_AGENT})
    try:
        try:
            with urlopen(request, timeout=settings.EXTERNAL_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except HTTPError as error:
            if client_error_body and 400 <= error.code < 500:
                return json.load(error)
            raise
    except (URLError, TimeoutError, ValueError) as error:
        raise ExternalServiceError(f"{service} request failed: {error}") from error
