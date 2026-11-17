from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from fuel_route.application.import_stations import Geocoder, geocode_stations
from fuel_route.infrastructure.city_cache import CityCache
from fuel_route.infrastructure.csv_source import read_station_csv
from fuel_route.infrastructure.gazetteer import load_gazetteer
from fuel_route.infrastructure.station_repository import replace_all_stations

DATA = settings.STATION_DATA_DIR


def add_station_data_arguments(parser) -> None:
    """Input files shared by import_stations and resolve_missing_cities."""
    parser.add_argument("--csv", default=DATA / "fuel-prices-for-be-assessment.csv")
    parser.add_argument("--places", default=DATA / "2024_Gaz_place_national.zip")
    parser.add_argument("--cousubs", default=DATA / "2024_Gaz_cousubs_national.zip")
    parser.add_argument("--city-cache", default=DATA / "geocode_cache.json")


def offline_geocoders(places: str, cousubs: str, cache: CityCache) -> list[Geocoder]:
    # Places first: a city beats the county subdivision that shares its name; the cache covers the rest.
    return [load_gazetteer(Path(places)), load_gazetteer(Path(cousubs)), cache]


class Command(BaseCommand):
    help = "Import the fuel price CSV, geocoding each station to its city (offline)."

    def add_arguments(self, parser) -> None:
        add_station_data_arguments(parser)

    def handle(self, *args, csv: str, places: str, cousubs: str, city_cache: str, **options) -> None:
        geocoders = offline_geocoders(places, cousubs, CityCache(Path(city_cache)))
        result = geocode_stations(read_station_csv(Path(csv)), geocoders)
        if not result.located:
            raise CommandError(f"No stations located ({dict(result.excluded)}); existing data left unchanged")
        count = replace_all_stations(result.located)

        self.stdout.write(self.style.SUCCESS(f"Imported {count} stations"))
        for reason, excluded in sorted(result.excluded.items()):
            self.stdout.write(f"Excluded {reason}: {excluded}")
        if result.unresolved_cities:
            cities = "; ".join(f"{city}, {state}" for city, state in sorted(result.unresolved_cities))
            self.stdout.write(f"Unresolved cities: {cities}")
