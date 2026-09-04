Analizando los cuatro puntos presentados a partir de la evidencia del repositorio, se identifican las causas raíz, sus implicaciones físicas y los mecanismos de resolución requeridos para cada uno:
1. Mapeo CAD Face ↔ Gmsh Surface (Prioridad Máxima)
Causa Raíz
El bucle actual en core/meshing.py asume de forma implícita un orden indexado (0, 1, \dots, N-1) que no está garantizado por OpenCASCADE (OCC) ni por el API de Gmsh. Cuando CadQuery/OpenCASCADE exporta o genera un modelo STEP, los punteros o índices internos de shape.Faces() pueden diferir de las etiquetas numéricas (tags) que Gmsh asigna internamente a las entidades de dimensión 2 (dim=2).
Solución Técnica Determinista
Para lograr un mapeo determinista 1:1 entre cq.Shape().Faces()[fi] y las superficies de Gmsh sin depender del orden de enumeración, se pueden aplicar dos enfoques dentro de la integración OCC/Gmsh:
 * Uso de Physical Groups de Gmsh (Recomendado):
   Al transferir la geometría a Gmsh mediante la API C++/Python de OpenCASCADE/Gmsh (gmsh.model.occ), se debe asignar a cada cara CAD un Physical Group explícito utilizando su índice CAD fi:
   # tag_gmsh es el tag devuelto al importar o crear la superficie en OCC
gmsh.model.addPhysicalGroup(2, [tag_gmsh], tag=fi, name=f"face_{fi}")

   Al extraer los elementos de superficie, en lugar de iterar con enumerate(), se consulta directamente a Gmsh por el tag o nombre del Physical Group asociado a la entidad.
 * Identificación por Centroide / Propiedades Geométricas:
   Si la malla proviene de la importación de un archivo STEP intermedio donde se perdieron los tags OCC, la correspondencia se verifica calculando el centroide y la superficie total de shape.Faces()[fi] mediante OpenCASCADE (GProp_GProps) y comparándolo con el centroide de la superficie en Gmsh mediante gmsh.model.getCenterOfMass(2, stag).
2. Compatibilidad de ProvisionalTet4Mesher con Cargas por Cara
Causa Raíz
ProvisionalTet4Mesher agrupa globalmente todas las caras externas bajo la clave genérica "boundary". Al carecer de segmentación por caras individuales, GenerativeDesignEngine._face_triangles_for_load() intenta buscar la clave face_<fi> y, al no hallarla, recurre al fallback uniforme (aplicar la carga sobre todo el contorno o sobre el volumen/nodos más cercanos).
Diagnóstico e Implementación
 * ¿Tiene información suficiente actualmente? No. ProvisionalTet4Mesher genera una representación de contorno simplificada/convex-hull/global que carece de la topología refinada del modelo CAD original.
 * Acción Requerida:
   * Evitar la falsa asociación: No intentar mapear artificialmente "boundary" a face_<fi>.
   * Mecanismo de Fallback Explícito: Si se utiliza ProvisionalTet4Mesher, la interfaz debe explicitar que la condición de carga se aplicará de forma global o distribuida uniformemente en la frontera exterior disponible, emitiendo un warning explícito cuando se requiera aplicar una carga en una cara específica (fi).
3. Semántica y Cálculo de volfrac
Conflicto Conceptual
Existen dos formas de definir la fracción de volumen (volfrac) en optimización topológica con regiones preservadas:
Diagnóstico
La fórmula actual del código (target_vol = self.volfrac * self._vol0_free) implementa la Opción A si no se suma el volumen protegido, lo que significa que el volfrac especificado por el usuario aplica únicamente sobre el material no protegido.
Si el usuario especifica volfrac = 0.30 (esperando que la pieza final pese el 30% del volumen del bounding box original), pero un 10% del modelo está protegido por cargas/apoyos, la masa final real de la pieza terminada será 0.30 \times 0.90 + 0.10 = 0.37 (37% del total).
Semántica Correcta recomendada para el Proyecto
Para software de diseño generativo CAD/FEM, la convención estándar en la industria (e.g., SIMP tradicional, Ansys, Fusion 360) es la Opción B (Volumen Físico Total) respecto al dominio total de entrada:
Si V_{\text{protegido}} \ge \text{volfrac} \times V_{\text{total}}, el solver debe lanzar una excepción o fijar la región optimizable al límite inferior \rho_{\text{min}}.
4. Comportamiento e Interacción del Halo Automático
Análisis de la Interacción de Regiones
El flujo de estado para las variables en topopt.py debe mantener la siguiente jerarquía de conjuntos disjuntos y/o superpuestos:
 * _active (Elementos Optimitzables): Elementos que forman parte de las variables de diseño (\rho). Excluye los Voids/Obstructions y los elementos en ProtectedRegion / Halo.
 * _preserved (Elementos Fijos a \rho = 1.0): Unión de \text{ProtectedRegion} \cup \text{Halo}(\text{LoadNodes} \cup \text{SupportNodes}).
 * _void (Elementos Fijos a \rho = \rho_{\text{min}}): Volúmenes de interferencia o pasajes de herramientas.
Verificación de Requisitos para la Implementación
 * Unión de Cargas y Apoyos: La operación halo_nodes = set(load_nodes) | set(support_nodes) asegura que la interfaz mecánica completa quede protegida contra discontinuidades numéricas en el cálculo de esfuerzos/SENS.
 * Cálculo Automático del Radio (radius = None): Cuando radius es None o <= 0, el método debe calcular el radio efectivo R_{\text{halo}} en función del tamaño medio del elemento (h_{\text{elem}}), típicamente:
   
   
   Esto garantiza que al menos 1 o 2 capas de elementos adyacentes a las condiciones de contorno no sufran degradación de densidad durante las primeras iteraciones del algoritmo optimizador (MMA/OC).


# nota: investigación genética en la siguiente fracción del documento 

Nota de alcance: no tengo acceso al repositorio real (no se subió código, solo este documento). El análisis que sigue es una investigación de arquitectura/semántica basada en el comportamiento documentado de Gmsh, OCCT/CadQuery y SIMP, no una lectura del código fuente real. Donde la confirmación requiere evidencia empírica del repo, indico el diagnóstico exacto a correr contra el código real.
P1 — CAD Face ↔ Gmsh Surface
Causa raíz. No existe contrato documentado entre shape.Faces()[i] (traversal OCCT vía TopExp_Explorer, usado por CadQuery) y el orden de gmsh.model.getEntities(2) tras un import STEP. Son dos indexaciones independientes:
CadQuery: orden de TopExp_Explorer(shape, TopAbs_FACE).
Gmsh: orden del mapa interno (GEntityFactory) poblado al sincronizar el kernel OCC tras importShapes().
Confirmé en la documentación de la API de Gmsh (gmsh.model.occ.importShapes/importShapesNativePointer) que outDimTags solo devuelve tags en el orden de las shapes de entrada — es decir, si se importa un solo compound/solid, se recibe únicamente el tag de nivel superior (dim=3), no una lista de tags de caras alineada con shape.Faces(). El código actual, al usar getEntities(2) después de importar, está confiando implícitamente en el orden interno del mapa de Gmsh, que en la práctica suele parecerse al de OCCT pero no es parte del contrato público — puede diferir con seams, múltiples sólidos, caras compartidas, o entre versiones de Gmsh/OCCT.
Confirmación: hipótesis verosímil y no descartable, pendiente de verificación empírica.
Diagnóstico a correr contra el código real:
Python
Usar una geometría asimétrica (sin caras paralelas de igual área) para que el test sea discriminante.
Solución técnica mínima: correspondencia explícita por firma geométrica, no por índice.
Antes de mallar: computar {face_id: (centroid, normal, area)} desde CadQuery.
Tras occ.synchronize(): computar lo mismo por gmsh_tag.
Emparejar por distancia mínima en (centroid, normal, area) con tolerancia; si el segundo mejor candidato cae dentro de la tolerancia de ambigüedad → error explícito (no elegir en silencio).
Fijar addPhysicalGroup(2, [tag], name=f"face_{face_id}") con ese face_id estable — esto resuelve a la vez el problema universal de Physical Groups mencionado en el contexto del proyecto.
Archivos/funciones: GmshTet4Mesher._extract_all_surface_elements(); nuevo módulo face_correspondence.py con build_face_correspondence(cq_shape, gmsh_model, tol) -> dict[face_id, gmsh_tag]; FaceRegion/NodeSelectionEngine deben consumir face_id estable, no índice de enumeración.
Tests: (a) shape asimétrico, import directo en memoria vs. round-trip STEP, verificar mapeo idéntico; (b) caso con dos caras de área/normal casi idénticas → debe lanzar error de ambigüedad, no adivinar.
Riesgo a documentar: piezas simétricas (caras opuestas de igual área y normal antiparalela) pueden requerir desambiguación adicional por posición absoluta del centroide — dejar esto como límite conocido del método.
P2 — ProvisionalTet4Mesher ↔ surface triangles
Causa raíz: no es solo un mismatch de nombres ("boundary" vs face_*), es pérdida estructural de información. Según se describe, el mesher provisional detecta frontera contando caras de tet que aparecen una sola vez — esto es una operación puramente topológica sobre la conectividad tet, sin ningún vínculo a face_id de CAD. Renombrar "boundary" a "face_X" no arregla nada si no se sabe cuál X corresponde a cada triángulo.
Confirmación: consistente con lo descrito; alta probabilidad de que el pipeline con provisional mesher caiga siempre al fallback uniforme para cargas por cara. Falta confirmar empíricamente si _face_triangles_for_load() realmente no encuentra face_* en este camino.
Diagnóstico:
Python
Solución técnica mínima (por capas):
Corto plazo (recuperación geométrica): cuando no exista face_{id} pero sí boundary, filtrar boundary contra la geometría de la cara CAD: proyectar centroides de triángulo sobre la superficie CAD del face_id de la carga y aceptar solo los que caen dentro (distancia de proyección + dot(normal_tri, normal_cad) > umbral).
Medio plazo (propagación de etiqueta): dado que NodeSelectionEngine ya sabe qué face_id originó cada nodo seleccionado, propagar esa etiqueta: un triángulo de frontera cuyos 3 nodos pertenecen al conjunto de nodos de face_id se etiqueta como perteneciente a face_id.
Fallback explícito: si ninguna de las dos aplica, el fallback uniforme debe emitir warning/log explícito, no ejecutarse en silencio — la doc ya identifica correctamente que "los tests de conservación de fuerza pasan pero la distribución espacial es incorrecta"; eso debe ser detectable, no solo evitable.
Archivos/funciones: ProvisionalTet4Mesher (extracción de superficie), GenerativeDesignEngine._face_triangles_for_load(), nodal_area_weights().
Tests:
Assert: nodos de los triángulos devueltos ⊆ node_indices seleccionados de la cara.
Assert de centroide de la distribución de fuerza nodal, no solo magnitud resultante — este es el test que la suite actual no tiene y que enmascara el bug (conservación de fuerza total ≠ distribución espacial correcta).
Test que capture el warning cuando se cae al fallback uniforme.
P3 — Semántica de volfrac con regiones protegidas
Cuál es correcta: matemáticamente, la formulación SIMP estándar define volfrac sobre el dominio de diseño (elementos "activos", pasibles de redistribución) — así lo hacen prácticamente todos los códigos de referencia (99-line SIMP con "passive elements", OptiStruct, Inspire): la restricción es ∫_Ω_active ρ dV ≤ volfrac · |Ω_active|, y las regiones "passive"/protegidas quedan fuera del presupuesto porque el multiplicador de Lagrange y el OC operan solo sobre variables de diseño activas. Es decir: Opción A es la semántica interna correcta y necesaria — mezclar regiones fijas en la restricción rompe la derivación del criterio de optimalidad.
Pero el problema real que reporta el documento no es que A esté "mal" — es que el usuario/GUI probablemente piensa en términos de Opción B (fracción del volumen físico total, más intuitiva y a menudo la que importa contractualmente: "reducir la masa total en 70%"). Ahí está el origen del bug percibido.
Resolución: mantener A como semántica interna del solver (no negociable matemáticamente), exponer B como parámetro derivado con conversión explícita:
Código
Archivos/funciones: SIMPSolver, punto donde se computa target_vol; agregar volfrac_mode: Literal["active","total"] con la conversión anterior y raise ValueError en caso infactible (no clamping silencioso).
Tests:
volfrac_mode="active" → volumen físico final = volfrac·V_active + V_fix (no volfrac·V_total).
volfrac_mode="total" → volumen físico final ≈ volfrac_total·V_total dentro de tolerancia, para varios ratios V_fix/V_total.
Caso infactible (V_fix/V_total > volfrac_total) → debe lanzar error, no producir resultado silenciosamente incorrecto.
Riesgo a documentar: default recomendado = "active" (estándar de literatura, evita infactibilidad sorpresa), con la GUI pidiendo típicamente "total" y convirtiendo internamente, mostrando el chequeo de infactibilidad como validación de UI.
P4 — Halo automático
Punto crítico de causa raíz probable: radius=None no debe derivar de filter_radius. Son parámetros conceptualmente distintos — filter_radius es un parámetro de regularización numérica del filtro de densidad/sensibilidad (típicamente ~2–3× tamaño medio de elemento, ajustado para controlar checkerboarding), mientras que el radio del halo es un parámetro físico (cuánto material rígido real rodea una BC/carga, con justificación tipo Saint-Venant/RBE3). Conflacionarlos acopla dos decisiones de diseño no relacionadas — cambiar el filtro cambiaría el halo sin intención.
Checklist de verificación (test matrix, cada ítem requiere test dedicado sobre el repo real):
#
Requisito
Test
1
Halo alrededor de nodos de carga
Elementos protegidos ⊇ vecindario geométrico de nodos de carga dentro de radius
2
Halo alrededor de nodos de apoyo
ídem para BCs
3
Halo combinado carga+apoyo
unión correcta, sin duplicar/perder elementos en intersección
4
Combinación con ProtectedRegion
unión (no reemplazo) de conjuntos de elementos protegidos
5
No convertir todo el contorno en protegido
test con BC pequeña en modelo grande → %protegido acotado, no ≈100%
6
Radio configurable por usuario
pasar radius explícito y verificar que se respeta, no se ignora
7
Halo desactivable
radius=0 o flag → sin elementos adicionales protegidos
8
radius=None usa tamaño real de elemento, no filter_radius
instrumentar y verificar que el valor resuelto proviene de la métrica de malla (p.ej. longitud de arista media de elementos incidentes a los nodos), no de filter_radius
Archivos/funciones: protect_elements_near_nodes(node_indices, radius=None), punto de combinación con ProtectedRegion, exposición del parámetro en GUI (ya prevista en el .ui).
Riesgo a documentar: en geometrías con BCs distribuidas en gran parte del contorno (soportes tipo "clamped edge"), el halo automático puede legítimamente aproximarse a proteger mucho del contorno — el test del ítem 5 debe diferenciar "comportamiento correcto para BC extensa" de "bug que sobre-protege BC puntual".
Prioridad de ejecución recomendada
P1 primero — si la correspondencia CAD↔Gmsh es errónea, invalida cualquier verificación de P2 (no se sabría si el error viene de la extracción de superficie o de la propagación al provisional mesher).
P2 — depende del resultado de P1.
P4 (ítem 8, filter_radius vs tamaño de elemento) — independiente, rápido de confirmar/corregir.
P3 — es una decisión de producto/documentación, no bloquea los otros tres; puede resolverse en paralelo.
El riesgo transversal que señala correctamente el documento se mantiene: P1 y P2 son ambos casos donde la conservación de fuerza total puede pasar los tests existentes mientras la distribución espacial es física­mente incorrecta — cualquier test nuevo debe verificar centroide/forma de la distribución nodal, no solo la resultante.