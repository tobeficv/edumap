import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")  # esto es pa que matplotlib no intente abrir una ventana
import matplotlib.pyplot as plt
import pandas as pd
from django.shortcuts import render

# el csv chico que armamos con datos/preparar_datos.py (sale de los datos del Mineduc)
RUTA_DATOS = "datos/matricula_comunas.csv"

# un color fijo pa cada dependencia, asi todos los graficos se ven parejos
COLORES = {
    "Municipal": "#4C72B0",
    "SLEP": "#DD8452",
    "Particular Subvencionado": "#55A868",
    "Particular Pagado": "#C44E52",
    "Corp. Administración Delegada": "#8172B2",
}
ORDEN_DEPENDENCIAS = list(COLORES.keys())


def cargar_datos():
    # lee el csv y lo devuelve como dataframe
    return pd.read_csv(RUTA_DATOS, encoding="utf-8")


def miles(numero):
    # 3541783 -> "3.541.783" (con punto como se usa en Chile)
    return f"{numero:,.0f}".replace(",", ".")


def porcentaje(numero):
    # 12.345 -> "12,3 %" (con coma decimal)
    texto = f"{numero:.1f} %"
    return texto.replace(".", ",")


def index(request):
    datos = cargar_datos()
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]
    # los numeritos de las tarjetas del inicio
    contexto = {
        "anio_inicial": datos["anio"].min(),
        "anio_final": anio_final,
        "total_alumnos": miles(ultimo["matricula"].sum()),
        "total_establecimientos": miles(ultimo["establecimientos"].sum()),
        "total_comunas": ultimo["comuna"].nunique(),
    }
    return render(request, "matricula/index.html", contexto)


def listado1(request):
    # Listado 1: cuantos alumnos hay cada año, separado por dependencia
    datos = cargar_datos()
    tabla = datos.pivot_table(index="anio", columns="dependencia",
                              values="matricula", aggfunc="sum", fill_value=0)
    tabla = tabla[ORDEN_DEPENDENCIAS]
    tabla["Total"] = tabla.sum(axis=1)

    filas = []
    total_anterior = None
    for anio, fila in tabla.iterrows():
        # el primer año no tiene con quien compararse, por eso va un guion
        if total_anterior is None:
            variacion = "—"
        else:
            cambio = (fila["Total"] - total_anterior) / total_anterior * 100
            variacion = f"{cambio:+.1f} %".replace(".", ",")
        total_anterior = fila["Total"]
        valores = []
        for dependencia in ORDEN_DEPENDENCIAS:
            valores.append(miles(fila[dependencia]))
        filas.append({
            "anio": anio,
            "valores": valores,
            "total": miles(fila["Total"]),
            "variacion": variacion,
        })

    contexto = {"dependencias": ORDEN_DEPENDENCIAS, "filas": filas}
    return render(request, "matricula/listado1.html", contexto)


def listado2(request):
    # Listado 2: las comunas donde mas cayo la matricula publica
    # ojo: "publica" = Municipal + SLEP, porque muchos colegios municipales
    # se pasaron a los SLEP y si miramos solo municipal parece que se vaciaron
    datos = cargar_datos()
    anio_inicial = datos["anio"].min()
    anio_final = datos["anio"].max()

    publica = datos[(datos["dependencia"] == "Municipal") | (datos["dependencia"] == "SLEP")]
    inicio = publica[publica["anio"] == anio_inicial].groupby(["region", "comuna"])["matricula"].sum()
    fin = publica[publica["anio"] == anio_final].groupby(["region", "comuna"])["matricula"].sum()

    # juntamos los dos años en una sola tabla (si una comuna no tiene dato queda en 0)
    tabla = pd.DataFrame({"inicio": inicio, "fin": fin}).fillna(0)
    tabla["diferencia"] = tabla["fin"] - tabla["inicio"]
    tabla["variacion"] = tabla["diferencia"] / tabla["inicio"] * 100

    # dejamos fuera las comunas muy chicas (menos de 1000 alumnos publicos)
    # porque ahi cualquier cambio chiquito da un porcentaje gigante
    tabla = tabla[tabla["inicio"] >= 1000]

    # ordenamos de la que mas alumnos perdio a la que menos y sacamos las 15 primeras
    tabla = tabla.sort_values("diferencia")
    tabla = tabla.head(15)

    filas = []
    posicion = 1
    for (region, comuna), fila in tabla.iterrows():
        filas.append({
            "posicion": posicion,
            "comuna": comuna,
            "region": region,
            "inicio": miles(fila["inicio"]),
            "fin": miles(fila["fin"]),
            "diferencia": miles(fila["diferencia"]),
            "variacion": porcentaje(fila["variacion"]),
        })
        posicion = posicion + 1

    contexto = {
        "titulo": "Comunas con mayor caída de la matrícula pública",
        "anio_inicial": anio_inicial,
        "anio_final": anio_final,
        "filas": filas,
    }
    return render(request, "matricula/listado2.html", contexto)


def listado3(request):
    # Listado 3: foto del ultimo año por region
    datos = cargar_datos()
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]

    # por cada region sumamos alumnos y colegios
    por_region = ultimo.groupby("region")[["matricula", "establecimientos", "rurales"]].sum()

    # y aparte cuantos de esos alumnos estan en la publica (Municipal + SLEP)
    publica = ultimo[(ultimo["dependencia"] == "Municipal") | (ultimo["dependencia"] == "SLEP")]
    publica_region = publica.groupby("region")["matricula"].sum()
    por_region["publica"] = publica_region

    # de la region con mas alumnos a la con menos
    por_region = por_region.sort_values("matricula", ascending=False)
    total_pais = por_region["matricula"].sum()

    filas = []
    for region, fila in por_region.iterrows():
        filas.append({
            "region": region,
            "establecimientos": miles(fila["establecimientos"]),
            "rurales": miles(fila["rurales"]),
            "matricula": miles(fila["matricula"]),
            "parte_pais": porcentaje(fila["matricula"] / total_pais * 100),
            "parte_publica": porcentaje(fila["publica"] / fila["matricula"] * 100),
        })

    contexto = {
        "titulo": "Matrícula por región",
        "anio_final": anio_final,
        "filas": filas,
        "total_pais": miles(total_pais),
    }
    return render(request, "matricula/listado3.html", contexto)


def grafico1(request):
    # Grafico de barras: alumnos por region en el ultimo año
    datos = cargar_datos()
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]
    por_region = ultimo.groupby("region")["matricula"].sum().sort_values()
    valores = por_region.values / 1000  # en miles pa que los numeros no sean eternos

    figura, eje = plt.subplots(figsize=(9, 6))
    barras = eje.barh(por_region.index, valores, color="#4C72B0")
    eje.set_title(f"Matrícula escolar por región, {anio_final}")
    eje.set_xlabel("Alumnos matriculados (miles)")
    eje.set_ylabel("Región")
    eje.set_xlim(0, valores.max() * 1.12)  # un poco de espacio extra pa las etiquetas
    eje.bar_label(barras, fmt="%.0f", padding=3)
    eje.grid(axis="x", alpha=0.3)
    figura.tight_layout()
    # pasamos la imagen a texto (base64) pa poder mandarla al html
    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()

    parte_rm = por_region["Metropolitana"] / por_region.sum() * 100
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
    datos = cargar_datos()
    tabla = datos.pivot_table(index="anio", columns="dependencia",
                              values="matricula", aggfunc="sum", fill_value=0)
    publica = (tabla["Municipal"] + tabla["SLEP"]) / 1000

    figura, eje = plt.subplots(figsize=(9, 5))
    # una linea por dependencia
    for dependencia in ORDEN_DEPENDENCIAS:
        eje.plot(tabla.index, tabla[dependencia] / 1000, marker="o",
                 linewidth=2, color=COLORES[dependencia], label=dependencia)
    # y una extra punteada con la publica completa
    eje.plot(tabla.index, publica, marker="s", linewidth=2, linestyle="--",
             color="#333333", label="Pública total (Municipal + SLEP)")
    eje.set_title("Evolución de la matrícula por dependencia, 2019–2025")
    eje.set_xlabel("Año")
    eje.set_ylabel("Alumnos matriculados (miles)")
    eje.set_xticks(tabla.index)
    eje.grid(True, alpha=0.3)
    eje.legend(fontsize=8, loc="center left", bbox_to_anchor=(1, 0.5))
    figura.tight_layout()
    # pasamos la imagen a texto (base64) pa poder mandarla al html
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
    # Grafico de dispersion: cada puntito es una comuna
    # eje x = que % de sus alumnos iban a la publica al principio
    # eje y = cuanto cambio su matricula total entre el primer y el ultimo año
    # la idea es ver si las comunas mas "publicas" son las que mas alumnos pierden
    datos = cargar_datos()
    anio_inicial = datos["anio"].min()
    anio_final = datos["anio"].max()

    inicio = datos[datos["anio"] == anio_inicial]
    fin = datos[datos["anio"] == anio_final]
    publica_inicio = inicio[(inicio["dependencia"] == "Municipal") | (inicio["dependencia"] == "SLEP")]

    tabla = pd.DataFrame({
        "total_inicio": inicio.groupby("comuna")["matricula"].sum(),
        "total_fin": fin.groupby("comuna")["matricula"].sum(),
        "publica_inicio": publica_inicio.groupby("comuna")["matricula"].sum(),
    }).fillna(0)

    # igual que en el listado 2, sacamos las comunas muy chiquitas
    tabla = tabla[tabla["total_inicio"] >= 1000]

    tabla["peso_publica"] = tabla["publica_inicio"] / tabla["total_inicio"] * 100
    tabla["variacion"] = (tabla["total_fin"] - tabla["total_inicio"]) / tabla["total_inicio"] * 100

    # el tamaño del punto depende de cuantos alumnos tiene la comuna
    tamanos = tabla["total_inicio"] / 400

    figura, eje = plt.subplots(figsize=(9, 6))
    eje.scatter(tabla["peso_publica"], tabla["variacion"], s=tamanos,
                color="#4C72B0", alpha=0.5, edgecolors="white")
    eje.axhline(0, color="#333333", linewidth=1)  # linea del 0: arriba crecio, abajo bajo
    eje.set_title(f"Peso de la educación pública vs. variación de la matrícula por comuna")
    eje.set_xlabel(f"% de alumnos en educación pública en {anio_inicial}")
    eje.set_ylabel(f"Variación de la matrícula total {anio_inicial}–{anio_final} (%)")
    eje.grid(True, alpha=0.3)
    figura.tight_layout()
    # pasamos la imagen a texto (base64) pa poder mandarla al html
    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()

    # la correlacion nos dice si hay relacion (cerca de 0 = casi nada)
    correlacion = tabla["peso_publica"].corr(tabla["variacion"])
    texto_correlacion = f"{correlacion:.2f}".replace(".", ",")
    comunas_bajan = (tabla["variacion"] < 0).sum()

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
            f"hasta {anio_final}. {comunas_bajan} de las {len(tabla)} comunas quedan "
            f"bajo la línea del 0, o sea, perdieron alumnos. La correlación entre "
            f"ambas variables ({texto_correlacion}) {lectura}"
        ),
        "grafico": grafico,
        "alt": "Dispersión de comunas según peso de la educación pública y variación de su matrícula",
    }
    return render(request, "matricula/grafico.html", contexto)


def grafico4(request):
    # Grafico circular: como se reparte la matricula del ultimo año entre dependencias
    datos = cargar_datos()
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]
    por_dependencia = ultimo.groupby("dependencia")["matricula"].sum()
    por_dependencia = por_dependencia[ORDEN_DEPENDENCIAS]  # mismo orden que siempre

    # armamos la lista de colores en el mismo orden
    colores = []
    for dependencia in ORDEN_DEPENDENCIAS:
        colores.append(COLORES[dependencia])

    figura, eje = plt.subplots(figsize=(9, 6))
    eje.pie(por_dependencia.values, colors=colores,
            autopct="%1.1f%%", startangle=90, pctdistance=0.8,
            wedgeprops={"edgecolor": "white"})
    # los nombres van en la leyenda al lado, porque encima de la torta se pisaban
    eje.legend(por_dependencia.index, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9)
    eje.set_title(f"Distribución de la matrícula por dependencia, {anio_final}")
    eje.axis("equal")  # pa que quede redondo y no ovalado
    figura.tight_layout()
    # pasamos la imagen a texto (base64) pa poder mandarla al html
    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()

    total = por_dependencia.sum()
    parte_subvencionado = por_dependencia["Particular Subvencionado"] / total * 100
    parte_publica = (por_dependencia["Municipal"] + por_dependencia["SLEP"]) / total * 100
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
