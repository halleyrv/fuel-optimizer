from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from fuel_route.application.import_stations import geocode_stations
from fuel_route.infrastructure.csv_source import read_station_csv
from fuel_route.infrastructure.gazetteer import load_gazetteer
from fuel_route.infrastructure.station_repository import replace_all_stations

DATA = settings.STATION_DATA_DIR


class Command(BaseCommand):
    help = "Import the fuel price CSV, geocoding each station to its city (offline)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--csv", default=DATA / "fuel-prices-for-be-assessment.csv")
        parser.add_argument("--places", default=DATA / "2024_Gaz_place_national.zip")
        parser.add_argument("--cousubs", default=DATA / "2024_Gaz_cousubs_national.zip")

    def handle(self, *args, csv: str, places: str, cousubs: str, **options) -> None:
        # Places first: a city beats the county subdivision that shares its name.
        geocoders = [load_gazetteer(Path(places)), load_gazetteer(Path(cousubs))]
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
