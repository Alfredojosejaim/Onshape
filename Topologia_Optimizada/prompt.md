FASE 1 — CONSOLIDACIÓN DE ARQUITECTURA DESKTOP NATIVA Y DESACOPLAMIENTO WEB

ROL

Actúa como PROGRAMADOR SENIOR Y ARQUITECTO DE SOFTWARE especializado en aplicaciones CAD/CAE desktop, Python, PySide6, VTK, geometría CAD, FEA y arquitecturas de software desacopladas.

Trabaja directamente sobre el repositorio existente.

NO desarrolles una aplicación desde cero.

Antes de modificar cualquier archivo, audita nuevamente el estado ACTUAL del repositorio y comprende las modificaciones realizadas anteriormente.

---

OBJETIVO

Consolidar el proyecto como una aplicación CAD/CAE desktop nativa, ejecutándose localmente y sin depender de un navegador ni de un servidor web local para su funcionamiento normal.

La aplicación debe poder:

- iniciar como aplicación desktop;
- cargar y procesar modelos localmente;
- visualizar geometría localmente;
- realizar selección local;
- ejecutar mallado local;
- ejecutar FEA local;
- ejecutar optimización local;
- gestionar sus Features y Studies localmente;
- funcionar sin conexión a Internet durante el uso normal.

La única comunicación obligatoria con Internet en esta etapa será la necesaria para validar la licencia/suscripción.

---

REGLA FUNDAMENTAL

NO reemplaces la arquitectura existente sin auditarla primero.

El repositorio ya contiene una implementación desktop, viewport, renderer, escena, selección, navegación, CAD, mallado y pipeline.

Debes reutilizarla y corregir únicamente aquello que sea necesario.

No dupliques sistemas que ya existen.

No crees una segunda implementación de:

- viewport;
- cámara;
- renderer;
- selección;
- navegación;
- pipeline;
- carga CAD.

---

1. AUDITORÍA OBLIGATORIA

Antes de modificar código identifica:

- punto de entrada real;
- flujo de inicialización;
- MainWindow;
- UI;
- Viewport3D;
- Camera;
- Scene;
- Renderer;
- SelectionManager;
- NavigationManager;
- CADService;
- PipelineController;
- servicios;
- módulos de geometría;
- mallado;
- FEA;
- optimización;
- servidor/API;
- dependencias web;
- cualquier comunicación HTTP interna;
- cualquier dependencia del navegador.

Determina exactamente qué componentes son:

A. Parte del núcleo desktop

B. Servicios locales reutilizables

C. Código web heredado

D. Código que debe mantenerse temporalmente por compatibilidad

E. Código obsoleto que puede eliminarse

No elimines código únicamente porque parezca relacionado con la web.

---

2. ARQUITECTURA NATIVA

El flujo normal de la aplicación debe ser:

Desktop Application
        ↓
PySide6 UI
        ↓
Application Layer
        ↓
Core
        ↓
CAD / Mesh / FEA / Optimization
        ↓
GPU / CPU

NO:

Desktop
   ↓
HTTP localhost
   ↓
FastAPI
   ↓
Python

si la operación puede ejecutarse directamente dentro del proceso de la aplicación.

El servidor HTTP local no debe ser un requisito para ejecutar las funcionalidades principales.

---

3. ELIMINAR LA DEPENDENCIA FUNCIONAL DE LA WEB

Identifica todas las funcionalidades que actualmente dependan de:

- FastAPI;
- Flask;
- servidor HTTP;
- endpoints localhost;
- JavaScript;
- HTML;
- navegador;
- WebView;
- REST interno.

Para cada una determina si:

1. puede migrarse directamente a Python;
2. puede convertirse en un servicio interno;
3. debe mantenerse por una razón técnica;
4. pertenece exclusivamente a una futura integración externa.

Migra a llamadas internas aquellas funcionalidades que no necesitan HTTP.

No mantengas una API REST simplemente por conservar la arquitectura anterior.

---

4. SEPARACIÓN DE RESPONSABILIDADES

La aplicación debe aproximarse conceptualmente a:

UI
 ↓
Commands
 ↓
Application Services
 ↓
Core
 ├── CAD
 ├── Mesh
 ├── FEA
 └── Optimization

La UI no debe contener:

- operaciones CAD;
- lógica FEA;
- algoritmos de optimización;
- generación de mallas;
- llamadas directas a APIs externas.

La UI debe coordinar acciones y presentar resultados.

---

5. MAINWINDOW

Audita "MainWindow".

Extrae de ella cualquier lógica que no pertenezca a la interfaz.

Evita que "MainWindow" se convierta en un controlador monolítico.

La ventana debe encargarse principalmente de:

- composición de widgets;
- menús;
- toolbars;
- acciones;
- paneles;
- conexión de señales;
- actualización visual.

La lógica de negocio debe vivir fuera de ella.

---

6. COMMANDS / ACTIONS

Preparar una capa de comandos que permita posteriormente implementar operaciones como:

Boolean
Transform
Mirror
Pattern
Fillet
Chamfer
Measure

y estudios como:

Structural Optimization
Generative Design
Strength
Elasticity
Deformation

Un comando debe separar:

Parameters
Selections
Validation
Execution
Result

No implementar todas las operaciones ahora.

Crear la infraestructura para que puedan incorporarse posteriormente.

---

7. DOCUMENTO Y MODELO

Preparar una abstracción de documento local:

Document
├── Model
├── Bodies
├── Features
├── Studies
└── Results

El documento debe representar el estado de la aplicación independientemente de la interfaz gráfica.

No es necesario implementar todavía un formato definitivo de guardado.

---

8. FEATURE HISTORY

Preparar la infraestructura para que las operaciones puedan formar una secuencia reproducible:

Import STEP
      ↓
Boolean
      ↓
Transform
      ↓
Study
      ↓
Result

El sistema debe permitir posteriormente tener una línea de tiempo CAD real.

No conviertas todavía el Timeline visual en un simple sustituto del antiguo flujo de optimización.

---

9. SELECCIÓN

Conservar el sistema de selección existente y desacoplarlo del viewport cuando sea necesario.

La selección debe representar entidades CAD, no solamente actores gráficos.

Prepararla para:

- Body;
- Solid;
- Face;
- Edge;
- Vertex;
- selección múltiple.

El viewport debe visualizar la selección, pero el modelo debe ser quien la interprete.

---

10. NAVEGACIÓN

Conservar el "NavigationManager" existente.

NO crear otro sistema de navegación.

Audita y consolida el sistema actual.

Debe quedar preparado para perfiles como:

Onshape
AutoCAD
Fusion 360
Blender

El cambio de perfil debe modificar el comportamiento de navegación sin duplicar el viewport.

Si actualmente existen perfiles implementados, mantenlos y corrige solamente problemas encontrados.

Preparar la posibilidad de guardar la preferencia del usuario localmente.

---

11. CAD Y GEOMETRÍA

Mantener el sistema CAD existente siempre que sea funcional.

El procesamiento de:

- STEP;
- CadQuery;
- OpenCascade/OCP;
- tessellation;

debe ejecutarse localmente.

No introducir una API web para operaciones que ya pueden realizarse directamente mediante las bibliotecas locales.

---

12. MALLADO, FEA Y OPTIMIZACIÓN

El mallado, FEA y optimización deben ejecutarse localmente.

Las operaciones pesadas deben ejecutarse fuera del hilo principal de Qt cuando corresponda.

La UI debe permanecer responsiva.

No introducir comunicación HTTP entre componentes locales solamente para separar procesos lógicos.

Si una operación requiere aislamiento de procesos por estabilidad o rendimiento, puede utilizarse un proceso local, pero debe estar justificado.

---

13. DISEÑO GENERATIVO

Mantener preparada la arquitectura para dos casos:

Caso A

CAD existente
      ↓
Optimización
      ↓
Geometría optimizada

Caso B

Pieza A
    ↓
Espacio de diseño
    ↓
Generación de conexión
    ↓
Pieza B
    ↓
Optimización
    ↓
CAD generado

No implementar todavía el algoritmo completo de diseño generativo.

Pero no diseñes la arquitectura suponiendo que el resultado final será únicamente una malla STL.

Debe quedar preparada para:

Generated Geometry
       ↓
CAD / B-Rep
       ↓
STEP

---

14. INTERNET Y LICENCIA

La aplicación será comercial y funcionará mediante suscripción.

Por diseño:

Internet NO debe ser necesaria para utilizar las funciones CAD/CAE normales.

La conexión a Internet se utilizará para validar la licencia.

Crear una abstracción independiente:

LicenseManager

Conceptualmente:

Application
    ↓
LicenseManager
    ↓
License Server

El resto de la aplicación NO debe conocer detalles de HTTP, URLs, tokens o servidores de licencia.

Debe recibir únicamente estados como:

Licensed
Trial
Expired
Invalid
OfflineGracePeriod

No implementar todavía un backend comercial de licencias si no existe.

Preparar únicamente la arquitectura local necesaria para integrarlo posteriormente.

---

15. MODO OFFLINE

Diseñar la aplicación para que una interrupción temporal de Internet no destruya el estado de trabajo ni bloquee innecesariamente operaciones locales.

La política exacta de funcionamiento offline debe quedar encapsulada dentro de "LicenseManager".

No dispersar comprobaciones como:

if internet:

por toda la aplicación.

Las funcionalidades CAD/CAE no deben consultar directamente el estado de Internet.

---

16. FUTURA INTEGRACIÓN CON CAD EXTERNOS

No eliminar la posibilidad de integrar posteriormente:

- Onshape;
- otros CAD;
- importadores;
- plugins;
- conectores externos.

Pero estas integraciones deben considerarse adaptadores externos, no parte del núcleo de la aplicación.

Conceptualmente:

Core Application
       ↑
       │
Integration Adapters
 ├── Onshape
 ├── Other CAD
 └── Future integrations

El núcleo debe seguir funcionando independientemente de ellos.

---

17. INTERFAZ

En esta fase:

NO realizar el rediseño visual definitivo.

No modificar todavía de forma significativa:

- colores;
- iconos;
- estética;
- tema;
- estilo visual.

Sí puedes realizar cambios estructurales necesarios para soportar la nueva arquitectura.

La interfaz visual definitiva será una fase posterior.

---

18. DEPENDENCIAS

Audita "requirements" y cualquier sistema de dependencias.

Elimina únicamente dependencias web que ya no sean necesarias para la aplicación desktop.

No elimines dependencias que pertenezcan a:

- CAD;
- VTK;
- PySide6;
- Gmsh;
- FEA;
- optimización;
- procesamiento geométrico.

Si una dependencia tiene múltiples usos, verifica todos ellos antes de eliminarla.

---

19. VALIDACIÓN

Después de los cambios verifica:

1. La aplicación inicia directamente como desktop.
2. No necesita navegador.
3. No necesita levantar manualmente un servidor web.
4. El viewport funciona.
5. La navegación funciona.
6. Los perfiles de navegación existentes funcionan.
7. STEP continúa cargándose.
8. La selección continúa funcionando.
9. La tessellation continúa funcionando.
10. El mallado continúa funcionando.
11. FEA continúa funcionando.
12. SIMP/optimización existente continúa funcionando.
13. Las operaciones pesadas no bloquean la UI.
14. El proyecto puede ejecutarse sin conexión a Internet, salvo la validación de licencia.
15. La ausencia temporal de Internet no provoca errores internos en CAD/CAE.
16. No existen dependencias HTTP innecesarias entre componentes locales.
17. No existen referencias rotas por la eliminación de componentes web.
18. La futura integración con servicios externos sigue siendo arquitectónicamente posible.

Corrige los errores encontrados antes de finalizar.

---

REGLAS ABSOLUTAS

NO desarrolles desde cero.

NO rediseñes visualmente la aplicación todavía.

NO reemplaces VTK/PySide6 sin una justificación técnica.

NO crees otro sistema de navegación si ya existe "NavigationManager".

NO dupliques funcionalidades existentes.

NO conviertas Python a otro lenguaje.

NO cierres la puerta a componentes especializados en otros lenguajes cuando exista una justificación técnica futura.

NO utilices HTTP localhost para comunicar componentes que pueden comunicarse directamente.

NO hagas que Internet sea necesaria para CAD/CAE.

NO disperses la lógica de licencia por la aplicación.

NO elimines la posibilidad de futuras integraciones con Onshape u otros CAD.

NO implementes todavía el algoritmo completo de diseño generativo.

NO implementes todavía todas las operaciones CAD.

---

RESULTADO FINAL

La aplicación debe quedar consolidada como:

┌─────────────────────────────────────┐
│       DESKTOP CAD/CAE APP           │
│                                     │
│  PySide6                            │
│      ↓                              │
│  Application Layer                 │
│      ↓                              │
│  Document / Commands / Studies     │
│      ↓                              │
│  Core                               │
│   ├── CAD                           │
│   ├── Mesh                          │
│   ├── FEA                           │
│   └── Optimization                  │
│                                     │
│  VTK → GPU                          │
│                                     │
└─────────────────────────────────────┘
             │
             │ únicamente licencia
             ▼
       License Server

La aplicación debe poder ejecutarse y realizar sus funciones principales completamente de forma local.

Entrega un informe final breve indicando:

- arquitectura encontrada;
- problemas detectados;
- cambios realizados;
- archivos creados;
- archivos modificados;
- archivos eliminados;
- dependencias eliminadas/agregadas;
- código web conservado y motivo;
- código web eliminado;
- componentes reutilizados;
- componentes desacoplados;
- estado de "NavigationManager";
- estado del sistema de selección;
- estado del pipeline;
- estado de la arquitectura CAD/CAE;
- estado de "LicenseManager";
- pruebas realizadas;
- problemas pendientes;
- recomendaciones para la siguiente fase.