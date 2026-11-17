from typing import Protocol

from fuel_route.domain.geocoding import Place


class ExternalServiceError(Exception):
    """A routing or geocoding provider failed (timeout, network or bad response)."""


class LocationResolver(Protocol):
    def resolve(self, query: str) -> Place | None: ...
