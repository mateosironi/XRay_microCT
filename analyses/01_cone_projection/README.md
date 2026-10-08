# 01 · Proyección del cono: punto principal y rotación del detector

Determina, con el macro de Fiji `proyeccion_cono.ijm`, la **desalineación del punto principal** (offsets en *u* y *v*) y el **ángulo de rotación del detector**, mediante el análisis geométrico de la proyección del cono del haz de rayos X sobre el detector.

No requiere análisis posterior en Python: el resultado son directamente parámetros geométricos del sistema.

![Parametrización del punto principal del haz y ángulo fuera de plano del detector a partir de la proyección cónica](resultados\imagen2.png)

## Contenido

| Archivo | Descripción |
|---|---|
| `proyeccion_cono.ijm` | Macro de Fiji/ImageJ |
| `data/` | Imagen de entrada de ejemplo |

## Entradas y salidas

| | Descripción |
|---|---|
| **Entrada** | Imagen radiográfica del círculo (proyección del cono del haz), abierta y activa en Fiji |
| **Parámetro** | `BETA_DEG`: semi-ángulo del haz cónico, en grados (variable editable cerca del inicio del macro, línea 14). Debe ajustarse al sistema que se analiza |
| **Salida (imagen)** | Imagen RGB con gráficos superpuestos: ejes de la elipse, punto principal y ángulo de inclinación fuera de plano |
| **Salida (tabla)** | Longitudes `2a` y `2b` de los ejes mayor y menor respectivamente, ángulo `Ang` entre el eje mayor y el eje horizontal, desalineación del punto principal con respecto al centro (`Delta_U`, `Delta_V`), `C_w` y `R` (criterios de circularidad), y `Alfa` (ángulo de rotación del detector, fuera del plano ideal) |

## Cómo usarlo

1. Abrir [Fiji](https://fiji.sc) y abrir la imagen de la proyección del cono que está en `data/`, dejándola activa.
2. Editar `BETA_DEG` en el macro si corresponde.
3. *Plugins ▸ Macros ▸ Run…* y elegir `proyeccion_cono.ijm`.
4. Revisar la imagen RGB superpuesta y la tabla de resultados.

<!-- TODO: indicar el nombre de la imagen de ejemplo de data/ y el valor de BETA_DEG usado en el informe. -->

## Contexto

Es uno de los dos métodos directos de calibración geométrica del trabajo; el otro, basado en un cilindro, está en [`02_cylinder_eta`](../02_cylinder_eta), y el método general con esferas en [`03_sphere_centroids`](../03_sphere_centroids).
