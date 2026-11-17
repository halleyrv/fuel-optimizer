from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from fuel_route.domain.geocoding import Place, is_us_state
from fuel_route.domain.stations import Station, StationRow, consolidate


class Geocoder(Protocol):
    def locate(self, city: str, state: str) -> Place | None: ...


@dataclass(frozen=True)
class LocatedStation:
    station: Station
    place: Place


@dataclass
class ImportResult:
    located: list[LocatedStation] = field(default_factory=list)
    excluded: Counter[str] = field(default_factory=Counter)
    unresolved_cities: set[tuple[str, str]] = field(default_factory=set)


def geocode_stations(rows: Iterable[StationRow], geocoders: Sequence[Geocoder]) -> ImportResult:
    """Consolidate US rows and attach a city-level location, trying geocoders in order.

    `outside_usa` counts CSV rows; `unresolved_city` counts consolidated stations.
    """
    result = ImportResult()
    us_rows = []
    for row in rows:
        if is_us_state(row.state):
            us_rows.append(row)
        else:
            result.excluded["outside_usa"] += 1

    for station in consolidate(us_rows):
        place = next(
            (p for g in geocoders if (p := g.locate(station.city, station.state)) is not None),
            None,
        )
        if place is None:
            result.excluded["unresolved_city"] += 1
            result.unresolved_cities.add((station.city, station.state))
        else:
            result.located.append(LocatedStation(station, place))
    return result
