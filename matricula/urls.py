from django.urls import path
from . import views

# las rutas de la app: cada una apunta a su vista en views.py
# el name es el que usamos en el menu con {% url 'nombre' %}
urlpatterns = [
    path("", views.index, name="index"),
    # las 3 tablas
    path("listado1", views.listado1, name="listado1"),
    path("listado2", views.listado2, name="listado2"),
    path("listado3", views.listado3, name="listado3"),
    # los 4 graficos
    path("grafico1", views.grafico1, name="grafico1"),
    path("grafico2", views.grafico2, name="grafico2"),
    path("grafico3", views.grafico3, name="grafico3"),
    path("grafico4", views.grafico4, name="grafico4"),
]
