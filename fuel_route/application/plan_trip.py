from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from fuel_route.domain.geocoding import Place
from fuel_route.domain.optimizer import FuelPlan, FuelStop, StationOnRoute, Vehicle, plan_fuel


class ExternalServiceError(Exception):
    """A routing or geocoding provider failed (timeout, network or bad response)."""


class LocationResolver(Protocol):
    def resolve(self, query: str) -> Place | None: ...


class LocationNotFound(Exception):
    def __init__(self, field: str, query: str) -> None:
        super().__init__(f"{field} location not found: {query!r}")
        self.field = field
        self.query = query


class RouteNotFound(Exception):
    """The routing provider found no drivable route between the two points."""


@dataclass(frozen=True)
class Route:
    distance_miles: Decimal
    duration_minutes: Decimal
    coordinates: list[list[float]]  # GeoJSON LineString order: [longitude, latitude]


class Router(Protocol):
    def route(self, start: Place, finish: Place) -> Route: ...


@dataclass(frozen=True)
class CorridorStation:
    """A station near the route, with its position along it (city-level location)."""

    station_id: int
    name: str
    address: str
    city: str
    state: str
    longitude: float
    latitude: float
    price: Decimal
    mile: Decimal


class StationFinder(Protocol):
    def along(self, route: Route) -> list[CorridorStation]: ...


@dataclass(frozen=True)
class TripPlan:
    route: Route
    plan: FuelPlan
    stops: list[tuple[FuelStop, CorridorStation]]


def plan_trip(
    start: str,
    finish: str,
    initial_fuel: Decimal,
    resolver: LocationResolver,
    router: Router,
    finder: StationFinder,
    vehicle: Vehicle = Vehicle(),
) -> TripPlan:
    """Resolve both ends, route once, find corridor stations and plan the cheapest fuel stops.

    External calls: at most two geocoding fallbacks (only for non "City, ST" input) plus one route.
    Raises LocationNotFound, RouteNotFound, ExternalServiceError or InfeasibleRoute.
    """
    places = {}
    for field, query in (("start", start), ("finish", finish)):
        if (place := resolver.resolve(query)) is None:
            raise LocationNotFound(field, query)
        places[field] = place
    route = router.route(places["start"], places["finish"])
    stations = {s.station_id: s for s in finder.along(route)}
    plan = plan_fuel(
        route.distance_miles,
        [StationOnRoute(s.station_id, s.mile, s.price) for s in stations.values()],
        vehicle,
        initial_fuel,
    )
    return TripPlan(route, plan, [(stop, stations[stop.station_id]) for stop in plan.stops])
