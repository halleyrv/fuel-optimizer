from django.urls import path

from fuel_route.api.views import OptimizeRouteView

urlpatterns = [path("routes/optimize/", OptimizeRouteView.as_view(), name="route-optimize")]
