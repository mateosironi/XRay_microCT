# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   A partir de los parámetros de la ESF ajustada, calcula la LSF
#              analítica (derivada del modelo erf + arctan) y la MTF (módulo de
#              la FFT de la LSF, normalizado en k = 0). Determina la resolución
#              espacial como la frecuencia k_c donde MTF = MTF_UMBRAL y
#              RE = 1 / (2·k_c).
#              Paso 2 de 2 del análisis de perfil único:
#              ajuste_esf_analitico.py -> lsf_mtf_analitica.py
# Entradas:    data/ESF_params.csv — salida de ajuste_esf_analitico.py.
#              Ajustar: PARAMS_PATH, X_MIN, X_MAX, N_PUNTOS, FREQ_MAX, MTF_UMBRAL.
# Salidas:     data/ESF_lsf.csv y data/ESF_mtf.csv.
#              resultados/lsf_mtf_analitica.png y figura interactiva (LSF y MTF).
#              Consola: k_c y RE.
# Notas:       - LSF(x) = |a1·(2·b1/√π)·exp(-b1²(x-x0)²) + a2·b2/(1 + b2²(x-x0)²)|.
#              - [X_MIN, X_MAX] fija la resolución en frecuencia (Δk = 1/(X_MAX-X_MIN))
#                y trunca las colas de la LSF (la componente arctan decae como
#                1/x²): debe contener el borde, x0, con margen a ambos lados.
#              - No se aplica ventana: es el equivalente analítico de
#                mtf_multiple.py (que usa derivada numérica y ventana de Hamming).
# =============================================================================

import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# --- Parámetros configurables ------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PARAMS_PATH = os.path.join(BASE_DIR, "data", "ESF_params.csv")
OUTPUT_DIR  = os.path.join(BASE_DIR, "resultados")

X_MIN, X_MAX = 0.0, 2.0   # Intervalo de evaluación (mm)
N_PUNTOS     = 1000
FREQ_MAX     = 40         # Límite del eje x en el gráfico de MTF (lp/mm)
MTF_UMBRAL   = 0.1        # Umbral de resolución espacial (fracción)
FONT_SIZE    = 14
# ----------------------------------------------------------------------------

def frecuencia_corte(freq, mtf, umbral):
    """Primer cruce descendente de la MTF por `umbral`, con interpolación lineal
    (misma lógica que mtf_multiple.py). Devuelve None si no hay cruce."""
    cruces = np.where(np.diff(np.sign(mtf - umbral)) < 0)[0]
    if len(cruces) == 0:
        return None
    idx = cruces[0]
    return freq[idx] + (umbral - mtf[idx]) * (freq[idx+1] - freq[idx]) / (mtf[idx+1] - mtf[idx])

# ===== Load parameters =====
if not os.path.exists(PARAMS_PATH):
    raise FileNotFoundError(f"No se encontró {PARAMS_PATH}. Ejecutar antes ajuste_esf_analitico.py.")

params = pd.read_csv(PARAMS_PATH).set_index('parameter')['value']
a1, b1, a2, b2, c, x0 = params[['a1', 'b1', 'a2', 'b2', 'c', 'x0']]

if not (X_MIN < x0 < X_MAX):
    print(f"AVISO: x0 = {x0:.4g} mm queda fuera de [{X_MIN}, {X_MAX}] mm; ajustar X_MIN y X_MAX.")

# ===== Derivative (LSF) =====
def lsf_model(x, a1, b1, a2, b2, x0):
    term1 = (2 * a1 * b1 / np.sqrt(np.pi)) * np.exp(-b1**2 * (x - x0)**2)
    term2 = (a2 * b2) / (1 + b2**2 * (x - x0)**2)
    return abs(term1 + term2)

# ===== Evaluate =====
x_dense = np.linspace(X_MIN, X_MAX, N_PUNTOS)
dx      = x_dense[1] - x_dense[0]
y_lsf   = lsf_model(x_dense, a1, b1, a2, b2, x0)

# ===== MTF =====
fft_vals = np.fft.fft(y_lsf)
mtf      = np.abs(fft_vals)
mtf      = mtf / mtf[0]                  # Normalizar al valor DC (frecuencia 0)
freqs    = np.fft.fftfreq(len(x_dense), d=dx)

# Solo frecuencias positivas
pos      = freqs > 0
freqs    = freqs[pos]
mtf      = mtf[pos]

# ===== Resolución espacial =====
kc = frecuencia_corte(freqs, mtf, MTF_UMBRAL)
if kc is not None:
    print(f"k_c (MTF = {MTF_UMBRAL:.0%}) = {kc:.3f} lp/mm   |   RE = 1/(2·k_c) = {1000/(2*kc):.2f} µm")
else:
    print(f"Advertencia: la MTF no cae por debajo de {MTF_UMBRAL}.")

# ===== Plot LSF =====
plt.rcParams.update({'font.size': FONT_SIZE})
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

axes[0].plot(x_dense, y_lsf, '-', color='blue', linewidth=2.5, label=r"$LSF(x)$")
axes[0].set_xlabel('$x$ (mm)')
axes[0].set_ylabel('Intensidad / mm')
axes[0].legend()
axes[0].grid(True)

# ===== Plot MTF =====
axes[1].plot(freqs, mtf, '-', color='red', linewidth=2.5, label='MTF')
axes[1].axhline(y=MTF_UMBRAL, color='gray', linestyle='--', label=f'MTF = {MTF_UMBRAL}')
axes[1].set_xlabel('Frecuencia espacial (mm$^{-1}$)')
axes[1].set_ylabel('MTF')
axes[1].set_xlim(0, FREQ_MAX)
axes[1].set_ylim(0, 1.2)
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
os.makedirs(OUTPUT_DIR, exist_ok=True)
fig.savefig(os.path.join(OUTPUT_DIR, "lsf_mtf_analitica.png"), dpi=150)
plt.show()

# ===== Save =====
lsf_out = PARAMS_PATH.replace('_params.csv', '_lsf.csv')
mtf_out = PARAMS_PATH.replace('_params.csv', '_mtf.csv')
pd.DataFrame({'x': x_dense, 'lsf': y_lsf}).to_csv(lsf_out, index=False)
pd.DataFrame({'freq': freqs, 'mtf': mtf}).to_csv(mtf_out, index=False)
print(f"LSF guardada en: {lsf_out}")
print(f"MTF guardada en: {mtf_out}")
