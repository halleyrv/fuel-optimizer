from decimal import Decimal

import pytest

from fuel_route.domain.stations import StationRow
from fuel_route.infrastructure.csv_source import read_station_csv

HEADER = "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price\n"


def test_reads_rows_trimming_padded_fields(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(HEADER + '7,WOODSHED ,"I-44, EXIT 283 & US-69",Effingham     ,OK,307,3.00733333\n')

    assert read_station_csv(path) == [
        StationRow(7, "WOODSHED", "I-44, EXIT 283 & US-69", "Effingham", "OK", 307, Decimal("3.00733333"))
    ]


def test_rejects_a_row_with_an_invalid_price(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(HEADER + "7,STOP,I-1,Town,OK,1,abc\n")

    with pytest.raises(ValueError, match="line 2"):
        read_station_csv(path)
