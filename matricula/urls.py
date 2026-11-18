from django.urls import path
from . import views

# las rutas de la app: cada una apunta a su vista en views.py
# el name es el que usamos en el menu con {% url 'nombre' %}
urlpatterns = [
    path("", views.index, name="index"),
    # los 4 reportes usan la misma vista, el numero dice cual es (1, 2, 3 o 4)
    path("reporte/<int:numero>", views.listado, name="reporte"),
    path("reporte/<int:numero>/pdf", views.descargar_pdf, name="reporte_pdf"),
    path("reporte/<int:numero>/excel", views.descargar_excel, name="reporte_excel"),
    # los graficos
    path("grafico1", views.grafico1, name="grafico1"),
    path("grafico2", views.grafico2, name="grafico2"),
    path("grafico3", views.grafico3, name="grafico3"),
    path("grafico4", views.grafico4, name="grafico4"),
    path("grafico5", views.grafico5, name="grafico5"),
]
