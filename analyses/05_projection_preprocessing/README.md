# 05 · Preprocesado de proyecciones

Dos macros de Fiji que se usan **en secuencia** para preparar las proyecciones radiográficas. Es un análisis independiente de los anteriores.

| Orden | Macro | Qué hace |
|---|---|---|
| 1 | `01_FFC.ijm` | Corrección de campo plano (*flat-field correction*) sobre un lote de proyecciones, usando stacks de calibración (*darks* y *flats*) para mitigar el ruido del sensor y las inhomogeneidades del haz |
| 2 | `02_correccion_temporal.ijm` | Corrección temporal de la intensidad del haz sobre un stack de proyecciones: normaliza la intensidad del fondo de cada imagen respecto del valor medio de la última proyección |

## Entradas y salidas

| Macro | Entradas | Salidas |
|---|---|---|
| `01_FFC.ijm` | Directorio de entrada (proyecciones crudas) y directorio de salida. Stacks de *Darks* y *Flats* abiertos y activos en Fiji | Lote de proyecciones corregidas en formato `.tiff` (16 bits) |
| `02_correccion_temporal.ijm` | Directorio con las imágenes originales (`.tiff`), que en este flujo es la salida de `01_FFC.ijm`; directorio de salida; una región de interés (ROI) representativa del fondo, definida manualmente | Lote de proyecciones normalizadas guardadas en disco y un gráfico comparativo de la intensidad de fondo original frente a la corregida |

## Datos de ejemplo

```text
data/
├── Darks/          dark1.tif … dark5.tif
├── Flats/          flat1.tif … flat5.tif
└── proyecciones/   ima0.tif … ima13.tif
```

## Cómo usarlo

1. Abrir [Fiji](https://fiji.sc) y cargar los stacks de calibración, por ejemplo con *File ▸ Import ▸ Image Sequence…* sobre `Darks/` y sobre `Flats/`, dejándolos abiertos.
2. Ejecutar `01_FFC.ijm` con *Plugins ▸ Macros ▸ Run…* e indicar el directorio de las proyecciones crudas (`data/proyecciones/`) y un directorio de salida.
3. Ejecutar `02_correccion_temporal.ijm`, indicando como entrada el directorio de salida del paso anterior, un nuevo directorio de salida y, cuando corresponda, la ROI de fondo.
4. Comparar la intensidad de fondo original y corregida en el gráfico que genera el segundo macro.
