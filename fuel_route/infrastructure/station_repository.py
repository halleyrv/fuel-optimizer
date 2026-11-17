import json
from collections.abc import Iterable
from decimal import Decimal

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import connection, transaction

from fuel_route.application.import_stations import LocatedStation
from fuel_route.application.plan_trip import CorridorStation, Route
from fuel_route.models import FuelStation


@transaction.atomic
def replace_all_stations(located: Iterable[LocatedStation]) -> int:
    """Swap the station table for a fresh import in one transaction."""
    FuelStation.objects.all().delete()
    created = FuelStation.objects.bulk_create(
        FuelStation(
            opis_id=item.station.opis_id,
            name=item.station.name,
            address=item.station.address,
            city=item.station.city,
            state=item.station.state,
            rack_id=item.station.rack_id,
            retail_price=item.station.price,
            location=Point(item.place.longitude, item.place.latitude, srid=4326),
            location_precision="city",
            location_radius_m=item.place.radius_m,
        )
        for item in located
    )
    return len(created)


# The constant-distance ST_DWithin uses the GIST index; the second one applies each
# station's own tolerance (base corridor + its city radius, capped).
_CORRIDOR_SQL = """
WITH route AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(geojson)s), 4326) AS geom)
SELECT s.opis_id, s.name, s.address, s.city, s.state,
       ST_X(s.location::geometry), ST_Y(s.location::geometry), s.retail_price,
       ST_LineLocatePoint(route.geom, s.location::geometry) AS fraction
FROM fuel_route_fuelstation s, route
WHERE ST_DWithin(s.location, route.geom::geography, %(max_m)s)
  AND ST_DWithin(s.location, route.geom::geography, %(base_m)s + LEAST(s.location_radius_m, %(cap_m)s))
ORDER BY fraction
"""


class PostgisStationFinder:
    """Stations within the corridor around a route, ordered by their mile along it."""

    def along(self, route: Route) -> list[CorridorStation]:
        base, cap = settings.CORRIDOR_BASE_METERS, settings.CORRIDOR_RADIUS_CAP_METERS
        params = {
            "geojson": json.dumps({"type": "LineString", "coordinates": route.coordinates}),
            "base_m": base,
            "cap_m": cap,
            "max_m": base + cap,
        }
        with connection.cursor() as cursor:
            cursor.execute(_CORRIDOR_SQL, params)
            rows = cursor.fetchall()
        # shortcut: the line fraction is measured in degrees, so the mile is approximate
        # (good enough for city-level station locations).
        return [
            CorridorStation(opis_id, name, address, city, state, lon, lat, price, Decimal(str(fraction)) * route.distance_miles)
            for opis_id, name, address, city, state, lon, lat, price, fraction in rows
        ]
