"""Turns use-case results and failures into the JSON shapes of docs/api-contract.md."""

import json
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.contrib.gis.geos import GEOSGeometry
from rest_framework.views import exception_handler

from fuel_route.application.plan_trip import ExternalServiceError, LocationNotFound, RouteNotFound, TripPlan
from fuel_route.domain.optimizer import ORIGIN_WINDOW_MILES, InfeasibleReason, InfeasibleRoute, Vehicle

TRIP_ERRORS = (LocationNotFound, RouteNotFound, InfeasibleRoute, ExternalServiceError)
SIMPLIFY_TOLERANCE_DEGREES = 0.0005  # about 50 m; keeps a cross-country route in a few thousand points


def number(value: Decimal, places: int) -> float:
    return float(Decimal(value).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP))


def trip_to_dict(trip: TripPlan, map_url: str) -> dict[str, Any]:
    plan, route = trip.plan, trip.route
    consumed = plan.initial_fuel + plan.total_gallons - plan.remaining_fuel
    # Parsing GeoJSON builds the line in one GEOS call; LineString(coords) costs one call per point.
    geojson = json.dumps({"type": "LineString", "coordinates": route.coordinates})
    line = GEOSGeometry(geojson, srid=4326).simplify(SIMPLIFY_TOLERANCE_DEGREES, preserve_topology=True)
    return {
        "route": {
            "distance_miles": number(route.distance_miles, 1),
            "duration_minutes": number(route.duration_minutes, 1),
            "geometry": {"type": "LineString", "coordinates": [[round(x, 5), round(y, 5)] for x, y in line.coords]},
        },
        "fuel_stops": [
            {
                "station_id": station.station_id,
                "name": station.name,
                "address": station.address,
                "city": station.city,
                "state": station.state,
                "location": {"type": "Point", "coordinates": [station.longitude, station.latitude]},
                "location_precision": "city",
                "mile": number(stop.mile, 1),
                "price_per_gallon": number(stop.price, 3),
                "gallons": number(stop.gallons, 2),
                "cost": number(stop.cost, 2),
            }
            for stop, station in trip.stops
        ],
        "summary": {
            "distance_miles": number(route.distance_miles, 1),
            "total_gallons_consumed": number(consumed, 2),
            "initial_fuel_gallons": number(plan.initial_fuel, 2),
            "total_gallons_purchased": number(plan.total_gallons, 2),
            "remaining_fuel_gallons": number(plan.remaining_fuel, 2),
            "total_fuel_cost": number(plan.total_cost, 2),
            "number_of_stops": len(trip.stops),
        },
        "map_url": map_url,
    }


def _infeasible_detail(error: InfeasibleRoute) -> str:
    """Say why the trip cannot be done and what the client can change."""
    if error.reason == InfeasibleReason.NO_STATION_NEAR_ORIGIN:
        return (
            f"No fuel station in the supplied price list within {ORIGIN_WINDOW_MILES} miles of the start, "
            "so the trip cannot begin on an empty tank. Set initial_fuel_gallons to depart with fuel."
        )
    vehicle_range = Vehicle().tank_gallons * Vehicle().mpg
    return (
        f"A stretch of the route longer than {vehicle_range} miles has no fuel station "
        f"(from mile {number(error.at_mile, 1):,.1f}), so the destination cannot be reached."
    )


def error_to_dict(error: Exception) -> tuple[int, dict[str, Any]]:
    match error:
        case LocationNotFound():
            return 404, {"error": "location_not_found", "detail": str(error), "field": error.field}
        case RouteNotFound():
            return 422, {"error": "route_not_found", "detail": f"No drivable route: {error}"}
        case InfeasibleRoute():
            return 422, {"error": str(error.reason), "detail": _infeasible_detail(error), "at_mile": number(error.at_mile, 1)}
        case _:
            return 502, {"error": "external_service_error", "detail": str(error)}


def api_exception_handler(exc: Exception, context: dict[str, Any]):
    """DRF's own errors (malformed JSON, wrong method) in the contract's error shape."""
    response = exception_handler(exc, context)
    if response is not None:
        code = "invalid_request" if response.status_code == 400 else getattr(exc, "default_code", "error")
        response.data = {"error": code, "detail": str(response.data.get("detail", response.data))}
    return response
