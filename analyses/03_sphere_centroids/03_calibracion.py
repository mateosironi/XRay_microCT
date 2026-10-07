# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Implementa el método de calibración geométrica de múltiples pro-
#              yecciones. A partir de los puntos de interés de cada elipse, realiza
#              un cambio de variables y dos ajustes lineales para determinar:
#              D (distancia foco-detector), V_0 (coordenada v del punto
#              principal), U_0 (coordenada u del punto principal), η (ángulo
#              de inclinación del eje de rotación) y F (distancia foco-objeto).
# Entradas:    resultados/puntos_de_interes.csv — salida de puntos_de_interes.py.
#              Constantes (L_REAL, ERR_L, DU, DV, ANCHO_PX, ALTO_PX, ERR_PX): config.py.
# Salidas:     Impresión en consola de D, V_0, U_0, η y F con incertidumbres.
#              resultados/ajustes_lineales.png — figura con los dos ajustes lineales.
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import (DU, DV, ANCHO_PX, ALTO_PX, L_REAL, ERR_L, ERR_PX, RESULTS_DIR)

# --- Parámetros configurables ------------------------------------------------
CSV_PATH  = os.path.join(RESULTS_DIR, "puntos_de_interes.csv")
FONT_SIZE = 16
# ----------------------------------------------------------------------------

def distancia_mm(u1, u2, v1, v2):
    """Distancia euclídea entre dos puntos en coordenadas de pixel, en mm."""
    return np.sqrt(((u1 - u2) * DU)**2 + ((v1 - v2) * DV)**2)

# --- Carga de datos ----------------------------------------------------------
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"No se encontró {CSV_PATH}. Ejecutar antes puntos_de_interes.py.")
df = pd.read_csv(CSV_PATH, sep=',')
num_elipses = len(df)

# --- Cambio de variables (Yang et al., ec. 5.12) ----------------------------
# Para cada elipse i, se definen:
#   y_i = (v_{i3} + v_{i1}) / 2          (promedio vertical de vértices del eje menor)
#   x_i = sgn(v_{i0} - v_c) * (v_{i3} - v_{i1}) / |p_{i2} - p_{i4}|
#        donde |p_{i2} - p_{i4}| es la longitud del eje mayor en mm.
# El ajuste y_i = D * x_i + V_0 da: pendiente → D, ordenada → V_0.

y_yang   = np.empty(num_elipses)   # y_i [px]
x_yang   = np.empty(num_elipses)   # x_i [adimensional, px/mm]
eje_may  = np.empty(num_elipses)   # |p_{i2} - p_{i4}| [mm]
u_cent   = np.empty(num_elipses)   # u_{i0}: coordenada u del centro [px]
v_cent   = np.empty(num_elipses)   # v_{i0}: coordenada v del centro [px]

for i, row in df.iterrows():
    u0, v0 = row["u_0"], row["v_0"]
    u1, v1 = row["u_1"], row["v_1"]   # vértice eje menor (-)
    u2, v2 = row["u_2"], row["v_2"]   # vértice eje mayor (-)
    u3, v3 = row["u_3"], row["v_3"]   # vértice eje menor (+)
    u4, v4 = row["u_4"], row["v_4"]   # vértice eje mayor (+)

    longitud_mayor = distancia_mm(u2, u4, v2, v4)
    eje_may[i] = longitud_mayor

    y_yang[i] = (v3 + v1) / 2

    # sgn según semiplano vertical del centro respecto al detector
    signo = 1.0 if v0 >= ALTO_PX / 2 else -1.0
    x_yang[i] = signo * (v3 - v1) / longitud_mayor

    u_cent[i] = u0
    v_cent[i] = v0

# --- Ajuste 1: y_i = D * x_i + V_0 (Yang et al., ec. 5.13) -----------------
# Pendiente  → D   [mm]  distancia foco-detector
# Ordenada   → V_0 [px]  coordenada v del punto principal

p1, cov1 = np.polyfit(x_yang, y_yang, 1, cov=True)
D_fit, V_0 = p1
err_D_fit  = np.sqrt(cov1[0, 0])
err_V_0    = np.sqrt(cov1[1, 1])
R2_1 = np.corrcoef(x_yang, y_yang)[0, 1]**2

print("=" * 55)
print("Ajuste 1: y_i = D·x_i + V_0")
print(f"  D   = {D_fit:.4f} ± {err_D_fit:.4f} mm")
print(f"  V_0 = {V_0:.4f} ± {err_V_0:.4f} px,   (Delta V = {ALTO_PX/2 - V_0:.4f} ± {err_V_0:.4f} px)")
print(f"  R²  = {R2_1:.6f}")

# --- Ajuste 2: u_{i0} = a2 + b2 * v_{i0} (Yang et al., ec. 5.14) -----------
# Ordenada + pendiente * V_0 → U_0 [px]  coordenada u del punto principal
# arctan(pendiente)           → η  [°]   inclinación del eje de rotación

p2, cov2 = np.polyfit(v_cent, u_cent, 1, cov=True)
b2, a2 = p2
var_b2, var_a2 = cov2[0, 0], cov2[1, 1]
cov_ab = cov2[0, 1]
err_b2 = np.sqrt(var_b2)
err_a2 = np.sqrt(var_a2)
R2_2 = np.corrcoef(v_cent, u_cent)[0, 1]**2

U_0     = a2 + b2 * V_0
err_U_0 = np.sqrt(var_a2 + V_0**2 * var_b2 + 2*V_0*cov_ab + b2**2 * err_V_0**2)

eta      = np.arctan(b2)
err_eta  = np.degrees(np.abs(1.0 / (1.0 + b2**2)) * err_b2)

print("\nAjuste 2: u_{i0} = a2 + b2·v_{i0}")
print(f"  U_0 = {U_0:.4f} ± {err_U_0:.4f} px    (Delta U = {ANCHO_PX/2 - U_0:.4f} ± {err_U_0:.4f} px)")
print(f"  η   = {np.degrees(eta):.4f} ± {err_eta:.4f} °")
print(f"  R²  = {R2_2:.6f}")

# --- Cálculo de F: distancia foco-objeto (Yang et al., ec. 5.15) ------------
# Usando la primera y la última esfera.

r0 = distancia_mm(u_cent[0], u_cent[-1], v_cent[0], v_cent[-1])   # distancia entre centros
r1 = eje_may[0]    # eje mayor esfera 1
r2 = eje_may[-1]   # eje mayor esfera N

S   = r0**2 + (r1/2)**2 + (r2/2)**2 - (r1 * r2) / 2
F   = (L_REAL * D_fit) / np.sqrt(S)

err_dist = ERR_PX * DU   # incertidumbre en distancias de imagen [mm]

dF_dl  = F / L_REAL
dF_dD  = F / D_fit
dF_dr0 = -(F / (2*S)) * 2*r0
dF_dr1 = -(F / (2*S)) * (r1/2 - r2/2)
dF_dr2 = -(F / (2*S)) * (r2/2 - r1/2)

err_F = np.sqrt(
    (dF_dl  * ERR_L)**2 +
    (dF_dD  * err_D_fit)**2 +
    (dF_dr0 * err_dist)**2 +
    (dF_dr1 * err_dist)**2 +
    (dF_dr2 * err_dist)**2
)

print(f"\n  F   = {F:.4f} ± {err_F:.4f} mm")
print("=" * 55)

# --- Gráficos ----------------------------------------------------------------
plt.rcParams.update({'font.size': FONT_SIZE})

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Ajuste 1
axes[0].scatter(x_yang, y_yang, zorder=3)
axes[0].plot(x_yang, D_fit * x_yang + V_0, color='red',
             label=r'$y_i = D \cdot x_i + V_0$')
axes[0].set_xlabel(r'$x_i$')
axes[0].set_ylabel(r'$y_i$ [px]')
axes[0].legend()
axes[0].grid(True)

# Ajuste 2
axes[1].scatter(v_cent, u_cent, zorder=3)
axes[1].plot(v_cent, a2 + b2 * v_cent, color='red',
             label=r'$u_{i0} = a_2 + b_2 \cdot v_{i0}$')
axes[1].set_xlabel(r'$v_{i0}$ [px]')
axes[1].set_ylabel(r'$u_{i0}$ [px]')
axes[1].legend()
axes[1].grid(True)

fig.tight_layout()
os.makedirs(RESULTS_DIR, exist_ok=True)
fig.savefig(os.path.join(RESULTS_DIR, "ajustes_lineales.png"), dpi=150)
plt.show()