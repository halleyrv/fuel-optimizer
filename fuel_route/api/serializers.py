from decimal import Decimal

from rest_framework import serializers


class TripRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200)
    finish = serializers.CharField(max_length=200)
    initial_fuel_gallons = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal(0), max_value=Decimal(50), default=Decimal(0)
    )
