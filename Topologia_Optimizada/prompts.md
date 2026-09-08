AUDITORÍA Y CIERRE P1/P2 — CORRESPONDENCIA CAD ↔ FEM

Trabaja exclusivamente sobre el código REAL del repositorio.

Objetivo

Auditar y, si corresponde, corregir la cadena completa:

CAD Face → Gmsh Surface → Physical Group → elementos/nodos FEM → SubModelPart → condición FEA.

El objetivo NO es rediseñar la arquitectura ni agregar nuevas funcionalidades de UI.

La arquitectura actual debe conservarse.

Contexto obligatorio

"core/face_correspondence.py" ya implementa una correspondencia geométrica determinista entre caras OCCT/CadQuery y superficies Gmsh utilizando firma geométrica, asignación global mediante Hungarian algorithm y rechazo explícito de ambigüedades.

NO reemplazar esta solución por correspondencia basada en orden de enumeración.

NO introducir IDs ficticios ni fallbacks silenciosos.

"AGENTS.md" define:

- P1 = correspondencia OCCT ↔ Gmsh.
- P2 = clasificación de frontera/caras hacia elementos FEM.
- P1 debe resolverse antes de P2.

"PROJECT_STATUS.md" es la fuente de verdad del estado actual.

1. AUDITORÍA

Inspecciona como mínimo:

- "core/face_correspondence.py"
- "core/meshing.py"
- "core/boundary.py"
- "core/conditions.py"
- "core/topo_problem.py"
- "core/kratos_adapter.py"
- "core/kratos_bridge.py"
- "core/selection.py"
- "ARQUITECTURA_SELECCION_NODOS.md"
- tests relacionados con correspondencia, meshing, physical groups y selección.

Determina con evidencia de código:

1. Si P1 está realmente resuelto o solamente parcialmente endurecido.
2. Si existen casos donde la correspondencia pueda producir una asignación incorrecta sin lanzar error.
3. Si la firma geométrica es suficiente para los casos contemplados.
4. Qué ocurre con caras idénticas, simétricas, cilíndricas, planas, pequeñas y múltiples sólidos.
5. Si una cara CAD seleccionada conserva su identidad hasta Gmsh.
6. Si los physical groups se construyen utilizando esa correspondencia.
7. Si los elementos/nodos resultantes llegan correctamente al SubModelPart correspondiente.
8. Si P2 sigue siendo provisional o ya puede considerarse válido para cargas reales.
9. Detecta cualquier fallback silencioso, asignación por orden, índice ambiguo o pérdida de identidad.
10. Comprueba que no exista una segunda implementación de la misma lógica en otro módulo.

2. REGLA DE SEGURIDAD

No ocultar errores.

Si una correspondencia no puede demostrarse de forma determinista:

- fallar explícitamente;
- proporcionar un diagnóstico útil;
- no asignar arbitrariamente otra cara;
- no utilizar el orden de enumeración como fallback.

La prioridad es CORRECCIÓN, no intentar que todos los modelos pasen.

3. CORRECCIONES

Si encuentras errores reales:

- realiza la mínima modificación necesaria;
- conserva las APIs públicas existentes siempre que sea posible;
- no cambies la arquitectura general;
- no modifiques la UI salvo que sea estrictamente necesario para corregir el flujo;
- no agregues dependencias innecesarias;
- no implementes funcionalidades futuras.

Si P1 ya está correctamente resuelto, NO lo reescribas.

En ese caso concentra el trabajo en demostrar y cerrar P2.

4. TESTS OBLIGATORIOS

Agrega o corrige tests para demostrar como mínimo:

- sólido simple con caras planas;
- sólido con caras curvas;
- múltiples caras geométricamente similares;
- geometría simétrica;
- múltiples sólidos;
- correspondencia ambigua → debe fallar explícitamente;
- mismatch CAD/Gmsh → debe fallar explícitamente;
- ningún fallback por orden;
- cara CAD → superficie Gmsh → physical group;
- physical group → elementos/nodos;
- elementos/nodos → SubModelPart;
- condición aplicada a una cara → mismos nodos/elementos esperados en el solver.

Los tests deben comprobar identidad, no solamente que "el código ejecuta".

5. VALIDACIÓN FINAL

Después de modificar:

1. Ejecuta todos los tests disponibles que sean compatibles con el entorno.
2. Ejecuta comprobación sintáctica de todo Python.
3. Comprueba imports.
4. Identifica claramente cualquier test que no pueda ejecutarse por dependencia externa.
5. No declares P1/P2 como resuelto sin evidencia.

6. RESULTADO ESPERADO

Al finalizar entrega:

A. Estado P1

"RESUELTO / PARCIAL / NO RESUELTO"

Explica exactamente por qué.

B. Estado P2

"RESUELTO / PARCIAL / NO RESUELTO"

Explica exactamente qué falta.

C. Cambios realizados

Lista únicamente archivos modificados y qué se corrigió.

D. Tests

Indica cantidad de tests ejecutados, cantidad aprobada y cualquier bloqueo externo.

E. Riesgos restantes

Lista únicamente problemas reales que puedan afectar la siguiente etapa.

F. Próximo paso

Si P1 y P2 quedan resueltos, NO inventes una nueva etapa. Determina cuál es el siguiente cuello de botella real del producto según "PROJECT_STATUS.md" y la arquitectura vigente.

Restricción fundamental

Este ciclo NO debe convertir el proyecto nuevamente en una aplicación dependiente de Onshape.

La aplicación continúa siendo:

CAD/CAE standalone → importar STEP → definir condiciones → mallar → FEA → optimización → reconstrucción CAD.

La integración con Onshape queda como una capa futura/adaptador externo y no debe contaminar el núcleo.