# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Grafica la resolución espacial medida, RE = 1/(2·k_c) (k_c: frecuencia
#              donde MTF = 10 %), en función de la magnificación M, junto con:
#                (a) la resolución analítica esperada para dos tamaños de foco s,
#                        RE(M) = sqrt( ((p + c)/M)² + (s·(M-1)/M)² )   con c = 0;
#                (b) el ajuste de los datos marcados con "usar_en_ajuste" a ese
#                    mismo modelo, con c libre y s = S_AJUSTE fijo.
#              p es el tamaño de pixel; c es una corrección (mm) al tamaño de pixel
#              nominal: el modelo solo depende de p + c ("pixel efectivo").
#              Paso 3 de 3 del análisis con múltiples perfiles:
#              suavizado_esf_multiple.py -> mtf_multiple.py
#              -> resolucion_vs_magnificacion.py
# Entradas:    Lista MEDICIONES, editada por el usuario: una entrada por conjunto
#              de datos (p. ej. por alineación), con listas de igual longitud
#              M, k_c y dk_c (k_c ± incertidumbre, en lp/mm, obtenidos con
#              mtf_multiple.py). El número de magnificaciones es libre.
#              Ajustar además: PIXEL_MM, S1, S2, S_AJUSTE, AJUSTE_PONDERADO.
# Salidas:     resultados/resolucion_vs_magnificacion.png y figura interactiva.
#              resultados/ajuste_resolucion.csv — c, su error, p + c, χ² reducido, R².
#              Consola: resumen del ajuste.
# Notas:       - k_c debe corresponder al plano del objeto, igual que el modelo.
#              - Se necesitan al menos 2 puntos en el ajuste. Con AJUSTE_PONDERADO
#                los pesos son 1/dRE y el error de c se escala con el χ² reducido
#                (absolute_sigma=False), de modo que no subestima el error si el
#                modelo no reproduce los datos dentro de sus incertidumbres.
#              - c está acotado a p + c > 0 (el modelo es simétrico en p + c).
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# --- Parámetros configurables ------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "resultados")

PIXEL_MM = 0.0495    # Tamaño de pixel del detector p (mm)
S1 = 0.005           # Tamaño de foco 1 (mm), curva de referencia con c = 0
S2 = 0.007           # Tamaño de foco 2 (mm), curva de referencia con c = 0
S_AJUSTE = 0.007     # Tamaño de foco fijo en el ajuste (mm)
AJUSTE_PONDERADO = True   # True: pesos 1/dRE; False: mínimos cuadrados simples

# Mediciones: agregar, quitar o editar entradas y valores. M, k_c y dk_c deben
# tener la misma longitud dentro de cada entrada. k_c y dk_c en lp/mm.
MEDICIONES = [
    {
        "nombre": "1.ª alineación", "color": "red", "usar_en_ajuste": True,
        "M":    [2.42, 2.8, 3.32, 4.08, 5.3],
        "k_c":  [16.2, 18.8, 21.3, 25.1, 30.9],
        "dk_c": [0.1, 0.08, 0.1, 0.2, 0.5],
    },
    {
        "nombre": "2.ª alineación", "color": "blue", "usar_en_ajuste": True,
        "M":    [1.78, 2.41, 2.82, 3.32, 4.10, 4.73, 6.86],
        "k_c":  [11.5, 15.2, 17.2, 22.2, 24.5, 27.2, 36.3],
        "dk_c": [0.2, 0.1, 0.5, 0.3, 0.2, 0.5, 0.6],
        # Valores alternativos (versión previa):
        # "k_c":  [11.5, 14.7, 16.7, 18.8, 23.3, 25.4, 34.1],
        # "dk_c": [0.2, 0.1, 0.5, 0.5, 0.2, 0.4, 0.6],
    },
]
# ----------------------------------------------------------------------------

# Función analítica de la resolución espacial
def resolucion_analitica(s, M, p, c=0.0):
    """RE(M) = sqrt(((p + c)/M)² + (s(M-1)/M)²): suma en cuadratura del pixel
    efectivo proyectado al plano del objeto y de la penumbra geométrica del foco.
    Con c = 0 es el modelo con el tamaño de pixel nominal."""
    Sum1 = (p + c)/M
    Sum2 = s*(M-1)/M
    return np.sqrt(Sum1**2 + Sum2**2)

# --- Preparación de las mediciones -------------------------------------------
for med in MEDICIONES:
    for clave in ("M", "k_c", "dk_c"):
        med[clave] = np.asarray(med[clave], dtype=float)
    if not (len(med["M"]) == len(med["k_c"]) == len(med["dk_c"])):
        raise ValueError(f"'{med['nombre']}': M, k_c y dk_c deben tener la misma longitud.")
    # Resolución medida y propagación de incertidumbre
    med["res"]   = 1/(2*med["k_c"])                   # valor principal de la resolución
    med["d_res"] = med["dk_c"]/(2*med["k_c"]**2)      # incertidumbre de la resolución

M_dense = np.linspace(1, 7, 60)
res_s1 = resolucion_analitica(S1, M_dense, PIXEL_MM)
res_s2 = resolucion_analitica(S2, M_dense, PIXEL_MM)

# --- Ajuste de c --------------------------------------------------------------
usados = [m for m in MEDICIONES if m["usar_en_ajuste"]]
if not usados:
    raise ValueError("Ninguna entrada de MEDICIONES tiene usar_en_ajuste = True.")
M_aj   = np.concatenate([m["M"] for m in usados])
res_aj = np.concatenate([m["res"] for m in usados])
dres_aj = np.concatenate([m["d_res"] for m in usados])
n_aj = len(M_aj)
if n_aj < 2:
    raise ValueError("El ajuste necesita al menos 2 puntos.")
if AJUSTE_PONDERADO and np.any(dres_aj <= 0):
    raise ValueError("Con AJUSTE_PONDERADO todas las incertidumbres dk_c deben ser > 0.")

def modelo_ajuste(M, c):
    return resolucion_analitica(S_AJUSTE, M, PIXEL_MM, c)

popt, pcov = curve_fit(
    modelo_ajuste, M_aj, res_aj, p0=[0.0],
    sigma=dres_aj if AJUSTE_PONDERADO else None, absolute_sigma=False,
    bounds=(-PIXEL_MM, np.inf),
)
c_fit, c_err = popt[0], np.sqrt(pcov[0, 0])

residuos = res_aj - modelo_ajuste(M_aj, c_fit)
gl       = n_aj - 1
chi2_red = (np.sum((residuos/dres_aj)**2) / gl) if AJUSTE_PONDERADO else np.nan
R2       = 1 - np.sum(residuos**2) / np.sum((res_aj - res_aj.mean())**2)

print("=" * 60)
print("AJUSTE: RE(M) = sqrt(((p + c)/M)² + (s·(M-1)/M)²)")
print(f"  p = {PIXEL_MM} mm (fijo),  s = {S_AJUSTE} mm (fijo)")
print(f"  Datos ajustados: {', '.join(m['nombre'] for m in usados)}  (n = {n_aj})")
print(f"  c     = {c_fit:.5f} ± {c_err:.5f} mm")
print(f"  p + c = {PIXEL_MM + c_fit:.5f} mm   ({(PIXEL_MM + c_fit)/PIXEL_MM:.2f} × p)")
if AJUSTE_PONDERADO:
    print(f"  χ²_red = {chi2_red:.2f}  ({gl} grados de libertad)")
print(f"  R²    = {R2:.5f}")
print("=" * 60)

os.makedirs(OUTPUT_DIR, exist_ok=True)
pd.DataFrame([{
    "c_mm": c_fit, "c_err_mm": c_err, "p_mm": PIXEL_MM,
    "p_mas_c_mm": PIXEL_MM + c_fit, "s_mm": S_AJUSTE, "n_puntos": n_aj,
    "ponderado": AJUSTE_PONDERADO, "chi2_reducido": chi2_red, "R2": R2,
    "datos_ajustados": "; ".join(m["nombre"] for m in usados),
}]).to_csv(os.path.join(OUTPUT_DIR, "ajuste_resolucion.csv"), index=False)

# --- Gráfico -----------------------------------------------------------------
plt.figure(figsize=(9,7))
for med in MEDICIONES:
    usada = med["usar_en_ajuste"]
    plt.errorbar(med["M"], med["res"], yerr=med["d_res"], fmt='o',
                 label=med["nombre"] + (" (usada en el ajuste)" if usada else ""),
                 color=med["color"], ecolor=med["color"], alpha=0.7, capsize=4,
                 elinewidth=1.5, markersize=6, zorder=5,
                 markerfacecolor=med["color"] if usada else 'none')
plt.plot(M_dense, res_s1, '-', label=f'$s_1$ = {S1} mm', color='green', linewidth=2.5)
plt.plot(M_dense, res_s2, '-', label=f'$s_2$ = {S2} mm', color='orange', linewidth=2.5)
plt.plot(M_dense, modelo_ajuste(M_dense, c_fit), '--', color='purple', linewidth=2.5, zorder=4,
         label=f'Ajuste ($s$ = {S_AJUSTE} mm): $c$ = {c_fit:.4f} ± {c_err:.4f} mm')
plt.xlabel('$M$')
plt.ylabel('Resolución Espacial (mm)')
plt.locator_params(axis='y', nbins=10)
plt.xlim(1,7)
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(os.path.join(OUTPUT_DIR, "resolucion_vs_magnificacion.png"), dpi=300)
plt.show()
