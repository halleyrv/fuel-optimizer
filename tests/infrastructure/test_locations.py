from urllib.error import URLError

import pytest
from django.core.cache import cache

from fuel_route.application.plan_trip import ExternalServiceError
from fuel_route.domain.geocoding import Place, PlaceIndex
from fuel_route.infrastructure.locations import CityStateResolver, NominatimResolver
from tests.infrastructure.fake_http import respond

NEW_YORK = Place(40.71, -74.0, 1000.0)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


class FakeFallback:
    def __init__(self, place=None):
        self.place, self.queries = place, []

    def resolve(self, query):
        self.queries.append(query)
        return self.place


def test_city_state_is_resolved_offline_without_the_fallback():
    index = PlaceIndex()
    index.add("New York", "NY", NEW_YORK)
    fallback = FakeFallback()

    assert CityStateResolver([index], fallback).resolve("New York, NY") == NEW_YORK
    assert fallback.queries == []


def test_unknown_city_or_other_formats_use_the_fallback():
    fallback = FakeFallback(NEW_YORK)
    resolver = CityStateResolver([PlaceIndex()], fallback)

    assert resolver.resolve("Empire State Building") == NEW_YORK
    assert fallback.queries == ["Empire State Building"]


def test_nominatim_returns_the_first_us_match_and_caches_it():
    with respond([{"lat": "40.7484", "lon": "-73.9857"}]) as urlopen:
        resolver = NominatimResolver()
        first = resolver.resolve("Empire State Building")
        second = resolver.resolve("Empire State Building")

    assert first == second == Place(40.7484, -73.9857, 0.0)
    assert urlopen.call_count == 1
    request = urlopen.call_args.args[0]
    assert "countrycodes=us" in request.full_url
    assert request.get_header("User-agent").startswith("fuel-route-optimizer")


def test_nominatim_without_results_returns_none():
    with respond([]):
        assert NominatimResolver().resolve("Nowhere Land") is None


def test_nominatim_network_failure_is_reported_as_external_error():
    with respond(URLError("timed out")), pytest.raises(ExternalServiceError, match="nominatim"):
        NominatimResolver().resolve("Somewhere")
