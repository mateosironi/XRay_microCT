# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Configuración única, compartida por todos los scripts de este
#              análisis (rutas, geometría del detector, parámetros del fantoma)
#              y carga validada de la tabla de centroides.
# Entradas:    data/tabla_centroides.csv — columnas X1,Y1,X2,Y2,...,XN,YN [px],
#              salida de centroides_esferas.ijm.
# Uso:         Los valores de abajo corresponden al conjunto de datos de ejemplo
#              incluido en el repositorio. Para otra adquisición, modificar
#              ÚNICAMENTE este archivo.
# =============================================================================

import os
import warnings
import pandas as pd

# --- Rutas (relativas a este archivo, no al directorio de ejecución) ---------
ROOT_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(ROOT_DIR, "data")
RESULTS_DIR = os.path.join(ROOT_DIR, "resultados")
CSV_PATH    = os.path.join(DATA_DIR, "tabla_centroides.csv")

# --- Detector ----------------------------------------------------------------
ANCHO_PX = 2940      # eje u [px]
ALTO_PX  = 2304      # eje v [px]
DU       = 0.0495    # tamaño de píxel en u [mm/px]
DV       = 0.0495    # tamaño de píxel en v [mm/px]

# --- Fantoma e incertidumbres ------------------------------------------------
L_REAL   = 28.0      # distancia real entre el centro de la esfera 1 y la última [mm]
ERR_L    = 0.1       # incertidumbre en L_REAL [mm]
ERR_PX   = 0.5       # incertidumbre en distancias de imagen [px]


def cargar_centroides(csv_path=CSV_PATH):
    """Lee la tabla de centroides y devuelve un DataFrame con columnas X1,Y1,...,XN,YN.

    - Descarta cualquier columna que no tenga la forma X<n> o Y<n> (p. ej. la
      columna de índice que agrega ImageJ).
    - Verifica que las columnas estén en el orden X1,Y1,X2,Y2,... que asumen
      los scripts.
    - Avisa si hay coordenadas fuera del detector (señal típica de ANCHO_PX y
      ALTO_PX intercambiados o de una configuración que no corresponde a los datos).
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"No se encontró {csv_path}. Ver el README de esta carpeta "
            "para obtener o generar tabla_centroides.csv."
        )
    df = pd.read_csv(csv_path)
    df = df.filter(regex=r"^[XY]\d+$")

    n = df.shape[1] // 2
    esperadas = [f"{c}{i + 1}" for i in range(n) for c in "XY"]
    if n == 0 or df.shape[1] % 2 != 0 or list(df.columns) != esperadas:
        raise ValueError(
            "Se esperaban las columnas X1,Y1,X2,Y2,...,XN,YN; "
            f"se encontraron: {list(df.columns)}"
        )

    max_u = df.filter(regex=r"^X").max().max()
    max_v = df.filter(regex=r"^Y").max().max()
    if max_u > ANCHO_PX or max_v > ALTO_PX:
        warnings.warn(
            f"Hay coordenadas fuera del detector (u máx = {max_u:.0f}, "
            f"v máx = {max_v:.0f}; ANCHO_PX = {ANCHO_PX}, ALTO_PX = {ALTO_PX}). "
            "Revisar config.py: ¿están intercambiados o no corresponden a estos datos?",
            stacklevel=2,
        )
    return df
