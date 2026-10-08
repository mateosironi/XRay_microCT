# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   A partir de perfiles ESF suavizados, calcula la LSF (derivada
#              numérica), la MTF (transformada de Fourier de la LSF con ventana
#              de Hamming), la MTF promedio y la resolución espacial: frecuencia
#              de corte k_c donde MTF = MTF_UMBRAL (10 %) y RE = 1 / (2·k_c).
#              Paso 2 de 3 del análisis con múltiples perfiles:
#              suavizado_esf_multiple.py -> mtf_multiple.py
#              -> resolucion_vs_magnificacion.py
# Entradas:    data/edges_sm.csv — salida de suavizado_esf_multiple.py.
#              Ajustar: FILE_PATH, MAGNIFICACION, FREQ_MAX, MTF_UMBRAL,
#                       EXPORTAR_CSV.
# Salidas:     Consola: k_c medio ± error estándar de la media (SEM), desviación
#              estándar y RE ± SEM.
#              Dos figuras interactivas: LSF y MTF (con promedio).
#              Si EXPORTAR_CSV: resultados/lsf.csv, resultados/mtf.csv y
#              resultados/resumen_resolucion.csv (una fila por ejecución; sus
#              k_c y SEM son los valores que se vuelcan a
#              resolucion_vs_magnificacion.py).
# Notas:       - k_c se obtiene por interpolación lineal en el primer cruce
#                descendente de la MTF por el umbral; RE = 1/(2·k_c) en mm.
#              - x debe estar en mm; k_c queda en lp/mm del mismo plano que x.
#              - La ventana de Hamming abarca todo el rango de x: el pico de la
#                LSF debería estar cerca del centro (usar BORDE_X y COLA en
#                suavizado_esf_multiple.py). El script avisa si no es así.
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- Parámetros configurables ------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
FILE_PATH  = os.path.join(BASE_DIR, "data", "edges_sm.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "resultados")

MAGNIFICACION = None   # opcional: se registra en resumen_resolucion.csv
FREQ_MAX      = 40     # Límite del eje x en el gráfico de MTF (lp/mm)
MTF_UMBRAL    = 0.1    # Umbral de resolución espacial (fracción, típico: 0.1)
EXPORTAR_CSV  = True

FONT_SIZE  = 18
# ----------------------------------------------------------------------------

def frecuencia_corte(freq, mtf, umbral):
    """Primer cruce descendente de la MTF por `umbral`, con interpolación lineal.
    Devuelve None si la MTF no cae por debajo del umbral."""
    cruces = np.where(np.diff(np.sign(mtf - umbral)) < 0)[0]
    if len(cruces) == 0:
        return None
    idx = cruces[0]
    return freq[idx] + (umbral - mtf[idx]) * (freq[idx+1] - freq[idx]) / (mtf[idx+1] - mtf[idx])

# --- Carga de datos ----------------------------------------------------------
if not os.path.exists(FILE_PATH):
    raise FileNotFoundError(f"No se encontró {FILE_PATH}. Ejecutar antes suavizado_esf_multiple.py.")

data = pd.read_csv(FILE_PATH, header=0)
x    = data.iloc[:, 0].values.astype(float)
dx   = np.mean(np.diff(x))   # espaciado uniforme asumido
n    = len(x)

# Eje de frecuencias (compartido por todas las MTF)
freq          = np.fft.fftfreq(n, d=dx)
positivo      = freq >= 0
freq          = freq[positivo]

# --- Estructuras de salida ---------------------------------------------------
lsf_data = {data.columns[0]: x}
mtf_data = {"frec": freq}
mtf_list = []
kc_list  = []
desvio_pico = []   # posición del pico de la LSF respecto del centro de la ventana

# --- Figuras -----------------------------------------------------------------
plt.rcParams.update({'font.size': FONT_SIZE})
fig_lsf, ax_lsf = plt.subplots(figsize=(9, 7))
fig_mtf, ax_mtf = plt.subplots(figsize=(9, 7))

# --- Cálculo por perfil ------------------------------------------------------
for col_idx in range(1, data.shape[1]):
    col_name = data.columns[col_idx]
    y        = data.iloc[:, col_idx].values.astype(float)

    # LSF: derivada numérica + ventana de Hamming
    lsf            = np.abs(np.gradient(y, dx))
    lsf_ventana    = lsf * np.hamming(n)
    lsf_data[col_name] = lsf_ventana
    desvio_pico.append((np.argmax(lsf) - (n - 1) / 2) / ((n - 1) / 2))

    # MTF: FFT de la LSF ventaneada, normalizada en k=0
    mtf_full = np.abs(np.fft.fft(lsf_ventana))[positivo]
    mtf      = mtf_full / mtf_full[0] if mtf_full[0] != 0 else mtf_full
    mtf_data[col_name] = mtf
    mtf_list.append(mtf)

    # Frecuencia de corte por interpolación lineal
    kc = frecuencia_corte(freq, mtf, MTF_UMBRAL)
    if kc is not None:
        kc_list.append(kc)
    else:
        print(f"Advertencia: perfil '{col_name}' no cae por debajo de MTF = {MTF_UMBRAL}.")

    # Graficación
    line = ax_lsf.plot(x, lsf_ventana, alpha=0.6, linewidth=1.5)[0]
    ax_mtf.plot(freq, mtf, color=line.get_color(), alpha=0.7, linewidth=1)

# Aviso: pico de la LSF lejos del centro de la ventana de Hamming
if np.max(np.abs(desvio_pico)) > 0.1:
    print(f"AVISO: el pico de la LSF se aleja hasta {100*np.max(np.abs(desvio_pico)):.0f} % "
          "de la semiventana respecto del centro; la ventana de Hamming atenúa el pico "
          "y puede sesgar la MTF. Centrar el recorte en el borde (BORDE_X, COLA).")

# --- MTF promedio ------------------------------------------------------------
mtf_array = np.array(mtf_list)
mtf_mean  = np.mean(mtf_array, axis=0)
mtf_data["MTF_mean"] = mtf_mean
ax_mtf.plot(freq, mtf_mean, color='black', linewidth=3, label='MTF promedio', zorder=10)

# --- Resolución espacial -----------------------------------------------------
resumen = None
if kc_list:
    kc_arr  = np.array(kc_list)
    kc_mean = np.mean(kc_arr)
    kc_std  = np.std(kc_arr, ddof=1) if len(kc_arr) > 1 else np.nan
    kc_sem  = kc_std / np.sqrt(len(kc_arr))
    RE      = 1.0 / (2.0 * kc_mean)   # mm
    RE_sem  = RE * kc_sem / kc_mean   # mm (propagación: dRE = dk / (2 k²))

    print("\n" + "=" * 52)
    print(f"  RESOLUCIÓN ESPACIAL  (MTF = {int(MTF_UMBRAL*100)}%)")
    print("=" * 52)
    print(f"  k_c medio : {kc_mean:.3f} ± {kc_sem:.3f} lp/mm")
    print(f"  Desv. est.: {kc_std:.3f} lp/mm  (n = {len(kc_arr)})")
    print(f"  RE = 1/(2·k_c) = {RE*1000:.2f} ± {RE_sem*1000:.2f} µm")
    print("=" * 52 + "\n")

    resumen = {
        "magnificacion": MAGNIFICACION, "n_perfiles": len(kc_arr),
        "mtf_umbral": MTF_UMBRAL, "kc_medio_lp_mm": kc_mean,
        "kc_sem_lp_mm": kc_sem, "kc_std_lp_mm": kc_std,
        "RE_mm": RE, "RE_sem_mm": RE_sem,
    }

# --- Formato de figuras ------------------------------------------------------
ax_lsf.set_xlabel("$x$ (mm)")
ax_lsf.set_ylabel("LSF")
ax_lsf.grid(True, alpha=0.5)
fig_lsf.tight_layout()

ax_mtf.axhline(MTF_UMBRAL, color='red', linestyle='--',
               label=f'MTF = {int(MTF_UMBRAL*100)}%')
ax_mtf.set_xlabel("$k_x$ (lp/mm)")
ax_mtf.set_ylabel("MTF")
ax_mtf.set_xlim(0, FREQ_MAX)
ax_mtf.grid(True, alpha=0.5)
ax_mtf.legend()
fig_mtf.tight_layout()

# --- Guardar -----------------------------------------------------------------
if EXPORTAR_CSV:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pd.DataFrame(lsf_data).to_csv(os.path.join(OUTPUT_DIR, "lsf.csv"), index=False)
    pd.DataFrame(mtf_data).to_csv(os.path.join(OUTPUT_DIR, "mtf.csv"), index=False)
    if resumen is not None:
        pd.DataFrame([resumen]).to_csv(os.path.join(OUTPUT_DIR, "resumen_resolucion.csv"), index=False)
    fig_lsf.savefig(os.path.join(OUTPUT_DIR, "lsf.png"), dpi=150)
    fig_mtf.savefig(os.path.join(OUTPUT_DIR, "mtf.png"), dpi=150)
    print(f"Resultados guardados en: {OUTPUT_DIR}")

plt.show()
