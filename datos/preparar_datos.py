
import sys
from pathlib import Path

import pandas as pd

CARPETA = Path(sys.argv[1])
SALIDA = Path(__file__).parent / "matricula_comunas.csv"

ARCHIVOS = {
    2019: ("matricula_2019.csv", ";"),
    2020: ("matricula_2020.csv", ";"),
    2021: ("matricula_2021.csv", ";"),
    2022: ("matricula_2022.csv", ";"),
    2023: ("matricula_2023.csv", ";"),
    2024: ("matricula_2024.csv", ";"),
    2025: ("matricula_2025.csv", ","),
}
COLUMNAS = ["AGNO", "RBD", "COD_DEPE2", "RURAL_RBD", "COD_REG_RBD",
            "NOM_COM_RBD", "ESTADO_ESTAB", "MAT_TOTAL"]

MAPA_REGION = {
    1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 6: "O'Higgins", 7: "Maule", 8: "Biobío",
    9: "Araucanía", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
    13: "Metropolitana", 14: "Los Ríos", 15: "Arica y Parinacota", 16: "Ñuble",
}
MAPA_DEPENDENCIA = {
    1: "Municipal", 2: "Particular Subvencionado", 3: "Particular Pagado",
    4: "Corp. Administración Delegada", 5: "SLEP",
}

tablas = []
for anio, (nombre, sep) in ARCHIVOS.items():
    tabla = pd.read_csv(CARPETA / nombre, sep=sep, encoding="utf-8",
                        usecols=COLUMNAS, low_memory=False)
    tablas.append(tabla)
df = pd.concat(tablas, ignore_index=True)

df = df[(df["ESTADO_ESTAB"] == 1) & (df["MAT_TOTAL"] > 0)].copy()
df["comuna"] = df["NOM_COM_RBD"].str.strip().str.title()
df["region"] = df["COD_REG_RBD"].map(MAPA_REGION)
df["dependencia"] = df["COD_DEPE2"].map(MAPA_DEPENDENCIA)

resumen = (df.groupby(["AGNO", "region", "comuna", "dependencia"])
             .agg(matricula=("MAT_TOTAL", "sum"),
                  establecimientos=("RBD", "nunique"),
                  rurales=("RURAL_RBD", "sum"))
             .reset_index()
             .rename(columns={"AGNO": "anio"}))
resumen.to_csv(SALIDA, index=False, encoding="utf-8")
print(f"Guardado {SALIDA} con {len(resumen)} filas")
print(resumen.groupby("anio")[["matricula", "establecimientos"]].sum())
