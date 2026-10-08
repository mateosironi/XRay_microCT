# 04 · Resolución espacial y MTF

Mide la **resolución espacial** del sistema a partir de perfiles de intensidad a través de un borde absorbente, y estudia cómo cambia con la **magnificación** *M*.

![Resolución espacial en función de la magnificación](resultados/resolucion_vs_magnificacion.png)

## Fundamento

Para cada perfil a través del borde:

1. **ESF** (*edge spread function*): el perfil de intensidad medido.
2. **LSF** (*line spread function*): la derivada de la ESF.
3. **MTF**: módulo de la transformada de Fourier de la LSF, normalizado en frecuencia cero.
4. **Resolución espacial**: se toma la frecuencia $k_c$ donde la MTF cae al 10 %, y $RE = 1/(2k_c)$.

Se aplica con **dos métodos análogos**: uno numérico, con múltiples perfiles, y otro analítico, con un único perfil ajustado.

## Obtención de los perfiles (macros de Fiji)

| Macro | Qué hace |
|---|---|
| `perfiles.ijm` | Extrae perfiles de intensidad perpendiculares a un borde definido manualmente por el usuario, en cada imagen de un stack (rectángulos pequeños distribuidos a lo largo del borde, de longitud y grosor prestablecidos). Genera un `.csv` con la intensidad en función de una misma variable *x* |
| `cortes_radiales.ijm` | Opcional. Genera un conjunto de cortes radiales (*substack*) a partir de una reconstrucción axial, identificando automáticamente el centro del objeto por análisis de partículas, con *n* muestreos angulares equidistantes. Sirve para obtener las imágenes con borde desde una tomografía |

`edge_sample_image.tif` es una imagen de ejemplo con un borde para probar `perfiles.ijm`.

## Método A · Múltiples perfiles (`multiples_perfiles/`)

| Paso | Script | Qué hace | Entrada → salida |
|---|---|---|---|
| 1 | `suavizado_esf_multiple.py` | Suaviza e interpola cada ESF con un ajuste polinómico local de peso gaussiano, sobre un eje *x* más denso | `data/edges.csv` → `data/edges_sm.csv` |
| 2 | `mtf_multiple.py` | LSF por derivada numérica, MTF con ventana de Hamming, MTF promedio y resolución espacial ($k_c$ y *RE* con su error estándar) | `data/edges_sm.csv` → `resultados/` (`lsf.csv`, `mtf.csv`, `resumen_resolucion.csv` y figuras) |
| 3 | `resolucion_vs_magnificacion.py` | Resolución en función de *M* y ajuste al modelo de abajo | valores de $k_c$ editados en el script → `resultados/` de esta carpeta |

Cada ejecución de los pasos 1 y 2 corresponde a **una magnificación**. Los $k_c$ de cada una se vuelcan en la lista `MEDICIONES` del paso 3, que puede tener cualquier número de magnificaciones.

## Método B · Perfil único analítico (`perfil_unico_analitico/`)

| Paso | Script | Qué hace | Entrada → salida |
|---|---|---|---|
| 1 | `ajuste_esf_analitico.py` | Ajusta un único perfil al modelo $a_1\,\mathrm{erf}(b_1(x-x_0)) + a_2\arctan(b_2(x-x_0)) + c$ | `data/ESF.csv` → `data/ESF_params.csv` y `data/ESF_fit.csv` |
| 2 | `lsf_mtf_analitica.py` | LSF analítica (derivada del modelo), MTF por FFT, $k_c$ y *RE* | `data/ESF_params.csv` → `data/ESF_lsf.csv`, `data/ESF_mtf.csv` y `resultados/lsf_mtf_analitica.png` |

## Resolución frente a la magnificación

`resolucion_vs_magnificacion.py` compara las resoluciones medidas con el modelo

$$RE(M) = \sqrt{\left(\frac{p + c}{M}\right)^2 + \left(\frac{s\,(M-1)}{M}\right)^2}$$

donde *p* es el tamaño de píxel (0.0495 mm), *s* el tamaño del foco y *c* una corrección al píxel nominal (solo se determina *p + c*). El gráfico muestra:

- dos curvas de referencia con $c = 0$ y $s = 0.005$ mm y $0.007$ mm;
- el **ajuste de *c*** a los puntos marcados con `usar_en_ajuste` en `MEDICIONES`, con $s = 0.007$ mm fijo.

Los resultados del ajuste (*c*, su error, *p + c*, χ² reducido y R²) quedan en `resultados/ajuste_resolucion.csv`.

## Cómo ejecutarlo

```bash
python multiples_perfiles/suavizado_esf_multiple.py
python multiples_perfiles/mtf_multiple.py
python resolucion_vs_magnificacion.py

python perfil_unico_analitico/ajuste_esf_analitico.py
python perfil_unico_analitico/lsf_mtf_analitica.py
```

Cada script tiene sus parámetros editables al inicio, y avisa por consola si la configuración puede afectar al resultado (por ejemplo, si el polinomio local interpola exactamente en vez de suavizar, o si el pico de la LSF no está centrado en la ventana de Hamming).
