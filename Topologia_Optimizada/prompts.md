ETAPA — CERRAR SELECCIÓN DE PIEZA Y EJECUCIÓN ESTRUCTURAL REAL

Trabaja directamente sobre el repositorio actual.

La arquitectura CAD/CAE base ya existe. No reconstruyas sistemas funcionales. Esta etapa se concentra exclusivamente en cerrar:

SELECCIÓN CAD
↓
"TopologyOptimizationStudy.parts"
↓
"PipelineController"
↓
MALLA
↓
CONDICIONES
↓
SIMP
↓
RESULTADO

1. Auditoría focalizada

Revisa únicamente:

- "desktop/ui/panels/study_panel.py"
- "desktop/ui/main_window.py"
- "desktop/pipeline/controller.py"
- "core/optimization_studies.py"
- "core/cad_entity.py"
- "desktop/viewport/selection.py"
- "core/conditions.py"
- tests relacionados.

No hagas una auditoría general.

2. Selección real de la pieza

Actualmente "StudyPanel" representa la pieza objetivo mediante texto y permite implícitamente utilizar el primer sólido.

Esto debe corregirse.

El usuario debe poder seleccionar uno o más sólidos reales desde el viewport y esas selecciones deben convertirse en "CadEntityRef".

Cada referencia debe conservar como mínimo:

- "entity_type = SOLID";
- "model_id";
- "solid_id" o identificador estable equivalente.

Después deben almacenarse mediante:

"study.add_part(ref)"

No utilizar el primer sólido automáticamente cuando existe una selección explícita.

No crear otro "SelectionManager".

3. Integración UI → selección → estudio

Modifica únicamente lo necesario para que el flujo sea:

1. importar STEP;
2. iniciar creación de estudio;
3. activar selección de pieza;
4. seleccionar sólido(s) en viewport;
5. mostrar las piezas seleccionadas;
6. confirmar;
7. crear "TopologyOptimizationStudy.parts" con esas referencias.

Reutiliza el sistema de selección existente y sus callbacks/mecanismos actuales.

No crear una interfaz paralela ni rediseñar la aplicación.

4. Validación de piezas

El estudio debe rechazar:

- cero piezas;
- entidades que no sean "SOLID";
- referencias incompatibles con el "model_id" actual;
- sólidos imposibles de resolver.

Los errores deben llegar claramente a la UI.

No basta con comprobar que "parts" tenga elementos: validar la coherencia de las referencias cuando la información disponible lo permita.

5. Hacer que "study.parts" gobierne la ejecución

Existe actualmente una discrepancia:

"TopologyOptimizationStudy" posee "parts", pero "PipelineController.execute_study()" continúa utilizando el estado global:

- "self.model_id"
- "self.mesh_nodes"
- "self.mesh_elements"

Corrige esto.

Para Optimización estructural, el sólido seleccionado en "study.parts" debe determinar inequívocamente la geometría utilizada por el estudio.

Si el modelo contiene varios sólidos:

- no asumir el primero;
- resolver el sólido seleccionado;
- utilizarlo como dominio de análisis.

No implementar todavía análisis multi-body avanzado. El objetivo es que el sólido seleccionado sea el dominio correcto y determinista.

6. Malla automática

"execute_study()" debe garantizar que exista una malla válida antes de ejecutar SIMP.

Si no existe:

- utilizar el generador de malla existente;
- generar la malla;
- actualizar "self.mesh", "self.mesh_nodes" y "self.mesh_elements";
- continuar automáticamente con el estudio.

No crear otro sistema de mallado.

La ejecución desde UI debe continuar utilizando "run_in_background()".

7. Condiciones reutilizables

Mantener:

"study.conditions" → IDs
"ConditionManager" → objetos reales

Al ejecutar:

"study.consume_conditions(self.conditions)"

debe obtenerse el conjunto real de condiciones y pasarse al camino de optimización.

Verifica específicamente:

- carga → fuerzas/nodos/DOF;
- soporte/restricción → DOF fijos;
- regiones protegidas → elementos preservados;
- obstrucciones → elementos vacíos cuando puedan mapearse.

Una condición no mapeable debe generar un estado/error explícito.

Nunca producir silenciosamente un resultado físicamente incorrecto.

No crear otro sistema de condiciones ni otro mapper si ya existe infraestructura reutilizable.

8. Resultado

Mantener exactamente el sistema existente:

SIMP
↓
"StudyResult"
↓
"Document.add_result()"
↓
"ResultsPanel"
↓
"Viewport3D.show_density()"

El resultado debe corresponder al sólido seleccionado.

No crear otro sistema de resultados.

9. Tests

Añade o adapta únicamente los tests necesarios para demostrar:

1. selección de un sólido → "CadEntityRef";
2. "study.parts" recibe la referencia seleccionada;
3. no se acepta una entidad que no sea "SOLID";
4. no se acepta un sólido incompatible;
5. selección de múltiples sólidos no duplica referencias;
6. las condiciones continúan referenciándose por ID;
7. las condiciones llegan realmente a "run_optimization(..., conditions=...)";
8. una condición de carga llega al solver;
9. una restricción llega a los DOF fijos;
10. preservados/obstrucciones se transmiten correctamente cuando son mapeables;
11. una condición no soportada no produce un resultado silencioso;
12. un estudio sin malla genera automáticamente la malla;
13. el estudio utiliza la pieza seleccionada y no el primer sólido;
14. "StudyResult" llega al "Document";
15. las densidades quedan disponibles para "Viewport3D";
16. la ejecución pesada desde UI continúa en background.

Utiliza mocks/stubs cuando sea apropiado para evitar geometrías pesadas innecesarias.

10. Compatibilidad

No romper:

- Boolean;
- Conditions;
- "ConditionManager";
- "SelectionManager";
- "FeatureHistory";
- Timeline;
- Document;
- Generative Design;
- PySide6;
- VTK;
- flujos heredados basados en "forces"/"constraints".

No modificar algoritmos de optimización salvo que sea imprescindible para conectar correctamente los datos.

Restricciones estrictas

- No crear otro "SelectionManager".
- No crear otro "ConditionManager".
- No crear otro "PipelineController".
- No crear otro sistema de malla.
- No crear otro sistema de resultados.
- No migrar a C++.
- No introducir dependencias innecesarias.
- No rediseñar visualmente la aplicación.
- No hacer investigación extensa.
- No reconstruir sistemas existentes.
- No considerar la tarea terminada solo porque los tests unitarios pasan.

Validación final

Ejecuta la suite existente y los nuevos tests.

Después verifica el encadenamiento:

STEP
↓
selección real de sólido
↓
"CadEntityRef"
↓
"study.parts"
↓
condiciones por ID
↓
validación
↓
malla automática si hace falta
↓
condiciones → solver
↓
SIMP
↓
"StudyResult"
↓
Document
↓
ResultsPanel / Viewport

Comprueba específicamente que:

- no se utilice implícitamente el primer sólido;
- la malla corresponda al dominio seleccionado;
- las condiciones no se dupliquen;
- Boolean siga funcionando;
- Generative Design siga funcionando;
- la UI no se bloquee.

Actualiza "PROJECT_STATUS.md" únicamente con funcionalidades realmente verificadas.

Al finalizar informa solamente:

- archivos modificados;
- problemas reales encontrados;
- correcciones realizadas;
- flujo de selección → estudio → solver conseguido;
- tests ejecutados y resultado;
- pendientes reales.

Prioridad: selección real → dominio correcto → malla → condiciones → solver → resultado → pruebas.