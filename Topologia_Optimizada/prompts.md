AUDITORÍA, CONSOLIDACIÓN Y TRAZABILIDAD DE LA INTERFAZ CAD/CAE

Audita primero el estado actual del proyecto y después implementa únicamente los cambios necesarios.

OBJETIVO

Consolidar una interfaz desktop CAD/CAE funcional, modular y fácil de modificar visualmente.

La interfaz debe quedar separada de la lógica del programa, de forma que posteriormente sea posible modificar su distribución, tamaños, paneles, toolbars y apariencia sin tener que modificar el núcleo CAD/CAE.

---

1. AUDITORÍA

Revisa como mínimo:

- "desktop/ui/main_window.py"
- "desktop/ui/panels/"
- "desktop/viewport/"
- "desktop/pipeline/controller.py"
- "core/document.py"
- "core/features/"
- condiciones y estudios
- menús y toolbars
- tests relacionados con desktop/UI

Determina:

1. qué componentes de UI son funcionales;
2. cuáles son únicamente visuales;
3. qué conexiones UI → Controller → Core ya existen;
4. qué conexiones están incompletas;
5. dónde existe lógica de negocio mezclada innecesariamente con código visual;
6. qué partes de "MainWindow" deberían modularizarse;
7. qué funcionalidades del núcleo todavía no tienen una acción de interfaz conectada.

No declares una funcionalidad como implementada únicamente porque exista una clase, botón o método.

---

2. TRAZABILIDAD OBLIGATORIA

Después de la auditoría, crea o actualiza un documento:

"docs/UI_IMPLEMENTATION_MAP.md"

Este documento debe convertirse en el mapa técnico de la interfaz.

Para cada acción importante visible en la interfaz, documenta exactamente qué ocurre cuando el usuario la utiliza.

Por ejemplo:

Botón: Carga
UI:
    desktop/ui/panels/...
Acción/Senal:
    ...
Método ejecutado:
    ...
Controller:
    desktop/pipeline/controller.py → ...
Core:
    core/... → ...
Resultado:
    ...
Estado actualizado:
    ...

Ejemplo conceptual:

Botón "Carga"
→ abre/selecciona archivo de cargas
→ ejecuta `import_file_cargas(...)`
→ `PipelineController`
→ crea/actualiza la condición correspondiente
→ actualiza Document/estado
→ DesignTree/Properties refleja el cambio

El documento debe indicar los nombres reales encontrados en el código, no nombres inventados.

Debe existir trazabilidad como mínimo para:

- Importar CAD/STEP
- Selección
- Carga
- Restricciones
- Elasticidad
- Unión Boolean
- Obstrucciones
- Regiones protegidas
- Crear/modificar condiciones
- Generar malla
- Operaciones CAD
- Transformar
- Mirror
- Pattern
- Ejecutar FEA
- Ejecutar estudios disponibles
- Visualizar resultados
- Exportar
- Acciones de Design Tree
- Acciones de Timeline
- Propiedades

Si una acción no está implementada, debe indicarse explícitamente:

Estado: NO CONECTADO
Motivo: ...

No se debe crear código ficticio únicamente para llenar el documento.

---

3. IMPLEMENTACIÓN

Mantener el núcleo

No reconstruyas ni reemplaces:

- CAD
- Document
- FeatureHistory
- condiciones
- malla
- FEA
- Kratos
- PipelineController
- Viewport3D
- SelectionManager
- NavigationManager

Si funcionan, reutilízalos.

Modularizar la interfaz

Organiza la UI para que:

- "MainWindow" actúe principalmente como coordinador;
- los paneles sean independientes;
- menús y toolbars puedan modificarse sin alterar el backend;
- la distribución pueda modificarse fácilmente;
- el estilo visual esté centralizado;
- las acciones de UI estén separadas de la lógica de negocio.

No crees abstracciones innecesarias.

---

4. ESTADO ÚNICO

La interfaz debe reflejar el estado real del programa.

Evita:

- estados duplicados;
- managers duplicados;
- copias independientes del modelo;
- árboles paralelos;
- timelines que no representen el estado real.

La fuente de verdad debe continuar siendo la arquitectura existente.

---

5. INTEGRACIÓN FUNCIONAL

Comprueba que las acciones principales realmente ejecuten las operaciones existentes de extremo a extremo.

Para cada acción:

UI
↓
Signal / Event
↓
Handler
↓
Controller
↓
Core
↓
Estado actualizado
↓
UI sincronizada

Si alguna etapa está desconectada, corrígela cuando exista una implementación real en el proyecto que pueda reutilizarse.

No inventes funcionalidades futuras.

---

6. EDICIÓN VISUAL

"desktop/ui/crea3d_mainwindow.ui" es únicamente un boceto visual.

No es necesario integrarlo ni convertirlo.

La arquitectura final debe facilitar posteriormente modificar:

- posición y tamaño de paneles;
- orden de toolbars;
- agrupación de herramientas;
- sidebar;
- propiedades;
- resultados;
- timeline;
- viewport;
- menús;
- espaciados;
- tipografía;
- iconos;
- apariencia.

No intentes crear un editor tipo Canva/PowerPoint dentro de la aplicación. El objetivo es conseguir una arquitectura de UI cuya presentación pueda modificarse fácilmente sin tocar la lógica CAD/CAE.

---

7. DOCUMENTACIÓN

Además de "docs/UI_IMPLEMENTATION_MAP.md", actualiza únicamente la documentación que haya quedado desactualizada por los cambios.

El mapa debe permitir que otro desarrollador pueda responder rápidamente:

«"¿Qué código se ejecuta cuando presiono este botón?"»

Por tanto, evita descripciones genéricas. Utiliza rutas, clases, métodos, señales y componentes reales del repositorio.

---

8. RESTRICCIONES

- No reconstruir el proyecto.
- No migrar a C++.
- No modificar FEA sin encontrar un error real.
- No modificar funcionalidades CAD que funcionan.
- No eliminar funcionalidades existentes.
- No integrar obligatoriamente el ".ui".
- No crear una segunda arquitectura de UI.
- No crear managers duplicados.
- No introducir dependencias innecesarias.
- No implementar funcionalidades futuras no definidas.
- No inventar métodos para la documentación.
- No declarar una acción funcional si no existe conexión de extremo a extremo.

---

9. VERIFICACIÓN

Después de implementar:

1. Ejecuta todos los tests existentes.
2. Comprueba que la aplicación inicia.
3. Comprueba viewport.
4. Comprueba selección.
5. Comprueba navegación.
6. Comprueba acciones CAD/CAE principales.
7. Comprueba sincronización de:
   - Design Tree
   - Properties
   - Results
   - Timeline
8. Comprueba que las acciones documentadas en "UI_IMPLEMENTATION_MAP.md" coincidan con el código real.
9. Comprueba que no se haya roto funcionalidad existente.

Finalmente informa:

- qué encontraste;
- qué estaba correctamente implementado;
- qué estaba desconectado;
- qué modularizaste;
- qué modificaste;
- qué quedó pendiente;
- tests ejecutados y resultado;
- ruta del documento de trazabilidad creado/actualizado.

Regla fundamental: la interfaz, la documentación y el código deben describir la misma arquitectura.