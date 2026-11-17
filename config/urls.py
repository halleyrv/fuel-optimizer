from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/", include("fuel_route.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Demo page outside the API: a static client that calls POST /api/v1/routes/optimize/.
    path("map/", TemplateView.as_view(template_name="fuel_route/map.html"), name="route-map"),
]
