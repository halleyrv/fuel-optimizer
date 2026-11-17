from decimal import Decimal

import pytest

from fuel_route.domain.optimizer import (
    InfeasibleRoute,
    InfeasibleReason,
    StationOnRoute,
    Vehicle,
    plan_fuel,
)

D = Decimal
TRUCK = Vehicle(tank_gallons=D(50), mpg=D(10))


def station(station_id: int, mile: str, price: str) -> StationOnRoute:
    return StationOnRoute(station_id, D(mile), D(price))


def purchases(plan) -> list[tuple[int, Decimal, Decimal]]:
    return [(stop.station_id, stop.gallons, stop.cost) for stop in plan.stops]


def assert_fuel_balances(plan, route_miles: str) -> None:
    consumed = D(route_miles) / TRUCK.mpg
    assert plan.initial_fuel + plan.total_gallons - plan.remaining_fuel == consumed


def test_destination_within_initial_fuel_needs_no_stops_and_costs_nothing():
    plan = plan_fuel(D(200), [station(1, "50", "3.0")], TRUCK, initial_fuel=D(30))

    assert plan.stops == []
    assert plan.total_cost == D("0.00")
    assert plan.remaining_fuel == D(10)
    assert_fuel_balances(plan, "200")


def test_empty_tank_buys_only_the_fuel_the_trip_needs_at_the_origin():
    plan = plan_fuel(D(120), [station(1, "4", "3.5")], TRUCK)

    assert purchases(plan) == [(1, D(12), D("42.00"))]
    assert plan.remaining_fuel == 0
    assert_fuel_balances(plan, "120")


def test_buys_only_enough_to_reach_the_next_cheaper_station():
    stations = [station(1, "0", "4.0"), station(2, "100", "3.0"), station(3, "400", "2.0")]

    plan = plan_fuel(D(450), stations, TRUCK)

    assert purchases(plan) == [(1, D(10), D("40.00")), (2, D(30), D("90.00")), (3, D(5), D("10.00"))]
    assert plan.total_cost == D("140.00")
    assert_fuel_balances(plan, "450")


def test_fills_the_tank_when_no_cheaper_station_is_in_range():
    stations = [station(1, "0", "3.0"), station(2, "300", "4.0"), station(3, "450", "5.0")]

    plan = plan_fuel(D(900), stations, TRUCK)

    assert purchases(plan) == [(1, D(50), D("150.00")), (2, D(30), D("120.00")), (3, D(10), D("50.00"))]
    assert plan.total_gallons == D(90)
    assert_fuel_balances(plan, "900")


def test_never_buys_more_than_the_tank_holds():
    stations = [station(1, "0", "2.0"), station(2, "490", "9.0"), station(3, "980", "9.0")]

    plan = plan_fuel(D(1400), stations, TRUCK, initial_fuel=D(20))

    assert all(stop.gallons <= TRUCK.tank_gallons for stop in plan.stops)
    assert plan.stops[0].gallons == D(30)
    assert_fuel_balances(plan, "1400")


def test_initial_fuel_is_not_charged():
    plan = plan_fuel(D(300), [station(1, "100", "3.0")], TRUCK, initial_fuel=D(10))

    assert purchases(plan) == [(1, D(20), D("60.00"))]


def test_gap_longer_than_the_range_is_infeasible():
    stations = [station(1, "0", "3.0"), station(2, "600", "3.0")]

    with pytest.raises(InfeasibleRoute) as error:
        plan_fuel(D(800), stations, TRUCK)

    assert error.value.reason == InfeasibleReason.GAP_EXCEEDS_RANGE
    assert error.value.at_mile == D(0)


def test_empty_tank_without_a_station_near_the_origin_is_infeasible():
    with pytest.raises(InfeasibleRoute) as error:
        plan_fuel(D(300), [station(1, "40", "3.0")], TRUCK)

    assert error.value.reason == InfeasibleReason.NO_STATION_NEAR_ORIGIN


def test_station_inside_the_origin_window_counts_as_departure_fuel():
    plan = plan_fuel(D(300), [station(1, "15", "3.0")], TRUCK, origin_window_miles=D(15))

    assert purchases(plan) == [(1, D(30), D("90.00"))]


@pytest.mark.parametrize("initial", ["-1", "50.1"])
def test_initial_fuel_must_fit_in_the_tank(initial):
    with pytest.raises(ValueError, match="initial_fuel"):
        plan_fuel(D(100), [], TRUCK, initial_fuel=D(initial))


def brute_force_cost(route_miles: int, stations: list[StationOnRoute], tank: int, mpg: int) -> Decimal | None:
    """Exact minimum cost by dynamic programming over whole gallons (all gaps are multiples of mpg)."""
    points = sorted(stations, key=lambda s: s.mile)
    best = {0: D(0)}  # fuel on arrival at the current point -> min cost
    previous_mile = D(0)
    for point in [*points, None]:
        mile = D(route_miles) if point is None else point.mile
        burn = int((mile - previous_mile) / mpg)
        best = {fuel - burn: cost for fuel, cost in best.items() if fuel >= burn}
        if point is None:
            return min(best.values()) if best else None
        filled: dict[int, Decimal] = {}
        for fuel, cost in best.items():
            for bought in range(tank - fuel + 1):
                total = cost + bought * point.price
                if total < filled.get(fuel + bought, total + 1):
                    filled[fuel + bought] = total
        best, previous_mile = filled, mile


def test_greedy_matches_the_exact_optimum_on_random_routes():
    import random

    rng = random.Random(7)
    for _ in range(200):
        route = rng.randrange(100, 1500, 10)
        stations = [station(0, "0", f"{rng.uniform(2, 5):.2f}")] + [
            station(n, str(rng.randrange(10, route, 10)), f"{rng.uniform(2, 5):.2f}") for n in range(1, rng.randint(1, 12))
        ]
        expected = brute_force_cost(route, stations, 50, 10)
        if expected is None:
            with pytest.raises(InfeasibleRoute):
                plan_fuel(D(route), stations, TRUCK, origin_window_miles=D(0))
        else:
            plan = plan_fuel(D(route), stations, TRUCK, origin_window_miles=D(0))
            assert plan.total_cost == expected.quantize(D("0.01")), (route, stations)


def test_origin_window_station_keeps_its_real_position_for_range_checks():
    stations = [station(1, "10", "3.0"), station(2, "505", "3.0")]

    plan = plan_fuel(D(600), stations, TRUCK, origin_window_miles=D(15))

    # 1 gallon pays for the 10 miles driven before the departure station, then the tank is filled.
    assert purchases(plan) == [(1, D(51), D("153.00")), (2, D(9), D("27.00"))]
    assert_fuel_balances(plan, "600")
