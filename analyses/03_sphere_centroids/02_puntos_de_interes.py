# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   A partir de los parámetros de cada elipse ajustada, calcula y
#              grafica los cinco puntos de interés (centro y cuatro vértices)
#              de cada trayectoria elíptica.
# Entradas:    resultados/parametros_elipses.csv — salida de fit_elipses.py.
#              Geometría del detector y rutas: config.py. Aquí solo FONT_SIZE
#              y ELIPSE_ETIQUETADA.
# Salidas:     resultados/puntos_de_interes.csv — coordenadas de los 5 puntos y α por
#              esfera (p1, p3: eje menor; p2, p4: eje mayor).
#              resultados/puntos_de_interes.png  — figura con elipses y puntos.
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import ANCHO_PX, ALTO_PX, RESULTS_DIR

# --- Parámetros configurables ------------------------------------------------
CSV_PATH          = os.path.join(RESULTS_DIR, "parametros_elipses.csv")
FONT_SIZE         = 16
ELIPSE_ETIQUETADA = 1   # Número de esfera cuyos puntos se etiquetan (1-indexed). None para omitir.
# ----------------------------------------------------------------------------

# --- Función de puntos de interés --------------------------------------------
def puntos_int(x0, y0, A, B, C, alfa_deg):
    """
    Calcula el centro y los cuatro vértices de la elipse
    A(u-x0)² + B(v-y0)² + 2C(u-x0)(v-y0) = 1,
    usando los autovalores de la matriz cónica y el ángulo α.

    α es el ángulo del EJE MENOR respecto de u (α = ½·atan2(2C, A-B)).
    Devuelve (p0, p1, p2, p3, p4, alfa_rad), con:
        p1, p3: vértices del eje menor (+) y (-)
        p2, p4: vértices del eje mayor (-) y (+)
    (misma numeración que el cambio de variables de calibracion.py).
    """
    alfa = np.radians(alfa_deg)
    M = np.array([[A, C], [C, B]])
    eigvals, _ = np.linalg.eigh(M)

    idx = np.argsort(eigvals)
    semieje_mayor = 1.0 / np.sqrt(eigvals[idx[0]])   # autovalor menor -> semieje mayor
    semieje_menor = 1.0 / np.sqrt(eigvals[idx[1]])   # autovalor mayor -> semieje menor

    R = np.array([[np.cos(alfa), -np.sin(alfa)],
                  [np.sin(alfa),  np.cos(alfa)]])
    v_menor = R @ np.array([semieje_menor, 0.0])     # α apunta sobre el eje menor
    v_mayor = R @ np.array([0.0, semieje_mayor])

    p0 = np.array([x0, y0])
    p1 = p0 + v_menor   # vértice eje menor (+)
    p2 = p0 - v_mayor   # vértice eje mayor (-)
    p3 = p0 - v_menor   # vértice eje menor (-)
    p4 = p0 + v_mayor   # vértice eje mayor (+)

    return p0, p1, p2, p3, p4, alfa

# --- Carga de datos ----------------------------------------------------------
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"No se encontró {CSV_PATH}. Ejecutar antes fit_elipses.py.")
df = pd.read_csv(CSV_PATH, sep=',')

# --- Figura ------------------------------------------------------------------
plt.rcParams.update({'font.size': FONT_SIZE})
cmap = plt.get_cmap('tab10')

fig, ax = plt.subplots(figsize=(10, 8))
ax.set_xlabel("$u$ [px]")
ax.set_ylabel("$v$ [px]")
ax.set_aspect('equal')
ax.set_xlim(0, ANCHO_PX)
ax.set_ylim(0, ALTO_PX)
ax.invert_yaxis()
ax.grid(True)

u_range = np.linspace(0, ANCHO_PX, ANCHO_PX + 1)
v_range = np.linspace(0, ALTO_PX,  ALTO_PX + 1)
U_m, V_m = np.meshgrid(u_range, v_range)

# --- Cálculo y graficación ---------------------------------------------------
registros = []

for _, row in df.iterrows():
    k     = int(row["esfera"]) - 1
    x0    = row["x0 (px)"]
    y0    = row["y0 (px)"]
    A     = row["A"]
    B     = row["B"]
    C     = row["C"]
    alfa  = row["alfa (°)"]
    color = cmap(k % 10)

    p0, p1, p2, p3, p4, alfa_rad = puntos_int(x0, y0, A, B, C, alfa)

    pts = np.array([p0, p1, p2, p3, p4])
    ax.plot(pts[:, 0], pts[:, 1], 'o', color=color, label=f'Esfera {k+1}')

    if ELIPSE_ETIQUETADA is not None and k + 1 == ELIPSE_ETIQUETADA:
        for j, (pu, pv) in enumerate(pts):
            ax.annotate(
                f'$\\vec{{p}}_{{{k+1},{j}}}$',
                xy=(pu, pv),
                xytext=(8, 6),
                textcoords='offset points',
                fontsize=FONT_SIZE - 2,
                color=color,
            )

    Z = A*(U_m - x0)**2 + B*(V_m - y0)**2 + 2*C*(U_m - x0)*(V_m - y0) - 1
    ax.contour(U_m, V_m, Z, levels=[0], colors=[color])

    registros.append({
        "esfera": k + 1,
        "u_0": p0[0], "v_0": p0[1],
        "u_1": p1[0], "v_1": p1[1],   # eje menor (+)
        "u_2": p2[0], "v_2": p2[1],   # eje mayor (-)
        "u_3": p3[0], "v_3": p3[1],   # eje menor (-)
        "u_4": p4[0], "v_4": p4[1],   # eje mayor (+)
        "alfa (°)": np.degrees(alfa_rad),
    })

# --- Guardar resultados ------------------------------------------------------
resultados_dir = RESULTS_DIR
os.makedirs(resultados_dir, exist_ok=True)

csv_out = os.path.join(resultados_dir, "puntos_de_interes.csv")
pd.DataFrame(registros).to_csv(csv_out, index=False)
print(f"Puntos guardados en: {csv_out}")

fig.legend(loc='upper right', fontsize='small')
fig.tight_layout()
fig.savefig(os.path.join(resultados_dir, "puntos_de_interes.png"), dpi=300)
plt.show()