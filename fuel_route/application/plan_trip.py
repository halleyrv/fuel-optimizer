from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from fuel_route.domain.geocoding import Place


class ExternalServiceError(Exception):
    """A routing or geocoding provider failed (timeout, network or bad response)."""


class LocationResolver(Protocol):
    def resolve(self, query: str) -> Place | None: ...


class RouteNotFound(Exception):
    """The routing provider found no drivable route between the two points."""


@dataclass(frozen=True)
class Route:
    distance_miles: Decimal
    duration_minutes: Decimal
    coordinates: list[list[float]]  # GeoJSON LineString order: [longitude, latitude]


class Router(Protocol):
    def route(self, start: Place, finish: Place) -> Route: ...
