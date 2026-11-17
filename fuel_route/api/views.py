from typing import Any
from urllib.parse import urlencode

from django.http import HttpRequest
from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.renderers import TemplateHTMLRenderer
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


_HTML_ERROR = OpenApiResponse(OpenApiTypes.STR, description="HTML page explaining the error (same codes as the JSON endpoint).")


class RouteMapView(APIView):
    renderer_classes = [TemplateHTMLRenderer]

    @extend_schema(
        summary="Show the planned trip on a map (HTML)",
        description=(
            "Same inputs and plan as `POST /api/v1/routes/optimize/`, rendered as an HTML page: the route, "
            "a marker per fuel stop and a table of purchases. Open it in a browser, for example "
            "`/api/v1/routes/map/?start=Chicago%2C+IL&finish=Denver%2C+CO`. Every JSON response links here "
            "through `map_url`."
        ),
        parameters=[TripRequestSerializer],
        responses={
            (200, "text/html"): OpenApiResponse(OpenApiTypes.STR, description="HTML page with the route map."),
            (400, "text/html"): _HTML_ERROR,
            (404, "text/html"): _HTML_ERROR,
            (422, "text/html"): _HTML_ERROR,
            (502, "text/html"): _HTML_ERROR,
        },
    )
    def get(self, request: Request) -> Response:
        status, body = _plan(request, request.query_params)
        context = {"trip": body if status == 200 else None, "error": body}
        return Response(context, status=status, template_name="fuel_route/map.html")
