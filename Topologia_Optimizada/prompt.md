AUDITORÍA Y LIMPIEZA DEL REPOSITORIO — ELIMINACIÓN DE ARQUITECTURA OBSOLETA

ROL

Actúa como PROGRAMADOR SENIOR Y ARQUITECTO DE SOFTWARE especializado en aplicaciones CAD/CAE desktop.

Trabaja directamente sobre el repositorio existente.

NO desarrolles funcionalidades nuevas en esta tarea.

El objetivo exclusivo de esta fase es auditar, detectar y eliminar inconsistencias y restos de etapas anteriores del proyecto.

---

OBJETIVO

El proyecto ha evolucionado considerablemente y existen documentos, código, comentarios, configuraciones o estructuras pertenecientes a etapas anteriores que pueden estar desactualizados.

Necesitamos dejar el repositorio limpio y coherente con la arquitectura ACTUAL.

No asumas que una implementación mencionada en documentación antigua sigue existiendo.

No implementes nuevamente funcionalidades que ya fueron reemplazadas.

No reintroduzcas arquitecturas abandonadas.

---

1. AUDITORÍA COMPLETA

Antes de modificar cualquier cosa, revisa:

- estructura completa del repositorio;
- código fuente;
- desktop;
- viewport;
- renderer;
- scene;
- selección;
- navegación;
- CAD;
- mallado;
- FEA;
- optimización;
- servicios;
- API;
- scripts;
- configuraciones;
- requirements;
- README;
- documentación;
- prompts;
- comentarios relevantes.

Determina qué corresponde al estado actual y qué pertenece a etapas anteriores.

---

2. CLASIFICACIÓN

Clasifica los elementos encontrados en:

ACTUAL

Código/documentación que corresponde a la arquitectura vigente.

NECESARIO

Código antiguo que todavía es utilizado por componentes actuales.

LEGADO

Código perteneciente a una etapa anterior pero que todavía podría ser necesario temporalmente.

OBSOLETO

Código que ya no tiene ninguna dependencia ni función actual.

DOCUMENTACIÓN OBSOLETA

Documentación que describe una arquitectura que ya no existe.

REFERENCIA HISTÓRICA

Información que puede conservarse únicamente si tiene valor histórico o técnico.

No elimines elementos sin comprobar dependencias.

---

3. ARQUITECTURA VIGENTE

Toma como dirección actual del proyecto:

APLICACIÓN DESKTOP NATIVA
        ↓
PySide6
        ↓
Application / Core
        ↓
CAD / Mesh / FEA / Optimization
        ↓
VTK / GPU

La aplicación debe funcionar localmente.

Internet no debe ser necesaria para utilizar las funciones CAD/CAE.

La conexión a Internet quedará reservada para la futura validación de licencia/suscripción.

---

4. CÓDIGO WEB OBSOLETO

Busca específicamente:

- servidores localhost;
- FastAPI;
- endpoints internos;
- HTML;
- JavaScript;
- WebView;
- dashboards web;
- comunicación HTTP interna;
- APIs utilizadas únicamente para comunicar módulos locales.

Para cada componente determina si:

1. todavía es utilizado;
2. tiene una función vigente;
3. pertenece a una integración futura;
4. es legado;
5. es completamente obsoleto.

NO elimines automáticamente todo código web.

Si un componente todavía es necesario, documenta por qué.

Si solamente pertenece a la antigua interfaz web y ya no tiene ninguna dependencia vigente, elimínalo.

---

5. REFERENCIAS A ARQUITECTURAS ANTIGUAS

Busca referencias a conceptos que ya no representen el estado actual.

Por ejemplo:

- aplicación web como interfaz principal;
- navegador como requisito;
- localhost como requisito;
- iFrame;
- FeatureScript como núcleo de la aplicación;
- Onshape como dependencia obligatoria;
- conexión permanente a Onshape;
- arquitectura exclusivamente basada en REST;
- versiones anteriores del pipeline;
- prototipos reemplazados;
- sistemas duplicados.

No elimines una referencia simplemente porque contenga una palabra antigua.

Determina primero si sigue siendo técnicamente relevante.

---

6. PROMPTS Y DOCUMENTACIÓN

Revisa todos los archivos de documentación relacionados con instrucciones de desarrollo.

Especialmente:

prompts.md

"prompts.md" debe contener ÚNICAMENTE el prompt de desarrollo actualmente vigente.

Eliminar los prompts anteriores que ya fueron reemplazados.

No conservar una cadena de prompts históricos dentro de "prompts.md".

Si existe documentación que contradice la arquitectura actual:

- actualizarla;
- o eliminarla si ya no tiene utilidad.

---

7. COMENTARIOS Y DOCSTRINGS

Busca comentarios que describan arquitecturas antiguas.

Ejemplos:

"la aplicación funciona mediante navegador"
"FastAPI controla la interfaz"
"FeatureScript comunica con Python"
"Onshape es obligatorio"

Si ya no son ciertos, actualízalos o elimínalos.

No modifiques comentarios técnicos que continúen siendo correctos.

---

8. DEPENDENCIAS

Revisa:

- requirements;
- pyproject;
- configuraciones;
- scripts de instalación;
- dependencias JavaScript;
- dependencias web.

Identifica dependencias que solamente existen por la antigua interfaz web.

Elimínalas únicamente si no son utilizadas por ningún componente vigente.

No elimines:

- PySide6;
- VTK;
- Gmsh;
- CadQuery/OCP;
- dependencias FEA;
- dependencias de optimización;

si todavía son utilizadas.

---

9. ARCHIVOS DUPLICADOS

Busca implementaciones duplicadas o reemplazadas.

Especialmente:

- múltiples sistemas de viewport;
- múltiples cámaras;
- múltiples renderers;
- múltiples sistemas de navegación;
- múltiples pipelines;
- múltiples cargadores CAD;
- APIs antiguas y nuevas para la misma función.

Si existen dos implementaciones:

1. determina cuál utiliza realmente la aplicación;
2. determina cuál es la arquitectura vigente;
3. conserva la vigente;
4. elimina la obsoleta si no tiene dependencias.

No mantengas dos sistemas funcionales para hacer lo mismo sin una razón técnica.

---

10. NAVIGATION MANAGER

El proyecto ya dispone de un sistema de navegación.

No crees otro.

Audita el "NavigationManager" existente y determina qué partes son actuales.

Conserva la arquitectura existente.

No implementes todavía nuevos perfiles de navegación salvo que sea estrictamente necesario para corregir una inconsistencia.

---

11. DESKTOP

La aplicación debe continuar siendo desktop.

El punto de entrada debe abrir directamente la aplicación gráfica.

No convertir nuevamente el proyecto a una aplicación web.

Si existe un fallback web antiguo únicamente para desarrollo, determina si sigue siendo necesario.

Si no lo es, elimínalo o sepáralo claramente del flujo normal de la aplicación.

---

12. ON-SHAPE

Onshape ya no debe considerarse el núcleo obligatorio de la aplicación.

La aplicación debe poder funcionar independientemente.

Cualquier integración futura con Onshape debe estar conceptualmente separada del núcleo.

No elimines código de integración si todavía es necesario para una fase posterior, pero evita que el código actual dependa de Onshape para funcionar.

---

13. NO IMPLEMENTAR NUEVAS FUNCIONES

En esta tarea NO implementar:

- nuevos booleanos;
- nuevo sistema de Features;
- nuevo sistema de Studies;
- diseño generativo;
- nueva UI;
- nuevo diseño visual;
- nuevos perfiles de navegación;
- nuevo solver;
- nueva FEA.

Esta tarea es exclusivamente de:

AUDITORÍA + LIMPIEZA + CONSOLIDACIÓN.

---

14. VALIDACIÓN DE LA LIMPIEZA

Después de eliminar o modificar componentes:

1. ejecuta la aplicación;
2. verifica que inicia;
3. verifica que el viewport funciona;
4. verifica la navegación;
5. verifica la carga de modelos;
6. verifica la selección;
7. verifica el pipeline existente;
8. verifica que no existen imports rotos;
9. verifica que no existen referencias a archivos eliminados;
10. verifica que requirements sigue siendo correcto;
11. verifica que la aplicación no requiere navegador;
12. verifica que las funcionalidades actuales siguen funcionando.

---

15. INFORME FINAL

Entrega un informe breve con:

Eliminado

Lista de archivos/componentes eliminados y motivo.

Conservado

Componentes antiguos que todavía son necesarios y por qué.

Actualizado

Archivos de documentación, comentarios o configuración corregidos.

Dependencias

Dependencias eliminadas, conservadas o modificadas.

Arquitectura actual

Describe brevemente cómo funciona realmente el proyecto después de la limpieza.

Problemas pendientes

Indica problemas que encontraste pero que deliberadamente NO corregiste porque pertenecen a fases posteriores.

---

REGLAS ABSOLUTAS

NO desarrolles funcionalidades nuevas.

NO rediseñes la interfaz.

NO reconstruyas el proyecto.

NO reemplaces tecnologías funcionales.

NO elimines código sin comprobar dependencias.

NO vuelvas a introducir arquitecturas abandonadas.

NO conserves documentación que contradiga deliberadamente el estado actual.

NO utilices "prompts.md" como historial de prompts.

"prompts.md" debe contener únicamente el prompt vigente.

La prioridad es:

DEJAR EL REPOSITORIO LIMPIO, COHERENTE Y SIN RESTOS CONFUSOS DE ETAPAS ANTERIORES.