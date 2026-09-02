CORRECCIÓN E INTEGRACIÓN — SISTEMA DE CONDICIONES CAD/CAE

Trabaja directamente sobre el repositorio actual. No reconstruyas la arquitectura desde cero y no hagas investigación extensa. Audita únicamente lo necesario para identificar las inconsistencias descritas y corrígelas sobre la implementación existente.

Objetivo

Consolidar el sistema actual de condiciones CAD/CAE y dejarlo correctamente integrado con el pipeline, UI, historial y estudios de optimización.

La arquitectura existente debe mantenerse:

SelectionManager
      ↓
Command
      ↓
Condition
      ↓
ConditionManager
      ↓
FeatureHistory / Document
      ↓
Optimization Study

Las condiciones son objetos reutilizables y los estudios deben referenciarlas mediante sus IDs, sin duplicarlas.

1. Corregir ProtectedRegion

Revisa la discrepancia actual entre:

- "core/commands.py"
- "desktop/ui/panels/condition_panel.py"
- "test_conditions.py"

Asegúrate de que "ProtectedRegionCommand" exista, esté correctamente registrado en "CommandType" y "FeatureType", pueda construir un "ProtectedRegion" y sea compatible con el "ConditionPanel".

Debe permitir:

- seleccionar una o varias caras;
- almacenar referencias geométricas;
- validar que exista al menos una selección;
- crear la condición reutilizable;
- registrarla mediante el pipeline existente.

No crear otro sistema de selección.

2. Consolidar la validación de comandos

Revisa el flujo:

PipelineController.execute_command()
        ↓
command.validate()
        ↓
_execute_condition()

Evita realizar innecesariamente la misma validación dos veces.

Mantén una única responsabilidad clara para la validación, sin romper los comandos existentes.

3. Consolidar ConditionManager

Verifica que:

- "ConditionManager" sea la única fuente de objetos "Condition";
- las condiciones tengan IDs estables;
- los estudios almacenen únicamente IDs;
- "consume_conditions()" resuelva las condiciones existentes;
- una misma condición nunca sea copiada/duplicada al incorporarla a un estudio;
- eliminar o modificar la referencia de un estudio no destruya la condición compartida.

Mantener compatibilidad con serialización/deserialización existente.

4. Integrar correctamente Optimización estructural

Actualmente "TopologyOptimizationStudy" ya permite almacenar:

parts
conditions

pero su validación todavía depende del sistema antiguo de "loads" y "constraints".

Corrige esto para que el estudio pueda utilizar las condiciones reutilizables como fuente principal de configuración.

Debe poder representar conceptualmente:

Optimización estructural
├── Pieza(s)
├── Carga
├── Elasticidad
├── Obstrucciones
└── Regiones protegidas

Las condiciones deben ser seleccionadas desde las existentes, no recreadas dentro del estudio.

No reemplaces todavía el solver SIMP. Solo integra correctamente sus entradas con esta nueva arquitectura.

5. Preparar Optimización generativa

Revisa "GenerativeDesignStudy" y conserva su arquitectura actual.

Debe continuar soportando:

Escenario A

Pieza existente
      ↓
Condiciones
      ↓
Generación/optimización

Escenario B

Pieza A + Pieza B
      ↓
Espacio disponible
      ↓
Generación de geometría
      ↓
Optimización
      ↓
CAD resultante

No implementar todavía el algoritmo completo de generación de geometría.

Solo garantizar que el estudio pueda recibir correctamente piezas objetivo y condiciones reutilizables.

6. Boolean

No reconstruir Boolean.

Revisa únicamente que:

- continúe utilizando el "SelectionManager" existente;
- seleccione target + herramientas;
- ejecute Union/Cut/Intersection;
- respete "keep_tools";
- registre el resultado mediante el FeatureHistory existente;
- sea compatible con las condiciones y estudios.

No crear otro historial ni otro sistema de Features.

7. UI

Corrige únicamente lo necesario para que las herramientas existentes funcionen con la arquitectura consolidada.

No realizar todavía un rediseño visual.

El "ConditionPanel" debe poder crear correctamente:

- Carga
- Elasticidad
- Obstrucción
- Regiones protegidas

y entregar los comandos al pipeline existente.

8. Pruebas

Ejecuta la suite existente y corrige los tests que estén desactualizados respecto a la arquitectura real.

Añade únicamente las pruebas necesarias para verificar:

- ProtectedRegionCommand;
- creación y validación de condiciones;
- registro en ConditionManager;
- registro en FeatureHistory;
- serialización;
- ausencia de duplicación;
- consumo de condiciones por "TopologyOptimizationStudy";
- consumo de condiciones por "GenerativeDesignStudy";
- coexistencia con Boolean.

Restricciones

- No reescribir el proyecto.
- No crear sistemas paralelos.
- No crear otro SelectionManager.
- No crear otro FeatureHistory.
- No crear otro Timeline/DesignTree.
- No eliminar funcionalidad existente.
- No cambiar PySide6/VTK sin necesidad técnica real.
- No implementar todavía los tipos concretos de "Pruebas".
- No implementar todavía el algoritmo completo de Generative Design.
- No hacer rediseño visual.
- No detenerse para investigación innecesaria.

Validación final

Antes de terminar:

1. Ejecuta todos los tests.
2. Corrige los errores encontrados.
3. Comprueba que las condiciones se crean, almacenan y recuperan correctamente.
4. Comprueba que Optimización estructural puede consumirlas por ID.
5. Comprueba que Generative Design puede consumirlas por ID.
6. Comprueba que Boolean y las condiciones utilizan el mismo historial.
7. Comprueba que no existen implementaciones duplicadas de estos sistemas.

Al finalizar, informa solamente:

- archivos modificados;
- problemas corregidos;
- funcionalidades integradas;
- tests ejecutados y resultado;
- pendientes reales.

Prioridad: corregir → integrar → probar → dejar listo para la siguiente etapa. No reconstruir lo que ya funciona.