from decimal import Decimal
from urllib.error import URLError

import pytest

from fuel_route.application.plan_trip import ExternalServiceError, Route, RouteNotFound
from fuel_route.domain.geocoding import Place
from fuel_route.infrastructure.osrm import OsrmRouter
from tests.infrastructure.fake_http import http_error, respond

NEW_YORK = Place(40.7128, -74.006, 0.0)
PHILADELPHIA = Place(39.9526, -75.1652, 0.0)
LINE = [[-74.006, 40.7128], [-75.1652, 39.9526]]


def test_one_request_returns_distance_duration_and_geometry():
    payload = {"code": "Ok", "routes": [{"distance": 160934.4, "duration": 7200, "geometry": {"type": "LineString", "coordinates": LINE}}]}

    with respond(payload) as urlopen:
        route = OsrmRouter().route(NEW_YORK, PHILADELPHIA)

    assert route == Route(distance_miles=Decimal("100"), duration_minutes=Decimal("120"), coordinates=LINE)
    assert urlopen.call_count == 1
    url = urlopen.call_args.args[0].full_url
    assert "/route/v1/driving/-74.006,40.7128;-75.1652,39.9526?" in url
    assert "overview=full" in url and "geometries=geojson" in url


def test_no_route_between_points_is_reported():
    # Verified against router.project-osrm.org: NoRoute comes back as HTTP 400 with a JSON body.
    with respond(http_error(400, {"code": "NoRoute", "message": "Impossible route between points"})), pytest.raises(RouteNotFound):
        OsrmRouter().route(NEW_YORK, PHILADELPHIA)


@pytest.mark.parametrize("failure", [URLError("timed out"), {"unexpected": True}])
def test_network_failure_or_malformed_response_is_an_external_error(failure):
    with respond(failure), pytest.raises(ExternalServiceError, match="osrm"):
        OsrmRouter().route(NEW_YORK, PHILADELPHIA)
