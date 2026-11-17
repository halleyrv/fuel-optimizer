from decimal import Decimal

import pytest

from fuel_route.application.plan_trip import (
    CorridorStation,
    ExternalServiceError,
    LocationNotFound,
    Route,
    RouteNotFound,
    TripPlan,
)
from fuel_route.domain.optimizer import FuelPlan, FuelStop, InfeasibleReason, InfeasibleRoute

D = Decimal
URL = "/api/v1/routes/optimize/"
ROUTE = Route(D("300.04"), D("290.06"), [[-100.123456, 40.0], [-99.5, 40.0001], [-90.0, 40.0]])
STATION = CorridorStation(7, "STOP", "I-80, EXIT 1", "Town", "NE", -99.9, 40.0, D("3.4567"), D("5.04"))
STOP = FuelStop(7, D("5.04"), D("3.4567"), D("30.004"), D("103.71"))
TRIP = TripPlan(ROUTE, FuelPlan([STOP], D(0), D(0)), [(STOP, STATION)])


def post(client, **body):
    return client.post(URL, {"start": "A, NE", "finish": "B, NE", **body}, content_type="application/json")


def test_returns_route_stops_summary_and_map_link(client, planner):
    response = post(client, initial_fuel_gallons=0)

    assert response.status_code == 200
    body = response.json()
    assert planner.calls == [("A, NE", "B, NE", D(0))]
    assert body["route"]["distance_miles"] == 300.0
    assert body["route"]["duration_minutes"] == 290.1
    assert body["route"]["geometry"]["type"] == "LineString"
    assert body["route"]["geometry"]["coordinates"][0] == [-100.12346, 40.0]
    assert body["fuel_stops"] == [
        {
            "station_id": 7,
            "name": "STOP",
            "address": "I-80, EXIT 1",
            "city": "Town",
            "state": "NE",
            "location": {"type": "Point", "coordinates": [-99.9, 40.0]},
            "location_precision": "city",
            "mile": 5.0,
            "price_per_gallon": 3.457,
            "gallons": 30.0,
            "cost": 103.71,
        }
    ]
    assert body["summary"] == {
        "distance_miles": 300.0,
        "total_gallons_consumed": 30.0,
        "initial_fuel_gallons": 0.0,
        "total_gallons_purchased": 30.0,
        "remaining_fuel_gallons": 0.0,
        "total_fuel_cost": 103.71,
        "number_of_stops": 1,
    }
    assert body["map_url"] == "http://testserver/api/v1/routes/map/?start=A%2C+NE&finish=B%2C+NE&initial_fuel_gallons=0"


def test_initial_fuel_defaults_to_zero(client, planner):
    post(client)

    assert planner.calls[0][2] == D(0)


@pytest.mark.parametrize(
    ("body", "field"),
    [({"start": ""}, "start"), ({"finish": None}, "finish"), ({"initial_fuel_gallons": 50.5}, "initial_fuel_gallons"), ({"initial_fuel_gallons": -1}, "initial_fuel_gallons")],
)
def test_invalid_input_is_rejected_with_field_errors(client, planner, body, field):
    response = post(client, **body)

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"
    assert field in response.json()["fields"]
    assert planner.calls == []


@pytest.mark.parametrize(
    ("error", "status", "expected"),
    [
        (LocationNotFound("finish", "Atlantis"), 404, {"error": "location_not_found", "field": "finish"}),
        (RouteNotFound("Impossible route"), 422, {"error": "route_not_found"}),
        (InfeasibleRoute(InfeasibleReason.GAP_EXCEEDS_RANGE, D("120.04")), 422, {"error": "gap_exceeds_range", "at_mile": 120.0}),
        (InfeasibleRoute(InfeasibleReason.NO_STATION_NEAR_ORIGIN, D(0)), 422, {"error": "no_station_near_origin", "at_mile": 0.0}),
        (ExternalServiceError("osrm request failed: timed out"), 502, {"error": "external_service_error"}),
    ],
)
def test_failures_map_to_stable_error_codes(client, planner, error, status, expected):
    planner.result = error

    response = post(client)

    assert response.status_code == status
    body = response.json()
    assert {key: body[key] for key in expected} == expected
    assert body["detail"]


def test_map_page_renders_the_route_and_stops(client, planner):
    response = client.get("/api/v1/routes/map/", {"start": "A, NE", "finish": "B, NE"})

    assert response.status_code == 200
    html = response.content.decode()
    assert "leaflet" in html and "STOP" in html and "103.71" in html
    assert planner.calls == [("A, NE", "B, NE", D(0))]


def test_map_page_shows_errors_with_their_status(client, planner):
    planner.result = LocationNotFound("start", "Atlantis")

    response = client.get("/api/v1/routes/map/", {"start": "Atlantis", "finish": "B, NE"})

    assert response.status_code == 404
    assert "Atlantis" in response.content.decode()


def test_malformed_json_uses_the_same_error_shape(client, planner):
    response = client.post(URL, "{not json", content_type="application/json")

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"
    assert "JSON" in response.json()["detail"]
