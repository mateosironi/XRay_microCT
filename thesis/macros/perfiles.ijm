// =============================================================================
// Autor: Mateo Sironi
// Institución: FAMAF - UNC
// Propósito: Extraer perfiles de intensidad perpendiculares a un borde definido 
// manualmente por el usuario en cada imagen de un stack. La línea perpendicular
// de medición tiene una longitud y grosor prestablecidos.
// Entradas:  - Stack de imágenes (con calibración espacial en mm).
//            - Trazado interactivo de una línea directriz en cada slice.
// Salidas:   - Tabla "Perfiles_Stack" con el eje espacial (x_mm) y las 
//              intensidades medidas (p1, p2, ..., pn) para cada imagen.
// =============================================================================

if (nSlices == 1) {
    exit("Error: Esta macro requiere un stack de imágenes.");
}

// 1. Configuración y Calibración
getVoxelSize(pw, ph, pd, unit);
if (unit != "mm") {
    print("Advertencia: La imagen no parece estar calibrada en mm.");
}

// Parámetros de medición
longitud_mm = 1.8; 
grosor_px = 80; 
L_px = longitud_mm / pw; // Conversión a píxeles

tableName = "Perfiles_Stack";
Table.create(tableName);
setTool("line");

// 2. Iteración y Extracción de Perfiles
for (s = 1; s <= nSlices; s++) {
    setSlice(s);
    run("Select None");
    
    // Interacción con el usuario
    waitForUser("Traza el borde", "Imagen " + s + " de " + nSlices + ":\nDibuja una línea recta a lo largo del borde y presiona OK.");

    if (selectionType() != 5) { 
        exit("Error: Debes dibujar una línea recta en la imagen " + s + ".");
    }

    // Geometría de la línea directriz
    getLine(x1, y1, x2, y2, originalWidth);
    dx = x2 - x1;
    dy = y2 - y1;
    dist = sqrt(dx * dx + dy * dy);

    // Vector unitario perpendicular
    ux_perp = -dy / dist;
    uy_perp = dx / dist;

    // Centro geométrico de la línea trazada
    cx = x1 + dx / 2;
    cy = y1 + dy / 2;

    // Coordenadas de los extremos de la línea perpendicular
    px1 = cx - (L_px / 2) * ux_perp;
    py1 = cy - (L_px / 2) * uy_perp;
    px2 = cx + (L_px / 2) * ux_perp;
    py2 = cy + (L_px / 2) * uy_perp;

    // Trazado y medición del perfil
    makeLine(px1, py1, px2, py2);
    Roi.setStrokeWidth(grosor_px);
    profile = getProfile();

    // 3. Almacenamiento de Resultados
    if (s == 1) {
        for (j = 0; j < profile.length; j++) {
            Table.set("x_mm", j, j * pw);
        }
    }

    colName = "p" + s;
    for (j = 0; j < profile.length; j++) {
        Table.set(colName, j, profile[j]);
    }
}

// 4. Limpieza del entorno
Roi.setStrokeWidth(1);
run("Select None");
Table.update;
print("Proceso completado. Se analizaron " + nSlices + " imágenes.");