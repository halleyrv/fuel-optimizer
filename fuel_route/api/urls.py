from django.urls import path

from fuel_route.api.views import OptimizeRouteView, RouteMapView

urlpatterns = [
    path("routes/optimize/", OptimizeRouteView.as_view(), name="route-optimize"),
    path("routes/map/", RouteMapView.as_view(), name="route-map"),
]
