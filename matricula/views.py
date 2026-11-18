import base64
from io import BytesIO
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")  # esto es pa que matplotlib no intente abrir una ventana
import matplotlib.pyplot as plt
import pandas as pd
from django.http import FileResponse, Http404
from django.shortcuts import render
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from .models import Matricula

# las dependencias en el orden en que las mostramos siempre
DEPENDENCIAS = ["Municipal", "SLEP", "Particular Subvencionado",
                "Particular Pagado", "Corp. Administración Delegada"]
# un color pa cada dependencia (mismo orden de arriba)
COLORES = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]


def leer_datos():
    # antes leiamos el csv, ahora los datos salen de la base sqlite (modelo Matricula)
    # lo pasamos a dataframe pa que el resto del codigo siga igual
    filas = Matricula.objects.all().values()
    return pd.DataFrame(list(filas))


def miles(numero):
    # 3541783 -> "3.541.783" (con punto como se usa en Chile)
    texto = f"{numero:,.0f}"
    return texto.replace(",", ".")


def porcentaje(numero):
    # 12.345 -> "12,3 %" (con coma decimal)
    texto = f"{numero:.1f} %"
    return texto.replace(".", ",")


def formato(valor):
    # como se ve cada valor en la pagina y en el pdf
    # (en el excel van sin formato pa que sigan siendo numeros)
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.1f}".replace(".", ",")
    if isinstance(valor, int):
        return miles(valor)
    return str(valor)


def es_publica(datos):
    # publica = Municipal + SLEP
    return datos[(datos["dependencia"] == "Municipal") | (datos["dependencia"] == "SLEP")]


# ---------------- REPORTES ----------------
# cada reporte arma un diccionario con titulo, explicacion, encabezados y filas
# asi la pagina, el pdf y el excel usan los mismos datos

def reporte1(request):
    # Reporte 1: cuantos alumnos hay cada año, separado por dependencia
    datos = leer_datos()
    anios = sorted(datos["anio"].unique())

    filas = []
    total_anterior = 0
    for anio in anios:
        datos_anio = datos[datos["anio"] == anio]
        fila = [str(anio)]
        total = 0
        for dependencia in DEPENDENCIAS:
            suma = int(datos_anio[datos_anio["dependencia"] == dependencia]["matricula"].sum())
            fila.append(suma)
            total = total + suma
        fila.append(total)

        # el primer año no tiene con quien compararse
        if total_anterior == 0:
            fila.append(None)
        else:
            fila.append(round((total - total_anterior) / total_anterior * 100, 1))
        filas.append(fila)
        total_anterior = total

    return {
        "titulo": "Matrícula nacional por año y dependencia",
        "explicacion": (
            "La tabla muestra cuántos alumnos había matriculados cada año en Chile, "
            "separados según la dependencia administrativa del establecimiento. La columna "
            "Variación compara el total con el año anterior. Se consideran solo "
            "establecimientos funcionando y con alumnos, igual que en las cifras oficiales "
            "del Mineduc."
        ),
        "encabezados": ["Año"] + DEPENDENCIAS + ["Total", "Variación (%)"],
        "filas": filas,
        "archivo": "reporte1_matricula_nacional",
    }


def reporte2(request):
    # Reporte 2: las comunas donde mas cayo la matricula publica
    datos = leer_datos()
    anio_inicial = datos["anio"].min()
    anio_final = datos["anio"].max()

    publica = es_publica(datos)
    inicio = publica[publica["anio"] == anio_inicial]
    fin = publica[publica["anio"] == anio_final]

    lista = []
    for comuna in inicio["comuna"].unique():
        datos_comuna = inicio[inicio["comuna"] == comuna]
        alumnos_inicio = int(datos_comuna["matricula"].sum())
        alumnos_fin = int(fin[fin["comuna"] == comuna]["matricula"].sum())

        # sacamos las comunas muy chicas porque cualquier cambio da un % gigante
        if alumnos_inicio >= 1000:
            lista.append({
                "comuna": comuna,
                "region": datos_comuna["region"].iloc[0],
                "inicio": alumnos_inicio,
                "fin": alumnos_fin,
                "diferencia": alumnos_fin - alumnos_inicio,
            })

    # ordenamos de la que mas perdio a la que menos y dejamos las 15 primeras
    tabla = pd.DataFrame(lista)
    tabla = tabla.sort_values("diferencia")
    tabla = tabla.head(15)

    filas = []
    posicion = 1
    for i, fila in tabla.iterrows():
        variacion = round(fila["diferencia"] / fila["inicio"] * 100, 1)
        filas.append([posicion, fila["comuna"], fila["region"], int(fila["inicio"]),
                      int(fila["fin"]), int(fila["diferencia"]), variacion])
        posicion = posicion + 1

    return {
        "titulo": "Comunas con mayor caída de la matrícula pública",
        "explicacion": (
            f"La tabla muestra las 15 comunas que más alumnos perdieron en la educación "
            f"pública entre {anio_inicial} y {anio_final}. Se cuenta como pública la "
            f"matrícula municipal + SLEP, porque muchos colegios municipales pasaron a los "
            f"Servicios Locales de Educación Pública y si se mirara solo lo municipal "
            f"parecería que se vaciaron. Solo se incluyen comunas con al menos 1.000 "
            f"alumnos en la pública en {anio_inicial}."
        ),
        "encabezados": ["#", "Comuna", "Región", f"Matrícula {anio_inicial}",
                        f"Matrícula {anio_final}", "Diferencia", "Variación (%)"],
        "filas": filas,
        "archivo": "reporte2_caida_publica",
    }


def reporte3(request):
    # Reporte 3: foto del ultimo año por region
    datos = leer_datos()
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]
    total_pais = int(ultimo["matricula"].sum())

    lista = []
    for region in ultimo["region"].unique():
        datos_region = ultimo[ultimo["region"] == region]
        lista.append({
            "region": region,
            "establecimientos": int(datos_region["establecimientos"].sum()),
            "rurales": int(datos_region["rurales"].sum()),
            "matricula": int(datos_region["matricula"].sum()),
            "publica": int(es_publica(datos_region)["matricula"].sum()),
        })

    # de la region con mas alumnos a la con menos
    tabla = pd.DataFrame(lista)
    tabla = tabla.sort_values("matricula", ascending=False)

    filas = []
    for i, fila in tabla.iterrows():
        filas.append([
            fila["region"],
            int(fila["establecimientos"]),
            int(fila["rurales"]),
            int(fila["matricula"]),
            round(fila["matricula"] / total_pais * 100, 1),
            round(fila["publica"] / fila["matricula"] * 100, 1),
        ])
    # fila final con el total
    filas.append(["Total país", None, None, total_pais, 100.0, None])

    return {
        "titulo": f"Matrícula por región ({anio_final})",
        "explicacion": (
            f"La tabla resume cada región en {anio_final}: cuántos establecimientos "
            f"funcionando tiene (y cuántos son rurales), cuántos alumnos hay matriculados, "
            f"qué parte de la matrícula del país representa y qué porcentaje de sus alumnos "
            f"asiste a la educación pública (municipal + SLEP). Las regiones están ordenadas "
            f"de mayor a menor matrícula."
        ),
        "encabezados": ["Región", "Establecimientos", "Rurales", "Matrícula",
                        "% del país", "% en educación pública"],
        "filas": filas,
        "archivo": "reporte3_matricula_region",
    }


def reporte4(request):
    # Reporte 4: los datos del grafico dinamico (region y año que elige el usuario)
    datos = leer_datos()
    # vienen por GET en la url, si no eligio nada: todo el pais y el ultimo año
    region = request.GET.get("region", "Todas")
    anio = request.GET.get("anio", str(datos["anio"].max()))

    filtrado = datos
    if region != "Todas":
        filtrado = filtrado[filtrado["region"] == region]
    # ojo: si el año no es un numero la seleccion queda vacia
    if anio.isdigit():
        filtrado = filtrado[filtrado["anio"] == int(anio)]
    else:
        filtrado = filtrado[filtrado["anio"] == -1]

    total = int(filtrado["matricula"].sum())
    filas = []
    for dependencia in DEPENDENCIAS:
        datos_dep = filtrado[filtrado["dependencia"] == dependencia]
        alumnos = int(datos_dep["matricula"].sum())
        # solo las dependencias que tienen alumnos en esa seleccion
        if alumnos > 0:
            filas.append([
                dependencia,
                alumnos,
                round(alumnos / total * 100, 1),
                int(datos_dep["establecimientos"].sum()),
                int(datos_dep["rurales"].sum()),
            ])

    if region == "Todas":
        lugar = "todo Chile"
    else:
        lugar = f"la región {region}"

    # la interpretacion cambia segun lo que salga
    if len(filas) > 0:
        mayor = filas[0]
        publica = 0
        for fila in filas:
            if fila[1] > mayor[1]:
                mayor = fila
            if fila[0] == "Municipal" or fila[0] == "SLEP":
                publica = publica + fila[1]
        interpretacion = (
            f"En {lugar} durante {anio} hay {miles(total)} alumnos. La dependencia con más "
            f"alumnos es {mayor[0]} con el {formato(mayor[2])} %, y la educación pública "
            f"(municipal + SLEP) reúne el {formato(round(publica / total * 100, 1))} %."
        )
    else:
        interpretacion = "No hay datos para la selección elegida, pruebe con otra región o año."

    return {
        "titulo": f"Matrícula por dependencia en {lugar}, {anio}",
        "explicacion": (
            "Datos del Mineduc (Resumen de Matrícula por Establecimiento) guardados en la "
            "base de datos SQLite del proyecto. Se filtran por la región y el año elegidos "
            "y se suman la matrícula, los establecimientos y los establecimientos rurales "
            "de cada dependencia. El % es la parte de la matrícula de la selección que "
            "corresponde a cada dependencia. Son los mismos datos del gráfico dinámico. "
        ),
        "interpretacion": interpretacion,
        "encabezados": ["Dependencia", "Matrícula", "% de la matrícula",
                        "Establecimientos", "Rurales"],
        "filas": filas,
        "archivo": f"reporte4_{region}_{anio}".replace(" ", "_"),
        "region": region,
        "anio": anio,
        "lugar": lugar,
        "total": total,
    }


def armar_reporte(request, numero):
    # elige el reporte segun el numero de la url
    if numero == 1:
        return reporte1(request)
    elif numero == 2:
        return reporte2(request)
    elif numero == 3:
        return reporte3(request)
    elif numero == 4:
        return reporte4(request)
    raise Http404("Ese reporte no existe")


def opciones_filtro():
    # las regiones y años pa los select del formulario
    datos = leer_datos()
    regiones = sorted(datos["region"].unique())
    anios = sorted(datos["anio"].unique(), reverse=True)
    return regiones, anios


def index(request):
    datos = leer_datos()
    anio_inicial = datos["anio"].min()
    anio_final = datos["anio"].max()

    # nos quedamos solo con el ultimo año pa los numeritos de las tarjetas
    ultimo = datos[datos["anio"] == anio_final]
    total_alumnos = ultimo["matricula"].sum()
    total_establecimientos = ultimo["establecimientos"].sum()
    total_comunas = len(ultimo["comuna"].unique())

    contexto = {
        "anio_inicial": anio_inicial,
        "anio_final": anio_final,
        "total_alumnos": miles(total_alumnos),
        "total_establecimientos": miles(total_establecimientos),
        "total_comunas": total_comunas,
    }
    return render(request, "matricula/index.html", contexto)


def listado(request, numero):
    # una sola vista pa los 4 reportes, lo que cambia es el numero de la url
    reporte = armar_reporte(request, numero)

    # pasamos los valores a texto con puntos y comas pa mostrarlos
    filas = []
    for fila in reporte["filas"]:
        nueva = []
        for valor in fila:
            nueva.append(formato(valor))
        filas.append(nueva)

    contexto = {
        "numero": numero,
        "titulo": reporte["titulo"],
        "explicacion": reporte["explicacion"],
        "interpretacion": reporte.get("interpretacion", ""),
        "encabezados": reporte["encabezados"],
        "filas": filas,
    }
    # el 4 lleva el formulario con los filtros
    if numero == 4:
        regiones, anios = opciones_filtro()
        contexto["regiones"] = regiones
        contexto["anios"] = anios
        contexto["region"] = reporte["region"]
        contexto["anio"] = reporte["anio"]
    return render(request, "matricula/reporte.html", contexto)


def descargar_pdf(request, numero):
    # pdf con reportlab, como en la guia 8
    reporte = armar_reporte(request, numero)

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30,
        topMargin=30, bottomMargin=30, title=reporte["titulo"],
    )
    estilos = getSampleStyleSheet()
    celda = ParagraphStyle("Celda", fontName="Helvetica", fontSize=9, leading=11)
    negrita = ParagraphStyle("Negrita", fontName="Helvetica-Bold", fontSize=9, leading=11)

    filas = [[Paragraph(escape(texto), negrita) for texto in reporte["encabezados"]]]
    for fila in reporte["filas"]:
        filas.append([Paragraph(escape(formato(valor)), celda) for valor in fila])
    if len(reporte["filas"]) == 0:
        filas.append([Paragraph("No hay datos para esta selección.", celda)]
                     + [""] * (len(reporte["encabezados"]) - 1))

    # repartimos el ancho de la hoja entre las columnas
    ancho_columna = (landscape(A4)[0] - 60) / len(reporte["encabezados"])
    tabla = LongTable(filas, colWidths=ancho_columna, repeatRows=1, hAlign="LEFT")
    formato_tabla = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if len(reporte["filas"]) == 0:
        formato_tabla.append(("SPAN", (0, 1), (-1, 1)))
    tabla.setStyle(TableStyle(formato_tabla))

    elementos = [
        Paragraph(escape(reporte["titulo"]), estilos["Title"]),
        Paragraph(escape(reporte["explicacion"]), estilos["Normal"]),
    ]
    if reporte.get("interpretacion"):
        elementos.append(Spacer(1, 6))
        elementos.append(Paragraph("Interpretación: " + escape(reporte["interpretacion"]), estilos["Normal"]))
    elementos.append(Spacer(1, 12))
    elementos.append(tabla)
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph("Fuente: Centro de Estudios Mineduc, Resumen de Matrícula por "
                               "Establecimiento Educacional 2019–2025.", estilos["Italic"]))
    documento.build(elementos)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=reporte["archivo"] + ".pdf")


def descargar_excel(request, numero):
    # excel con openpyxl, como en la guia 9
    reporte = armar_reporte(request, numero)

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Reporte"
    hoja.append(reporte["encabezados"])
    # aca van los valores sin formato, asi los numeros quedan como numeros en excel
    for fila in reporte["filas"]:
        hoja.append(fila)

    borde = Side(style="thin", color="D9D9D9")
    for fila in hoja:
        for celda in fila:
            celda.border = Border(left=borde, right=borde, top=borde, bottom=borde)
            # los % con un decimal y la matricula con separador de miles
            if isinstance(celda.value, float):
                celda.number_format = "0.0"
            elif isinstance(celda.value, int):
                celda.number_format = "#,##0"

    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E78")

    # ancho de cada columna segun el texto mas largo que tenga
    for columna in range(1, len(reporte["encabezados"]) + 1):
        largo = 10
        for fila in hoja.iter_rows(min_col=columna, max_col=columna):
            texto = str(fila[0].value or "")
            if len(texto) + 2 > largo:
                largo = len(texto) + 2
        hoja.column_dimensions[get_column_letter(columna)].width = largo

    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions

    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=reporte["archivo"] + ".xlsx")


# ---------------- GRAFICOS ----------------

def grafico1(request):
    # Grafico de barras: alumnos por region en el ultimo año
    datos = leer_datos()
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]

    lista = []
    for region in ultimo["region"].unique():
        alumnos = ultimo[ultimo["region"] == region]["matricula"].sum()
        lista.append({"region": region, "alumnos": alumnos})

    # ordenamos de menor a mayor pa que la barra mas larga quede arriba
    tabla = pd.DataFrame(lista)
    tabla = tabla.sort_values("alumnos")
    miles_alumnos = tabla["alumnos"] / 1000  # en miles pa que los numeros no sean eternos

    plt.figure(figsize=(9, 6))
    barras = plt.barh(tabla["region"], miles_alumnos, color="#4C72B0")
    plt.bar_label(barras, fmt="%.0f", padding=3)  # el numerito al final de cada barra
    plt.title(f"Matrícula escolar por región, {anio_final}")
    plt.xlabel("Alumnos matriculados (miles)")
    plt.ylabel("Región")
    plt.xlim(0, miles_alumnos.max() * 1.12)  # un poco de espacio extra pa los numeritos
    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    # pasamos la imagen a texto (base64) pa poder mandarla al html
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=120)
    plt.close()
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")

    alumnos_rm = ultimo[ultimo["region"] == "Metropolitana"]["matricula"].sum()
    parte_rm = alumnos_rm / ultimo["matricula"].sum() * 100
    contexto = {
        "titulo": "Matrícula por región",
        "explicacion": (
            f"Cada barra muestra cuántos alumnos (en miles) estaban matriculados "
            f"en {anio_final} en establecimientos funcionando de cada región. "
            f"La Región Metropolitana concentra cerca del {parte_rm:.0f} % de la "
            f"matrícula del país, mientras que Aysén y Magallanes son las de menor "
            f"tamaño. Las barras están ordenadas para comparar fácilmente."
        ),
        "grafico": grafico,
        "alt": "Barras horizontales con la matrícula escolar por región",
    }
    return render(request, "matricula/grafico.html", contexto)


def grafico2(request):
    # Grafico de lineas: como cambia la matricula de cada dependencia año a año
    datos = leer_datos()
    anios = sorted(datos["anio"].unique())

    plt.figure(figsize=(9, 5))

    # una linea por dependencia
    for i in range(len(DEPENDENCIAS)):
        dependencia = DEPENDENCIAS[i]
        valores = []
        for anio in anios:
            filtro = datos[(datos["anio"] == anio) & (datos["dependencia"] == dependencia)]
            valores.append(filtro["matricula"].sum() / 1000)
        plt.plot(anios, valores, marker="o", linewidth=2, color=COLORES[i], label=dependencia)

    # y una extra punteada con la publica completa (Municipal + SLEP)
    publica = []
    for anio in anios:
        datos_anio = datos[datos["anio"] == anio]
        filtro = datos_anio[(datos_anio["dependencia"] == "Municipal") | (datos_anio["dependencia"] == "SLEP")]
        publica.append(filtro["matricula"].sum() / 1000)
    plt.plot(anios, publica, marker="s", linewidth=2, linestyle="--",
             color="#333333", label="Pública total (Municipal + SLEP)")

    plt.title("Evolución de la matrícula por dependencia, 2019–2025")
    plt.xlabel("Año")
    plt.ylabel("Alumnos matriculados (miles)")
    plt.xticks(anios)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, loc="center left", bbox_to_anchor=(1, 0.5))  # leyenda afuera, a la derecha
    plt.tight_layout()

    # pasamos la imagen a texto (base64) pa poder mandarla al html
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=120)
    plt.close()
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # cuanto cambio la publica entre el primer año y el ultimo
    caida_publica = (publica[-1] - publica[0]) / publica[0] * 100
    texto_caida = f"{caida_publica:+.1f} %"
    texto_caida = texto_caida.replace(".", ",")
    contexto = {
        "titulo": "Evolución de la matrícula por dependencia",
        "explicacion": (
            "Cada línea muestra los alumnos matriculados por año según quién "
            "administra el establecimiento. La matrícula municipal cae y la de "
            "los SLEP sube porque los colegios se traspasan a los nuevos "
            "Servicios Locales; por eso la línea punteada suma ambas y muestra "
            f"la educación pública completa, que varía un {texto_caida} "
            "entre 2019 y 2025. La particular subvencionada se mantiene como la "
            "dependencia con más alumnos."
        ),
        "grafico": grafico,
        "alt": "Líneas con la evolución de la matrícula por dependencia entre 2019 y 2025",
    }
    return render(request, "matricula/grafico.html", contexto)


def grafico3(request):
    # Grafico de dispersion: cada puntito es una comuna
    # eje x = que % de sus alumnos iban a la publica al principio
    # eje y = cuanto cambio su matricula total entre el primer y el ultimo año
    # la idea es ver si las comunas mas "publicas" son las que mas alumnos pierden
    datos = leer_datos()
    anio_inicial = datos["anio"].min()
    anio_final = datos["anio"].max()
    inicio = datos[datos["anio"] == anio_inicial]
    fin = datos[datos["anio"] == anio_final]

    peso_publica = []   # eje x
    variaciones = []    # eje y
    tamanos = []        # tamaño de cada punto
    for comuna in inicio["comuna"].unique():
        inicio_comuna = inicio[inicio["comuna"] == comuna]
        total_inicio = inicio_comuna["matricula"].sum()

        # igual que en el listado 2, sacamos las comunas muy chiquitas
        if total_inicio >= 1000:
            total_fin = fin[fin["comuna"] == comuna]["matricula"].sum()
            publica = inicio_comuna[(inicio_comuna["dependencia"] == "Municipal") | (inicio_comuna["dependencia"] == "SLEP")]
            publica_inicio = publica["matricula"].sum()

            peso_publica.append(publica_inicio / total_inicio * 100)
            variaciones.append((total_fin - total_inicio) / total_inicio * 100)
            tamanos.append(total_inicio / 400)  # mientras mas alumnos, mas grande el punto

    plt.figure(figsize=(9, 6))
    plt.scatter(peso_publica, variaciones, s=tamanos, color="#4C72B0", alpha=0.5, edgecolors="white")
    plt.axhline(0, color="#333333", linewidth=1)  # linea del 0: arriba crecio, abajo bajo
    plt.title("Peso de la educación pública vs. variación de la matrícula por comuna")
    plt.xlabel(f"% de alumnos en educación pública en {anio_inicial}")
    plt.ylabel(f"Variación de la matrícula total {anio_inicial}–{anio_final} (%)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # pasamos la imagen a texto (base64) pa poder mandarla al html
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=120)
    plt.close()
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # contamos cuantas comunas quedaron bajo el 0 (perdieron alumnos)
    comunas_bajan = 0
    for variacion in variaciones:
        if variacion < 0:
            comunas_bajan = comunas_bajan + 1

    # la correlacion nos dice si hay relacion entre x e y (cerca de 0 = casi nada)
    correlacion = pd.Series(peso_publica).corr(pd.Series(variaciones))
    texto_correlacion = f"{correlacion:.2f}"
    texto_correlacion = texto_correlacion.replace(".", ",")

    # armamos la frase segun si la correlacion es positiva, negativa o casi nada
    if correlacion > 0.1:
        lectura = ("es positiva y débil: las comunas más dependientes de la "
                   "educación pública no son las que más alumnos pierden, al contrario, "
                   "tienden a perder un poco menos. Las comunas grandes y urbanas "
                   "(puntos grandes a la izquierda) son las que más bajan.")
    elif correlacion < -0.1:
        lectura = ("es negativa: mientras más peso tiene la educación pública en la "
                   "comuna, más tiende a caer su matrícula.")
    else:
        lectura = "es casi cero, o sea, las dos variables prácticamente no se relacionan."

    contexto = {
        "titulo": "Peso de la educación pública vs. variación de la matrícula",
        "explicacion": (
            f"Cada punto es una comuna con al menos 1.000 alumnos en {anio_inicial} "
            f"(el tamaño del punto indica cuántos alumnos tiene). En el eje horizontal "
            f"está el porcentaje de su matrícula que asistía a la educación pública "
            f"(municipal + SLEP) y en el vertical cuánto cambió su matrícula total "
            f"hasta {anio_final}. {comunas_bajan} de las {len(variaciones)} comunas quedan "
            f"bajo la línea del 0, o sea, perdieron alumnos. La correlación entre "
            f"ambas variables ({texto_correlacion}) {lectura}"
        ),
        "grafico": grafico,
        "alt": "Dispersión de comunas según peso de la educación pública y variación de su matrícula",
    }
    return render(request, "matricula/grafico.html", contexto)


def grafico4(request):
    # Grafico circular: como se reparte la matricula del ultimo año entre dependencias
    datos = leer_datos()
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]

    # los alumnos de cada dependencia, en el mismo orden de DEPENDENCIAS
    valores = []
    for dependencia in DEPENDENCIAS:
        suma = ultimo[ultimo["dependencia"] == dependencia]["matricula"].sum()
        valores.append(suma)

    plt.figure(figsize=(9, 6))
    plt.pie(valores, colors=COLORES, autopct="%1.1f%%", startangle=90, pctdistance=0.8)
    # los nombres van en la leyenda al lado, porque encima de la torta se pisaban
    plt.legend(DEPENDENCIAS, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9)
    plt.title(f"Distribución de la matrícula por dependencia, {anio_final}")
    plt.axis("equal")  # pa que quede redondo y no ovalado
    plt.tight_layout()

    # pasamos la imagen a texto (base64) pa poder mandarla al html
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=120)
    plt.close()
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # valores[0] = Municipal, valores[1] = SLEP, valores[2] = Particular Subvencionado
    total = sum(valores)
    parte_subvencionado = valores[2] / total * 100
    parte_publica = (valores[0] + valores[1]) / total * 100
    contexto = {
        "titulo": "Distribución de la matrícula por dependencia",
        "explicacion": (
            f"El gráfico muestra cómo se reparten los {miles(total)} alumnos de "
            f"{anio_final} según la dependencia del establecimiento. La particular "
            f"subvencionada concentra el {porcentaje(parte_subvencionado)}, mientras que "
            f"la educación pública (municipal + SLEP) suma el {porcentaje(parte_publica)}."
        ),
        "grafico": grafico,
        "alt": "Gráfico circular con la distribución de la matrícula por dependencia",
    }
    return render(request, "matricula/grafico.html", contexto)


def grafico5(request):
    # Grafico dinamico: el usuario elige region y año y se dibuja la matricula por dependencia
    # usa los mismos datos del reporte 4, asi el grafico y la tabla siempre coinciden
    reporte = reporte4(request)
    regiones, anios = opciones_filtro()

    grafico = ""
    if len(reporte["filas"]) > 0:
        nombres = []
        alumnos = []
        colores = []
        for fila in reporte["filas"]:
            nombres.append(fila[0])
            alumnos.append(fila[1] / 1000)  # en miles
            colores.append(COLORES[DEPENDENCIAS.index(fila[0])])  # cada dependencia con su color

        plt.figure(figsize=(9, 5))
        barras = plt.barh(nombres, alumnos, color=colores)
        plt.bar_label(barras, fmt="%.1f", padding=3)
        plt.gca().invert_yaxis()  # pa que quede en el mismo orden que la tabla
        plt.title(f"Matrícula por dependencia en {reporte['lugar']}, {reporte['anio']}")
        plt.xlabel("Alumnos matriculados (miles)")
        plt.ylabel("Dependencia")
        plt.xlim(0, max(alumnos) * 1.15)
        plt.grid(axis="x", alpha=0.3)
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=120)
        plt.close()
        grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")

    contexto = {
        "titulo": "Gráfico dinámico: matrícula por dependencia",
        "explicacion": (
            "Elija una región y un año y presione Actualizar. Cada barra es una dependencia "
            "administrativa (quién administra el colegio) y su largo son los alumnos "
            "matriculados, en miles, para esa selección. Así se puede comparar cómo cambia "
            "el peso de la educación pública y la particular entre regiones y años."
        ),
        "interpretacion": reporte["interpretacion"],
        "grafico": grafico,
        "regiones": regiones,
        "anios": anios,
        "region": reporte["region"],
        "anio": reporte["anio"],
    }
    return render(request, "matricula/grafico5.html", contexto)
