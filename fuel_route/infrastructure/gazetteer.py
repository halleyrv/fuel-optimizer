"""Loads US Census Gazetteer files (places or county subdivisions, public domain) into a PlaceIndex."""

import csv
import io
import math
import re
import zipfile
from pathlib import Path

from fuel_route.domain.geocoding import Place, PlaceIndex

# Census place types are lowercase, so "Carson City" keeps its capitalized "City".
_TYPE_SUFFIX = re.compile(
    r"\s+(city and borough|consolidated government|metropolitan government|unified government"
    r"|urban county|municipality|borough|township|village|town|city|CDP|CCD)\b.*$"
)


def clean_place_name(name: str) -> str:
    return _TYPE_SUFFIX.sub("", name).strip()


def _aliases(name: str) -> set[str]:
    # "Nashville-Davidson" -> "Nashville", "Boise City" -> "Boise".
    return {name.split("-")[0], name.removesuffix(" City")} - {name}


def load_gazetteer(path: Path) -> PlaceIndex:
    index = PlaceIndex()
    with zipfile.ZipFile(path) as archive:
        [member] = [n for n in archive.namelist() if n.endswith(".txt") and not n.startswith("__MACOSX/")]
        with archive.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1"), delimiter="\t")
            for record in reader:
                record = {key.strip(): value.strip() for key, value in record.items()}
                name = clean_place_name(record["NAME"])
                place = Place(
                    float(record["INTPTLAT"]),
                    float(record["INTPTLONG"]),
                    math.sqrt(float(record["ALAND"]) / math.pi),
                )
                index.add(name, record["USPS"], place)
                for alias in _aliases(name):
                    index.add(alias, record["USPS"], place, alias=True)
    return index
