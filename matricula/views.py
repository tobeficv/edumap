import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")  # esto es pa que matplotlib no intente abrir una ventana
import matplotlib.pyplot as plt
import pandas as pd
from django.shortcuts import render

# el csv que armamos con datos/preparar_datos.py (sale de los datos del Mineduc)
RUTA_DATOS = "datos/matricula_comunas.csv"

# las dependencias en el orden en que las mostramos siempre
DEPENDENCIAS = ["Municipal", "SLEP", "Particular Subvencionado",
                "Particular Pagado", "Corp. Administración Delegada"]
# un color pa cada dependencia (mismo orden de arriba)
COLORES = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]


def miles(numero):
    # 3541783 -> "3.541.783" (con punto como se usa en Chile)
    texto = f"{numero:,.0f}"
    return texto.replace(",", ".")


def porcentaje(numero):
    # 12.345 -> "12,3 %" (con coma decimal)
    texto = f"{numero:.1f} %"
    return texto.replace(".", ",")


def index(request):
    datos = pd.read_csv(RUTA_DATOS)
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


def listado1(request):
    # Listado 1: cuantos alumnos hay cada año, separado por dependencia
    datos = pd.read_csv(RUTA_DATOS)
    anios = sorted(datos["anio"].unique())

    filas = []
    total_anterior = 0
    for anio in anios:
        datos_anio = datos[datos["anio"] == anio]

        # sumamos los alumnos de cada dependencia y de paso el total
        valores = []
        total = 0
        for dependencia in DEPENDENCIAS:
            datos_dependencia = datos_anio[datos_anio["dependencia"] == dependencia]
            suma = datos_dependencia["matricula"].sum()
            valores.append(miles(suma))
            total = total + suma

        # el primer año no tiene con quien compararse, por eso va un guion
        if total_anterior == 0:
            variacion = "—"
        else:
            cambio = (total - total_anterior) / total_anterior * 100
            variacion = f"{cambio:+.1f} %"
            variacion = variacion.replace(".", ",")

        filas.append({
            "anio": anio,
            "valores": valores,
            "total": miles(total),
            "variacion": variacion,
        })
        total_anterior = total

    contexto = {"dependencias": DEPENDENCIAS, "filas": filas}
    return render(request, "matricula/listado1.html", contexto)


def listado2(request):
    # Listado 2: las comunas donde mas cayo la matricula publica
    # ojo: "publica" = Municipal + SLEP, porque muchos colegios municipales
    # se pasaron a los SLEP y si miramos solo municipal parece que se vaciaron
    datos = pd.read_csv(RUTA_DATOS)
    anio_inicial = datos["anio"].min()
    anio_final = datos["anio"].max()

    publica = datos[(datos["dependencia"] == "Municipal") | (datos["dependencia"] == "SLEP")]
    inicio = publica[publica["anio"] == anio_inicial]
    fin = publica[publica["anio"] == anio_final]

    # recorremos comuna por comuna y vamos guardando los resultados en una lista
    lista = []
    for comuna in inicio["comuna"].unique():
        datos_comuna = inicio[inicio["comuna"] == comuna]
        alumnos_inicio = datos_comuna["matricula"].sum()
        alumnos_fin = fin[fin["comuna"] == comuna]["matricula"].sum()

        # dejamos fuera las comunas muy chicas (menos de 1000 alumnos publicos)
        # porque ahi cualquier cambio chiquito da un porcentaje gigante
        if alumnos_inicio >= 1000:
            diferencia = alumnos_fin - alumnos_inicio
            variacion = diferencia / alumnos_inicio * 100
            region = datos_comuna["region"].iloc[0]  # la region de la primera fila
            lista.append({
                "comuna": comuna,
                "region": region,
                "inicio": alumnos_inicio,
                "fin": alumnos_fin,
                "diferencia": diferencia,
                "variacion": variacion,
            })

    # pasamos la lista a dataframe pa poder ordenarla facil
    # (de la que mas alumnos perdio a la que menos) y sacamos las 15 primeras
    tabla = pd.DataFrame(lista)
    tabla = tabla.sort_values("diferencia")
    tabla = tabla.head(15)

    filas = []
    posicion = 1
    for i, fila in tabla.iterrows():
        filas.append({
            "posicion": posicion,
            "comuna": fila["comuna"],
            "region": fila["region"],
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
    datos = pd.read_csv(RUTA_DATOS)
    anio_final = datos["anio"].max()
    ultimo = datos[datos["anio"] == anio_final]
    total_pais = ultimo["matricula"].sum()

    # por cada region sumamos alumnos, colegios y colegios rurales
    lista = []
    for region in ultimo["region"].unique():
        datos_region = ultimo[ultimo["region"] == region]
        # y aparte cuantos de esos alumnos van a la publica (Municipal + SLEP)
        publica = datos_region[(datos_region["dependencia"] == "Municipal") | (datos_region["dependencia"] == "SLEP")]
        lista.append({
            "region": region,
            "establecimientos": datos_region["establecimientos"].sum(),
            "rurales": datos_region["rurales"].sum(),
            "matricula": datos_region["matricula"].sum(),
            "publica": publica["matricula"].sum(),
        })

    # de la region con mas alumnos a la con menos
    tabla = pd.DataFrame(lista)
    tabla = tabla.sort_values("matricula", ascending=False)

    filas = []
    for i, fila in tabla.iterrows():
        filas.append({
            "region": fila["region"],
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
    datos = pd.read_csv(RUTA_DATOS)
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
    datos = pd.read_csv(RUTA_DATOS)
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
    datos = pd.read_csv(RUTA_DATOS)
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
    datos = pd.read_csv(RUTA_DATOS)
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
