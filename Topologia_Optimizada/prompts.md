IMPLEMENTACIÓN — CIERRE DEL MOTOR DUAL FEA

Audita y continúa el desarrollo directamente sobre el estado ACTUAL de "Alfredojosejaim/Onshape", carpeta "Topologia_Optimizada".

OBJETIVO

Cerrar la parte pendiente del motor dual FEA:

Motor local NumPy/SciPy ↔ Motor Kratos

La arquitectura dual ya existe. NO la reemplaces.

El objetivo es que ambos motores puedan recibir el mismo problema físico y que la aplicación pueda utilizarlos de forma verificable, diferenciando claramente:

- cálculo local;
- cálculo Kratos;
- comparación entre ambos;
- disponibilidad/limitaciones reales del backend.

1. AUDITORÍA FOCALIZADA

Revisa únicamente el flujo relacionado con:

- "core/fea.py"
- "core/solver_interface.py"
- "core/kratos_adapter.py"
- "core/kratos_bridge.py"
- "core/boundary.py"
- "core/conditions.py"
- "core/meshing.py"
- "desktop/pipeline/controller.py"
- tests FEA/Kratos/bridge/benchmarks.

Determina exactamente:

1. cómo el motor local construye y resuelve "K·u=f";
2. cómo se construye el mismo problema para Kratos;
3. cómo las restricciones llegan a ambos motores;
4. cómo las cargas llegan a ambos motores;
5. dónde se pierde actualmente la carga en la ruta Kratos;
6. si el problema está en el tipo de condición Kratos, el ensamblado, el "ModelPart", el "BuilderAndSolver", el orden de aplicación o el mecanismo de carga;
7. si existe una solución compatible con Kratos 10.4.3 sin introducir una dependencia externa innecesaria.

2. REGLA FUNDAMENTAL

No aceptes como solución:

- falsificar resultados;
- copiar el resultado local dentro de Kratos;
- introducir desplazamientos/compliance artificiales;
- declarar "success=True" cuando el RHS real no contiene la carga;
- ocultar el warning "setting the RHS to zero";
- modificar los tests para aceptar un resultado físicamente incorrecto.

Si Kratos 10.4.3 realmente impone una limitación concreta, demuestra técnicamente dónde ocurre y busca la forma correcta de construir/aplicar la carga utilizando las capacidades disponibles en esa versión.

3. CARGAS

La ruta Kratos debe soportar correctamente las cargas que el sistema ya modela.

Verifica especialmente:

- cargas puntuales;
- cargas distribuidas/superficiales;
- dirección;
- magnitud;
- selección geométrica de la cara;
- mapeo CAD → nodos/entidades Kratos;
- correspondencia con "physical_groups".

La carga debe terminar formando parte del sistema físico que Kratos ensambla.

No basta con almacenar "FORCE_X/Y/Z" en nodos si el mecanismo de solución utilizado no las consume.

4. RESTRICCIONES

Mantén el mecanismo existente de:

condición CAD → selección → nodos → condición Kratos

y verifica que no se esté aplicando accidentalmente a todos los nodos.

Una condición explícita que no pueda resolverse debe producir un error claro, no una región alternativa silenciosa.

5. MOTOR DUAL

Mantén una interfaz común para ambos motores.

El mismo problema de entrada debe poder expresarse como:

Mesh
Material
Boundary Conditions
Loads

y enviarse a:

Local FEA
Kratos FEA

El resultado debe conservar una estructura compatible para poder comparar:

- success/status;
- desplazamientos;
- compliance;
- energía elemental;
- número de nodos;
- número de elementos;
- información de convergencia.

6. VALIDACIÓN CROSS-ENGINE

Una vez que ambos motores puedan resolver un caso físicamente válido:

crear una prueba de regresión que ejecute el MISMO caso en ambos motores.

Comparar con tolerancias explícitas:

- desplazamientos;
- compliance;
- magnitudes relevantes de energía.

No exigir igualdad exacta: los métodos numéricos pueden producir pequeñas diferencias.

La prueba debe detectar una regresión real del bridge, de las cargas, las restricciones o el ensamblado.

7. CONVERGENCIA

Audita además que "success=True" represente convergencia real.

Especialmente en Kratos:

- no confiar ciegamente en "IsConverged()";
- no utilizar un residual que no represente realmente el residual del sistema;
- comprobar que un solve deliberadamente insuficiente no sea reportado como correctamente convergido.

Si el código actual ya tiene una estrategia de verificación/re-resolución, consérvala y corrígela únicamente si la auditoría demuestra un problema.

8. IMPLEMENTACIÓN

Después de identificar la causa:

1. Implementa la corrección mínima necesaria.
2. Mantén "local" como motor autocontenido.
3. Mantén Kratos como segundo motor.
4. No reemplaces el FEA local.
5. No migres el proyecto a C++.
6. No rediseñes la UI.
7. No modifiques CAD, viewport o navegación salvo que exista una dependencia directa demostrada.
8. No elimines funcionalidades existentes.
9. Añade tests específicos para la corrección.
10. Ejecuta los tests FEA/Kratos relacionados.
11. Ejecuta posteriormente la suite completa.

9. RESULTADO FINAL

Al terminar informa claramente:

Estado del motor local

Qué está realmente funcionando.

Estado del motor Kratos

Qué está realmente funcionando y qué fue corregido.

Causa raíz

Por qué el RHS estaba quedando en cero, si continúa ocurriendo o cómo fue solucionado.

Cross-engine

Si ambos motores ya pueden resolver el mismo caso físico y compararse automáticamente.

Tests

Cantidad ejecutada y resultado.

Pendientes

Solo problemas reales restantes del motor dual.

No declares el motor dual como COMPLETADO solamente porque existan dos backends. Debe existir una ruta verificable:

mismo problema → dos motores → resultados físicos → comparación automatizada.