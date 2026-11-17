from decimal import Decimal

from fuel_route.application.import_stations import geocode_stations
from fuel_route.domain.geocoding import Place
from fuel_route.domain.stations import StationRow

KNOWN = Place(35.0, -97.0, 1000.0)


class FakeGeocoder:
    def __init__(self, known: dict[tuple[str, str], Place]):
        self.known = known

    def locate(self, city: str, state: str) -> Place | None:
        return self.known.get((city, state))


def row(opis_id: int, city: str, state: str, price: str = "3.0") -> StationRow:
    return StationRow(opis_id, "STOP", "I-1, EXIT 1", city, state, 1, Decimal(price))


def test_geocodes_us_stations_and_reports_every_exclusion():
    rows = [
        row(1, "Big Cabin", "OK"),
        row(1, "Big Cabin", "OK", "4.0"),
        row(2, "Toronto", "ON"),
        row(3, "Nowhere", "TX"),
    ]

    result = geocode_stations(rows, [FakeGeocoder({("Big Cabin", "OK"): KNOWN})])

    assert [(s.station.opis_id, s.place, s.station.price) for s in result.located] == [(1, KNOWN, Decimal("3.5000"))]
    assert result.excluded == {"outside_usa": 1, "unresolved_city": 1}
    assert result.unresolved_cities == {("Nowhere", "TX")}


def test_falls_back_to_the_next_geocoder_when_the_first_misses():
    fallback = FakeGeocoder({("Nowhere", "TX"): KNOWN})

    result = geocode_stations([row(3, "Nowhere", "TX")], [FakeGeocoder({}), fallback])

    assert [s.place for s in result.located] == [KNOWN]
    assert result.excluded == {}
