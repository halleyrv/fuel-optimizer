import re
from dataclasses import dataclass

US_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO "
    "MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
)
_ABBREVIATIONS = {"ST": "SAINT", "STE": "SAINTE", "FT": "FORT", "MT": "MOUNT"}


@dataclass(frozen=True)
class Place:
    """City-level location: internal point plus the city's equivalent radius."""

    latitude: float
    longitude: float
    radius_m: float


def is_us_state(code: str) -> bool:
    return code in US_STATES


def normalize_city(name: str) -> str:
    words = re.sub(r"[.\-]", " ", name.upper().replace("'", "")).split()
    return " ".join(_ABBREVIATIONS.get(word, word) for word in words)


def _key(city: str, state: str) -> tuple[str, str]:
    # Sources disagree on spacing: "Mc Calla" vs "McCalla", "De Forest" vs "DeForest".
    return normalize_city(city).replace(" ", ""), state


class PlaceIndex:
    """In-memory lookup of places by normalized city and state."""

    def __init__(self) -> None:
        self._places: dict[tuple[str, str], tuple[bool, Place]] = {}

    def add(self, city: str, state: str, place: Place, alias: bool = False) -> None:
        key = _key(city, state)
        current = self._places.get(key)
        if current is None or (current[0] and not alias):
            self._places[key] = (alias, place)
        elif current[0] == alias and place.radius_m > current[1].radius_m:
            self._places[key] = (alias, place)

    def locate(self, city: str, state: str) -> Place | None:
        found = self._places.get(_key(city, state))
        return found[1] if found else None
