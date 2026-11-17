from fuel_route.domain.geocoding import Place, PlaceIndex, is_us_state, normalize_city, parse_city_state

PLACE = Place(latitude=38.6, longitude=-90.2, radius_m=1000.0)


def test_normalize_city_unifies_case_spacing_and_abbreviations():
    assert normalize_city("  St. Louis  ") == "SAINT LOUIS"
    assert normalize_city("FT WORTH") == "FORT WORTH"
    assert normalize_city("Mt. Vernon") == "MOUNT VERNON"
    assert normalize_city("Coeur d'Alene") == "COEUR DALENE"
    assert normalize_city("Winston-Salem") == "WINSTON SALEM"
    assert normalize_city("Ste. Genevieve") == "SAINTE GENEVIEVE"


def test_index_finds_place_by_normalized_city_and_state():
    index = PlaceIndex()
    index.add("St. Louis", "MO", PLACE)

    assert index.locate("SAINT LOUIS", "MO") == PLACE
    assert index.locate("SAINT LOUIS", "IL") is None


def test_alias_never_overrides_a_real_place_name():
    index = PlaceIndex()
    other = Place(1.0, 2.0, 3.0)
    index.add("Boise", "ID", PLACE)
    index.add("Boise", "ID", other, alias=True)

    assert index.locate("Boise", "ID") == PLACE


def test_larger_place_wins_when_two_places_share_a_name():
    index = PlaceIndex()
    big = Place(1.0, 2.0, 5000.0)
    index.add("Springfield", "IL", PLACE)
    index.add("Springfield", "IL", big)

    assert index.locate("Springfield", "IL") == big


def test_only_us_states_and_dc_are_accepted():
    assert is_us_state("TX") and is_us_state("DC")
    assert not is_us_state("ON") and not is_us_state("QC")


def test_lookup_ignores_spacing_differences_between_sources():
    index = PlaceIndex()
    index.add("McCalla", "AL", PLACE)
    index.add("DeForest", "WI", PLACE)

    assert index.locate("Mc Calla", "AL") == PLACE
    assert index.locate("De Forest", "WI") == PLACE


def test_alias_never_replaces_a_real_place_even_if_larger():
    index = PlaceIndex()
    larger_alias = Place(1.0, 2.0, 9999.0)
    index.add("Boise", "ID", PLACE)
    index.add("Boise", "ID", larger_alias, alias=True)

    assert index.locate("Boise", "ID") == PLACE


def test_real_place_replaces_an_earlier_alias():
    index = PlaceIndex()
    alias_place = Place(1.0, 2.0, 9999.0)
    index.add("Boise", "ID", alias_place, alias=True)
    index.add("Boise", "ID", PLACE)

    assert index.locate("Boise", "ID") == PLACE


def test_first_place_wins_when_two_places_tie_on_size():
    index = PlaceIndex()
    twin = Place(1.0, 2.0, PLACE.radius_m)
    index.add("Springfield", "IL", PLACE)
    index.add("Springfield", "IL", twin)

    assert index.locate("Springfield", "IL") == PLACE


def test_parse_city_state_accepts_city_comma_state():
    assert parse_city_state("New York, NY") == ("New York", "NY")
    assert parse_city_state("  winston-salem ,nc ") == ("winston-salem", "NC")


def test_parse_city_state_rejects_other_formats():
    assert parse_city_state("New York") is None
    assert parse_city_state("Toronto, ON") is None
    assert parse_city_state("1600 Pennsylvania Ave, Washington, DC 20500") is None
    assert parse_city_state("Paris, Lamar County, TX") is None
    assert parse_city_state(" , TX") is None
