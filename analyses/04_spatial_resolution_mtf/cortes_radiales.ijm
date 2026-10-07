// ==============================================================================
// Autor: Mateo Sironi
// Institución: FAMAF - UNC
// Propósito: Generar un conjunto de cortes radiales (substack) a partir de una 
//            reconstrucción axial. El script identifica automáticamente el 
//            centro del objeto mediante análisis de partículas y realiza n 
//            muestreos angulares equidistantes (Reslice).
// Entradas:  - Stack axial de microtomografía activo.
//            - N: Número de cortes radiales deseados (línea 15).
//            - M: Grosor del substack axial a procesar (línea 16).
// Salidas:   - Stack "Stack_Proyecciones" que contiene los cortes radiales.
// ==============================================================================

// 1. Parámetros de configuración
N = 10;   // Cantidad de proyecciones radiales
M = 101;  // Profundidad de slices axiales a procesar

stackOriginal = getImageID();
totalSlices = nSlices;

if (totalSlices < M) {
    exit("Error: El stack original es menor al rango M solicitado.");
}

// 2. Extracción del substack central
sliceCentral = floor(totalSlices / 2) + 1;
mitadM = floor(M / 2);
sliceInicio = sliceCentral - mitadM;
sliceFin = sliceCentral + mitadM;

run("Make Substack...", "slices=" + sliceInicio + "-" + sliceFin);
subStackID = getImageID();
W = getWidth();
H = getHeight();
radius = maxOf(W, H); // Radio extendido para asegurar cobertura total

// 3. Detección automática del eje central (Centroide)
setSlice(mitadM + 1);
run("Duplicate...", "title=temp_centroid");
setAutoThreshold("Otsu dark");
run("Set Measurements...", "centroid redirect=None decimal=5");
run("Analyze Particles...", "size=100-Infinity pixel circularity=0.50-1.00 display");

if (nResults == 0) {
    close("temp_centroid");
    exit("Error: No se detectó el objeto central para definir el eje de rotación.");
}

getVoxelSize(pw, ph, pd, unit);
xc_px = getResult("X", 0) / pw;
yc_px = getResult("Y", 0) / ph;

close("temp_centroid");
selectImage(subStackID);

// 4. Generación de Cortes Radiales
for (i = 0; i < N; i++) {
    selectImage(subStackID);
    
    // Cálculo angular
    theta = i * (2 * PI / N);
    dx = radius * cos(theta);
    dy = radius * sin(theta);
    
    // Definición de la línea de corte desde el centro hacia afuera
    makeLine(xc_px, yc_px, xc_px + dx, yc_px + dy);
    run("Reslice [/]...", "avoid");
    
    angulo_deg = i * (360 / N);
    rename("Corte_Radial_" + d2s(angulo_deg, 1) + "_deg");
}

// 5. Consolidación y Limpieza
run("Images to Stack", "name=Stack_Proyecciones title=Corte_Radial use");

if (isOpen("Results")) {
    selectWindow("Results");
    run("Close");
}

selectImage(subStackID);
close();
print("Proceso finalizado: Se generaron " + N + " cortes radiales.");