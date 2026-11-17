import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from fuel_route.application.import_stations import geocode_stations
from fuel_route.application.plan_trip import ExternalServiceError
from fuel_route.infrastructure.city_cache import CityCache
from fuel_route.infrastructure.csv_source import read_station_csv
from fuel_route.infrastructure.locations import locate_city_online
from fuel_route.management.commands.import_stations import add_station_data_arguments, offline_geocoders


class Command(BaseCommand):
    help = (
        "Resolve, once and online, the station cities the offline Gazetteer misses (Nominatim, "
        "1 request/s) and store them in the city cache so import_stations stays offline."
    )

    def add_arguments(self, parser) -> None:
        add_station_data_arguments(parser)

    def handle(self, *args, csv: str, places: str, cousubs: str, city_cache: str, **options) -> None:
        cache = CityCache(Path(city_cache))
        result = geocode_stations(read_station_csv(Path(csv)), offline_geocoders(places, cousubs, cache))
        pending = sorted(city for city in result.unresolved_cities if not cache.contains(*city))

        resolved = 0
        for count, (city, state) in enumerate(pending):
            if count:
                time.sleep(settings.NOMINATIM_MIN_INTERVAL_SECONDS)  # Nominatim usage policy
            try:
                place = locate_city_online(city, state)
            except ExternalServiceError as error:
                raise CommandError(f"{error}; {count} cities saved, run again to continue") from error
            cache.add(city, state, place)
            cache.save()  # after each city, so an interruption loses nothing
            resolved += place is not None

        self.stdout.write(self.style.SUCCESS(f"Resolved {resolved} of {len(pending)} cities into {city_cache}"))
