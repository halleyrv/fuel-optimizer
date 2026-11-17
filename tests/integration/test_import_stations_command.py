import io
import zipfile
from decimal import Decimal

import pytest
from django.core.management import call_command

from fuel_route.models import FuelStation

CSV = (
    "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price\n"
    '7,WOODSHED OF BIG CABIN,"I-44, EXIT 283 & US-69",Big Cabin,OK,307,3.0\n'
    '7,WOODSHED OF BIG CABIN,"I-44, EXIT 283 & US-69",Big Cabin,OK,307,4.0\n'
    "8,TOWNSHIP STOP,I-76,Bensalem,PA,1,3.5\n"
    "9,CANADA STOP,TCH-16,Toronto,ON,1,1.5\n"
    "10,LOST STOP,I-10,Nowhere,TX,1,2.5\n"
)
HEADER = "USPS\tGEOID\tANSICODE\tNAME\tLSAD\tFUNCSTAT\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG\n"


def gazetteer(path, line):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("gaz.txt", HEADER + line)
    return path


@pytest.fixture
def files(tmp_path):
    (tmp_path / "prices.csv").write_text(CSV)
    return {
        "csv": str(tmp_path / "prices.csv"),
        "places": str(gazetteer(tmp_path / "places.zip", "OK\t1\t1\tBig Cabin town\t43\tA\t3141592.65\t0\t0\t0\t36.5378\t-95.2225\n")),
        "cousubs": str(gazetteer(tmp_path / "cousubs.zip", "PA\t2\t2\tBensalem township\t44\tA\t100\t0\t0\t0\t40.1\t-74.9\n")),
    }


@pytest.mark.django_db
def test_import_stores_located_stations_and_reports_exclusions(files):
    out = io.StringIO()

    call_command("import_stations", **files, stdout=out)

    station = FuelStation.objects.get(opis_id=7)
    assert station.retail_price == Decimal("3.5000")
    assert (station.location.x, station.location.y) == (-95.2225, 36.5378)
    assert station.location_precision == "city"
    assert station.location_radius_m == pytest.approx(1000.0)
    assert FuelStation.objects.filter(opis_id=8).exists()
    assert FuelStation.objects.count() == 2
    report = out.getvalue()
    assert "Imported 2 stations" in report
    assert "outside_usa: 1" in report and "unresolved_city: 1" in report
    assert "Nowhere, TX" in report


@pytest.mark.django_db
def test_import_is_idempotent(files):
    call_command("import_stations", **files, stdout=io.StringIO())
    call_command("import_stations", **files, stdout=io.StringIO())

    assert FuelStation.objects.count() == 2
