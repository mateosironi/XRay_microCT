# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Pipeline unificado de calibración geométrica de micro-CT.
#              Integra: trayectorias de centroides, ajuste de elipses,
#              puntos de interés y calibración (D, V0, U0, η, F).
#              Equivale a ejecutar en secuencia fit_elipses.py,
#              puntos_de_interes.py y calibracion.py.
# Entradas:    data/tabla_centroides.csv  (columnas X1,Y1,...,XN,YN).
#              Geometría del detector, fantoma y rutas: config.py.
# Salidas:     resultados/pipeline_calibracion.png y ventana matplotlib con 4 gráficos
#              (izq.) y resumen de parámetros (der.).
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from config import (ANCHO_PX, ALTO_PX, DU, DV, L_REAL, ERR_L, ERR_PX,
                    RESULTS_DIR, cargar_centroides)

# ── Parámetros configurables ─────────────────────────────────────────────────
FONT_SIZE = 11
STEP      = 6          # submuestreo del meshgrid (solo visual; no afecta cálculos)
ELIPSE_ETIQUETADA = 1  # esfera cuyos vértices se anotan en gráfico de puntos (None para omitir)
# ─────────────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES
# ══════════════════════════════════════════════════════════════════════════════

def fit_ellipse(points):
    """Ajusta A(x-x0)²+B(y-y0)²+2C(x-x0)(y-y0)=1 por mínimos cuadrados."""
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


def div_puntos(puntos, x0, y0, a, b, c):
    """Divide puntos de la elipse en ramas creciente/decreciente y calcula R² por rama."""
    N  = len(puntos)
    x  = puntos[:, 0]
    dx = np.diff(x, append=x[0])
    signo_dx = np.sign(dx)
    crec, dcrec = [], []
    for i in range(N):
        if signo_dx[i] >= 0:
            crec.append(puntos[i])
        elif signo_dx[i] < 0:
            dcrec.append(puntos[i])
    crec  = np.array(crec)
    dcrec = np.array(dcrec)
    xc = crec[:, 0]  - x0;  xd = dcrec[:, 0] - x0
    yc = crec[:, 1]  - y0;  yd = dcrec[:, 1]  - y0
    yc_0 = np.mean(yc);     yd_0 = np.mean(yd)
    f_c = (-2*c*xc - np.sqrt(abs(4*(c*xc)**2 - 4*b*(a*xc**2 - 1)))) / (2*b)
    f_d = (-2*c*xd + np.sqrt(abs(4*(c*xd)**2 - 4*b*(a*xd**2 - 1)))) / (2*b)
    Sr_c = np.sum((-abs(yc) - f_c)**2);  Sr_d = np.sum((abs(yd) - f_d)**2)
    St_c = np.sum((-abs(yc) - yc_0)**2); St_d = np.sum((abs(yd) - yd_0)**2)
    R2_c = 1 - Sr_c/St_c
    R2_d = 1 - Sr_d/St_d
    return R2_c, R2_d, Sr_c, Sr_d


def puntos_int(x0, y0, A, B, C, alfa_deg):
    """Centro y cuatro vértices de la elipse a partir de sus parámetros.

    alfa_deg es el ángulo del EJE MENOR respecto de u. Devuelve
    (p0, p1, p2, p3, p4, alfa_rad), con p1, p3: vértices del eje menor (+, -)
    y p2, p4: vértices del eje mayor (-, +).
    """
    alfa = np.radians(alfa_deg)
    M = np.array([[A, C], [C, B]])
    eigvals, _ = np.linalg.eigh(M)
    idx = np.argsort(eigvals)
    semi_may = 1.0 / np.sqrt(eigvals[idx[0]])   # autovalor menor -> semieje mayor
    semi_min = 1.0 / np.sqrt(eigvals[idx[1]])   # autovalor mayor -> semieje menor
    R = np.array([[np.cos(alfa), -np.sin(alfa)],
                  [np.sin(alfa),  np.cos(alfa)]])
    v_min = R @ np.array([semi_min, 0.0])
    v_may = R @ np.array([0.0, semi_may])
    p0 = np.array([x0, y0])
    return p0, p0+v_min, p0-v_may, p0-v_min, p0+v_may, alfa


def distancia_mm(u1, u2, v1, v2):
    return np.sqrt(((u1-u2)*DU)**2 + ((v1-v2)*DV)**2)


def contorno_elipse(x0, y0, A, B, C, step=STEP):
    """Devuelve (U, V, Z) submuestreados para ax.contour."""
    u = np.arange(0, ANCHO_PX+1, step)
    v = np.arange(0, ALTO_PX+1,  step)
    U, V = np.meshgrid(u, v)
    Z = A*(U-x0)**2 + B*(V-y0)**2 + 2*C*(U-x0)*(V-y0) - 1
    return U, V, Z


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

# 1. Cargar datos (validación y rutas: config.py)
df_raw = cargar_centroides()

num_esferas = df_raw.shape[1] // 2
cmap_colors = plt.get_cmap('tab10').colors

# 2. Ajustar elipses y calcular puntos de interés
elipse_params = []   # (x0, y0, A, B, C, alfa_deg)
r2_elipses    = []   # (R2_c, R2_d) por esfera
puntos_lista  = []   # dict con p0..p4 por esfera
datos_puntos  = []   # para calibración

for k in range(num_esferas):
    xc = df_raw.iloc[:, 2*k]
    yc = df_raw.iloc[:, 2*k+1]
    ok = ~(xc.isna() | yc.isna())
    xs = xc[ok].astype(float).to_numpy()
    ys = yc[ok].astype(float).to_numpy()
    pts = np.column_stack((xs, ys))

    if len(pts) < 5:
        print(f"Esfera {k+1}: puntos insuficientes ({len(pts)}), omitida.")
        continue

    x0, y0, A, B, C = fit_ellipse(pts)
    alfa_deg = np.degrees(np.arctan2(2*C, A - B) / 2)
    R2_c, R2_d, _, _ = div_puntos(pts, x0, y0, A, B, C)

    p0, p1, p2, p3, p4, alfa_rad = puntos_int(x0, y0, A, B, C, alfa_deg)

    elipse_params.append((k, xs, ys, x0, y0, A, B, C, alfa_deg))
    r2_elipses.append((k+1, R2_c, R2_d))
    puntos_lista.append((k, p0, p1, p2, p3, p4, alfa_rad, x0, y0, A, B, C))
    datos_puntos.append({
        "esfera": k+1,
        "u_0": p0[0], "v_0": p0[1],
        "u_1": p1[0], "v_1": p1[1],
        "u_2": p2[0], "v_2": p2[1],
        "u_3": p3[0], "v_3": p3[1],
        "u_4": p4[0], "v_4": p4[1],
    })

df_pts = pd.DataFrame(datos_puntos)
n_el   = len(df_pts)

# 3. Calibración
y_yang  = np.empty(n_el)
x_yang  = np.empty(n_el)
eje_may = np.empty(n_el)
u_cent  = np.empty(n_el)
v_cent  = np.empty(n_el)

for i, row in df_pts.iterrows():
    u0,v0 = row["u_0"], row["v_0"]
    u1,v1 = row["u_1"], row["v_1"]
    u2,v2 = row["u_2"], row["v_2"]
    u3,v3 = row["u_3"], row["v_3"]
    u4,v4 = row["u_4"], row["v_4"]
    lm = distancia_mm(u2, u4, v2, v4)
    eje_may[i] = lm
    y_yang[i]  = (v3 + v1) / 2
    signo = 1.0 if v0 >= ALTO_PX / 2 else -1.0
    x_yang[i]  = signo * (v3 - v1) / lm
    u_cent[i]  = u0
    v_cent[i]  = v0

# Ajuste 1: y = D·x + V0
p1c, cov1 = np.polyfit(x_yang, y_yang, 1, cov=True)
D_fit, V_0 = p1c
err_D  = np.sqrt(cov1[0,0])
err_V0 = np.sqrt(cov1[1,1])
R2_aj1 = np.corrcoef(x_yang, y_yang)[0,1]**2

# Ajuste 2: u0 = a2 + b2·v0
p2c, cov2 = np.polyfit(v_cent, u_cent, 1, cov=True)
b2, a2 = p2c
var_b2, var_a2 = cov2[0,0], cov2[1,1]
cov_ab = cov2[0,1]
err_b2 = np.sqrt(var_b2)
err_a2 = np.sqrt(var_a2)
R2_aj2 = np.corrcoef(v_cent, u_cent)[0,1]**2

U_0     = a2 + b2 * V_0
err_U0  = np.sqrt(var_a2 + V_0**2*var_b2 + 2*V_0*cov_ab + b2**2*err_V0**2)
eta     = np.arctan(b2)
err_eta = np.degrees(np.abs(1.0/(1.0+b2**2)) * err_b2)

# Distancia foco-objeto F
r0  = distancia_mm(u_cent[0], u_cent[-1], v_cent[0], v_cent[-1])
r1, r2 = eje_may[0], eje_may[-1]
S   = r0**2 + (r1/2)**2 + (r2/2)**2 - (r1*r2)/2
F   = (L_REAL * D_fit) / np.sqrt(S)
err_dist = ERR_PX * DU
dF_dl = F/L_REAL; dF_dD = F/D_fit
dF_r0 = -(F/(2*S))*2*r0
dF_r1 = -(F/(2*S))*(r1/2 - r2/2)
dF_r2 = -(F/(2*S))*(r2/2 - r1/2)
err_F = np.sqrt((dF_dl*ERR_L)**2 + (dF_dD*err_D)**2 +
                (dF_r0*err_dist)**2 + (dF_r1*err_dist)**2 + (dF_r2*err_dist)**2)


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA UNIFICADA
# ══════════════════════════════════════════════════════════════════════════════

plt.rcParams.update({'font.size': FONT_SIZE})

fig = plt.figure(figsize=(20, 14))
fig.suptitle("Calibración por múltiples proyecciones", fontsize=13, fontweight='bold', y=0.99)

# GridSpec: columna izq. (plots) | columna der. (texto)
gs_root = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[3, 2], wspace=0.08,
                            left=0.07, right=0.99, top=0.92, bottom=0.08)

gs_left = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=gs_root[0],
                                           hspace=0.38, wspace=0.32)

ax1 = fig.add_subplot(gs_left[0, 0])   # trayectorias centroides
ax2 = fig.add_subplot(gs_left[0, 1])   # puntos de interés
ax3 = fig.add_subplot(gs_left[1, 0])   # ajuste lineal 1
ax4 = fig.add_subplot(gs_left[1, 1])   # ajuste lineal 2

ax_txt = fig.add_subplot(gs_root[1])
ax_txt.axis('off')

# ── Gráfico 1: trayectorias de centroides ────────────────────────────────────
ax1.set_title("Trayectorias de centroides", pad=6)
for k in range(num_esferas):
    xc = df_raw.iloc[:, 2*k]
    yc = df_raw.iloc[:, 2*k+1]
    ok = ~(xc.isna() | yc.isna())
    ax1.scatter(xc[ok], yc[ok], s=12, alpha=0.7, color=cmap_colors[k % 10],
                edgecolors='k', linewidths=0.3, label=f"Esf. {k+1}")
ax1.set_aspect('equal')
ax1.set_xlim(0, ANCHO_PX); ax1.set_ylim(ALTO_PX, 0)   # y invertido
ax1.set_xlabel("$u$ [px]"); ax1.set_ylabel("$v$ [px]")
ax1.legend(fontsize=7, ncol=2, loc='lower right')
ax1.grid(True, linewidth=0.4)

# ── Gráfico 2: puntos de interés ─────────────────────────────────────────────
ax2.set_title("Puntos de interés", pad=6)
for (k, p0, p1, p2, p3, p4, alfa_rad, x0, y0, A, B, C) in puntos_lista:
    color = cmap_colors[k % 10]
    pts = np.array([p0, p1, p2, p3, p4])
    ax2.plot(pts[:, 0], pts[:, 1], 'o', ms=5, color=color, label=f"Esf. {k+1}")
    U, V, Z = contorno_elipse(x0, y0, A, B, C)
    ax2.contour(U, V, Z, levels=[0], colors=[color], linewidths=0.8, alpha=0.6)
    if k + 1 == ELIPSE_ETIQUETADA:
        etiquetas = ['$p_0$','$p_1$','$p_2$','$p_3$','$p_4$']
        for j, (pu, pv) in enumerate(pts):
            ax2.annotate(etiquetas[j], xy=(pu, pv),
                         xytext=(5, 4), textcoords='offset points',
                         fontsize=8, color=color)
ax2.set_aspect('equal')
ax2.set_xlim(0, ANCHO_PX); ax2.set_ylim(ALTO_PX, 0)   # y invertido
ax2.set_xlabel("$u$ [px]"); ax2.set_ylabel("$v$ [px]")
ax2.legend(fontsize=7, ncol=2, loc='lower right')
ax2.grid(True, linewidth=0.4)

# ── Gráfico 3: ajuste lineal 1  (y_i = D·x_i + V0) ──────────────────────────
ax3.set_title(r"Ajuste 1: $y_i = D \cdot x_i + V_0$", pad=6)
x_lin = np.linspace(x_yang.min(), x_yang.max(), 200)
ax3.scatter(x_yang, y_yang, zorder=3, s=30)
ax3.plot(x_lin, D_fit*x_lin + V_0, color='red', lw=1.5)
ax3.set_xlabel(r"$x_i$")
ax3.set_ylabel(r"$y_i$ [px]")
ax3.grid(True, linewidth=0.4)

# ── Gráfico 4: ajuste lineal 2  (u_i0 = a2 + b2·v_i0) ───────────────────────
ax4.set_title(r"Ajuste 2: $u_{i0} = a_2 + b_2 \cdot v_{i0}$", pad=6)
v_lin = np.linspace(v_cent.min(), v_cent.max(), 200)
ax4.scatter(v_cent, u_cent, zorder=3, s=30)
ax4.plot(v_lin, a2 + b2*v_lin, color='red', lw=1.5)
ax4.set_xlabel(r"$v_{i0}$ [px]")
ax4.set_ylabel(r"$u_{i0}$ [px]")
ax4.grid(True, linewidth=0.4)

# ── Panel de texto ────────────────────────────────────────────────────────────
sep  = "─" * 38
dV   = ALTO_PX/2 - V_0
dU   = ANCHO_PX/2 - U_0

lineas = [
    "PARÁMETROS DE CALIBRACIÓN",
    sep,
    f"  D    = {D_fit:>10.4f} ± {err_D:.4f}  mm",
    f"  F    = {F:>10.4f} ± {err_F:.4f}  mm",
    f"  V₀   = {V_0:>10.4f} ± {err_V0:.4f}  px",
    f"  ΔV   = {dV:>+10.4f} ± {err_V0:.4f}  px",
    f"  U₀   = {U_0:>10.4f} ± {err_U0:.4f}  px",
    f"  ΔU   = {dU:>+10.4f} ± {err_U0:.4f}  px",
    f"  η    = {np.degrees(eta):>10.4f} ± {err_eta:.4f}  °",
    "",
    sep,
    "R² — AJUSTES LINEALES",
    sep,
    f"  Ajuste 1 (D, V₀)  R² = {R2_aj1:.6f}",
    f"  Ajuste 2 (U₀, η)  R² = {R2_aj2:.6f}",
    "",
    sep,
    "R² — ELIPSES AJUSTADAS",
    sep,
]
for esf, r2c, r2d in r2_elipses:
    lineas.append(f"  Esfera {esf:>2d}   R² = {(r2c+r2d)/2:.4f}")

texto = "\n".join(lineas)

ax_txt.text(
    0.06, 0.97, texto,
    transform=ax_txt.transAxes,
    fontsize=10.5,
    verticalalignment='top',
    fontfamily='monospace',
    bbox=dict(boxstyle='round,pad=0.7', facecolor='#f4f4f4',
              edgecolor='#aaaaaa', linewidth=1.2),
)

os.makedirs(RESULTS_DIR, exist_ok=True)
plt.savefig(os.path.join(RESULTS_DIR, "pipeline_calibracion.png"), dpi=150,
            bbox_inches='tight')
plt.show()