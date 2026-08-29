MIGRACIÓN A INTERFAZ GRÁFICA DESKTOP NATIVA + VISOR 3D

ROL

Actúa como un PROGRAMADOR SENIOR ESPECIALISTA EN DESARROLLO DE APLICACIONES DESKTOP, VISUALIZACIÓN 3D, CAD/CAE Y ARQUITECTURA DE SOFTWARE.

Trabaja directamente sobre el proyecto existente del repositorio.

NO desarrolles una aplicación desde cero.

Primero AUDITA la implementación actual, comprende su arquitectura y posteriormente realiza la migración necesaria.

---

OBJETIVO

La aplicación actualmente utiliza una interfaz web local para mostrar y controlar el visor 3D.

El objetivo es reemplazar esa interfaz por una INTERFAZ DESKTOP NATIVA, manteniendo y reutilizando la mayor cantidad posible de la arquitectura existente.

La aplicación debe ejecutarse como una aplicación de escritorio y abrir directamente su ventana gráfica.

NO utilizar el navegador como interfaz principal.

La solución debe quedar preparada para evolucionar posteriormente hacia una aplicación CAD/CAE profesional.

---

ESTRATEGIA TECNOLÓGICA

La aplicación existente está desarrollada principalmente en Python, por lo que Python debe considerarse la tecnología base y debe conservarse siempre que sea técnicamente razonable.

Sin embargo, NO cierres la arquitectura a Python ni a un único lenguaje o framework.

Primero analiza el proyecto y determina cuál es la solución tecnológica más adecuada para conseguir:

- interfaz desktop nativa;
- viewport 3D acelerado por GPU;
- navegación CAD fluida;
- buena integración con la arquitectura existente;
- mantenibilidad;
- extensibilidad futura;
- rendimiento con geometría compleja.

La opción preferida inicialmente es:

Python + PySide6 + tecnología 3D compatible con GPU

Pero puedes utilizar otras tecnologías, frameworks o lenguajes, incluyendo una arquitectura híbrida, si la auditoría demuestra que aportan una ventaja técnica significativa.

Por ejemplo, podría utilizarse un componente especializado en otro lenguaje para el rendering o viewport manteniendo Python como capa principal de aplicación.

NO introduzcas otro lenguaje únicamente por preferencia personal o complejidad innecesaria.

Si decides utilizar una tecnología diferente de Python/PySide6, justifica brevemente la decisión y explica cómo se integra con el proyecto existente.

NO conviertas todo el proyecto a otro lenguaje sin una justificación técnica clara.

NO desarrolles un motor gráfico desde cero.

---

AUDITORÍA PREVIA OBLIGATORIA

Antes de modificar código:

1. Revisa la estructura completa del proyecto.
2. Identifica el punto de entrada actual.
3. Identifica la interfaz gráfica actual.
4. Identifica cómo se crea actualmente el visor 3D.
5. Identifica qué biblioteca o tecnología gráfica utiliza.
6. Identifica cómo se cargan los modelos.
7. Identifica cómo se representa actualmente la geometría.
8. Identifica los controles de cámara existentes.
9. Identifica el sistema actual de selección.
10. Identifica qué componentes pueden reutilizarse.
11. Identifica qué componentes deben reemplazarse.
12. Identifica las dependencias gráficas actuales.
13. Identifica qué partes de la arquitectura dependen actualmente del navegador.
14. Determina cuál es la estrategia tecnológica más adecuada para la nueva interfaz.

No elimines código antes de comprobar que realmente pertenece a la interfaz que se está reemplazando.

---

NUEVA VENTANA PRINCIPAL

Crear una ventana desktop nativa con una estructura similar a una aplicación CAD.

Debe existir:

- barra de menú;
- barra de herramientas;
- viewport 3D central;
- panel lateral izquierdo;
- panel lateral derecho;
- barra de estado.

La distribución exacta puede adaptarse si existe una solución arquitectónicamente mejor.

El viewport debe ocupar la mayor parte de la ventana.

Los paneles deben poder redimensionarse.

Siempre debe priorizarse el espacio disponible para visualizar el modelo.

---

VIEWPORT 3D

El viewport es el componente principal de esta etapa.

Debe permitir visualizar el modelo 3D de manera fluida y utilizar aceleración mediante GPU.

Implementar:

- órbita;
- rotación;
- zoom;
- pan;
- ajuste del modelo a pantalla;
- vista isométrica;
- vista frontal;
- vista posterior;
- vista superior;
- vista inferior;
- vista izquierda;
- vista derecha.

La navegación debe sentirse similar a la de una aplicación CAD.

No desarrolles un sistema de rendering desde cero.

Utiliza una biblioteca o framework 3D adecuado al proyecto.

---

VISUALIZACIÓN

Implementar diferentes modos de visualización:

- sombreado;
- sombreado con aristas;
- wireframe;
- transparencia.

Agregar controles para:

- mostrar/ocultar ejes;
- mostrar/ocultar rejilla;
- centrar modelo;
- ajustar cámara.

La representación debe utilizar aceleración gráfica mediante GPU.

---

SELECCIÓN

El viewport debe disponer de selección mediante mouse.

Como mínimo debe ser posible:

- seleccionar el modelo;
- identificar visualmente la selección;
- deseleccionar.

La arquitectura del sistema de selección debe quedar preparada para poder diferenciar posteriormente entidades geométricas como:

- sólidos;
- caras;
- aristas;
- vértices.

No es necesario implementar todavía herramientas avanzadas de selección.

Lo importante es crear una base sólida y extensible.

---

ESCENA 3D

Separar conceptualmente:

- escena;
- cámara;
- geometría;
- representación visual;
- selección;
- renderer.

Evitar colocar toda la lógica del visor dentro de un único archivo.

Una estructura posible sería:

ui/
    main_window.py
    panels/

viewport/
    viewport_3d.py
    camera.py
    scene.py
    renderer.py
    selection.py

Adapta esta estructura al proyecto existente.

No la copies ciegamente.

Si la arquitectura actual permite una solución mejor, utiliza esa solución.

---

RENDERER

La interfaz y la lógica de escena no deben depender directamente de llamadas específicas de la API gráfica repartidas por todo el proyecto.

Centraliza la comunicación con el sistema gráfico.

Conceptualmente:

UI
 ↓
Viewport
 ↓
Scene
 ↓
Renderer
 ↓
GPU

La implementación concreta puede variar según la tecnología seleccionada.

Esto debe permitir evolucionar posteriormente el sistema gráfico sin tener que reescribir toda la interfaz.

---

GEOMETRÍA

Conserva el mecanismo existente para cargar los modelos siempre que sea correcto.

Primero determina qué formato utiliza actualmente el proyecto.

Si actualmente trabaja con STEP, STL u otro formato, adapta el mecanismo existente al nuevo viewport.

No reemplaces el sistema de geometría simplemente para cambiar la interfaz.

El objetivo de esta etapa es cambiar la PRESENTACIÓN E INTERACCIÓN GRÁFICA, no rehacer innecesariamente el procesamiento geométrico.

---

RENDIMIENTO

El viewport debe estar preparado para trabajar posteriormente con geometría y mallas de mayor complejidad.

Evita:

- reconstruir toda la escena innecesariamente;
- recalcular geometría durante cada movimiento de cámara;
- duplicar objetos sin necesidad;
- bloquear la interfaz;
- realizar operaciones pesadas en eventos de mouse.

La navegación de cámara debe mantenerse fluida.

Las operaciones pesadas deberán quedar preparadas para ejecutarse fuera del hilo principal cuando corresponda.

---

INTERFAZ

El diseño debe ser:

- profesional;
- limpio;
- técnico;
- moderno;
- sobrio;
- orientado a CAD.

Evita una apariencia de página web.

Debe sentirse como una aplicación de ingeniería.

El viewport debe ser visualmente dominante.

Los paneles laterales deben utilizar componentes nativos o apropiados para una aplicación desktop.

---

RESPONSIVIDAD

La ventana debe poder:

- maximizarse;
- minimizarse;
- redimensionarse;
- cambiar de resolución;
- utilizar diferentes tamaños de pantalla.

Los paneles deben adaptarse correctamente.

El viewport debe aprovechar automáticamente el espacio disponible.

---

ESTRUCTURA DEL CÓDIGO

Mantén una separación clara entre:

- interfaz;
- viewport;
- cámara;
- escena;
- renderer;
- selección;
- carga/representación del modelo.

No crear un archivo monolítico con toda la aplicación.

Utiliza clases y responsabilidades claramente separadas.

Mantén el código limpio, legible y documentado cuando sea necesario.

Si se utiliza más de un lenguaje, define claramente las responsabilidades y el mecanismo de comunicación entre componentes.

Evita introducir una arquitectura híbrida innecesariamente compleja.

---

MIGRACIÓN

No elimines inmediatamente la interfaz web actual.

Primero determina qué partes son exclusivamente gráficas y cuáles contienen lógica reutilizable.

Reutiliza todo aquello que siga siendo útil.

Una vez comprobado que la nueva interfaz funciona correctamente, elimina únicamente los componentes web que hayan quedado definitivamente obsoletos.

---

EJECUCIÓN

Al ejecutar la aplicación debe abrirse directamente la ventana desktop.

No debe ser necesario abrir manualmente un navegador.

Conserva el punto de entrada actual siempre que sea apropiado.

Por ejemplo:

python main.py

Si la arquitectura resultante requiere otro mecanismo de ejecución, utiliza el necesario y documenta claramente cómo iniciar la aplicación.

---

VALIDACIÓN

Antes de finalizar prueba obligatoriamente:

1. Inicio de la aplicación.
2. Apertura de la ventana principal.
3. Visualización del viewport.
4. Carga de un modelo existente.
5. Rotación orbital.
6. Zoom.
7. Pan.
8. Vistas predefinidas.
9. Ajuste automático del modelo.
10. Wireframe.
11. Sombreado.
12. Sombreado con aristas.
13. Transparencia.
14. Mostrar/ocultar ejes.
15. Mostrar/ocultar rejilla.
16. Selección.
17. Deselección.
18. Redimensionamiento de ventana.
19. Redimensionamiento de paneles.
20. Cierre correcto de la aplicación.

Corrige los errores encontrados antes de finalizar.

---

REGLAS

NO conviertas Python a otro lenguaje sin una justificación técnica.

NO cierres la arquitectura exclusivamente a Python si otra tecnología resulta claramente más adecuada para una parte específica del sistema.

NO desarrolles un motor gráfico desde cero.

NO rehagas innecesariamente el procesamiento de geometría.

NO elimines funcionalidades existentes sin comprobar su dependencia.

NO implementes funcionalidades que no sean necesarias para esta etapa.

NO introduzcas tecnologías adicionales sin una necesidad técnica concreta.

Prioriza una base gráfica sólida, limpia, extensible y preparada para evolucionar hacia una aplicación CAD/CAE profesional.

---

RESULTADO FINAL

Al finalizar, la aplicación debe disponer de una interfaz desktop nativa con un viewport 3D acelerado por GPU que permita navegar e inspeccionar el modelo de forma similar a una aplicación CAD.

La tecnología final debe ser la que resulte técnicamente más adecuada después de auditar el proyecto, priorizando la reutilización de Python y de los componentes existentes.

Entrega finalmente un informe breve indicando:

- tecnología gráfica seleccionada;
- justificación de la elección;
- arquitectura utilizada;
- archivos creados;
- archivos modificados;
- archivos eliminados;
- dependencias agregadas;
- componentes reutilizados;
- componentes reemplazados;
- cómo iniciar la aplicación;
- pruebas realizadas;
- problemas pendientes.