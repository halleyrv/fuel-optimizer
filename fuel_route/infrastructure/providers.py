from decimal import Decimal

from fuel_route.application.plan_trip import TripPlan, plan_trip
from fuel_route.infrastructure.locations import CityStateResolver, NominatimResolver, gazetteer_indexes
from fuel_route.infrastructure.osrm import OsrmRouter
from fuel_route.infrastructure.station_repository import PostgisStationFinder


def plan_trip_with_providers(start: str, finish: str, initial_fuel: Decimal) -> TripPlan:
    """Composition root: the use case wired to Gazetteer/Nominatim, OSRM and PostGIS."""
    resolver = CityStateResolver(gazetteer_indexes(), NominatimResolver())
    return plan_trip(start, finish, initial_fuel, resolver, OsrmRouter(), PostgisStationFinder())
