# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Ajusta un único perfil de intensidad ESF (Edge Spread Function)
#              con el modelo analítico
#                  ESF(x) = a1·erf(b1·(x - x0)) + a2·arctan(b2·(x - x0)) + c
#              por mínimos cuadrados no lineales, y guarda parámetros,
#              incertidumbres y la curva ajustada.
#              Paso 1 de 2 del análisis de perfil único:
#              ajuste_esf_analitico.py -> lsf_mtf_analitica.py
# Entradas:    data/ESF.csv — primera columna: posición x (mm); segunda
#              columna: intensidad. Ajustar: FILE_PATH, X_PLOT.
# Salidas:     data/ESF_params.csv — parámetros a1, b1, a2, b2, c, x0 y su
#                                      error estándar (raíz de la diagonal de pcov).
#              data/ESF_fit.csv    — curva ajustada sobre un eje x denso.
#              Figura interactiva; en consola: parámetros ± error y R².
# Notas:       x debe estar en mm (no se aplica ninguna conversión).
# =============================================================================

import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.optimize import curve_fit
from scipy.special import erf

# --- Parámetros configurables ------------------------------------------------
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "data", "ESF.csv")
X_PLOT    = (0, 2)    # Rango del eje x del gráfico (mm)
FONT_SIZE = 14
# ----------------------------------------------------------------------------

def esf_model(x, a1, b1, a2, b2, c, x0):
    return a1 * erf(b1 * (x - x0)) + a2 * np.arctan(b2 * (x - x0)) + c

# ===== Load data =====
if not os.path.exists(FILE_PATH):
    raise FileNotFoundError(f"No se encontró {FILE_PATH}. Ver el README de esta carpeta.")

data = pd.read_csv(FILE_PATH, header=0)
x_p = data.iloc[:, 0].values.astype(float)
y   = data.iloc[:, 1].values.astype(float)

x  = x_p  # Posición en mm

# ===== Fit =====
x0_guess = x[np.argmin(np.abs(y - (y.max() + y.min()) / 2))]
p0     = [y.max() / 2, 1.0, y.max() / 4, 1.0, np.mean(y), x0_guess]
bounds = ([-np.inf, 0, -np.inf, 0, -np.inf, x.min()],
          [ np.inf, np.inf,  np.inf, np.inf,  np.inf, x.max()])

popt, pcov = curve_fit(esf_model, x, y, p0=p0, bounds=bounds, maxfev=10000)
perr = np.sqrt(np.diag(pcov))

a1, b1, a2, b2, c, x0 = popt
print("Parámetros ajustados:")
for name, val, err in zip(['a1','b1','a2','b2','c','x0'], popt, perr):
    print(f"  {name} = {val:.6g} ± {err:.6g}")

# Bondad de ajuste
y_pred = esf_model(x, *popt)
ss_res = np.sum((y - y_pred)**2)
ss_tot = np.sum((y - y.mean())**2)
print(f"  R² = {1 - ss_res/ss_tot:.6f}")

# ===== Dense curve =====
x_dense = np.linspace(x[0], x[-1], 2 * len(x))
y_dense = esf_model(x_dense, *popt)

# ===== Plot =====
plt.rcParams.update({'font.size': FONT_SIZE})
plt.figure(figsize=(9, 7))
plt.plot(x, y, 'o', label='Datos originales', alpha=0.8)
plt.plot(x_dense, y_dense, '-', color='red', linewidth=2.5,
         label=r'Ajuste: $a_1\,\mathrm{erf}(b_1(x-x_0)) + a_2\arctan(b_2(x-x_0)) + c$')
plt.xlabel('$x$ (mm)')
plt.ylabel('Intensidad')
plt.xlim(*X_PLOT)
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# ===== Save =====
output_dense = os.path.splitext(FILE_PATH)[0] + '_fit.csv'
pd.DataFrame({'x_fit': x_dense, 'y_fit': y_dense}).to_csv(output_dense, index=False)
print(f"Curva ajustada guardada en: {output_dense}")

# ===== Save parameters =====
output_params = os.path.splitext(FILE_PATH)[0] + '_params.csv'
params_df = pd.DataFrame({
    'parameter': ['a1', 'b1', 'a2', 'b2', 'c', 'x0'],
    'value':     popt,
    'std_error': perr
})
params_df.to_csv(output_params, index=False)
print(f"Parámetros guardados en: {output_params}")
