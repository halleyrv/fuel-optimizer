"""Greedy refueling plan along a single route (see docs/domain-rules.md, section 4).

At each station: buy just enough to reach the next cheaper station in range;
if none is in range, fill the tank and continue to the cheapest station in range.
The destination counts as the cheapest point, so the last purchase is exact.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from itertools import takewhile

CENT = Decimal("0.01")
ORIGIN_WINDOW_MILES = Decimal(15)  # stations this close to the start allow departing on an empty tank
ZERO = Decimal(0)


@dataclass(frozen=True)
class Vehicle:
    tank_gallons: Decimal = Decimal(50)
    mpg: Decimal = Decimal(10)


@dataclass(frozen=True)
class StationOnRoute:
    station_id: int
    mile: Decimal  # distance from the origin along the route
    price: Decimal  # USD per gallon


@dataclass(frozen=True)
class FuelStop:
    station_id: int
    mile: Decimal
    price: Decimal
    gallons: Decimal
    cost: Decimal


@dataclass(frozen=True)
class FuelPlan:
    stops: list[FuelStop]
    initial_fuel: Decimal
    remaining_fuel: Decimal

    @property
    def total_gallons(self) -> Decimal:
        return sum((stop.gallons for stop in self.stops), ZERO)

    @property
    def total_cost(self) -> Decimal:
        return sum((stop.cost for stop in self.stops), ZERO).quantize(CENT)


class InfeasibleReason(StrEnum):
    NO_STATION_NEAR_ORIGIN = "no_station_near_origin"
    GAP_EXCEEDS_RANGE = "gap_exceeds_range"


class InfeasibleRoute(Exception):
    def __init__(self, reason: InfeasibleReason, at_mile: Decimal) -> None:
        super().__init__(f"{reason} at mile {at_mile}")
        self.reason = reason
        self.at_mile = at_mile


@dataclass(frozen=True)
class _Point:
    mile: Decimal
    price: Decimal
    station: StationOnRoute | None = None  # None: the destination


def plan_fuel(
    route_miles: Decimal,
    stations: Sequence[StationOnRoute],
    vehicle: Vehicle,
    initial_fuel: Decimal = ZERO,
    origin_window_miles: Decimal = ORIGIN_WINDOW_MILES,
) -> FuelPlan:
    if not ZERO <= initial_fuel <= vehicle.tank_gallons:
        raise ValueError("initial_fuel must be between 0 and the tank capacity")

    destination = _Point(route_miles, ZERO)
    on_route = sorted(
        (_Point(s.mile, s.price, s) for s in stations if ZERO <= s.mile <= route_miles),
        key=lambda p: (p.mile, p.price),
    )
    points = [*on_route, destination]

    # Departure: nothing can be bought at the origin. An origin-window station is reachable
    # even on an empty tank; the fuel for those first miles is bought (and paid) there.
    first = points[0]
    departure_fill = first.station is not None and first.mile <= origin_window_miles
    if first.mile > initial_fuel * vehicle.mpg and not departure_fill:
        reason = InfeasibleReason.NO_STATION_NEAR_ORIGIN if initial_fuel == 0 else InfeasibleReason.GAP_EXCEEDS_RANGE
        raise InfeasibleRoute(reason, ZERO)

    fuel, i, stops = initial_fuel - first.mile / vehicle.mpg, 0, []
    while points[i] is not destination:
        here = points[i]
        j, target = _next_stop(points, i, vehicle)
        if target > fuel:  # fuel < 0 only after a departure-window arrival
            stops.append(_buy(here, target - fuel))
            fuel = target
        fuel -= (points[j].mile - here.mile) / vehicle.mpg
        i = j

    return FuelPlan(stops, initial_fuel, fuel)


def _next_stop(points: list[_Point], i: int, vehicle: Vehicle) -> tuple[int, Decimal]:
    """From station i: the next point to drive to and the fuel needed when leaving.

    The next cheaper point in range wins (buy just enough to reach it); otherwise
    fill the tank and go to the cheapest point in range.
    """
    here = points[i]
    full_range = vehicle.tank_gallons * vehicle.mpg
    in_range = list(takewhile(lambda k: points[k].mile - here.mile <= full_range, range(i + 1, len(points))))
    if not in_range:
        raise InfeasibleRoute(InfeasibleReason.GAP_EXCEEDS_RANGE, here.station.mile)
    cheaper = next((k for k in in_range if points[k].price < here.price), None)
    if cheaper is not None:
        return cheaper, (points[cheaper].mile - here.mile) / vehicle.mpg
    return min(in_range, key=lambda k: points[k].price), vehicle.tank_gallons


def _buy(here: _Point, gallons: Decimal) -> FuelStop:
    station = here.station
    return FuelStop(station.station_id, station.mile, here.price, gallons, (gallons * here.price).quantize(CENT))
