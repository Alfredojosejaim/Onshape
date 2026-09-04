CORRECCIÓN FUNCIONAL — SELECCIÓN, CICLO DE MODELO Y MALLADO

Audita primero el estado REAL del repositorio y corrige los siguientes problemas observados durante pruebas con un STEP complejo. No rehagas sistemas que ya funcionan ni cambies la arquitectura general. Trabaja sobre las implementaciones existentes.

1. SELECCIÓN MÚLTIPLE DE CARAS — PRIORIDAD P0

La selección de caras debe funcionar mediante clic normal, sin Ctrl ni otras teclas modificadoras.

Comportamiento requerido:

- Clic sobre una cara no seleccionada → la agrega a la selección.
- Clic nuevamente sobre una cara ya seleccionada → la quita de la selección.
- Se pueden acumular tantas caras como sea necesario.
- Todas las caras seleccionadas deben permanecer visualmente resaltadas.
- La selección debe conservarse mientras se realizan nuevos clics.
- "ConditionPanel" debe recibir correctamente TODAS las caras seleccionadas.
- No crear un segundo sistema de selección: corregir el "SelectionManager"/picking existente.
- Mantener cuerpos/solidos y caras como tipos de entidad diferenciados.

Revisar especialmente la cadena:

"VTK picking → CellId → face_index → CadEntityRef → SelectionManager → MainWindow → ConditionPanel"

2. PRECISIÓN DEL PICKING — PRIORIDAD P0

Con STEP complejos la selección de caras no es suficientemente precisa.

Audita el mecanismo actual de picking y corrígelo para que:

- el clic identifique la cara B-Rep correcta;
- caras curvas, pequeñas o próximas puedan seleccionarse correctamente;
- no se seleccione una cara vecina por error;
- el "face_index" utilizado por el viewport corresponda realmente a la cara CAD;
- se mantenga la correspondencia ya implementada entre tessellation y cara CAD;
- no reemplaces innecesariamente "FaceSignature" ni el sistema CAD↔Gmsh ya endurecido.

Añade pruebas automatizadas para geometrías con:

- varias caras;
- caras curvas;
- caras próximas;
- múltiples selecciones acumulativas.

3. CERRAR/ELIMINAR MODELO — PRIORIDAD P0

Actualmente "Reiniciar flujo" no elimina realmente el modelo cargado.

Implementa un ciclo de vida correcto:

"Importar STEP → trabajar → Cerrar modelo → estado limpio → Importar otro STEP"

Cerrar/eliminar el modelo debe:

- eliminarlo de la caché del "CADService";
- limpiar la escena 3D;
- limpiar selección;
- limpiar tessellation;
- limpiar malla;
- limpiar condiciones;
- limpiar estudios/resultados asociados;
- limpiar referencias al modelo anterior;
- actualizar Design Tree / Properties / Results / Timeline;
- dejar la aplicación lista para importar otro STEP sin reiniciarla.

No dupliques gestores de estado. Utiliza los existentes y añade únicamente los métodos necesarios.

El usuario debe poder probar sucesivamente:

"pieza_A.step → cerrar → pieza_B.step → cerrar → pieza_C.step"

sin cerrar la aplicación.

4. REINICIO VS CERRAR MODELO

No confundas:

- Reiniciar flujo: reinicia operaciones/estado del flujo.
- Cerrar modelo: elimina el documento/modelo CAD actualmente cargado.

Si actualmente no existe esta separación, implementarla de forma coherente con la arquitectura existente.

Añade una acción visible en la UI para cerrar el modelo.

5. DIAGNÓSTICO DEL MALLADOR — PRIORIDAD P0

El usuario observa geometría cúbica/escalonada en zonas curvas durante la optimización.

Audita exactamente qué mallador está utilizando el STEP.

El sistema actual puede utilizar:

"GmshTet4Mesher"

y hacer fallback a:

"ProvisionalTet4Mesher"

No asumas cuál está ocurriendo.

Implementa diagnóstico explícito que permita saber:

- qué mallador fue utilizado;
- por qué se produjo fallback, si ocurrió;
- número de nodos;
- número de elementos;
- tamaño objetivo;
- información suficiente para diagnosticar el STEP complejo.

No ocultes errores de Gmsh detrás de un fallback silencioso.

6. GEOMETRÍA CURVA

Si los cubos observados provienen del "ProvisionalTet4Mesher", NO intentes solucionar el problema modificando el optimizador.

Primero determina y demuestra el origen.

Si Gmsh está funcionando, analiza la discretización resultante y determina si el problema está en:

- generación de malla;
- visualización de la malla;
- reconstrucción del resultado;
- representación de densidades.

Si Gmsh está fallando y se está utilizando el mallador provisional, identifica la causa concreta del fallo y corrígela si es una regresión o integración defectuosa.

El "ProvisionalTet4Mesher" sigue siendo un fallback, no debe convertirse accidentalmente en el mallador principal.

7. OPTIMIZACIÓN EXPERIMENTAL

La optimización actualmente puede ejecutarse aunque el flujo completo todavía no esté terminado.

No elimines el motor experimental.

Pero evita presentar el resultado como una optimización CAD/CAE final si todavía existen limitaciones conocidas.

Mantén la ejecución disponible para pruebas, pero registra claramente el estado experimental cuando corresponda.

8. PRUEBAS Y REGRESIÓN

Antes de terminar:

1. Ejecuta la suite existente.
2. Añade tests específicos para:
   - selección múltiple mediante clic normal;
   - toggle de selección;
   - picking correcto de varias caras;
   - limpieza completa al cerrar modelo;
   - importar un segundo STEP después de cerrar el primero;
   - detección explícita del mallador utilizado;
   - comportamiento ante fallback de Gmsh.
3. No rompas las pruebas existentes de:
   - correspondencia CAD↔Gmsh;
   - volfrac;
   - halo;
   - FEA NumPy/SciPy;
   - Kratos;
   - condiciones;
   - historial/timeline.

REGLAS

- Primero audita, después modifica.
- No rehagas arquitectura existente sin necesidad.
- No dupliques managers.
- No elimines funcionalidad existente.
- No implementes nuevas características de optimización en esta tarea.
- No conviertas el "ProvisionalTet4Mesher" en solución definitiva.
- Corrige las causas reales, no solamente los síntomas.
- Mantén Python/PySide6/VTK/Gmsh/Kratos y la arquitectura actual.
- Al finalizar, indica exactamente:
  1. archivos modificados;
  2. problemas corregidos;
  3. causa encontrada del picking;
  4. causa encontrada de los cubos;
  5. comportamiento del cierre de modelo;
  6. resultado de los tests;
  7. cualquier limitación que permanezca.