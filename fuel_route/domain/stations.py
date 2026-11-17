from collections.abc import Iterable
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

PRICE_STEP = Decimal("0.0001")


@dataclass(frozen=True)
class StationRow:
    """One line of the supplied price CSV."""

    opis_id: int
    name: str
    address: str
    city: str
    state: str
    rack_id: int
    price: Decimal


Station = StationRow  # A consolidated station has the same shape as a row.


def consolidate(rows: Iterable[StationRow]) -> list[Station]:
    """Merge rows sharing an OPIS ID into one station priced at the median.

    Rows with the same ID share address, city and state (verified on the
    supplied CSV); without timestamps no single row can be preferred.
    """
    groups: dict[int, list[StationRow]] = {}
    for row in rows:
        groups.setdefault(row.opis_id, []).append(row)
    return [_merge(group) for group in groups.values()]


def _merge(group: list[StationRow]) -> Station:
    price = Decimal(median(row.price for row in group)).quantize(PRICE_STEP, ROUND_HALF_UP)
    return replace(group[0], price=price)
