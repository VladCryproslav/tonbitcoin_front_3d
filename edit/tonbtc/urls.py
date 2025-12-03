"""
URL configuration for tonbtc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import permissions


class BothHttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ["http", "https"]
        return schema


schema_view = get_schema_view(
    openapi.Info(
        title="TonBTC API",
        default_version="v1",
        description="Description",
    ),
    generator_class=BothHttpAndHttpsSchemaGenerator,
    public=True,
    permission_classes=(permissions.IsAdminUser,),
)


from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from debug_toolbar.toolbar import debug_toolbar_urls
from django_ratelimit.decorators import ratelimit

admin_login_view = ratelimit(key='ip', rate='5/m', block=True)(admin.site.login)
    
urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += (
    [
        path("admpan15513/login/", admin_login_view, name="admin_login"),
        path("admpan15513/", admin.site.urls),
        path("webhook/", include("tgbot.urls")),
        path("api/", include("core.urls")),
        path(
            "swagger<format>/",
            schema_view.without_ui(cache_timeout=0),
            name="schema-json",
        ),
        path(
            "swagger/",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
        path(
            "redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
        ),
        # re_path(r"^advanced_filters/", include("advanced_filters.urls")),
    ]
    + debug_toolbar_urls()
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)
