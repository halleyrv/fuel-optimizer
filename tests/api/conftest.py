import pytest

from tests.api.test_optimize_route import TRIP


@pytest.fixture
def planner(monkeypatch):
    calls = []

    def fake(start, finish, initial_fuel):
        calls.append((start, finish, initial_fuel))
        if isinstance(fake.result, Exception):
            raise fake.result
        return fake.result

    fake.result = TRIP
    monkeypatch.setattr("fuel_route.api.views.plan_trip_with_providers", fake)
    fake.calls = calls
    return fake
