# EduMap — Matrícula escolar en Chile (Django)

Proyecto semestral de Visualización de Datos (IIP221W), Certamen 3 parte 1.
Datos: Centro de Estudios Mineduc, *Resumen de Matrícula por Establecimiento Educacional* 2019–2025.

## Integrante
- Felipe Callejas


## Links

- Sitio en AWS: http://18.116.201.69:8000/matricula/
- Video 1 (despliegue en AWS): https://youtu.be/43QYqAjOeI8
- Video 2 (presentación del software y el código): https://youtu.be/fGtahSoFaP4

## Qué tiene

- **Reportes** (menú Reportes): 4 tablas, cada una con los botones *Descarga en PDF* y *Descarga en Excel*.
  1. Matrícula nacional por año y dependencia
  2. Comunas con mayor caída de la matrícula pública
  3. Matrícula por región
  4. Matrícula por dependencia, con filtros de región y año (nuevo)
- **Gráficos** (menú Gráficos): barras, líneas, dispersión, circular y el gráfico dinámico (nuevo), donde se elige región y año y se actualiza el gráfico. El reporte 4 muestra los mismos datos del gráfico dinámico.
- Los datos están en la base de datos SQLite (`db.sqlite3`, modelo `Matricula`).

## Dependencias

Están en `requirements.txt`. Las principales:

- Django 5.1
- pandas (filtrar y sumar los datos)
- matplotlib (gráficos)
- reportlab (PDF)
- openpyxl (Excel)

## Cómo correrlo en el computador (Windows)

```
py -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

Después se abre http://127.0.0.1:8000/matricula/

La base `db.sqlite3` ya viene con los datos. Si se borra o queda vacía se vuelve a llenar con:

```
py cargar_datos.py
```

(lee `datos/matricula_comunas.csv` y lo guarda en la tabla Matricula)

## Despliegue en AWS (EC2)

Usé una instancia EC2 con Ubuntu. Como la base es SQLite, la base de datos es el archivo `db.sqlite3` que queda dentro de la instancia junto con el proyecto, así que Django la lee directo desde el servidor.

### 1. Crear la instancia

1. Entrar a la consola de AWS → **EC2** → **Lanzar instancia**.
2. Nombre: `edumap`. Imagen: **Ubuntu Server 24.04 LTS**. Tipo: **t2.micro** o **t3.micro** (capa gratuita).
3. Par de claves: crear uno nuevo (o usar *EC2 Instance Connect* para entrar desde el navegador).
4. En **Configuración de red** → grupo de seguridad, dejar estas reglas de entrada:
   - SSH, puerto 22
   - TCP personalizado, puerto **8000**, origen `0.0.0.0/0` (para poder entrar al sitio desde cualquier navegador)
5. Lanzar la instancia y copiar su **dirección IPv4 pública**.

### 2. Instalar el proyecto en la instancia

Conectarse (botón **Conectar** → EC2 Instance Connect) y correr:

```
sudo apt update
sudo apt install -y python3-venv python3-pip git
git clone https://github.com/tobeficv/edumap.git
cd edumap
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

Si la base vino vacía: `python cargar_datos.py`

### 3. Configuración de Django

En `edumap/settings.py` está:

```
ALLOWED_HOSTS = ["*"]
```

Esto deja que Django responda cuando se entra con la IP pública de la instancia (si no, sale error *DisallowedHost*). También se puede poner solo la IP: `ALLOWED_HOSTS = ["IP_PUBLICA"]`.

### 4. Levantar el servidor

```
python manage.py runserver 0.0.0.0:8000
```

El `0.0.0.0` hace que escuche las conexiones de afuera y no solo las de la propia máquina. Para que siga funcionando después de cerrar la consola:

```
nohup python manage.py runserver 0.0.0.0:8000 > servidor.log 2>&1 &
```

### 5. Probar desde otro navegador

Abrir `http://IP_PUBLICA:8000/matricula/` desde otro computador o el celular, y probar el gráfico dinámico, el reporte 4 y las descargas en PDF y Excel.

Notas: la IP pública cambia si se detiene y se vuelve a iniciar la instancia. Usé `runserver` porque es lo que vimos en el curso; para un sitio real habría que usar gunicorn + nginx y `DEBUG = False`.

## Archivos importantes

- `matricula/models.py`: modelo `Matricula` (año, región, comuna, dependencia, matrícula, establecimientos, rurales).
- `cargar_datos.py`: pasa el CSV a la base SQLite.
- `matricula/views.py`: las vistas. `reporte1` a `reporte4` arman los datos de cada reporte; `listado`, `descargar_pdf` y `descargar_excel` usan esos mismos datos para la página, el PDF y el Excel. `grafico1` a `grafico5` dibujan los gráficos con matplotlib.
- `matricula/urls.py`: las rutas (`reporte/<numero>`, `reporte/<numero>/pdf`, `reporte/<numero>/excel`, `grafico1`…`grafico5`).
- `matricula/templates/matricula/`: `base.html`, `menu.html`, `index.html`, `reporte.html` (sirve para los 4 reportes), `grafico.html`, `grafico5.html` y `filtros.html` (formulario de región y año).
- `datos/preparar_datos.py`: script con el que armé el CSV a partir de los archivos originales del Mineduc.
