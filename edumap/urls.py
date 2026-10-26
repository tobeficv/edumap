from django.contrib import admin
from django.urls import include, path

# rutas del proyecto completo
urlpatterns = [
    path("admin/", admin.site.urls),
    # todo lo que empiece con matricula/ se va a las rutas de la app
    path("matricula/", include("matricula.urls")),
]
