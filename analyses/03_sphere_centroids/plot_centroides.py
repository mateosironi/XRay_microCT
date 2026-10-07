# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Grafica las trayectorias (nube de centroides) de N esferas
#              metálicas a lo largo de su rotación, a partir de coordenadas
#              de pixel extraídas de proyecciones radiográficas.
# Entradas:    data/tabla_centroides.csv — columnas X1,Y1,...,XN,YN (px). Geometría del
#              detector y rutas: config.py. Aquí solo FONT_SIZE y PUNTO_SIZE.
# Salidas:     resultados/trayectorias_centroides.png (si GUARDAR_FIGURA) y figura interactiva.
# =============================================================================

import os
import matplotlib.pyplot as plt
from config import ANCHO_PX, ALTO_PX, RESULTS_DIR, cargar_centroides

# --- Parámetros configurables ------------------------------------------------
FONT_SIZE      = 16
PUNTO_SIZE     = 40
GUARDAR_FIGURA = True
# ----------------------------------------------------------------------------

df = cargar_centroides()
num_esferas = df.shape[1] // 2

cmap = plt.get_cmap('tab10')

plt.rcParams.update({'font.size': FONT_SIZE})
fig, ax = plt.subplots(figsize=(10, 8))

for k in range(num_esferas):
    x, y = df[f"X{k+1}"], df[f"Y{k+1}"]
    validos = ~(x.isna() | y.isna())

    ax.scatter(
        x[validos], y[validos],
        color=cmap(k % 10),
        label=f"Esfera {k+1}",
        s=PUNTO_SIZE,
        alpha=0.7,
        edgecolor='k',
        linewidths=0.5,
    )

ax.set_aspect('equal')
ax.set_xlabel("$u$ [px]")
ax.set_ylabel("$v$ [px]")
ax.set_xlim(0, ANCHO_PX)
ax.set_ylim(0, ALTO_PX)
ax.invert_yaxis()
#ax.legend()
ax.grid(True)
fig.tight_layout()

if GUARDAR_FIGURA:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    fig.savefig(os.path.join(RESULTS_DIR, "trayectorias_centroides.png"), dpi=150)
plt.show()
