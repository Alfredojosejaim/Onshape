CONSOLIDACIÓN DEL PROYECTO + NAVEGACIÓN + CÁMARA 3D

ROL

Actúa como PROGRAMADOR SENIOR Y ARQUITECTO DE SOFTWARE especializado en aplicaciones CAD/CAE desktop, Python, PySide6, VTK, cámaras 3D y visualización científica.

Trabaja directamente sobre el repositorio existente.

No desarrolles desde cero y no repitas trabajos que ya estén implementados.

El proyecto ya pasó por varias etapas de desarrollo. Debes trabajar sobre el estado REAL actual del código.

---

1. ESTADO REAL DEL PROYECTO

Audita brevemente el código actual, dando prioridad al código sobre informes antiguos.

Determina el estado actual de:

- aplicación desktop;
- PySide6;
- VTK;
- viewport;
- cámara;
- navegación;
- selección;
- CAD/STEP;
- Document;
- Features;
- Commands;
- Timeline;
- Booleanos;
- mallado;
- FEA;
- Kratos;
- optimización;
- diseño generativo.

No vuelvas a implementar funcionalidades que ya existan.

---

2. LIMPIEZA

Identifica documentación y código claramente obsoletos.

Busca:

- informes de etapas anteriores;
- prompts antiguos;
- arquitecturas abandonadas;
- implementaciones duplicadas;
- interfaces web antiguas;
- endpoints sin uso;
- imports innecesarios;
- código de prototipos reemplazados.

Elimina únicamente aquello cuya obsolescencia pueda verificarse.

No realices una reescritura general.

---

3. "prompts.md"

"prompts.md" debe contener únicamente el prompt vigente.

Eliminar los prompts anteriores.

No utilizarlo como historial.

---

4. ESTADO DEL PROYECTO

Crear o actualizar:

PROJECT_STATUS.md

Debe representar exclusivamente el estado REAL actual.

Incluir:

Desktop
Viewport
Camera
Navigation
Selection
CAD
Features
Commands
Boolean
Mesh
FEA
Kratos
Structural Optimization
Generative Design
CAD Reconstruction
UI
License

Indicar para cada elemento:

IMPLEMENTADO
PARCIAL
PENDIENTE

---

5. APLICACIÓN DESKTOP

La aplicación debe funcionar como aplicación desktop nativa.

El flujo normal debe ser:

PySide6
   ↓
Application
   ↓
Core
   ↓
CAD / Mesh / FEA / Optimization

No utilizar navegador ni servidor HTTP local para funcionalidades que puedan ejecutarse directamente.

Mantener separadas las futuras integraciones externas.

---

6. LICENCIA

Preparar una abstracción:

LicenseManager

La aplicación solo deberá necesitar Internet para la futura validación de licencia/suscripción.

CAD, mallado, FEA, optimización y visualización deben funcionar localmente.

No implementar todavía el servidor comercial de licencias.

No dispersar comprobaciones de Internet por el código.

---

7. NAVEGACIÓN — "NavigationManager"

El proyecto ya dispone de "NavigationManager".

NO crear otro sistema de navegación.

Completar su integración para permitir diferentes perfiles:

Onshape
AutoCAD
Fusion 360
Blender

La configuración debe modificar el comportamiento de:

- Orbit;
- Pan;
- Zoom;
- botones del mouse;
- modificadores de teclado cuando corresponda.

La preferencia debe poder guardarse localmente.

---

8. CÁMARA 3D — SISTEMA INDEPENDIENTE

IMPORTANTE: este sistema NO forma parte de "NavigationManager".

Separar claramente:

NavigationManager
        ↓
interpreta entradas del usuario
        ↓
CameraController
        ↓
transforma la cámara

"NavigationManager" determina qué acción solicita el usuario.

"CameraController" determina cómo se transforma la cámara en el espacio 3D.

---

9. LIBERTAD DE MOVIMIENTO DE LA CÁMARA

Actualmente la cámara presenta un comportamiento excesivamente dependiente de los ejes del mundo.

Corregir este comportamiento.

La cámara debe permitir una navegación 3D libre y natural.

Como referencia conceptual utilizar el comportamiento de cámara de Onshape.

No copiar código ni depender de Onshape.

La cámara debe poder:

- orbitar libremente alrededor del punto de interés;
- cambiar su orientación espacial;
- rotar en cualquier dirección necesaria;
- realizar pan independientemente de los ejes globales;
- hacer zoom respecto del punto de interés;
- mantener una orientación coherente durante la navegación.

Evitar imponer restricciones artificiales como:

X
Y
Z

para determinar cómo puede moverse la cámara.

Los ejes globales deben representar el mundo 3D, no limitar la libertad de orientación de la cámara.

---

10. ORBITA

La órbita debe realizarse alrededor de un:

Target / Focal Point

y no mediante desplazamientos arbitrarios de posición.

Conceptualmente:

Camera
   ↘
    Target
   ↗
Orbit

El punto de interés debe poder actualizarse según:

- modelo;
- selección;
- fit-to-view;
- interacción del usuario.

La rotación debe modificar la orientación y posición de la cámara manteniendo una relación coherente con el punto de interés.

---

11. PAN

El Pan debe mover:

Camera
+
Target

manteniendo la misma orientación relativa.

El movimiento debe realizarse según el espacio de la cámara, no según X/Y/Z globales arbitrarios.

Esto debe permitir desplazar el modelo visualmente de forma natural independientemente de la orientación actual.

---

12. ZOOM

El Zoom debe estar basado en la dirección de observación de la cámara.

Cuando sea apropiado, el punto bajo el cursor debe poder actuar como referencia para acercar/alejar la vista.

Evitar implementar zoom simplemente modificando una coordenada global.

---

13. VISTAS PREDEFINIDAS

Las vistas:

- frontal;
- posterior;
- superior;
- inferior;
- izquierda;
- derecha;
- isométrica;

deben seguir existiendo.

Estas vistas son posiciones/orientaciones predefinidas y no deben limitar la libertad posterior de la cámara.

Después de utilizar una vista predefinida, el usuario debe poder orbitar libremente desde ella.

---

14. FIT TO VIEW

"Fit to View" debe calcular una posición apropiada de la cámara respecto del bounding box/modelo.

No debe forzar permanentemente una orientación restringida.

Después de ejecutar Fit, el usuario debe recuperar inmediatamente el control libre de la cámara.

---

15. SEPARACIÓN DE RESPONSABILIDADES

Mantener conceptualmente:

Input
 ↓
NavigationManager
 ↓
CameraController
 ↓
VTK Camera

Y:

Scene
 ↓
Geometry
 ↓
Renderer

No mezclar:

- eventos de mouse;
- lógica de navegación;
- cálculos de cámara;
- renderizado;

en una única clase.

---

16. NO MODIFICAR INNECESARIAMENTE

No reemplazar VTK.

No crear otro viewport.

No crear otra cámara si la actual puede evolucionarse correctamente.

No crear otro NavigationManager.

No reescribir el sistema CAD.

No modificar innecesariamente FEA, Kratos o optimización.

---

17. VALIDACIÓN DE CÁMARA

Probar explícitamente:

1. Orbit desde la vista isométrica.
2. Orbit desde la vista frontal.
3. Orbit desde la vista superior.
4. Orbit desde una orientación arbitraria.
5. Rotación alrededor del modelo.
6. Pan con cámara inclinada.
7. Zoom con cámara inclinada.
8. Zoom hacia el punto de interés.
9. Fit to View.
10. Cambio de vista predefinida.
11. Volver a orbitar después de una vista predefinida.
12. Combinación Orbit → Pan → Zoom.
13. Combinación Pan → Orbit → Zoom.
14. Movimiento en orientaciones que no coincidan con X/Y/Z.
15. Cambio de perfil de navegación sin romper la cámara.

El comportamiento debe sentirse como una cámara CAD 3D libre y natural.

---

18. NO DETENER EL DESARROLLO

Después de limpiar y corregir la cámara/navegación, no conviertas la tarea nuevamente en una auditoría.

Si encuentras problemas menores relacionados directamente con esta tarea:

corrígelos y continúa.

Si encuentras problemas pertenecientes a etapas posteriores:

documentarlos y continuar.

---

19. NO IMPLEMENTAR TODAVÍA

No implementar:

- diseño visual definitivo;
- estética AutoCAD;
- nuevos booleanos;
- nuevas Features;
- nuevos Studies;
- algoritmo completo de diseño generativo;
- reconstrucción CAD avanzada;
- nuevas simulaciones.

---

20. VALIDACIÓN GENERAL

Al finalizar verifica:

1. Aplicación desktop inicia.
2. No necesita navegador.
3. Viewport funciona.
4. STEP funciona.
5. Selección funciona.
6. Pipeline existente funciona.
7. Kratos funciona.
8. Optimización existente funciona.
9. NavigationManager funciona.
10. Los perfiles existentes funcionan.
11. CameraController permite libertad de movimiento.
12. La documentación ya no contradice el código.
13. No existen imports rotos.
14. No existen referencias a archivos eliminados.

---

INFORME FINAL

Entrega un informe breve con:

Limpieza

Qué fue eliminado o actualizado.

Estado

Qué está realmente implementado.

Navegación

Qué perfiles funcionan.

Cámara

Qué se corrigió y cómo está separada de NavigationManager.

Licencia

Qué arquitectura quedó preparada.

Próximo paso

Cuál es la siguiente funcionalidad concreta que debe implementarse.

No propongas volver a realizar auditorías generales ya completadas.

---

REGLA PRINCIPAL

AUDITA LO NECESARIO → CORRIGE → IMPLEMENTA → PRUEBA → AVANZA.

No conviertas esta tarea en una auditoría interminable.

El objetivo es terminar esta fase con:

repositorio limpio + aplicación nativa + navegación configurable + cámara 3D libre y funcional.