from django.urls import path

from fuel_route.api.views import OptimizeRouteView, route_map

urlpatterns = [
    path("routes/optimize/", OptimizeRouteView.as_view(), name="route-optimize"),
    path("routes/map/", route_map, name="route-map"),
]
