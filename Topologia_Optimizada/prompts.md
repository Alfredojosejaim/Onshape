IMPLEMENTACIÓN — OPERACIONES BOOLEANAS CAD + MENÚ + TIMELINE

ROL

Actúa como PROGRAMADOR SENIOR especializado en aplicaciones CAD/CAE desktop, Python, PySide6, VTK y modelado CAD paramétrico.

Trabaja directamente sobre el repositorio existente.

NO desarrolles desde cero.

La arquitectura base ya existe. Reutiliza las clases y sistemas actuales de:

- Document;
- Features;
- Commands;
- FeatureHistory;
- SelectionManager;
- NavigationManager;
- Viewport3D;
- Timeline;
- DesignTree.

No reemplaces estos sistemas.

---

OBJETIVO

Convertir el sistema de operaciones Booleanas existente en una función CAD funcional e integrada con la aplicación.

Debe funcionar como una operación de una aplicación CAD:

Seleccionar cuerpos
        ↓
Boolean
        ↓
Elegir operación
        ↓
Configurar herramientas
        ↓
Ejecutar
        ↓
Nueva Feature
        ↓
Timeline
        ↓
Modelo actualizado

---

1. MENÚ SUPERIOR

Integrar una entrada funcional para operaciones Booleanas en el menú superior existente.

Por ejemplo:

Operaciones
 └── Boolean
       ├── Unión
       ├── Corte
       └── Intersección

Utiliza la estructura de menús que ya existe.

No realices todavía un rediseño visual.

---

2. SELECCIÓN DE CUERPOS

Utilizar el "SelectionManager" existente.

El usuario debe poder seleccionar cuerpos directamente desde el viewport.

La operación Boolean debe diferenciar:

Cuerpo objetivo

La pieza que se desea modificar.

Cuerpos herramienta

Las piezas utilizadas para realizar la operación.

Debe existir soporte para múltiples cuerpos herramienta.

Ejemplo:

Target:
[ Pieza A ]

Tools:
[ Pieza B ]
[ Pieza C ]
[ Pieza D ]

No crear otro sistema de selección.

---

3. PANEL DE OPERACIÓN

Al activar Boolean, mostrar un panel/diálogo funcional utilizando Qt.

Debe permitir:

Tipo de operación:

( ) Unión
( ) Corte
( ) Intersección

Cuerpo objetivo:
[ Seleccionar ]

Cuerpos herramienta:
[ Seleccionar ]

[ ] Conservar herramientas

        [ Aceptar ]
        [ Cancelar ]

La estética puede ser provisional.

La prioridad es funcionalidad y arquitectura.

---

4. FLUJO DE SELECCIÓN

Permitir seleccionar desde el viewport.

El flujo debe ser intuitivo:

1. activar Boolean;
2. elegir operación;
3. seleccionar cuerpo objetivo;
4. seleccionar uno o varios cuerpos herramienta;
5. decidir si conservar herramientas;
6. ejecutar.

Si el usuario selecciona cuerpos antes de abrir Boolean, reutilizar esas selecciones cuando sea posible.

---

5. VALIDACIÓN

Antes de ejecutar:

- debe existir un cuerpo objetivo;
- debe existir al menos un cuerpo herramienta;
- los cuerpos deben ser válidos para la operación;
- no permitir ejecutar configuraciones inválidas.

Mostrar errores mediante mensajes Qt claros.

No permitir que un error de entrada cierre la aplicación.

---

6. EJECUCIÓN CAD

Utilizar el mecanismo CAD existente.

NO crear un algoritmo geométrico nuevo si ya existe una implementación funcional.

Reutilizar el backend actual de operaciones Booleanas.

Las operaciones necesarias son:

Union
Cut
Intersection

La operación debe producir geometría CAD válida.

---

7. FEATURE

Cada operación ejecutada debe convertirse en una Feature dentro del historial.

Conceptualmente:

Boolean Feature
├── Operation
├── Target
├── Tools
└── Keep Tools

Guardar los parámetros necesarios para poder reconstruir la operación posteriormente.

No implementar todavía un sistema paramétrico avanzado si la arquitectura actual no lo soporta.

---

8. TIMELINE

La operación Boolean debe aparecer como una entrada en el Timeline.

Ejemplo:

Timeline

Sketch
Extrude
Boolean

El nombre debe indicar la operación.

Por ejemplo:

Boolean Cut
Boolean Union
Boolean Intersection

Utilizar el sistema de "FeatureHistory" existente.

No crear un segundo Timeline.

---

9. DESIGN TREE

El resultado debe reflejarse también en el árbol de objetos existente.

Ejemplo:

Bodies
 ├── Body A
 ├── Body B
 └── Boolean Cut

Adapta la representación a la arquitectura actual.

No reemplazar "DesignTreePanel".

---

10. KEEP TOOLS

Implementar correctamente:

Conservar herramientas = OFF

Los cuerpos herramienta pasan a considerarse consumidos por la operación.

Conservar herramientas = ON

Los cuerpos herramienta permanecen disponibles después de ejecutar la operación.

El comportamiento debe quedar registrado en la Feature.

No simplemente ocultar objetos visualmente.

---

11. ACTUALIZACIÓN DEL VIEWPORT

Después de ejecutar una operación:

1. actualizar la escena;
2. eliminar/ocultar los cuerpos consumidos según corresponda;
3. mostrar el resultado;
4. actualizar selección;
5. actualizar Design Tree;
6. actualizar Timeline;
7. ajustar la representación si es necesario.

No reconstruir innecesariamente toda la escena.

---

12. CANCELACIÓN

Si el usuario cancela:

- no crear Feature;
- no modificar el modelo;
- no modificar Timeline;
- no modificar Design Tree;
- restaurar la selección cuando sea posible.

---

13. ERRORES CAD

Si la operación geométrica falla:

- no crear una Feature inválida;
- conservar el modelo anterior;
- mostrar el motivo del fallo;
- permitir al usuario corregir la selección.

Nunca dejar el documento en un estado inconsistente.

---

14. PREPARACIÓN PARA FUTURAS OPERACIONES

Diseñar el flujo de comandos de forma extensible.

El objetivo futuro será tener:

Operaciones
 ├── Boolean
 ├── Extrude
 ├── Revolve
 ├── Fillet
 ├── Chamfer
 └── ...

Y posteriormente:

Estudios
 ├── Optimización estructural
 ├── Diseño generativo
 ├── Resistencia
 ├── Elasticidad
 └── ...

No implementar esas funciones todavía.

Simplemente evita una arquitectura que obligue a rehacer el menú o Command system posteriormente.

---

15. VALIDACIÓN OBLIGATORIA

Probar:

1. Unión de dos cuerpos.
2. Unión de múltiples cuerpos.
3. Corte de dos cuerpos.
4. Corte con múltiples herramientas.
5. Intersección.
6. Conservar herramientas activado.
7. Conservar herramientas desactivado.
8. Selección desde viewport.
9. Selección previa a activar Boolean.
10. Cancelación.
11. Configuración inválida.
12. Error geométrico.
13. Creación de Feature.
14. Aparición en Timeline.
15. Actualización del Design Tree.
16. Actualización del viewport.
17. Guardado y reconstrucción del documento si el sistema actual lo permite.

Corrige cualquier error encontrado.

---

REGLAS

NO crear otro SelectionManager.

NO crear otro FeatureHistory.

NO crear otro Timeline.

NO crear otro DesignTree.

NO reemplazar el backend CAD existente.

NO rediseñar visualmente toda la aplicación.

NO implementar todavía optimización ni diseño generativo.

NO realizar otra auditoría general.

Si encuentras un problema directamente relacionado con esta implementación, corrígelo dentro de esta tarea.

Si encuentras un problema perteneciente a una etapa posterior, documentarlo y continuar.

---

RESULTADO ESPERADO

Al finalizar debe ser posible utilizar Boolean como una operación CAD real:

Seleccionar
   ↓
Boolean
   ↓
Target + Tools
   ↓
Operación
   ↓
Keep Tools
   ↓
Ejecutar
   ↓
CAD actualizado
   ↓
Feature
   ↓
Timeline
   ↓
Design Tree

La implementación debe quedar preparada para que las próximas operaciones CAD y los futuros estudios CAE utilicen exactamente el mismo concepto de:

selección → configuración → Command → Feature/Study → historial → actualización del modelo.

Al finalizar entrega un informe breve con:

- archivos modificados;
- archivos creados;
- funcionalidades implementadas;
- pruebas realizadas;
- problemas pendientes.