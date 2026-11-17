import io
import json

import pytest
from django.core.management import call_command

from fuel_route.models import FuelStation
from tests.infrastructure.fake_http import respond
from tests.integration.test_import_stations_command import files  # noqa: F401  (shared fixture)


@pytest.mark.django_db
def test_resolves_unmatched_cities_once_and_the_import_uses_them_offline(files, tmp_path, settings):
    settings.NOMINATIM_MIN_INTERVAL_SECONDS = 0
    cache = tmp_path / "geocode_cache.json"
    assert files["city_cache"] == str(cache)
    found = [{"lat": "31.5", "lon": "-103.5", "address": {"ISO3166-2-lvl4": "US-TX"}}]
    out = io.StringIO()

    with respond(found) as urlopen:
        call_command("resolve_missing_cities", **files, stdout=out)
    with respond() as no_calls:
        call_command("resolve_missing_cities", **files, stdout=io.StringIO())
    call_command("import_stations", **files, stdout=io.StringIO())

    assert urlopen.call_count == 1
    assert no_calls.call_count == 0
    assert json.loads(cache.read_text()) == {"NOWHERE|TX": {"lat": 31.5, "lon": -103.5}}
    assert "Resolved 1 of 1" in out.getvalue()
    lost = FuelStation.objects.get(opis_id=10)
    assert (lost.location.x, lost.location.y) == (-103.5, 31.5)
    assert lost.location_radius_m == 0
