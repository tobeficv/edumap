from django.db import models


# cada fila es lo mismo que una fila del csv: año + comuna + dependencia
class Matricula(models.Model):
    anio = models.IntegerField()
    region = models.CharField(max_length=60)
    comuna = models.CharField(max_length=60)
    dependencia = models.CharField(max_length=60)
    matricula = models.IntegerField()
    establecimientos = models.IntegerField()
    rurales = models.IntegerField()

    def __str__(self):
        return f"{self.anio} {self.comuna} {self.dependencia}"
