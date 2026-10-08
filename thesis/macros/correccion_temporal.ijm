// =============================================================================
// Autor: Mateo Sironi
// Institución: FAMAF - UNC
// Propósito: Realizar una corrección temporal de la intensidad del haz de rayos
// X sobre un stack de proyecciones. Normaliza la intensidad del fondo de cada
// imagen respecto al valor medio de la última proyección.
// Entradas:  - Directorio con imágenes originales (.tiff).
//            - Directorio de salida para las imágenes corregidas.
//            - Región de Interés (ROI) representativa del fondo, definida
//              manualmente.
// Salidas:   - Lote de proyecciones normalizadas guardadas en disco.
//            - Gráfico comparativo de la intensidad de fondo original vs.
//              corregida.
// =============================================================================

// 1. Selección de directorios y filtrado de imágenes
inputDir = getDirectory("Directorio de entrada");
outputDir = getDirectory("Directorio de salida");
list = getFileList(inputDir);

tifCount = 0;
for (i = 0; i < list.length; i++) {
    if (endsWith(list[i], ".tif") || endsWith(list[i], ".tiff")) {
        tifCount++;
    }
}

if (tifCount == 0) {
    exit("Error: No se encontraron imágenes TIFF en el directorio de entrada.");
}

imgFiles = newArray(tifCount);
index = 0;
for (i = 0; i < list.length; i++) {
    if (endsWith(list[i], ".tif") || endsWith(list[i], ".tiff")) {
        imgFiles[index] = list[i];
        index++;
    }
}
numSlices = imgFiles.length;

// 2. Obtención de la imagen de referencia y definición de ROI
open(inputDir + imgFiles[numSlices - 1]);
origBitDepth = bitDepth();

setTool("rectangle");
waitForUser("Corrección temporal", "Dibuje un ROI en una zona representativa del fondo y presione OK.");
if (selectionType() == -1) {
    exit("Error: No se definió ningún ROI.");
}

Roi.getBounds(rx, ry, rw, rh);
getStatistics(area, lastMean, min, max);
close();

// Inicialización de vectores para el gráfico de control
meanValues_0 = newArray(numSlices);
meanValues_f = newArray(numSlices);
xValues = newArray(numSlices);

// 3. Procesamiento y normalización en lote
setBatchMode(true);

for (i = 0; i < numSlices; i++) {
    showProgress(i + 1, numSlices);
    open(inputDir + imgFiles[i]);
    
    // Medición original
    makeRectangle(rx, ry, rw, rh);
    getStatistics(area, mean_0, min_0, max_0);
    meanValues_0[i] = mean_0;
    xValues[i] = i + 1;

    if (mean_0 > 0) {
        // Corrección de fluctuación
        run("32-bit");
        factor = lastMean / mean_0;
        run("Multiply...", "value=" + factor);
        
        // Retorno a la profundidad original conservando el rango dinámico absoluto
        if (origBitDepth == 16) {
            setMinAndMax(0, 65535);
            run("16-bit");
        } else if (origBitDepth == 8) {
            setMinAndMax(0, 255);
            run("8-bit");
        }
        
        // Medición final
        makeRectangle(rx, ry, rw, rh);
        getStatistics(area, mean_f, min_f, max_f);
        meanValues_f[i] = mean_f;
        
    } else {
        meanValues_f[i] = mean_0; // Prevención de división por cero
    }

    saveAs("Tiff", outputDir + imgFiles[i]);
    close();
}

setBatchMode(false);

// 4. Generación de gráfico de resultados
Plot.create("Variación de intensidad", "N° Imagen", "Intensidad media del fondo", xValues, meanValues_0);
Plot.setStyle(0, "blue,none,2.0,Line");
Plot.add("line", xValues, meanValues_f);
Plot.setStyle(1, "red,none,2.0,Line");
Plot.addLegend("Original\tCorregida");
Plot.show();

showMessage("Listo", "Normalización completada. Resultados guardados en:\n" + outputDir);