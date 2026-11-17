from typing import Any
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from fuel_route.api.presenters import TRIP_ERRORS, error_to_dict, trip_to_dict
from fuel_route.api.serializers import ErrorSerializer, TripRequestSerializer, TripResponseSerializer
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
    @extend_schema(
        summary="Plan the cheapest fuel stops for a US trip",
        description=(
            "Routes between two US locations (one OSRM call) and returns the cost-optimal fuel stops "
            "for a vehicle with a 500-mile range at 10 MPG, plus the total fuel cost and a map link. "
            "`City, ST` resolves offline; other text uses Nominatim. See docs/domain-rules.md for assumptions."
        ),
        request=TripRequestSerializer,
        responses={
            200: TripResponseSerializer,
            400: OpenApiResponse(ErrorSerializer, description="`invalid_request`: missing field, wrong type or initial fuel outside 0-50."),
            404: OpenApiResponse(ErrorSerializer, description="`location_not_found`: start or finish cannot be resolved."),
            422: OpenApiResponse(
                ErrorSerializer,
                description="`route_not_found`, `no_station_near_origin` or `gap_exceeds_range`: the trip cannot be completed.",
            ),
            502: OpenApiResponse(ErrorSerializer, description="`external_service_error`: OSRM or Nominatim failed or timed out."),
        },
        examples=[
            OpenApiExample("Coast to coast", value={"start": "New York, NY", "finish": "Los Angeles, CA"}, request_only=True),
            OpenApiExample("Departing with fuel", value={"start": "Chicago, IL", "finish": "Denver, CO", "initial_fuel_gallons": 25}, request_only=True),
        ],
    )
    def post(self, request: Request) -> Response:
        status, body = _plan(request, request.data)
        return Response(body, status=status)


def route_map(request: HttpRequest) -> HttpResponse:
    status, body = _plan(request, request.GET)
    context = {"trip": body if status == 200 else None, "error": body}
    return render(request, "fuel_route/map.html", context, status=status)
