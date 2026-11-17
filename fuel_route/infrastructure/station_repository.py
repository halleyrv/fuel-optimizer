from collections.abc import Iterable

from django.contrib.gis.geos import Point
from django.db import transaction

from fuel_route.application.import_stations import LocatedStation
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
