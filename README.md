# EduMap — Matrícula escolar en Chile (Django)

Proyecto semestral de Taller de Visualización de Datos, Certamen 2.
Datos: Centro de Estudios Mineduc, *Resumen de Matrícula por Establecimiento Educacional* 2019–2025.

## Cómo correrlo

Si ya tienes el entorno creado:

```
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

En un computador nuevo:

```
py -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

Después abre http://127.0.0.1:8000/matricula/

## Qué hay en cada parte

- `datos/matricula_comunas.csv`: el resumen que usa la página (ya viene incluido).
- `datos/preparar_datos.py`: el script con el que armamos ese resumen. Lee los 7 CSV originales del Mineduc (van en `datos/originales/` y no se suben porque pesan mucho), deja solo los colegios funcionando y con alumnos, y suma todo por año, región, comuna y dependencia.
- `matricula/urls.py`: las rutas de las páginas (inicio, 3 listados y 4 gráficos).
- `matricula/views.py`: una vista por página. Cada una lee el CSV con pandas, arma la tabla o dibuja el gráfico con Matplotlib y se lo manda a la plantilla.
- `matricula/templates/matricula/`: `base.html` (Bootstrap), `menu.html` (el menú con los desplegables *Listados de datos* y *Gráficos*), `index.html`, `listado1-3.html` y `grafico.html` (la misma plantilla sirve para los 4 gráficos).
