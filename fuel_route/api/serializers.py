from decimal import Decimal

from rest_framework import serializers


class TripRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200)
    finish = serializers.CharField(max_length=200)
    initial_fuel_gallons = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal(0), max_value=Decimal(50), default=Decimal(0)
    )


# Response shapes below document the API (OpenAPI). The view builds plain dicts;
# tests/api/test_docs.py checks real responses against these serializers.


class LineStringSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["LineString"])
    coordinates = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()), help_text="[longitude, latitude] pairs")


class PointSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["Point"])
    coordinates = serializers.ListField(child=serializers.FloatField(), help_text="[longitude, latitude]")


class RouteSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration_minutes = serializers.FloatField()
    geometry = LineStringSerializer(help_text="Simplified to ~50 m to keep the response small.")


class FuelStopSerializer(serializers.Serializer):
    station_id = serializers.IntegerField(help_text="OPIS Truckstop ID")
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    location = PointSerializer()
    location_precision = serializers.ChoiceField(choices=["city"], help_text="Station positions are their city's center.")
    mile = serializers.FloatField(help_text="Distance from the start along the route.")
    price_per_gallon = serializers.FloatField()
    gallons = serializers.FloatField()
    cost = serializers.FloatField()


class SummarySerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    total_gallons_consumed = serializers.FloatField()
    initial_fuel_gallons = serializers.FloatField()
    total_gallons_purchased = serializers.FloatField()
    remaining_fuel_gallons = serializers.FloatField()
    total_fuel_cost = serializers.FloatField(help_text="USD spent on purchases; initial fuel is not charged.")
    number_of_stops = serializers.IntegerField()


class TripResponseSerializer(serializers.Serializer):
    route = RouteSerializer()
    fuel_stops = FuelStopSerializer(many=True)
    summary = SummarySerializer()
    map_url = serializers.URLField(help_text="HTML page with the route and stops on a map.")


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField(help_text="Stable error code.")
    detail = serializers.CharField()
    field = serializers.CharField(required=False, help_text="location_not_found: start or finish.")
    at_mile = serializers.FloatField(required=False, help_text="Infeasible routes: where the plan fails.")
    fields = serializers.DictField(required=False, help_text="invalid_request: errors per field.")
