// =============================================================================
// Autor: Mateo Sironi
// Institución: FAMAF - UNC
// Propósito: Calcular la desalineación del punto principal (offsets) y el
// ángulo de rotación del detector en microtomografía mediante el análisis
// geométrico de la proyección del cono del haz de Rayos X.
// Entradas:  - Imagen radiográfica del círculo (proyección del cono), abierta
//              y activa en FIJI.
//            - BETA_DEG: Semi-ángulo del haz cónico, en grados (línea 14).
// Salidas:   - Imagen RGB con gráficos superpuestos (ejes de elipse, punto
// principal y ángulo de inclinación fuera de plano)
//            - Tabla de resultados con Delta_U, Delta_V y Alfa.
// =============================================================================
 
    // Parámetros físicos
    BETA_DEG = 19.5; 

    if (nImages == 0) {
        showMessage("Error", "No hay imagen activa.");
        return;
    }

    // Preprocesamiento
    run("Duplicate...", "title=Resultado_Alineacion");
    run("8-bit");
    run("Clear Results");
    roiManager("Reset");
    run("Select None");

    // Binarización
    setAutoThreshold("Default dark");
    setOption("BlackBackground", true);
    run("Convert to Mask");

    // Detección y medición
    run("Set Measurements...", "area centroid fit shape redirect=None decimal=3");
    run("Analyze Particles...", "size=50-Infinity exclude clear include add");
    
    roiManager("Select", 0);

    // Extracción de datos morfológicos
    X_blob = getResult("X", 0);
    Y_blob = getResult("Y", 0);
    Major  = getResult("Major", 0);
    Minor  = getResult("Minor", 0);
    Angle  = getResult("Angle", 0);
    R      = Minor / Major;
    C      = getResult("Circ.", 0);
    
    X_img = getWidth() / 2;
    Y_img = getHeight() / 2;

    // Cálculos de desalineación
    dX = -(X_blob - X_img);
    dY = -(Y_blob - Y_img);

    toRad = PI / 180;
    toDeg = 180 / PI;
    angRad = Angle * toRad;
    beta_rad = BETA_DEG * toRad;
    
    ecc_term = sqrt(1 - (R * R));
    sin_alpha = cos(beta_rad) * ecc_term;
    Alpha_Deg = asin(sin_alpha) * toDeg;

    // Actualización de tabla
    setResult("Delta_X", 0, dX);
    setResult("Delta_Y", 0, dY);
    setResult("Alpha_Tilt_Cone", 0, Alpha_Deg);
    updateResults();

    run("RGB Color");
    
    // Eje Mayor (Verde)
    x1_maj = X_blob + (Major/2) * cos(angRad);
    y1_maj = Y_blob - (Major/2) * sin(angRad);
    x2_maj = X_blob - (Major/2) * cos(angRad);
    y2_maj = Y_blob + (Major/2) * sin(angRad);
    
    setColor("green");
    setLineWidth(8);
    drawLine(x1_maj, y1_maj, x2_maj, y2_maj);

    // Eje Menor (Magenta)
    x1_min = X_blob + (Minor/2) * cos(angRad + PI/2);
    y1_min = Y_blob - (Minor/2) * sin(angRad + PI/2);
    x2_min = X_blob - (Minor/2) * cos(angRad + PI/2);
    y2_min = Y_blob + (Minor/2) * sin(angRad + PI/2);

    setColor("magenta");
    drawLine(x1_min, y1_min, x2_min, y2_min);

    // Centro ideal (Cruz azul) y Centroides medidos (Punto rojo)
    setColor("blue");
    len = 60;
    drawLine(X_img - len, Y_img, X_img + len, Y_img);
    drawLine(X_img, Y_img - len, X_img, Y_img + len);
    
    setColor("red");
    fillOval(X_blob - 6, Y_blob - 6, 12, 12);

    // Impresión de parámetros calculados
    setFont("SansSerif", 60, "bold");
    
    setColor("green");
    drawString("2a: " + d2s(Major, 2) + " px", 20, 70);
    setColor("magenta");
    drawString("2b: " + d2s(Minor, 2) + " px", 20, 140);
    setColor("yellow");
    drawString("Ang: " + d2s(Angle, 2) + "°", 20, 210);
    drawString("Delta U: " + d2s(dX, 2) + " px", 20, 320);
    drawString("Delta V: " + d2s(dY, 2) + " px", 20, 390);
    drawString("C_w: " + d2s(C, 3), 20, 500);
    drawString("R: " + d2s(R, 3), 20, 570);
    drawString("Alfa: " + d2s(Alpha_Deg, 2) + "°", 20, 640);

    // Limpieza de entorno
    run("Select None");
    if (isOpen("ROI Manager")) {
        selectWindow("ROI Manager");
        run("Close");
    }
