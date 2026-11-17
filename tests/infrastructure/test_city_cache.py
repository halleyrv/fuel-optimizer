from fuel_route.domain.geocoding import Place
from fuel_route.infrastructure.city_cache import CityCache

BREEZEWOOD = Place(39.999, -78.24, 0.0)


def test_saved_entries_are_found_again_with_normalized_names(tmp_path):
    path = tmp_path / "cache.json"
    cache = CityCache(path)
    cache.add("Breezewood", "PA", BREEZEWOOD)
    cache.add("Nowhere", "TX", None)
    cache.save()

    reloaded = CityCache(path)

    assert reloaded.locate("BREEZEWOOD", "PA") == BREEZEWOOD
    assert reloaded.locate("Breezewood", "MD") is None
    assert reloaded.locate("Nowhere", "TX") is None
    assert reloaded.contains("Nowhere", "TX")
    assert not reloaded.contains("Elsewhere", "TX")


def test_missing_file_is_an_empty_cache(tmp_path):
    assert CityCache(tmp_path / "absent.json").locate("Breezewood", "PA") is None
