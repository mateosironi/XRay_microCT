# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Suaviza e interpola múltiples perfiles de intensidad ESF
#              (Edge Spread Function) medidos a lo largo de un borde absorbente,
#              mediante un ajuste polinómico local con peso gaussiano evaluado
#              sobre un eje x más denso.
#              Paso 1 de 3 del análisis con múltiples perfiles:
#              suavizado_esf_multiple.py -> mtf_multiple.py
#              -> resolucion_vs_magnificacion.py
# Entradas:    data/edges.csv — salida de perfiles.ijm. Primera columna:
#              posición x; columnas siguientes: un perfil de intensidad cada una.
#              Ajustar: FILE_PATH, CONVERSION_X, DX, M, BORDE_X, COLA, FACTOR,
#                       WINDOW_SIZE, POLY_ORDER, SIGMA.
# Salidas:     data/edges_sm.csv — perfiles suavizados sobre un eje x denso
#              (primera columna: <nombre_x>_fit).
#              Figura interactiva con datos crudos y curvas ajustadas.
# Notas:       - Tras la conversión (CONVERSION_X), x debe estar en mm. Para
#                comparar luego con el modelo de resolucion_vs_magnificacion.py,
#                x debe corresponder al plano del objeto.
#              - Con POLY_ORDER + 1 >= WINDOW_SIZE el polinomio local tiene tantos
#                parámetros como puntos y los interpola exactamente: no filtra
#                ruido (el script lo avisa por consola).
#              - SIGMA está en unidades de x (no en puntos). np.polyfit eleva el
#                peso w al cuadrado, por lo que el ancho gaussiano efectivo del
#                ajuste es SIGMA / sqrt(2).
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- Parámetros configurables ------------------------------------------------
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "data", "edges.csv")

# Conversión del eje x a mm:
#   "ninguna"        : x ya está en mm (opción por defecto)
#   "px_a_mm_objeto" : x_raw [px magnificados] * DX / M
#   "pulgadas_a_mm"  : x_raw * 25.4
CONVERSION_X = "ninguna"
DX = 0.0495             # Tamaño de pixel (mm/px)
M  = 5.2                # Magnificación

# Recorte simétrico alrededor del borde:
#   BORDE_X : posición del borde en las unidades del eje x (ya convertido, mm).
#             Poner None para usar todos los datos sin recortar.
#   COLA    : distancia (mismas unidades) a cada lado del borde.
#             El rango final será [BORDE_X - COLA, BORDE_X + COLA].
BORDE_X    = None       # ej. 1.23
COLA       = None       # ej. 0.5

# Interpolación y ajuste
FACTOR      = 2         # Factor de densificación del eje x de salida
WINDOW_SIZE = 7         # Ventana del ajuste móvil (número de puntos)
POLY_ORDER  = 4         # Orden del polinomio local
SIGMA       = None      # Ancho gaussiano en unidades de x (None → WINDOW_SIZE / 4)

FONT_SIZE   = 18
# ----------------------------------------------------------------------------

# --- Funciones de ajuste -----------------------------------------------------
def gaussian_moving_polyfit(x, y, window_size, poly_order, sigma):
    """
    Ajuste polinómico local de orden `poly_order` con peso gaussiano,
    centrado en cada punto del array x.
    Devuelve la lista de coeficientes locales y el R² ponderado de cada ventana.
    """
    n        = len(x)
    half_win = window_size // 2
    sigma    = sigma if sigma is not None else window_size / 4.0

    coeffs_list = [None] * n
    r2_list     = np.full(n, np.nan)

    for i in range(n):
        x_win = x[max(0, i - half_win) : min(n, i + half_win + 1)]
        y_win = y[max(0, i - half_win) : min(n, i + half_win + 1)]

        if len(x_win) < poly_order + 1:
            continue

        w = np.exp(-0.5 * ((x_win - x[i]) / sigma)**2)
        coeffs = np.polyfit(x_win, y_win, poly_order, w=w)
        coeffs_list[i] = coeffs

        y_pred  = np.polyval(coeffs, x_win)
        y_mean  = np.average(y_win, weights=w)
        ss_tot  = np.sum(w * (y_win - y_mean)**2)
        ss_res  = np.sum(w * (y_win - y_pred)**2)
        r2_list[i] = (1 - ss_res / ss_tot) if ss_tot > 0 else np.nan

    return coeffs_list, r2_list


def evaluate_dense_fit(x_dense, x_orig, coeffs_list, k=5, sigma_interp=None):
    """
    Evalúa el ajuste en un eje x denso interpolando entre los polinomios
    locales de los k vecinos más cercanos, con peso gaussiano.
    """
    sigma_interp = sigma_interp if sigma_interp is not None \
                   else np.median(np.diff(x_orig)) * k / 2.0
    y_dense = np.full_like(x_dense, np.nan)

    for i, xi in enumerate(x_dense):
        dists   = np.abs(x_orig - xi)
        nearest = np.argsort(dists)[:k]
        w       = np.exp(-0.5 * (dists[nearest] / sigma_interp)**2)

        y_vals, w_vals = [], []
        for idx, wi in zip(nearest, w):
            if coeffs_list[idx] is not None:
                y_vals.append(wi * np.polyval(coeffs_list[idx], xi))
                w_vals.append(wi)

        if w_vals and np.sum(w_vals) > 0:
            y_dense[i] = np.sum(y_vals) / np.sum(w_vals)

    return y_dense

# --- Carga, conversión y recorte de datos ------------------------------------
if not os.path.exists(FILE_PATH):
    raise FileNotFoundError(f"No se encontró {FILE_PATH}. Ver el README de esta carpeta.")

data  = pd.read_csv(FILE_PATH, header=0)
x_raw = data.iloc[:, 0].values.astype(float)

if CONVERSION_X == "ninguna":
    x = x_raw
elif CONVERSION_X == "px_a_mm_objeto":
    x = x_raw * (DX / M)
elif CONVERSION_X == "pulgadas_a_mm":
    x = x_raw * 25.4
else:
    raise ValueError(f"CONVERSION_X desconocida: {CONVERSION_X!r}")
print(f"Conversión del eje x: {CONVERSION_X}")

# Recorte simétrico alrededor del borde
if BORDE_X is not None and COLA is not None:
    mascara = (x >= BORDE_X - COLA) & (x <= BORDE_X + COLA)
    x    = x[mascara]
    data = data.iloc[mascara.nonzero()[0], :]
    print(f"Recorte aplicado: [{BORDE_X - COLA:.4f}, {BORDE_X + COLA:.4f}]  "
          f"({mascara.sum()} puntos)")
else:
    print("Sin recorte: se usan todos los puntos.")

# --- Avisos sobre la configuración del ajuste (no modifican el cálculo) ------
paso    = np.median(np.diff(x))
sigma_x = SIGMA if SIGMA is not None else WINDOW_SIZE / 4.0
if POLY_ORDER + 1 >= WINDOW_SIZE:
    print(f"AVISO: POLY_ORDER = {POLY_ORDER} con WINDOW_SIZE = {WINDOW_SIZE}: el polinomio "
          "local interpola exactamente los puntos y no filtra ruido. "
          "Para suavizar, usar WINDOW_SIZE > POLY_ORDER + 1.")
if sigma_x > WINDOW_SIZE * paso:
    print(f"AVISO: SIGMA = {sigma_x:.4g} (unidades de x) supera el ancho de la ventana "
          f"({WINDOW_SIZE * paso:.4g}): los pesos gaussianos quedan casi uniformes. "
          "SIGMA se expresa en unidades de x, no en puntos.")

x_dense  = np.linspace(x[0], x[-1], FACTOR * len(x))
col_x    = data.columns[0]
out_data = {col_x + "_fit": x_dense}

# --- Ajuste e interpolación --------------------------------------------------
plt.rcParams.update({'font.size': FONT_SIZE})
fig, ax = plt.subplots(figsize=(9, 7))

for col_idx in range(1, data.shape[1]):
    col_name = data.columns[col_idx]
    y        = data.iloc[:, col_idx].values.astype(float)

    coeffs_list, _ = gaussian_moving_polyfit(
        x, y, WINDOW_SIZE, POLY_ORDER, SIGMA
    )
    y_dense = evaluate_dense_fit(x_dense, x, coeffs_list)
    out_data[col_name] = y_dense

    line = ax.plot(x, y, 'o', alpha=0.3, markersize=4)[0]
    ax.plot(x_dense, y_dense, '-', color=line.get_color(),
            label=f'Fit {col_name}', linewidth=1.5)

if BORDE_X is not None:
    ax.axvline(BORDE_X, color='gray', linestyle='--', linewidth=1, label='Borde')

ax.set_xlabel('$x$ (mm)')
ax.set_ylabel('$ESF$')
ax.grid(True, alpha=0.5)
# ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
fig.tight_layout()

# --- Guardar -----------------------------------------------------------------
df_out      = pd.DataFrame(out_data)
output_path = os.path.splitext(FILE_PATH)[0] + '_sm.csv'
df_out.to_csv(output_path, index=False)
print(f"Perfiles guardados en: {output_path}")

plt.show()
