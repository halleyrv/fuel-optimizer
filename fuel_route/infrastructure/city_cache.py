import json
from pathlib import Path

from fuel_route.domain.geocoding import Place, normalize_city


def _key(city: str, state: str) -> str:
    return f"{normalize_city(city)}|{state}"


class CityCache:
    """Cities resolved once online (resolve_missing_cities), stored as JSON so imports stay offline.

    A null entry records a city Nominatim could not resolve, so it is never asked again.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: dict[str, dict[str, float] | None] = json.loads(path.read_text()) if path.exists() else {}

    def locate(self, city: str, state: str) -> Place | None:
        entry = self._entries.get(_key(city, state))
        # shortcut: Nominatim gives no city area here, so these stations get the base corridor only.
        return Place(entry["lat"], entry["lon"], 0.0) if entry else None

    def contains(self, city: str, state: str) -> bool:
        return _key(city, state) in self._entries

    def add(self, city: str, state: str, place: Place | None) -> None:
        self._entries[_key(city, state)] = {"lat": place.latitude, "lon": place.longitude} if place else None

    def save(self) -> None:
        self._path.write_text(json.dumps(self._entries, indent=2, sort_keys=True) + "\n")
