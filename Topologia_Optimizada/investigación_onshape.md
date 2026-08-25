## investigación se Geminis ## 
INVESTIGACIÓN HITO 2
1. Resumen ejecutivo
El presente informe establece la factibilidad y arquitectura técnica para la implementación del Hito 2 de la aplicación de optimización topológica integrada en Onshape. El objetivo de esta etapa es construir la infraestructura de Análisis por Elementos Finitos (FEA) 3D tetraédrico (Tet4), desde la captura de selección geométrica en Onshape hasta la resolución del sistema lineal K u = F, asegurando la compatibilidad con el método SIMP (Solid Isotropic Material with Penalization).
Tras un análisis exhaustivo de la API de Onshape, herramientas de mallado y solvers FEA en Python, se determinan los siguientes hallazgos principales:
 * Onshape: Es técnicamente imposible capturar clics directos sobre caras, bordes o vértices del viewport 3D dentro de una App Extension (Iframe) sin la intervención de un elemento intermedio. La arquitectura debe basarse en un puente entre un Custom Feature (FeatureScript) que captura la selección nativa en el Part Studio y la API REST consumida por el backend.
 * Mallado: Gmsh (vía su API Python nativa gmsh) es la herramienta óptima. Permite procesar el archivo STEP B-Rep, generar elementos sólidos Tet4 y conservar la identificación topológica de las caras CAD mediante Physical Groups y entidades B-Rep de OpenCASCADE.
 * Solver FEA: Se recomienda construir un solver propio basado en SciPy Sparse (scipy.sparse.linalg) enfocado exclusivamente en elementos Tet4 de elasticidad lineal. Esto garantiza el control total sobre la matriz de rigidez global K, requisito indispensable para la derivación e integración del método de variables de densidad (SIMP) sin la sobrecarga de un software externo generalista.
2. Selección geométrica en Onshape
A. ¿Puede una Integrated App obtener directamente una selección gráfica del viewport?
HECHO VERIFICADO: No. Las Integrated Apps de Onshape que se ejecutan dentro de un Iframe (Element Tab o App Extension) no tienen acceso al evento de puntero (clic) sobre el renderizador 3D nativo del navegador ni disponen de una API JavaScript de eventos de selección en tiempo real del viewport.
B. ¿Puede hacerlo sin FeatureScript?
HECHO VERIFICADO: No para selecciones sub-dimensionales (Caras, Edges, Vertices). A través de la REST API de Onshape (GET /api/parts/...), solo es posible consultar partes (Parts) o cuerpos (Bodies) enteros. No existe un endpoint REST de la API de Onshape que devuelva "la cara seleccionada actualmente por el usuario con el ratón" en la interfaz.
C. Si necesita FeatureScript, ¿cómo funcionaría el puente?
INFERENCIA / ARQUITECTURA TÉCNICA:
El puente de selección requiere un patrón de Custom Feature + Custom Data / REST API:
 * Custom Feature (FeatureScript): Se crea un FeatureScript propio (ej. "FEA Boundary Condition"). Este diálogo nativo en el Part Studio presenta un query collector (definition.myFace is Query) que permite al usuario hacer clic en cualquier cara, borde o vértice.
 * Asignación de Atributos: El FeatureScript asigna un atributo o metadato permanente a la entidad seleccionada usando setExternalFeatureData o asociando la selección a las propiedades del Feature en la historia del modelo.
 * Lectura vía REST API: La Integrated App (Iframe) o el backend de FastAPI solicita el árbol de operaciones (Feature List) mediante el endpoint:
   GET /api/v2/assemblies/d/{did}/w/{wid}/e/{eid} o GET /api/v2/partstudios/d/{did}/w/{wid}/e/{eid}/features.
 * Extraer Selección: El backend parsea el JSON devuelto por Onshape, identificando los Deterministic Feature IDs y los Transient IDs / Queries de las caras marcadas por el usuario.
D. ¿Qué información de la entidad seleccionada puede obtenerse?
 * Part / Body: ID de la parte, persistent ID, Bounding Box, volumen, área.
 * Face / Edge / Vertex: Identificadores deterministas (deterministicId), evaluadores geométricos (normal de la cara, área, centroide, tipo de superficie plana/cilíndrica) extraíbles mediante FeatureScript o la API de evaluación POST /api/v2/partstudios/.../evaluations.
E. Limitación importante para el Hito 2
HECHO VERIFICADO: Los Transient IDs de las caras en Onshape son volátiles y cambian cuando la geometría se regenera. Sin embargo, la exportación STEP desde Onshape asigna nombres a los sólidos pero no garantiza la persistencia del etiquetado interno de caras B-Rep con el mismo ID que Onshape usa internamente. Por lo tanto, el mapeo espacial o por atributos es estrictamente necesario.
3. CAD/STEP → FEM
Para procesar el archivo STEP generado por Onshape y convertirlo en una malla volumétrica 3D de tetraedros de 4 nodos (Tet4), se evaluaron las siguientes herramientas:
 * Gmsh:
   * Soporte STEP: Excelente. Integración nativa con OpenCASCADE (OCC) en C++.
   * Generación Tet4: Sí, algoritmos 3D (Delaunay, Frontal 3D).
   * API Python: Excelente, binding nativo oficial (import gmsh).
   * Windows & Licencia: Licencia GNU GPL v2+. Funciona perfectamente en Windows.
 * TetGen:
   * Soporte STEP: No directo. Requiere pasar previamente por una malla de superficie STL/PLC (.poly).
   * Inconveniente: Al requerir una triangulación superficial previa, se pierde la información topológica nativa de las caras B-Rep de STEP.
 * Netgen:
   * Soporte STEP: Muy bueno (a través de la integración con OpenCASCADE/NGSolve).
   * API Python: Muy completa (ngsolve / netgen).
   * Licencia: LGPL v2.1.
 * pygalmesh:
   * Soporte STEP: Limitado; depende de CGAL y requiere wrappers complejos para leer B-Rep STEP de manera directa.
4. Comparativa de malladores
| Criterio | Gmsh (gmsh) | Netgen (netgen) | TetGen / PyVista | pygalmesh |
|---|---|---|---|---|
| Soporte STEP (B-Rep) | Nativo (OpenCASCADE) | Nativo (OpenCASCADE) | No (Requiere STL) | Limitado (Vía CGAL) |
| Generación Tet4 | Sí (Delaunay 3D / HXT) | Sí | Sí | Sí |
| Calidad de Malla | Alta (Optimización 3D) | Alta | Media / Depende de STL | Muy Alta |
| Identificación de Caras | Fácil (Physical Groups) | Posible | Muy Difícil | Difícil |
| API Python Oficial | Sí (pip install gmsh) | Sí (pip install ngsolve) | Parcial (tetgen) | Sí |
| Windows Support | Completo (Binarios PIP) | Completo | Completo (Compilación) | Completo |
| Licencia | GPL v2+ | LGPL v2.1 | AGPL v3 | GPL v3 |
Conclusión del Mallador: Gmsh es la opción superior. Permite importar el STEP, acceder al kernel OpenCASCADE interno, definir grupos físicos para cada cara CAD y generar tetraedros Tet4 en pocas líneas de código ejecutable en Windows.
5. Mapeo CAD → FEM
El problema crítico del mapeo radica en trasladar la restricción fijada por el usuario en Onshape (ej. "Cara ID X") hacia los nodos de la malla volumétrica FEM generada tras importar el STEP.
Métodos Evaluados
 * IDs B-Rep y Physical Groups en Gmsh (Método Topológico - RECOMENDADO):
   * Mecanismo: Al importar el STEP en Gmsh vía OpenCASCADE, el kernel asigna a cada superficie B-Rep un tag numérico (Surface Tag). Gmsh permite crear Physical Groups basados en estos tags. Al generar la malla volumétrica, Gmsh conserva las caras de los elementos 2D y sus nodos en las fronteras de los Physical Groups.
   * Robustez: Alta. Es determinista y no depende de aproximaciones geométricas.
 * Geometría Espacial / Proximidad / Bounding Box (Método Geométrico de Respaldo):
   * Mecanismo: Se extraen los centroides, normales y Bounding Boxes de las caras en Onshape mediante la API REST. Al recibir la malla de Gmsh, se buscan todos los nodos FEM cuya distancia a la superficie analítica evaluada sea menor a una tolerancia \epsilon (d < \epsilon).
   * Robustez: Media. Útil si la exportación STEP pierde atributos de identidades, pero propenso a fallar en caras muy próximas o con curvaturas complejas.
 * Parametrización y Metadatos STEP (STEP AP203/AP214/AP242):
   * Mecanismo: Leer las etiquetas ADVANCED_FACE dentro del archivo de texto del STEP.
   * Robustez: Baja/Inconsistente. Las convenciones de nombres varían según el exportador CAD de Onshape.
RECOMENDACIÓN DE MAPEO: Implementar un enfoque híbrido Topológico-Geométrico. Usar las entidades B-Rep de Gmsh asignadas a Physical Groups como método primario, utilizando la evaluación de normal y distancia proyectada como validación de respaldo.
6. Comparativa de soluciones FEA
Para ejecutar un análisis estructural estático lineal 3D (K u = F) con elementos tetraédricos de 4 nodos (Tet4) y servir de base para la optimización SIMP, se comparan las siguientes alternativas:
| Criterio | Solver Propio (SciPy Sparse) | scikit-fem | SfePy | CalculiX | FEniCSx |
|---|---|---|---|---|---|
| Soporte Tet4 3D | Directo (Matriz 12 \times 12) | Nativo | Nativo | Nativo | Nativo |
| Acceso a K_e y u para SIMP | 100% Directo y Transparente | Alto | Medio | Muy Difícil (Text I/O) | Medio / Complejo |
| Entorno Windows | Nivel Nativo (Python puro) | Nativo | Nativo | Ejecutable (.exe) | Dificultad (WSL/Docker) |
| Facilidad de Integración | Máxima | Media | Compleja | Muy Baja | Compleja |
| Licencia | BSD / MIT (Propietario) | BSD-3-Clause | BSD-3-Clause | GPL v2 | LGPL v3 |
| Rendimiento Matriz Sparse | Alto (SuiteSparse/PyPardiso) | Alto | Alto | Muy Alto (Fortran/C) | Muy Alto |
7. Arquitectura FEA recomendada
Decisión: Desarrollar un Solver FEA lineal estático 3D propio en Python utilizando scipy.sparse (y opcionalmente pypardiso).
Justificación
Para la optimización topológica SIMP, los solvers externos cerrados como CalculiX o FEniCS implican una penalización severa en el rendimiento debido al intercambio constante de archivos de texto o a capas de abstracción pesadas.
En el método SIMP, la matriz de rigidez global K se ensambla modificando la rigidez de cada elemento en cada iteración (K_e(\rho_e) = \rho_e^p \cdot K_e^0). Controlar directamente la matriz elemental 12 \times 12 de Tet4 y el ensamblaje disperso (COO/CSR matrix) en Python proporciona:
 * Acceso instantáneo en memoria al vector de desplazamientos u y al strain/stress por elemento.
 * Eliminación de I/O en disco durante las iteraciones del bucle de optimización.
 * Compatibilidad 100\% nativa con Windows sin dependencias complejas.
8. Preparación para SIMP
Para evitar reescribir el solver FEA cuando se implemente SIMP en el Hito 3, el desarrollo del solver en el Hito 2 debe incorporar explícitamente la siguiente arquitectura:
 * Precalculo de Matrices Elementales Base (K_e^0):
   * Almacenar la matriz de rigidez no ponderada K_e^0 (12 \times 12) para cada elemento Tet4 en memoria.
   * La matriz global en cada iteración SIMP se ensamblará como:
     
     
     donde p es el factor de penalización (típicamente p=3) y \epsilon \approx 10^{-9} evita la singularidad.
 * Cálculo Eficiente de Compliancia y Sensibilidades:
   * El solver debe devolver el vector de desplazamientos global u.
   * La función objetivo es la compliancia c(\rho) = F^T u = \sum_{e} u_e^T K_e(\rho_e) u_e.
   * La derivada (sensibilidad) respecto a la densidad del elemento e es:
     
   * El solver FEA debe exponer un método optimizado que acepte un array de densidades \vec{\rho} y retorne la matriz K(\rho), el vector de desplazamientos u, y el array de compliancias elementales u_e^T K_e^0 u_e.
 * Manejo Estricto de D.O.F. (Degrees of Freedom):
   * El solver debe estructurar la eliminación de DOFs restringidos (condiciones de Dirichlet) de forma que la re-factorización del sistema en cada iteración sea ultra rápida.
9. Validación
Antes de integrar el solver en el pipeline de optimización, el módulo FEA debe superar el siguiente protocolo de validación numérica:
A. Prueba Teórica / Analítica: Viga en Voladizo (Cantilever Beam)
 * Geometría: Viga de sección rectangular 10 \text{ mm} \times 10 \text{ mm}, longitud L = 100 \text{ mm}.
 * Material: Aluminio (E = 68.9 \text{ GPa}, \nu = 0.33).
 * Carga: Carga puntual o distribuida en el extremo libre F_z = -100 \text{ N}.
 * Validación: Comparar la deflexión máxima \delta_{max} en el extremo contra la solución de Euler-Bernoulli o Timoshenko:
   
B. Patch Test 3D
 * Someter un cubo de elementos Tet4 a un campo de tensiones o desplazamientos constantes para verificar que el elemento pasa la prueba de convergencia y no presenta bloqueos (shear locking).
C. Estudio de Convergencia de Malla
 * Ejecutar el solver para tamaños de elemento decrecientes (h, h/2, h/4).
 * Graficar E_{relativo} = \left\vert{} \frac{\delta_{FEM} - \delta_{analítica}}{\delta_{analítica}} \right\vert{}.
 * Criterio de aceptación: El error relativo debe converger monótonamente por debajo del 5\% para mallas suficientemente refinadas.
10. Riesgos técnicos
 * Desalineación entre IDs de Caras en Onshape y Malla Gmsh:
   * Riesgo: La exportación STEP puede alterar los índices topológicos de las caras.
   * Mitigación: Usar el centroide y vector normal de la cara obtenido desde la API de Onshape para realizar una validación de proximidad espacial en la malla de Gmsh.
 * Pobre Desempeño Numérico en Matrices Dispersas Grandes:
   * Riesgo: El solver scipy.sparse.linalg.spsolve es monohilo y lento para mallas con más de 100.000 elementos.
   * Mitigación: Integrar pypardiso (wrapper en Python para Intel MKL Pardiso) que resuelve sistemas dispersos simétricos definidos positivos en entornos multihilo a alta velocidad.
 * Rigidez Excesiva del Elemento Tet4:
   * Riesgo: El elemento tetraédrico lineal de 4 nodos (Tet4) es propenso a rigidez excesiva frente a flexión (shear locking).
   * Mitigación: Mantener la densidad de la malla razonablemente alta en zonas de gradientes de tensión y validar el tamaño de elemento en la etapa de preprocesamiento.
11. Arquitectura final recomendada
Arquitectura Seleccionada para el Hito 2
[Onshape Part Studio]
  │ (Usuario selecciona cara mediante Custom Feature / FeatureScript)
  ▼
[Onshape REST API] ──(Descarga STEP + Attributes JSON)──► [FastAPI Backend]
                                                               │
                                                       (Importa STEP vía Gmsh)
                                                               ▼
                                                       [Gmsh Mesh Engine]
                                                               │
                                             (Extrae Nodos, Conectividad Tet4,
                                              y Physical Groups para BCs)
                                                               ▼
                                                       [Custom FEA Solver]
                                                    (SciPy Sparse + PyPardiso)
                                                               │
                                             (Calcula K, u, F, Tensiones Von Mises,
                                              y Compliancia por elemento)
                                                               ▼
                                                       [Preparación SIMP]
                                             (Matriz K_e^0 lista para Hito 3)

 * Captura de Selección: FeatureScript Custom Feature en Onshape para capturar selecciones de caras del usuario \rightarrow Almacenamiento en propiedades de Feature \rightarrow Lectura desde la API REST por FastAPI.
 * Procesamiento CAD/STEP: Exportación nativa STEP desde Onshape.
 * Generación de Malla: Gmsh Python API (gmsh), configurado para generación volumétrica 3D Tet4 con preservación de Physical Groups de superficies.
 * Mapeo CAD-FEM: Mapeo por Physical Groups de Gmsh validado por proximidad geométrica de centroide y normal de cara.
 * Solver FEA: Solver Estructural 3D propio en Python, implementado mediante scipy.sparse y pypardiso, operando sobre elementos Tet4.
 * Preparación SIMP: Estructuración del ensamblaje matricial parametrizado por el vector de densidad elemental \vec{\rho} y precalculo de K_e^0.
 * Validación: Suite de pruebas unitarias automatizadas con la prueba de la Viga en Voladizo (Cantilever Beam) y Patch Test.
12. Fuentes
 * Onshape Official Documentation & Developer Portal: App Extensions, FeatureScript Guide, and REST API Reference v2 (Documentation for Part Studios, Assemblies, and Evaluations).
 * Gmsh Reference Manual: A 3D finite element mesh generator with built-in pre- and post-processing facilities (Geuzaine, C., & Remacle, J.-F.).
 * SciPy Documentation: Sparse linear algebra (scipy.sparse.linalg) Module Reference.
 * PyPardiso Library Repository: Python interface to Intel MKL Pardiso solver for sparse linear systems.
 * Bendsøe, M. P., & Sigmund, O. (2003): Topology Optimization: Theory, Methods, and Applications. Springer Science & Business Media.

## investigación Microsoft copilot ##
INVESTIGACIÓN HITO 2

1. Resumen ejecutivo
La arquitectura recomendada para el Hito 2 es: usar FeatureScript en Onshape para capturar selecciones geométricas (caras, aristas, vértices) y transmitir sus IDs a la aplicación integrada; emplear Gmsh con kernel OpenCASCADE para generar mallas Tet4 desde STEP; mapear caras CAD a superficies de malla mediante Physical Groups; y utilizar SfePy como solver FEA 3D en Python, preparado para integración con SIMP. La validación debe incluir vigas en voladizo, pruebas de convergencia y patch tests.  

---

2. Selección geométrica en Onshape
- Hecho verificado: Onshape no expone directamente eventos de selección del viewport a Integrated Apps mediante la REST API.  
- FeatureScript: permite capturar selecciones de entidades (Part, Body, Face, Edge, Vertex) mediante queries (qEverything, qFace, qEdge, etc.) y obtener transient IDs y deterministic IDs .  
- Puente necesario: la aplicación integrada debe comunicarse con un FeatureScript personalizado que capture la selección y devuelva los IDs a través de parámetros o evaluaciones.  
- Limitación: sin FeatureScript, una app integrada no puede recibir selecciones gráficas.  

Conclusión:  
A. No, una Integrated App no obtiene selección directa.  
B. No, sin FeatureScript no es posible.  
C. Sí, con FeatureScript como puente.  
D. Se obtienen IDs de entidad (face, edge, vertex) y tipo geométrico.  
E. Limitación crítica: dependencia de FeatureScript para selección avanzada.  

---

3. CAD/STEP → FEM
- Gmsh (OCC kernel): Importa STEP, genera Tet4, controla tamaño, soporta Physical Groups, API Python, GPL .  
- TetGen: potente para tetraedros, pero requiere STL intermedio, licencia AGPL, menos soporte directo STEP .  
- Netgen: soporta STEP vía OCC, buena calidad de malla, API Python, LGPL .  
- pygalmesh: wrapper Python sobre CGAL, genera tetraedros, pero soporte STEP limitado.  

Conclusión: Gmsh con OCC es la opción más robusta.  

---

4. Comparativa de malladores
| Herramienta | STEP | Tet4 | API Python | Licencia | Calidad |
|-------------|------|------|------------|----------|---------|
| Gmsh | Sí (OCC) | Sí | Sí | GPL | Alta, refinamiento avanzado |
| TetGen | Indirecto (STL) | Sí | Parcial | AGPL | Buena, menos CAD |
| Netgen | Sí (OCC) | Sí | Sí | LGPL | Buena |
| pygalmesh | Limitado | Sí | Sí | MPL | Media |

---

5. Mapeo CAD → FEM
- Método robusto: usar Physical Groups en Gmsh OCC para etiquetar caras CAD y mantener correspondencia con superficies de malla y nodos FEM .  
- Alternativas: tags en CadQuery, proximidad geométrica, bounding boxes .  
- Conclusión: Physical Groups con IDs OCC es el método más fiable.  

---

6. Comparativa de soluciones FEA
- scikit-fem: ligero, Python, buen soporte 2D/3D, pero limitado en Tet4 grandes.  
- SfePy: Python, soporte 3D, Tet4, condiciones de frontera, tensiones, integración con SIMP, licencia BSD .  
- CalculiX: robusto, compatible Abaqus, pero flujo basado en input decks, menos flexible para integración directa.  
- FEniCS/DOLFINx: potente, variacional, buen soporte, pero curva de aprendizaje alta .  

Conclusión: SfePy es la mejor opción para integración Python + SIMP.  

---

7. Arquitectura FEA recomendada
- Solver: SfePy.  
- Malla: Gmsh OCC.  
- Selección: FeatureScript puente.  
- Mapeo: Physical Groups.  

---

8. Preparación para SIMP
El solver debe proporcionar:  
- Matriz de rigidez \(K\).  
- Vector de desplazamientos \(u\).  
- Tensiones y compliance.  
- Acceso a ensamblaje sparse.  
- Capacidad de iterar sobre elementos para actualizar densidades.  

---

9. Validación
Pruebas mínimas:  
- Viga en voladizo: comparar desplazamiento con solución analítica .  
- Convergencia de malla: refinar y verificar error relativo.  
- Patch tests: verificar consistencia de tensiones .  

---

10. Riesgos técnicos
- Dependencia de FeatureScript para selección.  
- Licencia GPL de Gmsh (compatibilidad con distribución).  
- Rendimiento de SfePy en modelos grandes.  
- Necesidad de validación rigurosa antes de SIMP.  

---

11. Arquitectura final recomendada
1. Selección geométrica: FeatureScript → IDs → App integrada.  
2. Geometría CAD: exportación STEP vía Onshape API.  
3. Malla Tet4: Gmsh OCC con Physical Groups.  
4. Mapeo CAD-FEM: Physical Groups mantienen correspondencia.  
5. Solver FEA: SfePy en Python.  
6. Preparación SIMP: acceso a \(K, u, \sigma, C\).  
7. Validación: viga en voladizo, convergencia, patch tests.  

---

12. Fuentes
- Onshape FeatureScript & Query Explorer   
- Onshape Custom Features   
- Gmsh & Netgen docs   
- TetGen workflow   
- Mapping CAD → FEM (Gmsh Physical Groups, CadQuery tags)   
- FEA solver comparisons (SfePy, FEniCS, CalculiX)   
- Validation methods (cantilever beam, patch test)