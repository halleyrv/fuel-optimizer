from django.contrib.gis.db import models


class FuelStation(models.Model):
    """A consolidated truck stop. Its location is city-level, never the exact pump."""

    opis_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    retail_price = models.DecimalField(max_digits=7, decimal_places=4)
    location = models.PointField(geography=True, srid=4326)  # spatial index created by default
    location_precision = models.CharField(max_length=10, default="city")
    location_radius_m = models.FloatField()

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.state})"
