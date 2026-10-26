import pandas as pd

# Este script se corre UNA sola vez pa armar el csv chico que usa la pagina.
# Los csv originales del Mineduc pesan mucho, asi que no van en github:
# hay que bajarlos de datosabiertos.mineduc.cl y dejarlos en la carpeta de abajo.
# Se corre desde la carpeta del proyecto con: python datos/preparar_datos.py
CARPETA = "datos/originales/"
SALIDA = "datos/matricula_comunas.csv"

# de las ~70 columnas que trae cada archivo solo usamos estas
COLUMNAS = ["AGNO", "RBD", "COD_DEPE2", "RURAL_RBD", "COD_REG_RBD",
            "NOM_COM_RBD", "ESTADO_ESTAB", "MAT_TOTAL"]

# los archivos traen codigos, aca los pasamos a nombres que se entiendan
REGIONES = {
    1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 6: "O'Higgins", 7: "Maule", 8: "Biobío",
    9: "Araucanía", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
    13: "Metropolitana", 14: "Los Ríos", 15: "Arica y Parinacota", 16: "Ñuble",
}
DEPENDENCIAS = {
    1: "Municipal", 2: "Particular Subvencionado", 3: "Particular Pagado",
    4: "Corp. Administración Delegada", 5: "SLEP",
}

# leemos un archivo por año, del 2019 al 2025
tablas = []
for anio in range(2019, 2026):
    archivo = CARPETA + "matricula_" + str(anio) + ".csv"
    # ojo: el de 2025 viene separado con coma y los demas con punto y coma
    if anio == 2025:
        separador = ","
    else:
        separador = ";"
    tabla = pd.read_csv(archivo, sep=separador, usecols=COLUMNAS, low_memory=False)
    tablas.append(tabla)
    print("leido", archivo)

# pegamos todos los años en una sola tabla
df = pd.concat(tablas)

# nos quedamos con los colegios funcionando (estado 1) y que tengan alumnos
df = df[df["ESTADO_ESTAB"] == 1]
df = df[df["MAT_TOTAL"] > 0]

# columnas nuevas con nombres mas amigables
df["anio"] = df["AGNO"]
df["region"] = df["COD_REG_RBD"].map(REGIONES)
df["comuna"] = df["NOM_COM_RBD"].str.strip().str.title()  # "PUENTE ALTO " -> "Puente Alto"
df["dependencia"] = df["COD_DEPE2"].map(DEPENDENCIAS)
df["matricula"] = df["MAT_TOTAL"]
df["establecimientos"] = 1  # cada fila es un colegio, asi que al sumar da cuantos colegios hay
df["rurales"] = df["RURAL_RBD"]  # 1 si el colegio es rural, 0 si no

# sumamos todo por año, region, comuna y dependencia
columnas_grupo = ["anio", "region", "comuna", "dependencia"]
columnas_suma = ["matricula", "establecimientos", "rurales"]
resumen = df.groupby(columnas_grupo)[columnas_suma].sum()
resumen = resumen.reset_index()  # pa que anio, region, etc. vuelvan a ser columnas normales

resumen.to_csv(SALIDA, index=False)
print("listo! se guardo", SALIDA, "con", len(resumen), "filas")
