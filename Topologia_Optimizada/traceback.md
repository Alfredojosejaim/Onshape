TRACEBACK TÉCNICO PARA INVESTIGACIÓN — P0.1

Contexto

El proyecto es una aplicación CAD/CAE standalone en Python, con:

- CadQuery/OCCT para geometría CAD.
- Gmsh para mallado Tet4.
- FEM local mediante NumPy/SciPy.
- Kratos como segundo motor FEA.
- Condiciones de carga seleccionadas sobre caras CAD.
- Optimización SIMP.

Se implementaron recientemente tres correcciones P0:

1. Extracción de elementos superficiales desde Gmsh.
2. Triangulación de frontera en el mesher provisional.
3. Halo automático alrededor de cargas y apoyos.

La implementación actual pasa los tests existentes, pero una auditoría del código detectó posibles problemas de integración que deben ser investigados antes de considerar P0 cerrado.

---

PROBLEMA 1 — CAD Face ↔ Gmsh Surface

Cadena sospechosa

La condición de carga comienza en una cara CAD seleccionada:

CAD Face
   ↓
FaceRegion / NodeSelectionEngine
   ↓
node_indices
   ↓
_face_triangles_for_load()
   ↓
face_surface_elements["face_<fi>"]
   ↓
nodal_area_weights()
   ↓
fuerza nodal
   ↓
FEA

El problema aparece en la extracción de superficies de Gmsh.

"GmshTet4Mesher._extract_all_surface_elements()" obtiene:

gmsh.model.getEntities(2)

y posteriormente enumera esas superficies para construir claves del tipo:

face_0
face_1
face_2
...

El código aparentemente utiliza el índice de enumeración de Gmsh como si correspondiera al índice de:

shape.Faces()

Hipótesis a investigar

No está demostrado que:

shape.Faces()[i]

corresponda necesariamente a:

gmsh_surface_enumeration[i]

Si el orden no es idéntico, una carga seleccionada sobre una cara CAD podría recibir los triángulos de otra superficie Gmsh.

Esto sería especialmente grave porque:

- los nodos seleccionados podrían pertenecer a la cara correcta;
- pero los triángulos utilizados para calcular áreas tributarias podrían pertenecer a otra cara;
- la distribución total de fuerza podría seguir conservándose;
- los tests de conservación de fuerza podrían pasar;
- pero la distribución espacial de la carga sería físicamente incorrecta.

Qué debe investigar Claude

Determinar si existe una correspondencia determinista y garantizada entre:

CadQuery/OCCT Face index
        ↕
Gmsh surface entity

No asumir que el orden de enumeración coincide.

Si no existe garantía, investigar la forma correcta de construir una correspondencia explícita y estable.

La solución debe mantener:

CAD face seleccionada
→ superficie Gmsh correspondiente
→ triángulos de esa superficie
→ pesos por área tributaria

---

PROBLEMA 2 — ProvisionalTet4Mesher

El mesher provisional genera una triangulación de frontera detectando caras de tetraedros que aparecen una sola vez.

Actualmente esos triángulos se almacenan bajo:

face_surface_elements["boundary"]

Sin embargo, "GenerativeDesignEngine._face_triangles_for_load()" aparentemente busca principalmente:

physical_groups
face_<fi>

Por lo tanto existe una posible desconexión:

ProvisionalTet4Mesher
        ↓
boundary
        X
        ↓
_face_triangles_for_load(load)
        ↓
nodal_area_weights()

Si la carga fue aplicada a una cara CAD específica, pero el provisional mesher solamente conoce:

boundary

sin una correspondencia entre esa frontera y la cara CAD seleccionada, el algoritmo podría terminar utilizando el fallback uniforme.

Hipótesis

El sistema podría estar funcionando correctamente desde el punto de vista de ejecución, pero la distribución tributaria podría no estar utilizándose realmente en determinados caminos del pipeline.

Qué debe investigar Claude

Determinar exactamente qué ocurre en este flujo:

LoadCondition
→ CAD face
→ node selection
→ provisional mesh
→ surface triangles
→ nodal_area_weights

Debe determinar:

1. Si "boundary" llega realmente a "_face_triangles_for_load()".
2. Si puede asociarse correctamente con una cara CAD concreta.
3. Si actualmente se está cayendo al fallback uniforme.
4. Si es posible crear una correspondencia correcta.
5. Si no es posible con la información disponible, determinar cuándo el fallback uniforme es físicamente aceptable y cuándo debe producir una limitación/error explícito.

No se debe simplemente modificar el código para que los tests pasen.

---

PROBLEMA 3 — Semántica de volfrac con regiones protegidas

"SIMPSolver" mantiene dominios separados:

_active
_preserved
_void

Las regiones protegidas y el halo se excluyen del dominio optimizable.

Actualmente el cálculo conceptual es:

target_vol = volfrac × volumen_del_dominio_libre

Mientras que las regiones protegidas permanecen con densidad 1.

Esto puede producir:

volfrac = 0.30
+
10% del modelo protegido
=
más del 30% del volumen físico total

Por ejemplo, aproximadamente:

30% del dominio libre
+
10% protegido

no necesariamente equivale a:

30% del volumen total

Qué debe investigar Claude

Determinar cuál debe ser la semántica correcta de "volfrac" para este proyecto:

Opción A

"volfrac" representa:

fracción del dominio optimizable

Opción B

"volfrac" representa:

fracción del volumen físico total

La decisión debe considerar el comportamiento esperado de SIMP y el hecho de que:

- ProtectedRegion tiene densidad fija 1.
- Halo tiene densidad fija 1.
- Void/Obstruction tiene densidad mínima.
- "_active" es el dominio realmente modificado por OC.

No cambiar arbitrariamente la implementación.

Primero determinar cuál semántica es técnicamente correcta para el producto y luego indicar cómo debe documentarse y probarse.

---

PROBLEMA 4 — Halo automático

Se implementó:

protect_elements_near_nodes(node_indices, radius=None)

Cuando "radius=None", el radio se obtiene a partir del tamaño característico de los elementos.

La intención es:

cargas
   ↓
nodos afectados
   ↓
halo
   ↓
elementos protegidos

y lo mismo para apoyos.

Debe verificarse que:

- se protejan elementos alrededor de nodos de carga;
- se protejan elementos alrededor de nodos de apoyo;
- carga + apoyo puedan generar un halo combinado;
- el halo se combine correctamente con "ProtectedRegion";
- no convierta arbitrariamente todo el contorno en material protegido;
- el usuario pueda configurar el radio;
- el halo pueda desactivarse;
- "radius=None" utilice tamaño real del elemento y no "filter_radius".

---

OBJETIVO DE LA INVESTIGACIÓN

No implementar todavía.

Investigar y entregar a la IA programadora:

1. Causa raíz de cada problema.
2. Confirmación de si realmente ocurre o es solamente una hipótesis.
3. Evidencia mediante código/tests.
4. Solución técnica mínima.
5. Archivos y funciones que deben modificarse.
6. Tests que deben agregarse o corregirse.
7. Riesgos o limitaciones que deban quedar documentados.

Restricciones

No:

- reconstruir la arquitectura;
- reemplazar SIMP;
- reemplazar FEA local;
- reemplazar Kratos;
- incorporar Kratos OptimizationApplication;
- incorporar MMA/GCMMA;
- incorporar Heaviside;
- crear nuevas condiciones innecesariamente;
- rediseñar la UI;
- eliminar funcionalidades existentes;
- modificar componentes que no estén relacionados con estos problemas.

La solución debe integrarse con las abstracciones existentes.

Prioridad

Investigar primero:

1. CAD Face ↔ Gmsh Surface
2. ProvisionalTet4Mesher ↔ surface triangles
3. volfrac + protected/halo
4. comportamiento completo del halo

La prioridad principal es evitar una situación en la que el programa produzca resultados aparentemente válidos pero físicamente incorrectos.