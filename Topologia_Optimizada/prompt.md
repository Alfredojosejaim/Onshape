SIGUIENTE ETAPA — AVANCE ACELERADO DEL PRODUCTO

El proyecto ya superó la fase principal de validación del motor.

Kratos Multiphysics está integrado como motor FEA y el flujo principal ya fue probado con geometría STEP real.

A partir de este momento comienza una fase de construcción acelerada del producto.

1. PRIMER PASO

Antes de modificar código:

1. Leer "README.md".
2. Leer "metodologia.md".
3. Revisar el estado actual del repositorio.
4. Revisar la documentación existente de implementación y pruebas.
5. Identificar qué funcionalidades ya están realmente funcionando.
6. Identificar cuál es el siguiente componente necesario para convertir el motor actual en una aplicación funcional.

No repetir investigaciones ya cerradas.

No volver a evaluar la decisión de Kratos.

No volver a investigar el funcionamiento básico del motor FEA.

No repetir pruebas históricas salvo que sean necesarias para detectar una regresión.

---

2. OBJETIVO

A partir del estado actual, avanzar hacia el producto funcional siguiendo esta dirección:

STEP REAL
   ↓
CADModel
   ↓
MALLA
   ↓
ESTUDIO
   ↓
MATERIAL
   ↓
CARGAS
   ↓
RESTRICCIONES
   ↓
FEA KRATOS
   ↓
RESULTADOS
   ↓
VISUALIZACIÓN
   ↓
OPTIMIZACIÓN
   ↓
RESULTADO FINAL

La prioridad es convertir progresivamente el motor ya funcional en un flujo de aplicación utilizable.

---

3. REGLA DE SELECCIÓN DE LA SIGUIENTE TAREA

Después de la auditoría inicial:

- determinar cuál es la funcionalidad pendiente más importante;
- determinar sus dependencias;
- verificar que esas dependencias ya existan;
- implementar esa funcionalidad.

No crear funcionalidades futuras si existe una dependencia anterior todavía incompleta.

Priorizar siempre:

funcionalidad necesaria → integración → prueba → siguiente funcionalidad.

No priorizar por cantidad de código ni por facilidad de implementación.

---

4. REGLA ESPECIAL PARA EL MAPEO CAD → NODOS

El mecanismo de mapeo CAD → nodos ya existe.

Mantener:

CAD Face
   ↓
BoundaryConditionMapper
   ↓
Mesh Nodes
   ↓
Kratos

No rediseñarlo.

Sin embargo, si durante la implementación se detecta que una cara CAD válida no puede mapearse correctamente a nodos:

NO ocultar el problema mediante un fallback automático que pueda producir una condición FEA físicamente incorrecta.

Registrar el fallo y aplicar estrictamente el protocolo de bloqueo de "metodologia.md".

---

5. PROTOCOLO DE BLOQUEO

No utilizar ensayo y error ilimitado.

Si aparece un error:

Corrección autónoma

Se permite una única corrección si:

- la causa es evidente;
- la solución está respaldada por el código o documentación;
- no implica especulación;
- puede verificarse inmediatamente.

Después ejecutar nuevamente la prueba.

Bloqueo

Si la causa no es evidente o la primera corrección falla:

DETENERSE.

No generar múltiples implementaciones alternativas.

Registrar:

- error;
- traceback;
- archivo;
- línea;
- función;
- entrada utilizada;
- comportamiento esperado;
- comportamiento obtenido;
- contexto técnico;
- hipótesis disponible.

Marcarlo como:

BLOQUEADO
REQUIERE INVESTIGACIÓN

y continuar únicamente con otra tarea independiente que no dependa de ese bloqueo.

---

6. TESTING

Cada funcionalidad implementada debe tener la prueba adecuada.

Cuando sea posible:

implementación
     ↓
test
     ↓
resultado
     ↓
evidencia

Utilizar geometría STEP real cuando la funcionalidad dependa del flujo CAD completo.

No utilizar mocks como evidencia de funcionamiento real.

---

7. DOCUMENTACIÓN

Después de cada intervención significativa actualizar la documentación correspondiente.

Registrar:

- qué se implementó;
- archivos modificados;
- pruebas ejecutadas;
- resultados;
- errores;
- bloqueos;
- funcionalidades completadas;
- siguiente tarea.

La documentación debe representar el estado real del código.

---

8. CONTROL DEL ALCANCE

NO implementar durante esta etapa:

- sistema de suscripción;
- protección comercial;
- integración con Onshape;
- integración con otros CAD;
- Rust;
- migración completa a C++;
- funcionalidades que no sean necesarias para avanzar hacia el producto funcional.

Estas decisiones ya fueron analizadas y se implementarán cuando corresponda.

---

9. REGLA DE VELOCIDAD

A partir de esta etapa:

NO SOBREAUDITAR.

La auditoría inicial debe ser suficiente para conocer el estado actual y elegir la siguiente tarea.

Después:

AUDITAR
   ↓
ELEGIR SIGUIENTE FUNCIÓN
   ↓
IMPLEMENTAR
   ↓
PROBAR
   ↓
DOCUMENTAR
   ↓
CONTINUAR

No detener el proyecto para volver a analizar decisiones ya cerradas.

---

10. CRITERIO DE FINALIZACIÓN

Al terminar esta intervención:

1. Debe existir una funcionalidad nueva real o una corrección concreta.
2. Debe estar integrada con la arquitectura existente.
3. Debe haber sido probada.
4. Debe quedar documentada.
5. Debe indicarse claramente cuál es el siguiente paso.

Si aparece un bloqueo técnico desconocido, detener únicamente esa línea de trabajo y documentarlo según "metodologia.md".

PRINCIPIO DE ESTA ETAPA

«El motor ya fue validado. Ahora hay que construir el producto alrededor de él.»

Avanzar de forma incremental, verificable y rápida.