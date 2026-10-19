from django.contrib import admin
from django.urls import include, path

# Rutas principales del proyecto
urlpatterns = [
    path("admin/", admin.site.urls),
    # Rutas de la aplicación matricula
    path("matricula/", include("matricula.urls")),
]
