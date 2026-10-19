# EduMap — Matrícula escolar en Chile (Django)

Proyecto semestral de Taller Visualización de Datos, Certamen 2.
Datos: Centro de Estudios Mineduc, *Resumen de Matrícula por Establecimiento Educacional* 2019–2025.

## Ejecutar

Si el entorno ya existe:

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

Abrir http://127.0.0.1:8000/matricula/

## Estructura

- `datos/preparar_datos.py`: lee los 7 CSV oficiales, aplica la limpieza del EDA y genera `datos/matricula_comunas.csv` (ya incluido).
- `matricula/views.py`: cada vista lee el resumen, prepara la tabla o dibuja el gráfico con Matplotlib y lo envía a la plantilla.
- `matricula/templates/matricula/`: `base.html` (Bootstrap), `menu.html` (menú con los desplegables *Listados de datos* y *Gráficos*) y las páginas.


