// =============================================================================
// Autor: Mateo Sironi
// Institución: FAMAF - UNC
// Propósito: Extraer las coordenadas (X, Y) de los centroides de n esferas 
//            en un stack de imágenes radiográficas (fantoma cilíndrico). 
//            Utiliza un umbral de binarización definido manualmente por el 
//            usuario sobre una imagen de referencia.
// Entradas:  - Directorio con la secuencia de imágenes en formato .tiff.
//            - Rango de umbral (lower, upper) ingresado interactivamente.
// Salidas:   - Archivo "tabla_centroides.csv" con las coordenadas extraídas.
// =============================================================================

// 1. Selección de directorio y filtrado de archivos .tiff
dir = getDirectory("Seleccione la carpeta con imágenes .tiff");
if (dir == "") {
    exit("No se seleccionó ningún directorio.");
}

list = getFileList(dir);
tifCount = 0;
for (i = 0; i < list.length; i++) {
    if (endsWith(list[i], ".tiff")) {
        tifCount++;
    }
}

tifFiles = newArray(tifCount);
index = 0;
for (i = 0; i < list.length; i++) {
    if (endsWith(list[i], ".tiff")) {
        tifFiles[index] = list[i];
        index++;
    }
}

// 2. Calibración de umbral (usando la penúltima imagen del stack)
penultimaImg = tifFiles[tifFiles.length - 2];
open(dir + penultimaImg);

run("Enhance Contrast", "saturated=0.35");
run("Median...", "radius=2");
run("Threshold...");

waitForUser("Umbral Manual", "Ajuste el umbral utilizando los deslizadores.\nNO presione 'Apply'.\nPresione OK en esta ventana al finalizar.");
getThreshold(lower, upper);

if (lower == -1) {
    exit("No se configuró el umbral correctamente.");
}
close();

// 3. Preparación de variables y encabezado CSV
setBatchMode(true);

imagesToProcess = tifFiles.length - 4;
results = newArray(imagesToProcess + 1);

header = "Imagen";
for (k = 1; k <= 8; k++) {
    header += ",X" + k + ",Y" + k;
}
results[0] = header;
rowIndex = 1;

run("Set Measurements...", "centroid area perimeter bounding redirect=None decimal=3");

// 4. Procesamiento en lote (omitiendo las últimas 4 imágenes)
for (i = 0; i < imagesToProcess; i++) {
    open(dir + tifFiles[i]);

    run("Enhance Contrast", "saturated=0.35");
    run("Median...", "radius=2");
    setThreshold(lower, upper);
    run("Convert to Mask");
    run("Analyze Particles...", "size=1000-Infinity circularity=0.85-1.00 show=Nothing display clear");

    row = tifFiles[i];
    for (j = 0; j < 8; j++) {
        if (j < nResults) {
            x = getResult("X", j);
            y = getResult("Y", j);
            row += "," + x + "," + y;
        } else {
            row += ",NaN,NaN";
        }
    }

    results[rowIndex] = row;
    rowIndex++;
    close();
}

// 5. Exportación de resultados
outputPath = dir + "tabla_centroides.csv";
file = File.open(outputPath);
for (i = 0; i < results.length; i++) {
    print(file, results[i]);
}
File.close(file);

setBatchMode(false);
print("Análisis finalizado. Archivo guardado en: " + outputPath);