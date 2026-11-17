from urllib.error import URLError

import pytest

from fuel_route.application.plan_trip import ExternalServiceError
from fuel_route.domain.geocoding import Place, PlaceIndex
from fuel_route.infrastructure.locations import CityStateResolver, NominatimResolver, locate_city_online
from tests.infrastructure.fake_http import http_error, respond

NEW_YORK = Place(40.71, -74.0, 1000.0)


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


def test_nominatim_http_error_is_reported_as_external_error():
    with respond(http_error(429, {"error": "rate limited"})), pytest.raises(ExternalServiceError, match="nominatim"):
        NominatimResolver().resolve("Somewhere")


@pytest.mark.parametrize("payload", [{"error": "unexpected"}, [{"display_name": "no coordinates"}], [{"lat": "north", "lon": "1"}]])
def test_nominatim_unexpected_payload_is_reported_as_external_error(payload):
    with respond(payload), pytest.raises(ExternalServiceError, match="nominatim"):
        NominatimResolver().resolve("Somewhere")


def test_online_city_lookup_accepts_a_result_in_the_requested_state():
    payload = [{"lat": "39.999", "lon": "-78.24", "address": {"ISO3166-2-lvl4": "US-PA"}}]

    with respond(payload) as urlopen:
        place = locate_city_online("Breezewood", "PA")

    assert place == Place(39.999, -78.24, 0.0)
    assert "addressdetails=1" in urlopen.call_args.args[0].full_url


@pytest.mark.parametrize("payload", [[], [{"lat": "1", "lon": "2", "address": {"ISO3166-2-lvl4": "US-MD"}}]])
def test_online_city_lookup_rejects_no_result_or_another_state(payload):
    with respond(payload):
        assert locate_city_online("Breezewood", "PA") is None
