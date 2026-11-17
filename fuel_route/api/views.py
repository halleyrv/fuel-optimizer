from typing import Any
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from fuel_route.api.presenters import TRIP_ERRORS, error_to_dict, trip_to_dict
from fuel_route.api.serializers import TripRequestSerializer
from fuel_route.infrastructure.providers import plan_trip_with_providers


def _plan(request: HttpRequest, data: Any) -> tuple[int, dict[str, Any]]:
    serializer = TripRequestSerializer(data=data)
    if not serializer.is_valid():
        return 400, {"error": "invalid_request", "detail": "Invalid request.", "fields": serializer.errors}
    values = serializer.validated_data
    try:
        trip = plan_trip_with_providers(values["start"], values["finish"], values["initial_fuel_gallons"])
    except TRIP_ERRORS as error:
        return error_to_dict(error)
    initial = f"{values['initial_fuel_gallons'].normalize():f}"
    query = urlencode({"start": values["start"], "finish": values["finish"], "initial_fuel_gallons": initial})
    return 200, trip_to_dict(trip, request.build_absolute_uri(f"{reverse('route-map')}?{query}"))


class OptimizeRouteView(APIView):
    def post(self, request: Request) -> Response:
        status, body = _plan(request, request.data)
        return Response(body, status=status)


def route_map(request: HttpRequest) -> HttpResponse:
    status, body = _plan(request, request.GET)
    context = {"trip": body if status == 200 else None, "error": body}
    return render(request, "fuel_route/map.html", context, status=status)
