FASE 1 — ARQUITECTURA CAD/CAE Y SISTEMA DE FEATURES

ROL

Actúa como PROGRAMADOR SENIOR Y ARQUITECTO DE SOFTWARE especializado en aplicaciones CAD/CAE, geometría computacional, visualización 3D, FEA y optimización.

Trabaja directamente sobre el repositorio existente.

NO desarrolles una aplicación desde cero.

Antes de modificar código, audita la implementación actual y comprende cómo están conectados el desktop, viewport, geometría, selección, pipeline, FEA y optimización.

---

OBJETIVO DE ESTA FASE

Preparar la arquitectura existente para evolucionar desde el actual visor/aplicación de optimización hacia una aplicación CAD/CAE independiente, capaz de incorporar progresivamente operaciones CAD, estudios de ingeniería, optimización estructural y diseño generativo.

Esta fase es principalmente arquitectónica y funcional.

NO realizar todavía un rediseño visual de la interfaz.

La estética será una fase posterior.

---

REGLA PRINCIPAL

REUTILIZA TODO LO QUE YA FUNCIONE.

No reemplaces componentes existentes simplemente para crear una arquitectura nueva.

Antes de modificar algo determina:

- qué existe;
- qué funciona;
- qué está incompleto;
- qué es provisional;
- qué puede reutilizarse;
- qué necesita ser adaptado;
- qué realmente debe reemplazarse.

No elimines funcionalidades existentes sin verificar sus dependencias.

---

1. AUDITORÍA

Audita como mínimo:

- punto de entrada;
- aplicación desktop;
- MainWindow;
- viewport;
- cámara;
- renderer;
- escena;
- selección;
- carga STEP;
- CadQuery/OCP;
- tessellation;
- Gmsh;
- FEA;
- optimización;
- PipelineController;
- servicios;
- dependencias;
- interfaz web/API restante.

Identifica acoplamientos innecesarios y responsabilidades mal ubicadas.

Antes de implementar nuevas estructuras, documenta brevemente qué arquitectura existe actualmente y qué modificaciones son realmente necesarias.

---

2. MODELO DE DOCUMENTO

Introduce, adapta o prepara una abstracción de documento CAD/CAE.

Conceptualmente:

Document
├── Models
├── Features
├── Studies
├── Results
└── Metadata

El documento debe poder representar la evolución del modelo y no solamente el estado final del viewport.

No es necesario desarrollar todavía un sistema completo de persistencia de documentos.

Lo importante es establecer una base extensible.

---

3. FEATURE HISTORY

Preparar una línea de operaciones reproducible.

Conceptualmente:

Document
   ↓
Feature 1
   ↓
Feature 2
   ↓
Feature 3
   ↓
Study
   ↓
Result

Cada Feature debe representar una operación o transformación del modelo.

Crear una abstracción que permita posteriormente incorporar:

- Boolean;
- transformación;
- mirror;
- pattern;
- fillet;
- chamfer;
- shell;
- medición;
- otras operaciones CAD.

NO implementar todas estas operaciones ahora.

Crear únicamente la arquitectura necesaria.

---

4. SISTEMA DE COMMANDS / FEATURES

Separar:

- parámetros;
- selección;
- validación;
- ejecución;
- resultado.

Conceptualmente:

Command
├── parameters
├── selections
├── validate()
└── execute()

Ejemplo futuro:

BooleanCommand
├── operation
├── target_body
├── tool_bodies
├── keep_tools
├── validate()
└── execute()

La UI no debe contener la lógica geométrica de la operación.

---

5. SISTEMA DE SELECCIÓN

Conservar y evolucionar el sistema de selección existente.

Prepararlo para distinguir:

- cuerpos/sólidos;
- caras;
- aristas;
- vértices;
- múltiples entidades.

Una selección debe contener suficiente información para identificar de forma estable la entidad CAD seleccionada.

No depender únicamente del actor gráfico de VTK.

El viewport representa la selección, pero la selección pertenece al modelo CAD.

---

6. SISTEMA DE NAVEGACIÓN

Crear una abstracción "NavigationManager".

Debe permitir posteriormente seleccionar diferentes esquemas de navegación:

- Onshape;
- AutoCAD;
- Fusion 360;
- Blender;
- otros.

No implementar todavía todos los perfiles si no es necesario.

Crear la arquitectura para que cada perfil traduzca entradas de:

- mouse;
- rueda;
- teclado;
- botones;
- modificadores;

a acciones internas como:

Orbit
Pan
Zoom
Rotate
Select
Fit

El viewport no debe contener lógica específica de un único esquema de navegación.

---

7. ESTUDIOS CAE

Separar el concepto de "Study" del concepto de "Feature".

Un estudio representa un análisis físico o de ingeniería.

Conceptualmente:

Study
├── geometry
├── material
├── loads
├── constraints
├── objectives
├── solver
└── results

Preparar la arquitectura para:

- resistencia;
- elasticidad;
- deformación;
- tensión;
- factor de seguridad;
- análisis posteriores.

No es necesario implementar todos los estudios ahora.

---

8. OPTIMIZACIÓN ESTRUCTURAL

Mantener la optimización estructural existente como un tipo específico de estudio.

Conceptualmente:

StructuralOptimizationStudy
├── design_region
├── loads
├── constraints
├── material
├── objective
├── volume_fraction
├── solver
└── result

No romper la implementación SIMP existente.

Adaptarla progresivamente a esta arquitectura.

---

9. DISEÑO GENERATIVO

Preparar desde ahora una arquitectura diferente para el diseño generativo.

NO asumir que diseño generativo significa simplemente ejecutar SIMP sobre una pieza existente.

Debe soportar dos escenarios:

ESCENARIO A — Pieza existente

El usuario proporciona una geometría CAD existente.

CAD existente
      ↓
Condiciones físicas
      ↓
Espacio de diseño
      ↓
Optimización
      ↓
Geometría optimizada

ESCENARIO B — Conexión entre piezas

El usuario proporciona, por ejemplo:

Pieza A
Pieza B

y define que ambas deben quedar conectadas físicamente.

El sistema debe poder crear material/geometría en el espacio disponible entre ellas y optimizar dicha conexión.

Conceptualmente:

Pieza A
   │
   │
   │ ← geometría generada
   │
Pieza B

La arquitectura debe contemplar:

GenerativeDesignStudy
├── input_geometry
├── connection_targets
├── design_space
├── loads
├── constraints
├── objectives
├── geometry_generation
├── optimization
└── generated_cad

La generación de geometría y la optimización deben ser componentes diferenciables.

---

10. CAD GENERADO

El diseño generativo debe quedar preparado para producir geometría CAD, no únicamente una malla visual.

La arquitectura futura debe permitir:

Condiciones
     ↓
Generación / optimización
     ↓
Representación volumétrica o malla
     ↓
Reconstrucción geométrica
     ↓
CAD/B-Rep
     ↓
STEP

No es necesario implementar todavía el algoritmo completo de reconstrucción CAD.

Pero NO diseñes la arquitectura suponiendo que el resultado final será únicamente STL o una malla.

El resultado generativo debe poder convertirse posteriormente en una geometría CAD utilizable.

---

11. PIPELINE

Adaptar el "PipelineController" existente para que funcione como coordinador de operaciones y estudios, evitando que concentre toda la lógica.

Separar conceptualmente:

UI
 ↓
Commands / Studies
 ↓
Application Services
 ↓
Core
 ↓
Solvers / Geometry / Meshing

Las operaciones pesadas no deben bloquear la interfaz.

Reutilizar los mecanismos existentes de ejecución en segundo plano cuando sean adecuados.

---

12. INTERFAZ ACTUAL

NO rediseñar visualmente la interfaz en esta fase.

No cambiar todavía:

- colores;
- iconografía;
- estilo visual;
- dimensiones;
- tema;
- estética.

Sí se permite modificar la estructura interna necesaria para soportar:

- árbol de modelo;
- historial de Features;
- selección;
- comandos;
- estudios;
- propiedades.

La mejora visual se realizará posteriormente.

---

13. ÁRBOL DE MODELO Y TIMELINE

Preparar conceptualmente el actual "DesignTreePanel" y "TimelinePanel" para evolucionar desde el flujo fijo de optimización hacia:

ÁRBOL

Modelo
├── Cuerpos
├── Operaciones
├── Estudios
└── Resultados

y:

TIMELINE

Importar STEP
      ↓
Boolean
      ↓
Otra Feature
      ↓
Estudio
      ↓
Resultado

No implementar todavía todas las operaciones.

La arquitectura debe permitir agregarlas sin rehacer la interfaz.

---

14. BARRA SUPERIOR

Preparar la arquitectura para que posteriormente la barra superior pueda organizar las funciones por categorías, por ejemplo:

Modelo
Optimización
Pruebas de rendimiento
Visualización
Herramientas

Dentro de Optimización:

Optimización estructural
Diseño generativo

Dentro de Pruebas:

Resistencia
Elasticidad
Deformación
...

No es necesario realizar todavía el rediseño visual de esta barra.

Preparar únicamente las acciones y comandos necesarios para que pueda implementarse posteriormente.

---

15. BOOLEANOS

Como primera Feature CAD futura, preparar la arquitectura para:

Boolean

Operación:
- Unión
- Diferencia
- Intersección

Pieza principal:
[ selección ]

Piezas herramienta:
[ selección múltiple ]

☑ Conservar herramientas

No implementar la operación si requiere modificar demasiadas capas en esta fase.

Primero asegúrate de que el sistema de selección, comandos, parámetros, historial y ejecución puede soportarla correctamente.

---

16. COMPATIBILIDAD TECNOLÓGICA

Python continúa siendo la base actual del proyecto.

No conviertas todo el proyecto a otro lenguaje.

Sin embargo, no cierres la arquitectura a Python de forma artificial.

Si una parte futura requiere una tecnología especializada para:

- rendering;
- geometría;
- generación de malla;
- solver;
- reconstrucción CAD;

podrá evaluarse una arquitectura híbrida si existe una justificación técnica real.

No introducir tecnologías adicionales sin necesidad.

---

17. VALIDACIÓN

Después de realizar los cambios verifica como mínimo:

1. La aplicación desktop inicia correctamente.
2. El viewport continúa funcionando.
3. Los modelos STEP continúan cargándose.
4. La tessellation continúa funcionando.
5. La selección existente continúa funcionando.
6. El sistema de cámara continúa funcionando.
7. El pipeline existente continúa funcionando.
8. El mallado continúa funcionando.
9. La FEA existente no se rompe.
10. La optimización SIMP existente no se rompe.
11. Las operaciones pesadas no bloquean innecesariamente la UI.
12. La nueva arquitectura permite representar Features y Studies.
13. El código no introduce dependencias circulares.
14. No quedan funcionalidades existentes inutilizadas.

Corrige los errores encontrados.

---

REGLAS

NO rediseñar todavía la interfaz visual.

NO eliminar la implementación existente sin justificarlo.

NO reescribir el proyecto desde cero.

NO reemplazar VTK/PySide6 simplemente por preferencia personal.

NO convertir Python a otro lenguaje.

NO cerrar la puerta a arquitecturas híbridas justificadas técnicamente.

NO implementar todas las funciones CAD ahora.

NO implementar todavía un sistema completo de diseño generativo.

La prioridad de esta fase es construir una arquitectura que permita implementar esas funciones correctamente después.

---

RESULTADO FINAL

Al finalizar, el proyecto debe conservar sus funcionalidades actuales y disponer de una base arquitectónica preparada para evolucionar hacia:

CAD
│
├── Modelado
├── Features
├── Selección
├── Historial
│
CAE
│
├── Estudios
├── Materiales
├── Cargas
├── Restricciones
├── FEA
│
Optimización
│
├── Estructural
└── Generativa
      │
      ├── Geometría existente
      └── Generación de geometría
             ↓
          CAD generado

Entrega al finalizar un informe breve indicando:

- arquitectura encontrada;
- cambios realizados;
- archivos creados;
- archivos modificados;
- archivos eliminados;
- componentes reutilizados;
- componentes reemplazados;
- nuevas abstracciones creadas;
- dependencias agregadas;
- funcionalidades verificadas;
- problemas encontrados;
- problemas pendientes;
- recomendaciones para la siguiente fase.