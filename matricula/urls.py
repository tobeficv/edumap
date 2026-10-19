from django.urls import path
from . import views

# Rutas internas de la aplicacion matricula
urlpatterns = [
    path("", views.index, name="index"),
    path("listado1", views.listado1, name="listado1"),
    path("listado2", views.listado2, name="listado2"),
    path("listado3", views.listado3, name="listado3"),
    path("grafico1", views.grafico1, name="grafico1"),
    path("grafico2", views.grafico2, name="grafico2"),
    path("grafico3", views.grafico3, name="grafico3"),
    path("grafico4", views.grafico4, name="grafico4"),
]
