CORRECCIÓN FINAL — VALIDACIÓN Y CONTROL DEL MAPEO CAD → NODOS

OBJETIVO ÚNICO

Corregir y validar específicamente el mecanismo actual de aplicación de cargas y restricciones para garantizar que, cuando existe una cara CAD identificable, la condición FEA se aplique mediante el mapeo geométrico CAD → nodos de malla y no mediante el fallback por coordenadas.

No rediseñar el sistema.

No investigar nuevamente Kratos.

No modificar otras partes del proyecto que no sean necesarias para resolver este problema.

---

1. ESTADO ACTUAL

El proyecto ya dispone de:

STEP
 ↓
CADModel
 ↓
CAD Shape
 ↓
Malla
 ↓
BoundaryConditionMapper
 ↓
CAD Face → Mesh Nodes
 ↓
Kratos

"solver_interface.py" actualmente intenta resolver las condiciones mediante:

1. "SubModelPart / boundary"
2. "CAD face mapping"
3. "coordinate-based fallback"

"boundary.py" ya contiene "BoundaryConditionMapper.map_faces_to_nodes()".

El problema pendiente es garantizar que el mecanismo principal sea realmente el mapeo geométrico de la cara CAD y que el fallback no oculte silenciosamente un fallo del mecanismo principal.

---

2. AUDITORÍA PREVIA

Antes de modificar código, revisar exclusivamente:

- "core/solver_interface.py"
- "core/boundary.py"
- "core/kratos_adapter.py"
- definición de "ConstraintDefinition"
- definición de "LoadDefinition"
- representación de "CADFace"
- código que genera/conserva "cad_shape"
- pruebas existentes relacionadas con boundary conditions.

Determinar exactamente:

¿De dónde sale location_face_id?
¿De dónde sale application_face_id?
¿Cómo se conserva el CAD Shape?
¿Cómo se identifica una cara?
¿Cómo llega esa información hasta BoundaryConditionMapper?
¿Cómo se convierten los índices de nodos?
¿Cómo llegan finalmente esos nodos a Kratos?

No modificar nada hasta comprender ese flujo.

---

3. REQUISITO PRINCIPAL

Cuando una restricción tenga un "location_face_id" válido y exista "cad_shape":

location_face_id
        ↓
resolve_face_index()
        ↓
CAD Shape.Faces()
        ↓
cara B-Rep real
        ↓
BoundaryConditionMapper
        ↓
nodos pertenecientes a esa cara
        ↓
apply_constraint_from_core()
        ↓
Kratos

Debe utilizarse esta ruta.

Para una carga:

application_face_id
        ↓
resolve_face_index()
        ↓
CAD Shape.Faces()
        ↓
cara B-Rep real
        ↓
BoundaryConditionMapper
        ↓
nodos pertenecientes a esa cara
        ↓
apply_load_from_core()
        ↓
Kratos

---

4. FALLBACK POR COORDENADAS

El fallback por coordenadas puede permanecer por compatibilidad.

Sin embargo:

NO debe ejecutarse silenciosamente cuando:

- existe "cad_shape";
- existe "location_face_id" / "application_face_id";
- el identificador de cara es válido;
- y el mapeo CAD debería poder ejecutarse.

Si el mapeo de una cara válida falla porque no encuentra nodos, debe registrarse claramente el motivo.

Ejemplo:

CAD FACE MAPPING FAILED
constraint: X
face_id: face_3
face_index: 3
matched_nodes: 0
tolerance: 0.5
reason: no mesh nodes matched the CAD face

Solo después de registrar claramente ese fallo podrá utilizarse el fallback.

---

5. DIFERENCIAR "CARA INVÁLIDA" DE "CARA SIN NODOS"

No tratar todos los fallos como iguales.

Distinguir:

Caso A — no existe identificador de cara

face_id = None

Puede utilizar fallback.

Caso B — identificador inválido

Ejemplo:

face_id = "base"

Si el sistema actual no puede resolverlo, documentar el motivo.

Caso C — identificador válido pero fuera del rango de caras

Debe considerarse un error de datos y registrarse.

Caso D — cara válida pero ningún nodo coincide

Debe registrarse como fallo del mapeo geométrico.

No ocultarlo.

Caso E — cara válida y nodos encontrados

Debe utilizarse exclusivamente ese conjunto de nodos.

---

6. NO PERMITIR FALSOS POSITIVOS

Una condición aplicada mediante CAD face mapping debe poder demostrar:

face_index = X
matched_nodes_count = N
node_indices = [...]

y esos nodos deben ser exactamente los enviados a:

adapter.apply_constraint_from_core()

o:

adapter.apply_load_from_core()

No utilizar "model_part.Nodes" completo.

No utilizar todos los nodos como fallback oculto.

---

7. VALIDACIÓN DE LA TOLERANCIA

Revisar la tolerancia actualmente utilizada por:

BoundaryConditionMapper.map_faces_to_nodes()

Determinar si la tolerancia actual es razonable respecto de la escala de la malla.

No cambiar arbitrariamente la tolerancia.

Si se necesita modificarla, justificarlo técnicamente y probarlo con el STEP real.

---

8. PRUEBA OBLIGATORIA

Utilizar un STEP real existente en el proyecto.

No generar una geometría artificial para esta prueba.

La prueba debe:

1. cargar el STEP;
2. obtener el "CAD Shape";
3. generar/utilizar la malla correspondiente;
4. identificar una cara real;
5. crear una restricción sobre esa cara;
6. crear una carga sobre una cara real;
7. ejecutar el mapeo;
8. registrar cuántos nodos fueron seleccionados;
9. ejecutar Kratos;
10. verificar que las condiciones fueron aplicadas únicamente sobre esos nodos.

---

9. EVIDENCIA OBLIGATORIA

La prueba debe dejar evidencia explícita de:

STEP utilizado:
Cara de restricción:
Face ID:
Face index:
Nodos seleccionados:
Cantidad de nodos:
Método utilizado:
    CAD_FACE_MAPPING / SUBMODELPART / COORDINATE_FALLBACK

Cara de carga:
Face ID:
Face index:
Nodos seleccionados:
Cantidad de nodos:
Método utilizado:
    CAD_FACE_MAPPING / SUBMODELPART / COORDINATE_FALLBACK

La evidencia debe demostrar específicamente que el método utilizado fue:

CAD_FACE_MAPPING

cuando la cara CAD era válida y estaba disponible.

---

10. TEST DE NO REGRESIÓN

Comprobar que:

- el solver Kratos continúa funcionando;
- el STEP real continúa cargándose;
- la malla continúa generándose;
- el FEA continúa ejecutándose;
- los resultados continúan regresando al Core;
- las condiciones no vuelven a aplicarse a todos los nodos.

No romper funcionalidades existentes para solucionar este problema.

---

11. SI EL MAPEADOR FALLA

Aplicar estrictamente el protocolo de "metodologia.md".

Si aparece un error cuya causa sea evidente:

- realizar una única corrección;
- volver a ejecutar la prueba.

Si la causa no es evidente:

DETENERSE.

No realizar múltiples modificaciones especulativas.

Registrar:

- traceback completo;
- archivo;
- línea;
- función;
- face_id;
- face_index;
- tolerancia;
- cantidad de nodos;
- geometría utilizada;
- estado de la malla;
- comportamiento esperado;
- comportamiento obtenido.

Marcarlo como:

BLOQUEO TÉCNICO
REQUIERE INVESTIGACIÓN

No intentar cinco soluciones diferentes.

---

12. NO HACER

Durante esta intervención NO:

- cambiar Kratos;
- cambiar el solver;
- cambiar la arquitectura del Core;
- implementar TopOpt;
- implementar licenciamiento;
- implementar UI;
- integrar CAD externo;
- introducir Rust;
- migrar a C++;
- eliminar el "BoundaryConditionMapper";
- reemplazar el sistema por una solución completamente diferente;
- repetir investigaciones anteriores sobre Kratos.

---

13. CRITERIO DE ÉXITO

La intervención se considera completada únicamente si se demuestra:

STEP REAL
   ↓
CAD Shape
   ↓
CAD Face identificada
   ↓
Face index
   ↓
BoundaryConditionMapper
   ↓
Nodos de esa cara
   ↓
Carga / Restricción
   ↓
Kratos

y la evidencia demuestra que:

NODOS SELECCIONADOS ≠ TODOS LOS NODOS

y que el método utilizado fue:

CAD_FACE_MAPPING

para una cara válida.

---

14. DOCUMENTACIÓN

Actualizar "resumen_implementacion.md" únicamente con esta intervención.

Registrar:

- problema original;
- auditoría realizada;
- cambios realizados;
- archivos modificados;
- STEP utilizado;
- cara utilizada;
- nodos obtenidos;
- método de selección;
- prueba ejecutada;
- resultado;
- si se utilizó o no fallback;
- errores encontrados;
- estado final.

Si la prueba demuestra que el mapeo CAD → nodos funciona correctamente:

«CERRAR ESTE PROBLEMA.»

No continuar modificándolo ni crear otra solución.

REGLA FINAL

El objetivo no es eliminar el fallback.

El objetivo es garantizar que:

«cuando existe una cara CAD válida, el sistema utilice realmente esa cara para determinar los nodos de la condición FEA y no oculte un fallo recurriendo silenciosamente a coordenadas.»

Resolver únicamente esto y detenerse.