import hashlib
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache as django_cache

from fuel_route.application.plan_trip import LocationResolver
from fuel_route.domain.geocoding import Place, PlaceIndex, parse_city_state
from fuel_route.infrastructure.gazetteer import load_gazetteer
from fuel_route.infrastructure.http import get_json

_NOT_FOUND = "not-found"


class CityStateResolver:
    """Resolves "City, ST" offline from the Gazetteer; anything else goes to the fallback."""

    def __init__(self, indexes: Sequence[PlaceIndex], fallback: LocationResolver) -> None:
        self._indexes = indexes
        self._fallback = fallback

    def resolve(self, query: str) -> Place | None:
        parsed = parse_city_state(query)
        if parsed:
            for index in self._indexes:
                if place := index.locate(*parsed):
                    return place
        return self._fallback.resolve(query)


class NominatimResolver:
    """OpenStreetMap Nominatim search restricted to the US; results are cached (usage policy)."""

    def resolve(self, query: str) -> Place | None:
        key = "nominatim:" + hashlib.sha256(query.strip().lower().encode()).hexdigest()
        cached = django_cache.get(key)
        if cached is None:
            params = urlencode({"q": query, "format": "jsonv2", "countrycodes": "us", "limit": 1})
            results = get_json("nominatim", f"{settings.NOMINATIM_URL}/search?{params}")
            cached = (float(results[0]["lat"]), float(results[0]["lon"])) if results else _NOT_FOUND
            django_cache.set(key, cached, timeout=None)
        return None if cached == _NOT_FOUND else Place(cached[0], cached[1], 0.0)


@cache
def gazetteer_indexes() -> tuple[PlaceIndex, PlaceIndex]:
    """Loaded once per process (~1 s); places first, then county subdivisions."""
    data: Path = settings.STATION_DATA_DIR
    return (
        load_gazetteer(data / "2024_Gaz_place_national.zip"),
        load_gazetteer(data / "2024_Gaz_cousubs_national.zip"),
    )
