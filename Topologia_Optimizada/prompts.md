IMPLEMENTACIÓN — SISTEMA DE HERRAMIENTAS Y CONDICIONES CAD

Trabaja directamente sobre el repositorio actual. No hagas una investigación extensa ni rediseñes el proyecto desde cero. Primero inspecciona brevemente la arquitectura existente y reutiliza sus sistemas actuales de selección, comandos, Features, FeatureHistory, Timeline, DesignTree, CAD y viewport.

Objetivo

Comenzar la implementación del sistema funcional de herramientas CAD/CAE que servirá de base para Optimización y Pruebas.

La arquitectura debe separar:

1. Herramientas principales
   
   - Optimización
   - Pruebas

2. Condiciones/subherramientas reutilizables
   
   - Carga
   - Elasticidad
   - Unión (Boolean)
   - Obstrucciones
   - Regiones protegidas

3. Historial de operaciones
   
   - Cada operación aplicada debe integrarse con el sistema existente de "Command → Feature → FeatureHistory → Timeline/DesignTree".
   - No crear sistemas paralelos de historial, selección o árbol.

Modelo conceptual

Las condiciones deben poder existir como objetos/features independientes y posteriormente ser seleccionadas por un estudio de optimización.

Ejemplo:

Estudio
 └── Optimización estructural
      ├── Pieza(s)
      ├── Carga 1
      ├── Elasticidad 1
      ├── Obstrucción 1
      └── Región protegida 1

El objetivo es que Optimización no tenga que recrear internamente estas condiciones, sino consumir las condiciones previamente creadas.

Implementación inicial

Implementa primero las bases necesarias para:

1. Carga

Debe permitir:

- seleccionar una o varias caras;
- definir orientación respecto a un plano:
  - paralelo;
  - perpendicular;
  - ángulo;
- definir el sentido de la dirección;
- introducir una magnitud numérica;
- permitir también el estado "indeterminado" como valor válido del modelo.

La herramienta debe guardar toda esta configuración como una condición reutilizable.

2. Elasticidad

Debe permitir:

- seleccionar una o varias caras;
- definir el rango/magnitud de flexión en mm;
- guardar la configuración como condición reutilizable.

3. Obstrucciones

Debe permitir:

- seleccionar una o varias piezas;
- definir opcionalmente un offset en mm;
- guardar la configuración como condición reutilizable.

4. Regiones protegidas

Utilizar el concepto Regiones protegidas en lugar de "Caras a conservar".

Debe permitir:

- seleccionar una o varias caras;
- almacenar esas referencias como geometría que la optimización no debe modificar.

Diseñar el modelo de forma que posteriormente pueda ampliarse para proteger regiones geométricas más complejas.

5. Unión / Boolean

Integrar la herramienta booleana existente o crearla únicamente si todavía no existe una implementación funcional.

Debe permitir:

- seleccionar dos o más piezas diferentes;
- seleccionar operación:
  - Unión;
  - Corte;
  - Intersección;
- opción "Conservar herramientas";
- ejecutar o cancelar;
- registrar el resultado mediante el sistema existente de Features/Commands/Timeline.

No crear un segundo sistema de selección ni de historial.

Optimización

Preparar únicamente la arquitectura necesaria para que posteriormente pueda recibir:

- Optimización estructural;
- Optimización generativa.

La optimización estructural deberá poder recibir:

- una o varias piezas;
- condiciones previamente creadas;
- porcentaje/parámetros propios de optimización.

La optimización generativa debe quedar preparada arquitectónicamente para dos escenarios:

1. optimizar una pieza ya existente;
2. recibir Pieza A + Pieza B y generar la geometría CAD que conecta físicamente ambas piezas mientras dicha geometría es optimizada.

No implementes todavía el algoritmo completo de diseño generativo. Solo deja correctamente separada la arquitectura para incorporarlo posteriormente.

Pruebas

Crear solamente la categoría/base extensible de "Pruebas".

No inventar ni implementar todavía los tipos concretos de pruebas, ya que serán definidos posteriormente.

Reglas importantes

- Reutiliza la arquitectura existente.
- No reemplaces sistemas funcionales sin necesidad.
- No dupliques "SelectionManager", "FeatureHistory", "Timeline", "DesignTree" ni servicios equivalentes.
- Mantén separación entre modelo, lógica de comandos y UI.
- Las herramientas deben poder funcionar independientemente de la interfaz visual definitiva.
- No hagas un rediseño visual completo.
- No conviertas el proyecto a C++ ni cambies de framework salvo que exista una necesidad técnica real y justificada.
- Mantén Python/PySide6/VTK donde ya sean adecuados.
- No elimines funcionalidades existentes.
- Si una función existente está incompleta, intégrala y corrígela en lugar de crear otra paralela.
- Mantén compatibilidad con el flujo CAD/STEP existente.

Validación

Después de implementar:

1. Ejecuta las pruebas existentes.
2. Añade pruebas unitarias para los nuevos modelos/condiciones cuando sea necesario.
3. Comprueba que las herramientas pueden:
   - crear una condición;
   - almacenar su configuración;
   - recuperarla posteriormente;
   - integrarse en el historial;
   - coexistir con las operaciones CAD existentes.
4. Comprueba que una optimización pueda consultar las condiciones creadas sin duplicarlas.
5. Verifica que no existan sistemas paralelos de selección/historial.

Al finalizar, informa brevemente:

- qué archivos modificaste;
- qué arquitectura reutilizaste;
- qué funciones quedaron implementadas;
- qué quedó preparado pero pendiente;
- resultado de las pruebas.

Prioridad: implementación funcional y arquitectura limpia. No detener el trabajo para realizar investigaciones innecesarias.