from decimal import Decimal

import pytest
from django.contrib.gis.geos import Point

from fuel_route.application.plan_trip import Route
from fuel_route.infrastructure.station_repository import PostgisStationFinder
from fuel_route.models import FuelStation

# East-west line at latitude 35: 0.01 degree of latitude is about 1.11 km.
ROUTE = Route(Decimal(100), Decimal(90), [[-100.0, 35.0], [-99.0, 35.0]])


def add(opis_id: int, lon: float, lat: float, radius_m: float, price: str = "3.5") -> None:
    FuelStation.objects.create(
        opis_id=opis_id, name=f"S{opis_id}", address="I-40", city="Town", state="OK", rack_id=1,
        retail_price=Decimal(price), location=Point(lon, lat, srid=4326), location_radius_m=radius_m,
    )


@pytest.mark.django_db
def test_returns_stations_inside_their_tolerance_ordered_by_route_mile(settings):
    settings.CORRIDOR_BASE_METERS = 5000
    settings.CORRIDOR_RADIUS_CAP_METERS = 10000
    add(1, -99.5, 35.05, radius_m=1000)  # ~5.6 km off: inside 5 km + 1 km radius
    add(2, -99.9, 35.0, radius_m=0)  # on the route, near the start
    add(3, -99.5, 35.05, radius_m=0)  # ~5.6 km off: outside the 5 km base
    add(4, -99.5, 35.2, radius_m=50000)  # ~22 km off: radius capped at 10 km
    add(5, -99.5, 36.0, radius_m=0)  # far away

    stations = PostgisStationFinder().along(ROUTE)

    assert [s.station_id for s in stations] == [2, 1]
    first = stations[0]
    assert first.mile == pytest.approx(Decimal(10), abs=Decimal("0.01"))
    assert (first.longitude, first.latitude) == (-99.9, 35.0)
    assert first.price == Decimal("3.5000")
    assert (first.name, first.city, first.state) == ("S2", "Town", "OK")
