AUDITORÍA Y MODULARIZACIÓN DE LA COMPOSICIÓN VISUAL DE LA UI

Audita el estado REAL actual del repositorio y trabaja sobre la implementación existente. No reconstruyas la interfaz desde cero ni reemplaces sistemas funcionales sin necesidad.

Objetivo

Hacer que la interfaz CAD/CAE sea más modular y fácil de modificar visualmente, manteniendo intacta la lógica existente.

Usa "docs/UI_IMPLEMENTATION_MAP.md" como referencia de trazabilidad. No lo recrees desde cero; actualízalo únicamente si los cambios realizados modifican rutas, clases, señales, controladores o conexiones documentadas.

1. Auditar antes de modificar

Identifica cómo está compuesta actualmente la UI, especialmente:

- "MainWindow"
- barra superior / menús
- toolbars
- panel lateral
- Design Tree
- Properties
- Results
- Timeline
- viewport
- barra inferior / estado
- diálogos y paneles secundarios
- señales y slots
- conexión UI → Controller → Core → State → UI

Determina qué responsabilidades visuales están excesivamente concentradas en "MainWindow" y cuáles conviene extraer.

No extraigas código simplemente por dividir archivos. Cada extracción debe aportar modularidad real.

2. Modularizar la composición visual

Cuando sea conveniente, separa la composición de la interfaz en componentes reutilizables, por ejemplo:

- construcción/configuración del menú
- toolbar
- barra superior
- composición del workspace
- paneles
- barra de estado
- configuración visual/tema
- acciones de UI

Los nombres y estructura finales deben adaptarse al código existente.

"MainWindow" debe quedar principalmente como coordinador de la ventana, no como contenedor de toda la construcción visual y lógica de cada componente.

La modificación de la distribución visual debería poder hacerse modificando los componentes/layouts correspondientes, sin tener que alterar la lógica CAD/CAE.

3. Preservar funcionalidad

Antes de mover cualquier código identifica sus dependencias.

Para cada extracción/refactorización registra:

"ubicación anterior → nueva ubicación → conexiones conservadas"

No rompas ni dupliques:

- señales/slots
- controllers
- estado del documento
- Design Tree
- Timeline
- selección
- propiedades
- resultados
- comandos
- historial
- viewport
- pipeline CAD/CAE

Debe mantenerse una única fuente de verdad.

No crear nuevos managers, estados o modelos paralelos si ya existe uno funcional.

4. Estilo visual

Centraliza, donde sea técnicamente conveniente, colores, tamaños, márgenes, fuentes, iconos y estilos para facilitar futuras modificaciones visuales.

Mantén la dirección visual actual:

- CAD profesional
- oscuro
- gris técnico
- organización inspirada en Onshape/AutoCAD
- viewport como área principal
- árbol/historial y propiedades claramente diferenciados

No hagas todavía un rediseño visual completo ni una búsqueda de “pixel perfect”.

5. Restricciones importantes

- No reemplazar PySide6.
- No reemplazar el viewport funcional.
- No eliminar funcionalidad existente.
- No reescribir el backend.
- No modificar la arquitectura CAD/CAE salvo que sea estrictamente necesario para conservar una conexión.
- No convertir obligatoriamente la interfaz a ".ui".
- "desktop/ui/crea3d_mainwindow.ui" es solamente una referencia visual.
- No crear un editor visual tipo Canva/PowerPoint.
- No crear una segunda arquitectura de UI.
- No realizar cambios cosméticos que dificulten la trazabilidad.

6. Verificación

Después de los cambios verifica:

1. La aplicación inicia correctamente.
2. El viewport continúa funcionando.
3. La selección continúa funcionando.
4. La navegación de cámara no se rompe.
5. Importación CAD/STEP continúa conectada.
6. Operaciones CAD continúan conectadas.
7. Boolean continúa funcionando.
8. Condiciones y cargas continúan conectadas.
9. Mesh y FEA continúan conectados.
10. Design Tree, Properties, Results y Timeline continúan sincronizados.
11. Los tests existentes continúan pasando.

Si alguna conexión ya estaba incompleta antes de la refactorización, no la inventes ni la “soluciones” arbitrariamente. Documenta su estado.

7. Documentación final

Actualiza "docs/UI_IMPLEMENTATION_MAP.md" solamente cuando una ruta o conexión haya cambiado realmente.

Al finalizar informa:

Hallazgos

- principales problemas encontrados en la composición actual.

Modularización realizada

- archivos creados/modificados;
- qué responsabilidad fue extraída;
- qué quedó en "MainWindow".

Trazabilidad

Para cada refactor importante:

"ANTES → DESPUÉS → CONEXIÓN PRESERVADA"

Pendientes

- elementos visuales aún no conectados;
- problemas encontrados que no correspondan a esta etapa.

Verificación

- tests ejecutados;
- resultado;
- smoke test de la aplicación si es posible.

Regla principal: primero comprende y conserva la arquitectura funcional existente; después modulariza la presentación. La interfaz debe quedar más fácil de modificar visualmente sin sacrificar ninguna capacidad CAD/CAE ya implementada.