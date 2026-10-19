import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")  # Dibujar sin abrir una ventana grafica
import matplotlib.pyplot as plt
import pandas as pd
from django.shortcuts import render

# Resumen generado por datos/preparar_datos.py a partir de los CSV del Mineduc
RUTA_DATOS = "datos/matricula_comunas.csv"

COLORES = {
    "Municipal": "#4C72B0",
    "SLEP": "#DD8452",
    "Particular Subvencionado": "#55A868",
    "Particular Pagado": "#C44E52",
    "Corp. Administración Delegada": "#8172B2",
}
ORDEN_DEPENDENCIAS = list(COLORES.keys())


def cargar_datos():
    return pd.read_csv(RUTA_DATOS, encoding="utf-8")


def miles(numero):
    return f"{numero:,.0f}".replace(",", ".")


def index(request):
    datos = cargar_datos()
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]
    contexto = {
        "anio_inicial": datos["anio"].min(),
        "anio_final": anio_final,
        "total_alumnos": miles(ultimo["matricula"].sum()),
        "total_establecimientos": miles(ultimo["establecimientos"].sum()),
        "total_comunas": ultimo["comuna"].nunique(),
    }
    return render(request, "matricula/index.html", contexto)


def listado1(request):
    # Lista 1: matricula nacional por año y dependencia administrativa
    datos = cargar_datos()
    tabla = datos.pivot_table(index="anio", columns="dependencia",
                              values="matricula", aggfunc="sum", fill_value=0)
    tabla = tabla[ORDEN_DEPENDENCIAS]
    tabla["Total"] = tabla.sum(axis=1)

    filas = []
    total_anterior = None
    for anio, fila in tabla.iterrows():
        if total_anterior is None:
            variacion = "—"
        else:
            variacion = f"{(fila['Total'] - total_anterior) / total_anterior * 100:+.1f} %".replace(".", ",")
        total_anterior = fila["Total"]
        filas.append({
            "anio": anio,
            "valores": [miles(fila[d]) for d in ORDEN_DEPENDENCIAS],
            "total": miles(fila["Total"]),
            "variacion": variacion,
        })

    contexto = {"dependencias": ORDEN_DEPENDENCIAS, "filas": filas}
    return render(request, "matricula/listado1.html", contexto)


def listado2(request):
    # TODO: falta armar la tabla/grafico
    contexto = {
        "titulo": "Comunas con mayor caída de la matrícula pública",
    }
    return render(request, "matricula/seccion.html", contexto)


def listado3(request):
    # TODO: falta armar la tabla/grafico
    contexto = {
        "titulo": "Matrícula por región",
    }
    return render(request, "matricula/seccion.html", contexto)


def grafico1(request):
    # Gráfico de barras: matrícula del último año por región
    datos = cargar_datos()
    anio_final = datos["anio"].max()
    por_region = (datos[datos["anio"] == anio_final]
                  .groupby("region")["matricula"].sum()
                  .sort_values())
    valores = por_region.values / 1000

    figura, eje = plt.subplots(figsize=(9, 6))
    barras = eje.barh(por_region.index, valores, color="#4C72B0")
    eje.set_title(f"Matrícula escolar por región, {anio_final}")
    eje.set_xlabel("Alumnos matriculados (miles)")
    eje.set_ylabel("Región")
    eje.set_xlim(0, valores.max() * 1.12)
    eje.bar_label(barras, fmt="%.0f", padding=3)
    eje.grid(axis="x", alpha=0.3)
    figura.tight_layout()
    # Convertir la imagen PNG a texto para enviarla a HTML
    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()

    contexto = {
        "titulo": "Matrícula por región",
        "explicacion": (
            f"Cada barra muestra cuántos alumnos (en miles) estaban matriculados "
            f"en {anio_final} en establecimientos funcionando de cada región. "
            f"La Región Metropolitana concentra cerca del "
            f"{por_region['Metropolitana'] / por_region.sum() * 100:.0f} % de la "
            f"matrícula del país, mientras que Aysén y Magallanes son las de menor "
            f"tamaño. Las barras están ordenadas para comparar fácilmente."
        ),
        "grafico": grafico,
        "alt": "Barras horizontales con la matrícula escolar por región",
    }
    return render(request, "matricula/grafico.html", contexto)


def grafico2(request):
    # Grafico de lineas: evolucion de la matricula por dependencia
    datos = cargar_datos()
    tabla = datos.pivot_table(index="anio", columns="dependencia",
                              values="matricula", aggfunc="sum", fill_value=0)
    publica = (tabla["Municipal"] + tabla["SLEP"]) / 1000

    figura, eje = plt.subplots(figsize=(9, 5))
    for dependencia in ORDEN_DEPENDENCIAS:
        eje.plot(tabla.index, tabla[dependencia] / 1000, marker="o",
                 linewidth=2, color=COLORES[dependencia], label=dependencia)
    eje.plot(tabla.index, publica, marker="s", linewidth=2, linestyle="--",
             color="#333333", label="Pública total (Municipal + SLEP)")
    eje.set_title("Evolución de la matrícula por dependencia, 2019–2025")
    eje.set_xlabel("Año")
    eje.set_ylabel("Alumnos matriculados (miles)")
    eje.set_xticks(tabla.index)
    eje.grid(True, alpha=0.3)
    eje.legend(fontsize=8, loc="center left", bbox_to_anchor=(1, 0.5))
    figura.tight_layout()
    # Convertir la imagen PNG a texto para enviarla a HTML
    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()

    caida_publica = (publica.iloc[-1] - publica.iloc[0]) / publica.iloc[0] * 100
    texto_caida = f"{caida_publica:+.1f} %".replace(".", ",")
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
    # TODO: falta armar la tabla/gráfico
    contexto = {
        "titulo": "Peso de la educación pública vs. variación de la matrícula",
    }
    return render(request, "matricula/seccion.html", contexto)


def grafico4(request):
    # TODO: falta armar la tabla/gráfico
    contexto = {
        "titulo": "Distribución de la matrícula por dependencia",
    }
    return render(request, "matricula/seccion.html", contexto)
