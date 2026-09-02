ETAPA FINAL — CIERRE DE OPERACIONES CAD Y CABOS SUELTOS

Objetivo

Audita y completa exclusivamente los faltantes detectados en la última auditoría del repositorio.

Repositorio: "Alfredojosejaim/Onshape"
Proyecto: "Topologia_Optimizada"

No rehagas arquitectura existente, no migres de lenguaje y no reemplaces sistemas funcionales. El objetivo es cerrar las operaciones CAD que quedaron parcialmente implementadas y dejar el flujo listo para avanzar a la siguiente etapa.

---

1. HALLAZGOS DE LA AUDITORÍA — VERIFICAR PRIMERO

A. "core/commands.py"

Existen comandos para:

- "TransformCommand"
- "MirrorCommand"
- "PatternCommand"

pero deben verificarse contra su ejecución real.

B. "desktop/pipeline/controller.py"

"execute_command()" actualmente tiene ejecución específica para Boolean y Conditions, pero Transform/Mirror/Pattern pueden terminar únicamente registrándose como "Feature".

Debe corregirse: esas operaciones deben ejecutarse realmente a través del pipeline cuando corresponda.

Flujo esperado:

"Command → PipelineController → CADService → nuevo resultado CAD → FeatureHistory/Document"

C. "services/cad_service.py"

Ya existen operaciones geométricas para:

- transformación;
- espejo;
- patrón lineal;
- patrón rectangular;
- patrón circular.

No reemplazarlas.

Hallazgo específico: el patrón circular dispone de un parámetro "center" en la arquitectura del comando, pero la implementación CAD aparentemente rota alrededor del origen.

Verifica esto directamente en el código y corrígelo si se confirma.

D. "desktop/ui/main_window.py"

No se encontraron handlers equivalentes a las operaciones Boolean/Study para:

- Transform;
- Mirror;
- Pattern.

Verifica si existen otras interfaces o rutas alternativas antes de crear nuevas.

Si realmente faltan, intégralas reutilizando los Commands y CADService existentes.

E. Historial / árbol / viewport

Debe comprobarse que una operación CAD ejecutada realmente:

1. modifica o genera el modelo correcto;
2. actualiza "model_id"/estado CAD;
3. refresca el viewport;
4. invalida correctamente malla/resultados si la geometría cambió;
5. registra la operación en "FeatureHistory";
6. aparece en "DesignTree";
7. mantiene coherencia con "Document" y Timeline.

No crear managers paralelos.

---

2. IMPLEMENTACIÓN REQUERIDA

Transform

Cerrar el flujo completo de Transform:

- UI para configurar los parámetros que el comando ya soporte;
- selección de cuerpos mediante el "SelectionManager" existente;
- creación del "TransformCommand";
- validación;
- ejecución real mediante "PipelineController";
- llamada al "CADService";
- actualización del modelo;
- actualización del viewport;
- registro en FeatureHistory/Document/DesignTree;
- invalidación de malla y resultados dependientes de la geometría.

No inventar parámetros que el modelo actual no necesite.

Mirror

Cerrar el mismo flujo para Mirror:

- selección de cuerpo;
- selección/configuración del plano o eje según la arquitectura existente;
- "MirrorCommand";
- ejecución real;
- actualización CAD/UI/historial;
- tests.

Pattern

Cerrar el flujo para Pattern:

- selección de cuerpo;
- configuración del tipo existente;
- cantidad;
- dirección/eje según corresponda;
- separación/ángulo según el tipo;
- ejecución real;
- actualización completa del modelo.

Debe soportar únicamente los tipos que ya estén definidos por la arquitectura actual. No crear funcionalidades ficticias solamente para aparentar soporte.

Patrón circular

Verificar específicamente el parámetro "center".

Si actualmente la geometría rota siempre alrededor de "(0,0,0)", corregirla para utilizar el centro definido por el usuario/comando.

Agregar una prueba que demuestre que un patrón circular con centro distinto del origen produce la geometría esperada.

---

3. INTEGRACIÓN CON EL MODELO

Cuando una operación CAD modifica la geometría:

- el nuevo resultado debe convertirse en el modelo activo;
- actualizar "model_id" y cualquier estado/cache relacionado;
- limpiar o invalidar malla FEM existente si ya no corresponde;
- limpiar/invalidate resultados FEA/TopOpt dependientes;
- actualizar tessellation;
- refrescar viewport;
- sincronizar DesignTree;
- conservar la operación como Feature.

No eliminar silenciosamente la historia anterior.

Si la arquitectura existente utiliza un mecanismo concreto para reemplazar el modelo activo, reutilizarlo.

---

4. SELECCIÓN

Reutilizar exclusivamente el "SelectionManager" existente.

No crear otro sistema de selección para Transform/Mirror/Pattern.

Las selecciones deben utilizar "CadEntityRef" cuando corresponda y respetar las validaciones existentes.

Validar al menos:

- ninguna pieza seleccionada;
- selección inválida;
- referencia inexistente;
- parámetros geométricos inválidos;
- operación que no pueda ejecutarse sobre la geometría seleccionada.

Los errores deben regresar como "CommandResult"/mecanismo existente y mostrarse correctamente en UI.

---

5. TESTS

No te limites a tests de construcción del Command.

Agregar pruebas que cubran el flujo real hasta donde permita la arquitectura actual:

Transform

- validación;
- ejecución CAD;
- resultado geométrico;
- actualización de modelo;
- FeatureHistory.

Mirror

- validación;
- ejecución CAD;
- resultado geométrico;
- historial.

Pattern

- lineal;
- rectangular si está definido;
- circular;
- especialmente centro circular distinto del origen.

Integración

Comprobar que después de una operación CAD:

- el modelo activo cambia correctamente;
- la malla anterior no se conserva incorrectamente;
- los resultados anteriores no se presentan como pertenecientes a la nueva geometría;
- el DesignTree refleja la operación.

Ejecutar también la suite completa existente.

---

6. AUDITORÍA DE CABOS ADICIONALES

Mientras implementas lo anterior, realiza una revisión focalizada, no una auditoría completa, buscando errores del mismo tipo:

- código que aparenta ejecutar una operación pero solamente registra una Feature;
- métodos implementados en "CADService" pero nunca conectados al pipeline;
- comandos existentes sin ruta de ejecución;
- UI existente sin backend;
- backend existente sin UI;
- estados/cache que no se invalidan después de modificar CAD;
- documentación que declare una funcionalidad como implementada cuando realmente no lo está.

Si encuentras alguno relacionado directamente con las operaciones CAD que estás cerrando, corrígelo.

No amplíes el alcance a funcionalidades nuevas no relacionadas.

---

7. FUNCIONALIDADES QUE NO DEBES ROMPER

Antes de modificar código, verifica dependencias.

No modificar innecesariamente:

- SelectionManager;
- flujo STEP;
- CADService existente;
- Boolean;
- FeatureHistory;
- Document;
- Timeline;
- DesignTree;
- FEA;
- Kratos;
- Topología;
- Generative Design;
- sistema de estudios;
- navegación/cámara;
- sistema de GPU.

Si necesitas modificar alguno para integrar correctamente una operación CAD, realiza únicamente el cambio mínimo necesario y verifica regresiones.

---

8. DOCUMENTACIÓN

Después de implementar y probar:

Actualizar "PROJECT_STATUS.md" para reflejar el estado real.

No declarar una funcionalidad como "IMPLEMENTADA" si únicamente existe su UI, Command o método aislado.

Documentar brevemente:

- Transform;
- Mirror;
- Pattern;
- corrección del centro del patrón circular;
- integración con historial/modelo/viewport;
- tests realizados.

---

9. CRITERIO DE FINALIZACIÓN

La etapa solamente se considera cerrada cuando:

"Selección → UI → Command → Validación → Pipeline → CADService → Geometría real → Modelo activo → Viewport → FeatureHistory/Document → DesignTree → Tests"

funcione de extremo a extremo para Transform, Mirror y Pattern.

Al finalizar:

1. ejecuta tests específicos;
2. ejecuta la suite completa;
3. corrige regresiones;
4. revisa "PROJECT_STATUS.md";
5. informa exactamente qué quedó implementado;
6. informa cualquier limitación real que permanezca.

No dejes implementaciones "placeholder", "pending" o simplemente registradas como Feature si la operación está declarada como soportada.

El objetivo es cerrar los cabos existentes, no comenzar una nueva arquitectura.