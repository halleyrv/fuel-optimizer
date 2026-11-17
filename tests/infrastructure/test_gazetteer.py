import math
import zipfile

import pytest

from fuel_route.domain.geocoding import Place
from fuel_route.infrastructure.gazetteer import clean_place_name, load_gazetteer

HEADER = "USPS\tGEOID\tANSICODE\tNAME\tLSAD\tFUNCSTAT\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG                 \n"


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Abanda CDP", "Abanda"),
        ("Indianapolis city (balance)", "Indianapolis"),
        ("Nashville-Davidson metropolitan government (balance)", "Nashville-Davidson"),
        ("Boise City city", "Boise City"),
        ("Carson City", "Carson City"),
        ("Georgetown town", "Georgetown"),
        ("Bensalem township", "Bensalem"),
        ("Autaugaville CCD", "Autaugaville"),
    ],
)
def test_clean_place_name_strips_census_type_suffix(raw, clean):
    assert clean_place_name(raw) == clean


def test_load_gazetteer_builds_index_with_aliases(tmp_path):
    path = tmp_path / "gaz.zip"
    lines = [
        "IN\t1\t1\tIndianapolis city (balance)\t57\tA\t3141592.65\t0\t0\t0\t39.776\t-86.146\n",
        "TN\t2\t2\tNashville-Davidson metropolitan government (balance)\t57\tA\t100\t0\t0\t0\t36.1\t-86.7\n",
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("gaz.txt", HEADER + "".join(lines))

    index = load_gazetteer(path)

    place = index.locate("INDIANAPOLIS", "IN")
    assert place == Place(39.776, -86.146, pytest.approx(math.sqrt(3141592.65 / math.pi)))
    assert index.locate("NASHVILLE", "TN") is not None
