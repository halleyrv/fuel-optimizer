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
    origin_window_miles: Decimal = Decimal(15),
) -> FuelPlan:
    if not ZERO <= initial_fuel <= vehicle.tank_gallons:
        raise ValueError("initial_fuel must be between 0 and the tank capacity")

    destination = _Point(route_miles, ZERO)
    on_route = sorted(
        (
            _Point(s.mile, s.price, s)
            for s in stations
            if ZERO <= s.mile <= route_miles
        ),
        key=lambda p: (p.mile, p.price),
    )
    points = [*on_route, destination]
    full_range = vehicle.tank_gallons * vehicle.mpg

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
        in_range = list(takewhile(lambda k: points[k].mile - here.mile <= full_range, range(i + 1, len(points))))
        if not in_range:
            raise InfeasibleRoute(InfeasibleReason.GAP_EXCEEDS_RANGE, here.station.mile)
        cheaper = next((k for k in in_range if points[k].price < here.price), None)
        if cheaper is not None:
            j, target = cheaper, (points[cheaper].mile - here.mile) / vehicle.mpg
        else:
            j, target = min(in_range, key=lambda k: points[k].price), vehicle.tank_gallons
        gallons = max(ZERO, target - fuel)  # fuel < 0 only after a departure-window arrival
        if gallons > 0:
            stops.append(
                FuelStop(
                    here.station.station_id,
                    here.station.mile,
                    here.price,
                    gallons,
                    (gallons * here.price).quantize(CENT),
                )
            )
            fuel += gallons
        fuel -= (points[j].mile - here.mile) / vehicle.mpg
        i = j

    return FuelPlan(stops, initial_fuel, fuel)
