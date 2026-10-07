// =============================================================================
// Autor: Mateo Sironi
// Institución: FAMAF - UNC
// Propósito: Calcular el ángulo eta y la desalineación entre el eje de 
// magnificación y el eje de movimiento del portamuestras. Utiliza dos  
// proyecciones radiográficas de un objeto cilíndrico, desfasadas 180° entre sí.
// Entradas:  Dos imágenes de proyecciones seleccionadas interactivamente.
// Salidas:   - Imagen multicanal (Merge) con superposición gráfica de ejes.
//            - Reporte de alineación impreso en la consola (Log).
// =============================================================================

run("Options...", "iterations=1 count=1 black");

// Variables globales para almacenar resultados de la medición
var x1, y1, ang1, maj1, x2, y2, ang2, maj2, w, h;
var grosor = 8;

// 1. Carga de Imágenes
path1 = File.openDialog("Selecciona la Imagen 1 (0°)");
open(path1);
id1 = getImageID();
rename("Img1");

path2 = File.openDialog("Selecciona la Imagen 2 (180°)");
open(path2);
id2 = getImageID();
rename("Img2");

// 2. Transformaciones geométricas
selectImage(id2);
run("Flip Horizontally");

// 3. Procesamiento y Análisis Morfológico
analizarImagen(id1, 1);
analizarImagen(id2, 2);

// 4. Superposición (Merge)
run("Merge Channels...", "c1=Img1 c2=Img2 create");
rename("Analisis_Interseccion");
id_final = getImageID();

// 5. Cálculos Trigonométricos
getDimensions(w, h, channels, slices, frames);
x_medio = w / 2;
y_medio = h / 2;

// Ángulos en radianes (ImageJ: 90° es vertical)
alpha1_rad = ang1 * PI / 180.0;
alpha2_rad = ang2 * PI / 180.0;

// Intersecciones con el eje horizontal central
x_int1 = x1 + (y1 - y_medio) / tan(alpha1_rad);
x_int2 = x2 + (y2 - y_medio) / tan(alpha2_rad);

distancia_intersecciones = abs(x_int1 - x_int2);
dev1 = 90 - ang1;
dev2 = 90 - ang2;
_2eta = abs(dev1 - dev2);

// 6. Visualización y Gráficos
selectImage(id_final);

// Ejes Centrales de la imagen (Azul)
makeLine(0, y_medio, w, y_medio);
Roi.setStrokeWidth(grosor);
Overlay.addSelection("blue");

makeLine(x_medio, 0, x_medio, h);
Roi.setStrokeWidth(grosor);
Overlay.addSelection("blue");

// Eje Imagen 1 (Rojo)
dibujarEje(x1, y1, ang1, maj1, "red");
makePoint(x_int1, y_medio, "small cross");
Roi.setStrokeWidth(grosor);
Overlay.addSelection("black");

// Eje Imagen 2 (Verde)
dibujarEje(x2, y2, ang2, maj2, "green");
makePoint(x_int2, y_medio, "small cross");
Roi.setStrokeWidth(grosor);
Overlay.addSelection("black");

// 7. Anotaciones en Pantalla
setFont("SansSerif", 60, "antialiased");
setColor("yellow");
Overlay.drawString("Delta d = " + d2s(distancia_intersecciones, 2) + " px", 50, 80);
Overlay.drawString("Dev. Ang. 1: " + d2s(dev1, 2) + "°", 50, 160);
Overlay.drawString("Dev. Ang. 2: " + d2s(dev2, 2) + "°", 50, 240);
Overlay.drawString("2eta = " + d2s(_2eta, 2) + "°", 50, 320);
Overlay.show();

// 8. Limpieza y Reporte
if (isOpen("ROI Manager")) { 
    selectWindow("ROI Manager"); 
    run("Close"); 
}
run("Select None");

print("--- REPORTE DE ALINEACIÓN ---");
print("Punto de corte Img1: x = " + d2s(x_int1, 3));
print("Punto de corte Img2: x = " + d2s(x_int2, 3));
print("Distancia entre cortes: " + d2s(distancia_intersecciones, 3) + " px");
print("Ángulo entre ejes (2eta): " + d2s(_2eta, 3) + "°");

// --- FUNCIONES AUXILIARES ---

function analizarImagen(id, num) {
    selectImage(id);
    run("8-bit");
    run("Invert");
    setAutoThreshold("Default dark");
    run("Convert to Mask");
    run("Fill Holes");
    run("Set Measurements...", "centroid fit display redirect=None decimal=3");
    run("Analyze Particles...", "size=500-Infinity show=Nothing clear add");
    
    if (roiManager("count") > 0) {
        roiManager("select", 0);
        List.setMeasurements;
        if (num == 1) {
            x1 = List.getValue("X"); y1 = List.getValue("Y");
            ang1 = List.getValue("Angle"); maj1 = List.getValue("Major");
        } else {
            x2 = List.getValue("X"); y2 = List.getValue("Y");
            ang2 = List.getValue("Angle"); maj2 = List.getValue("Major");
        }
    }
}

function dibujarEje(x, y, ang, maj, color) {
    alpha = ang * PI / 180.0;
    dx = (maj * 1.2) * cos(alpha);
    dy = -(maj * 1.2) * sin(alpha);
    makeLine(x - dx, y - dy, x + dx, y + dy);
    Roi.setStrokeWidth(grosor);
    Overlay.addSelection(color);}
