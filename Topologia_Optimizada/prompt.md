CORRECCIÓN FOCALIZADA — MAPEO GEOMÉTRICO DE CARGAS Y RESTRICCIONES

El objetivo de esta intervención es consolidar y hacer robusto el sistema actual de aplicación de cargas y restricciones FEA, eliminando cualquier dependencia de soluciones provisionales cuando sea posible.

CONTEXTO

La integración de Kratos con el Core ya está funcionando.

El problema anterior de aplicar cargas/restricciones a todos los nodos ya fue corregido.

Actualmente el sistema utiliza selección geométrica y dispone de mecanismos mediante "SubModelPart"/"boundary" y selección por coordenadas.

NO vuelvas a investigar Kratos ni rehagas la integración existente.

La tarea es exclusivamente mejorar este punto.

---

OBJETIVO

Conseguir un flujo coherente:

CADModel
   ↓
geometría seleccionada
   ↓
malla
   ↓
identificación de nodos pertenecientes a esa región
   ↓
Kratos
   ↓
carga / restricción

La selección debe representar una región física real del modelo, no simplemente una coordenada arbitraria.

---

TAREAS

1. Auditar la implementación actual de:
   
   - "solver_interface.py"
   - "kratos_adapter.py"
   - "CADModel"
   - información geométrica disponible después del STEP.
   - sistema actual de malla.
   - tests relacionados.

2. Determinar exactamente qué información geométrica conserva actualmente el "CADModel".

3. Determinar cómo puede identificarse una cara/región real del modelo y relacionarla posteriormente con los nodos de la malla.

4. Diseñar la solución más simple que permita:

cara/región CAD
      ↓
entidad geométrica identificable
      ↓
nodos de malla correspondientes
      ↓
BC / Load

5. Mantener la arquitectura desacoplada:

CAD
 ↓
CADModel
 ↓
Malla
 ↓
Solver Interface
 ↓
KratosAdapter

El Core no debe quedar acoplado innecesariamente a detalles internos de Kratos.

---

REGLA SOBRE LA SOLUCIÓN ACTUAL

La selección por coordenadas existente puede mantenerse como fallback técnico si sigue siendo necesaria.

Pero no debe utilizarse como mecanismo principal si existe una forma fiable de mapear:

cara/región geométrica → nodos de malla.

No eliminar una funcionalidad existente sin reemplazarla por una solución funcional equivalente o superior.

---

PRUEBAS

Implementar las pruebas mínimas necesarias para demostrar que:

1. Una región/cara seleccionada identifica únicamente los nodos correspondientes.

2. Una restricción se aplica exclusivamente a esos nodos.

3. Una carga se aplica exclusivamente a esos nodos.

4. No se modifican nodos pertenecientes a otras regiones.

5. El flujo funciona con geometría STEP real.

6. El resultado llega correctamente a Kratos.

No utilizar geometría artificial como única evidencia de esta funcionalidad.

---

PROTOCOLO DE BLOQUEO

Aplicar estrictamente "metodologia.md".

Si la solución es evidente y está respaldada por la implementación/documentación existente:

- realizar una única implementación;
- ejecutar la prueba.

Si aparece un problema cuya causa no sea evidente:

DETENERSE.

No realizar múltiples intentos especulativos.

Registrar el bloqueo completo:

- error;
- traceback;
- archivo;
- línea;
- función;
- entrada;
- comportamiento esperado;
- comportamiento obtenido;
- hipótesis disponible;
- solución investigada, si existe.

Dejarlo documentado como objeto de investigación externa.

---

NO HACER

No:

- investigar nuevamente Kratos;
- repetir el PoC;
- cambiar de motor FEA;
- implementar TopOpt;
- implementar licenciamiento;
- implementar UI;
- integrar Onshape;
- introducir Rust;
- migrar todo el proyecto a C++;
- rediseñar el Core completo;
- crear una arquitectura paralela.

---

CRITERIO DE FINALIZACIÓN

La tarea queda completada únicamente si se puede demostrar:

STEP REAL
   ↓
CADModel
   ↓
REGIÓN/CARA REAL
   ↓
MALLA
   ↓
NODOS CORRESPONDIENTES
   ↓
CARGA / RESTRICCIÓN
   ↓
KRATOS
   ↓
FEA

y las cargas/restricciones afectan únicamente a la región correspondiente.

Si esto no puede conseguirse de forma fiable con la arquitectura actual, no inventar una solución ni declarar completado el requisito.

Documentar el resultado real en "resumen_implementacion.md".