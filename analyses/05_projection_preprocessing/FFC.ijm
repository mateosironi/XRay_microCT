// =============================================================================
// Autor: Mateo Sironi
// Institución: FAMAF - UNC
// Propósito: Realizar la corrección de campo plano (Flat-Field Correction) 
//            sobre un lote de proyecciones radiográficas, utilizando stacks 
//            de calibración (Darks y Flats) para mitigar el ruido del sensor 
//            y las inhomogeneidades del haz de rayos X.
// Entradas:  - Directorios de entrada (proyecciones crudas) y salida.
//            - Stacks de imágenes "Darks" y "Flats" abiertos y activos en FIJI.
// Salidas:   - Lote de proyecciones corregidas en formato .tiff (16-bit).
// =============================================================================

// 1. Directorios de entrada y salida
inputDir = getDirectory("Seleccione el directorio de las proyecciones a corregir");
outputDir = getDirectory("Seleccione el directorio de salida");
list = getFileList(inputDir);

// 2. Generación de imágenes maestras (Promedios)
selectWindow("Darks"); 
darks = getImageID();
selectWindow("Flats"); 
flats = getImageID();

selectImage(darks);
run("32-bit");
run("Z Project...", "projection=[Average Intensity]");
rename("Dark_Avg");

selectImage(flats);
run("32-bit");
run("Z Project...", "projection=[Average Intensity]");
rename("Flat_Avg");

// 3. Extracción de parámetros de normalización
selectImage("Flat_Avg");
getStatistics(area, flatMean, flatMin, flatMax);
globalMax = flatMax;
print("Límite superior para conversión a 16-bit: " + globalMax);

M = getValue("Mode");
print("Factor de normalización (Moda de Flat_Avg): M = " + M);

// Liberar memoria de stacks originales
close("Darks");
close("Flats");

// 4. Mapa de ganancia (Gain_Map = Flat - Dark)
imageCalculator("Subtract create 32-bit", "Flat_Avg", "Dark_Avg");
rename("Gain_Map");

// Añadir epsilon para evitar división por 0
eps = 1e-6;
selectImage("Gain_Map");
run("Add...", "value=" + eps);

// 5. Procesamiento en lote de proyecciones
setBatchMode(true); 

for (i = 0; i < list.length; i++) {
    if (endsWith(list[i], ".tif") || endsWith(list[i], ".tiff")) {
        showProgress(i + 1, list.length);

        open(inputDir + list[i]);
        origProj = getTitle();
        run("32-bit");

        // Corrección de ruido de fondo (I - Dark)
        imageCalculator("Subtract create 32-bit", origProj, "Dark_Avg");
        rename("I_minus_D");

        // Normalización por mapa de ganancia (I - Dark) / (Flat - Dark)
        imageCalculator("Divide create 32-bit", "I_minus_D", "Gain_Map");
        rename("Norm");

        // Re-escalado
        selectImage("Norm");
        run("Multiply...", "value=" + M);
        
        // Conversión a 16-bit conservando la escala física
        setMinAndMax(0, globalMax); 
        run("16-bit");

        saveAs("Tiff", outputDir + list[i]);
        savedProj = getTitle();

        // Limpieza temporal de imágenes intermedias
        close(savedProj);
        close("I_minus_D");
        close(origProj);
    }
}

setBatchMode(false);

// 6. Limpieza del entorno y cierre
close("Flat_Avg");
close("Dark_Avg");
close("Gain_Map");

showMessage("Listo", "Flat-field correction completada. Resultados guardados en:\n" + outputDir);