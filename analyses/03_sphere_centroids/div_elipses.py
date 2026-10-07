# =============================================================================
# Autor:       Mateo Sironi
# Institución: FAMAF - UNC
# Propósito:   Función auxiliar de fit_elipses.py: coeficiente de determinación (R²) del
#              ajuste de una elipse a una trayectoria, calculado por separado
#              para las ramas creciente y decreciente en u.
# Entradas:    Llamada desde fit_elipses.py (no se ejecuta por sí sola).
# Salidas:     R2_c, R2_d, Sr_c, Sr_d.
# =============================================================================

import numpy as np

def div_puntos(puntos, x0, y0, a, b, c):
    """Divide los puntos de una elipse en ramas creciente/decreciente (según dx)
    y calcula el R² del ajuste en cada rama.

    puntos: array (N, 2) de coordenadas (u, v) en orden de adquisición.
    x0, y0, a, b, c: parámetros de A(x-x0)² + B(y-y0)² + 2C(x-x0)(y-y0) = 1
    (a = A, b = B, c = C).
    Devuelve (R2_c, R2_d, Sr_c, Sr_d).
    """
    N = len(puntos)
    x = puntos[:, 0]

    # Derivada discreta
    dx = np.diff(x, append=x[0])  # append para simular circularidad
    signo_dx = np.sign(dx)

    # Clasificar puntos como crecientes o decrecientes (dx = 0 cuenta como creciente)
    crec = []
    dcrec = []

    for i in range(N):
        if signo_dx[i] >= 0:
            crec.append(puntos[i])
        else:
            dcrec.append(puntos[i])

    crec = np.array(crec)
    dcrec = np.array(dcrec)

    xc = crec[:, 0] - x0
    xd = dcrec[:, 0] - x0
    yc = crec[:, 1] - y0
    yd = dcrec[:, 1] - y0

    # Cálculo de centro de masa y (crec y dcrec)
    yc_0 = np.mean(yc)
    yd_0 = np.mean(yd)

    # Puntos y_c = f_c e y_d = f_d predichos por el ajuste de la elipse
    f_c = (-2*c*xc - np.sqrt(abs(4*(c*xc)**2 - 4*b*(a*xc**2 - 1)))) / (2*b)
    f_d = (-2*c*xd + np.sqrt(abs(4*(c*xd)**2 - 4*b*(a*xd**2 - 1)))) / (2*b)

    # Suma de cuadrados residuales y suma total de cuadrados
    Sr_c = np.sum((-abs(yc) - f_c)**2)
    Sr_d = np.sum((abs(yd) - f_d)**2)

    St_c = np.sum((-abs(yc) - yc_0)**2)
    St_d = np.sum((abs(yd) - yd_0)**2)

    # Cálculo del coeficiente de determinación (R^2) de los ajustes
    R2_c = 1 - Sr_c/St_c
    R2_d = 1 - Sr_d/St_d

    return R2_c, R2_d, Sr_c, Sr_d
