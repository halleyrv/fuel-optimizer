from decimal import Decimal

from django.conf import settings
from django.core.cache import cache

from fuel_route.application.plan_trip import ExternalServiceError, Route, RouteNotFound
from fuel_route.domain.geocoding import Place
from fuel_route.infrastructure.http import get_json

METERS_PER_MILE = Decimal("1609.344")
ROUTE_CACHE_SECONDS = 24 * 3600  # roads rarely change; repeated trips skip the external call
_NO_ROUTE_CODES = {"NoRoute", "NoSegment"}  # no road connection / point too far from any road


class OsrmRouter:
    """Driving route from the public OSRM server in a single request."""

    def route(self, start: Place, finish: Place) -> Route:
        points = f"{start.longitude},{start.latitude};{finish.longitude},{finish.latitude}"
        key = f"osrm:{points}"
        if (cached := cache.get(key)) is not None:
            return cached
        route = self._fetch(points)
        cache.set(key, route, timeout=ROUTE_CACHE_SECONDS)
        return route

    def _fetch(self, points: str) -> Route:
        url = f"{settings.OSRM_URL}/route/v1/driving/{points}?overview=full&geometries=geojson"
        payload = get_json("osrm", url, client_error_body=True)
        code = payload.get("code") if isinstance(payload, dict) else None
        if code in _NO_ROUTE_CODES:
            raise RouteNotFound(payload.get("message", code))
        try:
            if code != "Ok":
                raise KeyError(code)
            best = payload["routes"][0]
            return Route(
                distance_miles=Decimal(str(best["distance"])) / METERS_PER_MILE,
                duration_minutes=Decimal(str(best["duration"])) / 60,
                coordinates=best["geometry"]["coordinates"],
            )
        except (KeyError, IndexError, TypeError) as error:
            raise ExternalServiceError(f"osrm returned an unexpected response: {error!r}") from error
