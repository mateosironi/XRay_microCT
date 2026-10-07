# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Ajusta elipses por regresión lineal (mínimos cuadrados) a las
#              trayectorias de N esferas metálicas en proyecciones rotacionales,
#              y calcula los coeficientes de determinación R² de cada ajuste.
# Entradas:    data/tabla_centroides.csv — columnas X1,Y1,X2,Y2,...,XN,YN.
#              Módulo div_elipses (función div_puntos).
#              Geometría del detector y rutas: config.py. Aquí solo FONT_SIZE.
# Salidas:     resultados/parametros_elipses.csv — parámetros (x0,y0,A,B,C,α).
#              resultados/grafico_elipses.png    — figura con elipses ajustadas.
#              α: ángulo (°) del eje MENOR de la elipse respecto de u.
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from div_elipses import div_puntos
from config import ANCHO_PX, ALTO_PX, RESULTS_DIR, cargar_centroides

# --- Parámetros configurables ------------------------------------------------
FONT_SIZE = 16
# ----------------------------------------------------------------------------

# --- Función de ajuste de elipse ---------------------------------------------
def fit_ellipse(points):
    """
    Ajusta una elipse A(x-x0)² + B(y-y0)² + 2C(x-x0)(y-y0) = 1
    por mínimos cuadrados. Devuelve (x0, y0, A, B, C).
    """
    x, y = points[:, 0], points[:, 1]

    A_mat = np.column_stack([x**2, -2*x, -2*y, 2*x*y, np.ones_like(x)])
    params, _, _, _ = np.linalg.lstsq(A_mat, -y**2, rcond=None)
    p0, p1, p2, p3, p4 = params

    denom = p0 - p3**2
    x0 = (p1 - p2 * p3) / denom
    y0 = (p0 * p2 - p1 * p3) / denom
    A  = p0 / (p0 * x0**2 + y0**2 + 2 * p3 * x0 * y0 - p4)
    B  = A / p0
    C  = p3 * B

    return x0, y0, A, B, C

# --- Carga de datos ----------------------------------------------------------
df = cargar_centroides()

num_esferas = df.shape[1] // 2

# --- Figura ------------------------------------------------------------------
plt.rcParams.update({'font.size': FONT_SIZE})
cmap = plt.get_cmap('tab10').colors

fig, ax = plt.subplots(figsize=(10, 8))
ax.set_xlabel("$u$ [px]")
ax.set_ylabel("$v$ [px]")
ax.set_aspect('equal')
ax.set_xlim(0, ANCHO_PX)
ax.set_ylim(0, ALTO_PX)
ax.invert_yaxis()
ax.grid(True)

# Malla para contorno de elipses
u_range = np.linspace(0, ANCHO_PX, ANCHO_PX + 1)
v_range = np.linspace(0, ALTO_PX,  ALTO_PX + 1)
U_m, V_m = np.meshgrid(u_range, v_range)

# --- Ajuste por esfera -------------------------------------------------------
parametros = []

for k in range(num_esferas):
    x_col, y_col = df.iloc[:, 2*k], df.iloc[:, 2*k + 1]
    validos = ~(x_col.isna() | y_col.isna())
    x_vals = x_col[validos].astype(float).to_numpy()
    y_vals = y_col[validos].astype(float).to_numpy()
    puntos = np.column_stack((x_vals, y_vals))

    if len(puntos) < 5:
        print(f"Esfera {k+1}: puntos insuficientes ({len(puntos)}), se omite.")
        continue

    color = cmap[k % 10]
    ax.plot(x_vals, y_vals, '.', color=color, label=f'Esfera {k+1}')

    x0, y0, A, B, C = fit_ellipse(puntos)
    R2_c, R2_d, _, _ = div_puntos(puntos, x0, y0, A, B, C)
    alfa = np.degrees(np.arctan2(2*C, A - B) / 2)

    print(f"Esfera {k+1}: R^2_c = {R2_c:.4f},  R^2_d = {R2_d:.4f}")

    parametros.append({
        "esfera": k + 1,
        "x0 (px)": x0, "y0 (px)": y0,
        "A": A, "B": B, "C": C,
        "alfa (°)": alfa,
    })

    Z = A*(U_m - x0)**2 + B*(V_m - y0)**2 + 2*C*(U_m - x0)*(V_m - y0) - 1
    ax.contour(U_m, V_m, Z, levels=[0], colors=[color])

# --- Guardar resultados ------------------------------------------------------
resultados_dir = RESULTS_DIR
os.makedirs(resultados_dir, exist_ok=True)

csv_out = os.path.join(resultados_dir, "parametros_elipses.csv")
pd.DataFrame(parametros).to_csv(csv_out, index=False)
print(f"\nParametros guardados en: {csv_out}")

fig.legend(loc='upper right', fontsize='small')
fig.tight_layout()
fig.savefig(os.path.join(resultados_dir, "grafico_elipses.png"), dpi=300)
plt.show()
