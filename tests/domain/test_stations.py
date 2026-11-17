from decimal import Decimal

from fuel_route.domain.stations import StationRow, consolidate


def row(opis_id: int, price: str, name: str = "STOP") -> StationRow:
    return StationRow(opis_id, name, "I-80, EXIT 27", "Atkinson", "NE", 1, Decimal(price))


def test_rows_with_same_id_become_one_station_priced_at_the_median():
    stations = consolidate([row(7, "3.589"), row(7, "3.389"), row(7, "3.449"), row(9, "3.0")])

    assert [s.opis_id for s in stations] == [7, 9]
    assert stations[0].price == Decimal("3.4490")
    assert stations[1].price == Decimal("3.0000")


def test_even_count_median_is_rounded_half_up_to_four_decimals():
    [station] = consolidate([row(1, "3.00005"), row(1, "3.0001")])

    assert station.price == Decimal("3.0001")


def test_consolidated_station_keeps_the_first_row_attributes():
    [station] = consolidate([row(20, "3.899", "PILOT TRAVEL CENTER #1243"), row(20, "3.899", "PILOT #1243")])

    assert station.name == "PILOT TRAVEL CENTER #1243"
