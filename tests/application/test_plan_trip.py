from decimal import Decimal

import pytest

from fuel_route.application.plan_trip import CorridorStation, LocationNotFound, Route, plan_trip
from fuel_route.domain.geocoding import Place
from fuel_route.domain.optimizer import InfeasibleRoute

D = Decimal
START, FINISH = Place(40.0, -100.0, 0.0), Place(40.0, -90.0, 0.0)
ROUTE = Route(D(300), D(300), [[-100.0, 40.0], [-90.0, 40.0]])
STATION = CorridorStation(7, "STOP", "I-80", "Town", "NE", -99.9, 40.0, D("3.5"), D(5))


class Resolver:
    def __init__(self, places):
        self.places = places

    def resolve(self, query):
        return self.places.get(query)


class Router:
    def __init__(self):
        self.calls = []

    def route(self, start, finish):
        self.calls.append((start, finish))
        return ROUTE


class Finder:
    def __init__(self, stations):
        self.stations = stations

    def along(self, route):
        assert route == ROUTE
        return self.stations


def plan(start="A, NE", finish="B, NE", stations=(STATION,), initial_fuel=D(0)):
    router = Router()
    resolver = Resolver({"A, NE": START, "B, NE": FINISH})
    return plan_trip(start, finish, initial_fuel, resolver, router, Finder(list(stations))), router


def test_plans_fuel_stops_on_the_routed_trip_with_one_routing_call():
    trip, router = plan()

    assert router.calls == [(START, FINISH)]
    assert trip.route == ROUTE
    assert [(station.station_id, stop.gallons, stop.cost) for stop, station in trip.stops] == [(7, D(30), D("105.00"))]
    assert trip.plan.total_cost == D("105.00")


def test_initial_fuel_is_passed_to_the_optimizer():
    trip, _ = plan(stations=(), initial_fuel=D(30))

    assert trip.stops == []
    assert trip.plan.remaining_fuel == D(0)


@pytest.mark.parametrize(("start", "finish", "missing"), [("Nowhere", "B, NE", "start"), ("A, NE", "Nowhere", "finish")])
def test_unknown_location_names_the_field(start, finish, missing):
    with pytest.raises(LocationNotFound) as error:
        plan(start, finish)

    assert (error.value.field, error.value.query) == (missing, "Nowhere")


def test_unreachable_destination_is_not_reported_as_success():
    with pytest.raises(InfeasibleRoute):
        plan(stations=())
