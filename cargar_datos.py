# pasa el csv de datos/ a la base de datos sqlite (tabla Matricula)
# se corre una sola vez con: python cargar_datos.py
import csv
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edumap.settings")
django.setup()

from matricula.models import Matricula

# borramos lo que habia pa que no se dupliquen las filas si se corre 2 veces
Matricula.objects.all().delete()

lista = []
with open("datos/matricula_comunas.csv", encoding="utf-8") as archivo:
    lector = csv.DictReader(archivo)
    for fila in lector:
        lista.append(Matricula(
            anio=int(fila["anio"]),
            region=fila["region"],
            comuna=fila["comuna"],
            dependencia=fila["dependencia"],
            matricula=int(fila["matricula"]),
            establecimientos=int(fila["establecimientos"]),
            rurales=int(fila["rurales"]),
        ))

# bulk_create guarda todas de una (con create una por una se demoraba mucho)
Matricula.objects.bulk_create(lista)
print("Filas cargadas:", Matricula.objects.count())
