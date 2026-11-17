import yaml
from django.core.management import call_command

from fuel_route.api.serializers import ErrorSerializer, TripResponseSerializer
from tests.api.test_optimize_route import URL, post


def test_openapi_schema_is_valid_without_warnings(tmp_path):
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(tmp_path / "schema.yml"))

    schema = (tmp_path / "schema.yml").read_text()
    assert "/api/v1/routes/optimize/" in schema
    assert "location_not_found" in schema


def test_swagger_ui_is_served(client):
    assert client.get("/api/docs/").status_code == 200


def test_documented_response_matches_the_real_response(client, planner):
    # A real host: Django's default "testserver" has no domain, so URLField would reject map_url.
    body = client.post(URL, {"start": "A, NE", "finish": "B, NE"}, content_type="application/json", HTTP_HOST="localhost:8000").json()

    serializer = TripResponseSerializer(data=body)
    assert serializer.is_valid(), serializer.errors
    assert set(serializer.fields) == set(body)


def test_documented_error_matches_the_real_error(client, planner):
    body = post(client, initial_fuel_gallons=99).json()

    assert ErrorSerializer(data=body).is_valid()


def test_map_page_is_documented_as_html_with_its_query_parameters(tmp_path):
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(tmp_path / "schema.yml"))

    schema = yaml.safe_load((tmp_path / "schema.yml").read_text())
    operation = schema["paths"]["/api/v1/routes/map/"]["get"]
    assert {p["name"] for p in operation["parameters"]} == {"start", "finish", "initial_fuel_gallons"}
    assert set(operation["responses"]) == {"200", "400", "404", "422", "502"}
    assert "text/html" in operation["responses"]["200"]["content"]
