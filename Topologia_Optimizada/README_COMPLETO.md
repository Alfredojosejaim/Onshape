
# PROMPT — FEATUREScript + COMUNICACIÓN REAL + PREVISUALIZACIÓN DINÁMICA + OPTIMIZACIÓN

Trabaja sobre el proyecto existente de **Topología Optimizada**.

La aplicación actualmente:

* se ejecuta correctamente;
* tiene interfaz web local;
* tiene backend funcionando;
* tiene conexión OAuth 2.0 real con Onshape.

**NO modificar innecesariamente estas partes.**

El problema actual es que el **FeatureScript no se comunica correctamente con la aplicación**, por lo que actualmente no existe un intercambio funcional de datos entre Onshape y el backend.

El objetivo de esta etapa es solucionar esa integración y crear un **Custom Feature de Topología Optimizada integrado dentro de Onshape**, con selección de geometría, restricciones opcionales y **previsualización dinámica mientras el usuario configura la operación**.

---

# 1. PRIORIDAD ABSOLUTA: COMUNICACIÓN REAL

Antes de implementar la optimización, solucionar:

**Onshape → FeatureScript → Backend → FeatureScript → Onshape**

Actualmente este flujo no funciona.

Auditar primero:

* FeatureScript actual;
* endpoint utilizado;
* método HTTP;
* URL;
* payload;
* CORS;
* túnel;
* FastAPI;
* respuesta del backend;
* errores;
* logs;
* configuración de Onshape;
* cualquier mecanismo utilizado para comunicar FeatureScript con Python.

Determinar exactamente:

**¿Por qué el FeatureScript no está llegando a la aplicación?**

No reemplazar el sistema actual sin entender primero el problema.

---

# 2. UTILIZAR `ejemplo.txt`

Existe un archivo:

`ejemplo.txt`

Leerlo completamente antes de modificar el FeatureScript.

Utilizarlo como referencia técnica para estudiar:

* comunicación FeatureScript → aplicación;
* construcción de solicitudes;
* recepción de respuestas;
* formato de datos;
* manejo de errores;
* mecanismos disponibles en FeatureScript.

NO copiar ciegamente el ejemplo.

Adaptarlo a la arquitectura actual.

Si el método utilizado en el ejemplo no es adecuado para el proyecto, explicar por qué y utilizar la alternativa técnicamente correcta.

---

# 3. PRUEBA DE COMUNICACIÓN ANTES DE OPTIMIZAR

Antes de implementar la optimización completa, conseguir esta prueba mínima:

1. Abrir Onshape.
2. Ejecutar el Custom Feature.
3. Introducir una selección simple.
4. FeatureScript genera una solicitud real.
5. Backend recibe la solicitud.
6. Backend devuelve una respuesta.
7. FeatureScript recibe la respuesta.
8. Mostrar dentro de Onshape que la comunicación fue exitosa.

Por ejemplo:

**"Conexión con Topología Optimizada: OK"**

No considerar terminada esta etapa solamente porque el endpoint existe.

Debe existir intercambio real de datos.

---

# 4. INTERFAZ WEB EXTERNA

Mantener la interfaz web externa **MUY SIMPLE**.

No convertirla en el configurador de optimización.

Debe mostrar únicamente:

**TOPOLOGÍA OPTIMIZADA**

Estado de la aplicación:
● Aplicación iniciada

Estado de Onshape:
● Conectado / ○ No conectado

Usuario:
[usuario]

[Conectar con Onshape]

[Desconectar]

Su objetivo es responder:

> ¿La aplicación está funcionando y conectada con Onshape?

Toda la interacción con el modelo debe ocurrir dentro de Onshape.

---

# 5. CUSTOM FEATURE DENTRO DE ONSHAPE

Crear/modificar un Custom Feature denominado:

**"Topología Optimizada"**

Todos los textos visibles para el usuario deben estar en español.

Esto incluye:

* nombre;
* títulos;
* grupos;
* botones;
* campos;
* checkboxes;
* mensajes;
* errores;
* descripciones.

El código interno puede utilizar nombres técnicos en inglés.

---

# 6. INTERFAZ DEL CUSTOM FEATURE

La interfaz debe ser sencilla.

Estructura propuesta:

### Topología Optimizada

**Pieza a modificar**

[ Seleccionar sólido ]

### Restricciones opcionales

☐ Piezas que obstruyen

[ Seleccionar geometría ]

☐ Lugares de anclaje

[ Seleccionar caras ]

☐ Caras sin modificar

[ Seleccionar caras ]

### Optimización

**Porcentaje de optimización**

[ 50 ] %

---

Las opciones de restricciones son **independientes y opcionales**.

No obligar al usuario a seleccionar:

* obstáculos;
* anclajes;
* caras protegidas.

Solamente se aplican cuando el usuario activa su correspondiente opción.

---

# 7. PIEZA A MODIFICAR

Crear:

**"Pieza a modificar"**

Este campo es obligatorio.

El usuario debe seleccionar un sólido.

Validar que la selección sea realmente un sólido.

No aceptar:

* superficies;
* geometría abierta;
* entidades incompatibles.

Si no es sólido:

**"La pieza seleccionada debe ser un sólido."**

La operación no debe continuar.

---

# 8. PIEZAS QUE OBSTRUYEN

Crear:

☐ **Piezas que obstruyen**

Si está desactivado:

* no solicitar selección;
* no enviar obstáculos;
* no aplicar esta restricción.

Si está activado:

☑ **Piezas que obstruyen**

permitir seleccionar las geometrías correspondientes.

Estas representan regiones que la pieza optimizada no debe ocupar.

---

# 9. LUGARES DE ANCLAJE

Crear:

☐ **Lugares de anclaje**

Si está desactivado:

* no solicitar selección;
* no enviar anclajes.

Si está activado:

☑ **Lugares de anclaje**

permitir seleccionar las caras donde la pieza está soportada/fijada.

Estas selecciones representan condiciones de frontera.

**No inventar fuerzas.**

Un anclaje representa una condición de soporte, no una magnitud de fuerza.

Si el solver requiere cargas para realizar un cálculo físico válido, documentar qué información adicional necesita y utilizar solamente parámetros realmente soportados.

---

# 10. CARAS SIN MODIFICAR

Crear:

☐ **Caras sin modificar**

Si está desactivado:

* no solicitar selección;
* no enviar geometría protegida.

Si está activado:

☑ **Caras sin modificar**

permitir seleccionar las caras que deben permanecer protegidas durante la optimización.

---

# 11. PORCENTAJE DE OPTIMIZACIÓN

Agregar:

**"Porcentaje de optimización"**

Ejemplo:

`50 %`

Debe representar claramente cuánto material/geometría se pretende eliminar.

Validar el rango permitido.

Como referencia:

* 0 % → sin reducción;
* 50 % → objetivo de reducción del 50 %;
* 80 % → objetivo de reducción del 80 %.

Pero comprobar que esta interpretación sea compatible con el algoritmo real.

No crear un campo que después no sea utilizado.

---

# 12. PAYLOAD

Diseñar un esquema estructurado.

Conceptualmente:

```text
{
    contexto: {
        documentId,
        workspaceId,
        elementId
    },

    pieza: {
        referencia
    },

    restricciones: {
        obstrucciones: [],
        anclajes: [],
        carasSinModificar: []
    },

    optimizacion: {
        porcentaje
    }
}
```

Los arrays opcionales deben poder estar vacíos.

Ejemplo:

```text
obstrucciones: []
```

si el usuario no activó la opción.

No enviar datos ficticios.

---

# 13. CONTEXTO ONSHAPE

Obtener correctamente:

* documentId;
* workspaceId;
* elementId.

No utilizar IDs hardcodeados.

No pedir al usuario que copie IDs manualmente.

---

# 14. PREVISUALIZACIÓN DINÁMICA

Este es un requisito fundamental.

El usuario debe poder **ver cómo evoluciona la pieza mientras configura el FeatureScript**, antes de aceptar definitivamente la operación.

El comportamiento deseado es similar al sistema de previsualización de las operaciones nativas de Onshape.

El usuario debe poder:

1. seleccionar la pieza;
2. activar/desactivar restricciones;
3. seleccionar geometría;
4. cambiar porcentaje;
5. observar cómo cambia la previsualización;
6. seguir modificando parámetros;
7. finalmente aceptar.

La previsualización debe actualizarse cuando cambien los parámetros relevantes.

---

# 15. NO ESPERAR AL BOTÓN ACEPTAR PARA EL PREVIEW

NO implementar el sistema como:

```text
Configurar todo
      ↓
Aceptar
      ↓
Calcular
```

El objetivo es:

```text
Seleccionar pieza
      ↓
Preview
      ↓
Agregar restricción
      ↓
Actualizar Preview
      ↓
Cambiar porcentaje
      ↓
Actualizar Preview
      ↓
Agregar otra restricción
      ↓
Actualizar Preview
      ↓
Aceptar
      ↓
Resultado final
```

El botón **Aceptar** debe consolidar el resultado final, no ser el primer momento en que se ejecuta todo el procesamiento.

---

# 16. PREVIEW VS CÁLCULO FINAL

Separar conceptualmente:

### PREVISUALIZACIÓN

Prioridad:

**velocidad + respuesta visual**

Debe permitir al usuario entender cómo podría quedar la pieza.

Puede utilizar:

* menor resolución;
* menor cantidad de iteraciones;
* simplificación geométrica;
* cálculo aproximado;

siempre que la representación siga siendo técnicamente válida.

### CÁLCULO FINAL

Prioridad:

**precisión + calidad**

Al aceptar la operación se debe ejecutar el procesamiento final con los parámetros definitivos.

No utilizar el preview como sustituto del resultado final.

---

# 17. IMPORTANTE: NO BLOQUEAR ONSHAPE INNECESARIAMENTE

Antes de implementar el preview, analizar cómo funciona realmente la regeneración de FeatureScript.

Determinar si es técnicamente viable realizar una llamada al backend durante la regeneración.

NO asumir que FeatureScript puede:

* ejecutar procesos externos arbitrariamente;
* esperar indefinidamente;
* mantener conexiones persistentes;
* realizar cálculos largos sin afectar la edición.

Si existe una limitación de tiempo o ejecución:

* documentarla;
* diseñar una arquitectura compatible;
* evitar bloquear la interfaz.

---

# 18. APROVECHAR EL SISTEMA DE PREVIEW DE ONSHAPE

No crear artificialmente un sistema paralelo de transparencia si Onshape ya proporciona un mecanismo nativo de preview para Custom Features.

Investigar cómo Onshape representa:

* geometría resultante;
* geometría temporal;
* opacidad;
* regeneración durante edición.

Utilizar el mecanismo nativo siempre que sea posible.

La intención es que el usuario perciba la optimización como una operación normal de Onshape.

---

# 19. GEOMETRÍA REAL

La aplicación todavía necesita obtener correctamente la geometría de la pieza.

Resolver esta parte.

Utilizar mecanismos reales de Onshape para obtener:

* geometría;
* topología;
* teselación;
* STEP;
* STL;
* u otro formato apropiado.

Elegir el formato compatible con el pipeline actual.

**NO utilizar:**

* geometría aleatoria;
* sólidos ficticios;
* resultados simulados;
* STEP ficticios.

---

# 20. ACTUALIZACIONES DURANTE EL PREVIEW

Cada vez que cambie una condición relevante:

* pieza;
* obstáculo;
* anclaje;
* cara protegida;
* porcentaje;

el sistema debe poder determinar si necesita actualizar el preview.

No recalcular innecesariamente si el cambio no afecta al resultado.

Implementar algún mecanismo de control de solicitudes para evitar:

```text
Cambio 1 → cálculo
Cambio 2 → cálculo
Cambio 3 → cálculo
Cambio 4 → cálculo
```

todos simultáneamente.

Si el usuario realiza varios cambios rápidamente, utilizar una estrategia apropiada de:

* debounce;
* cancelación;
* cola;
* última solicitud válida.

El objetivo es que solamente se procese el estado más reciente.

---

# 21. IDENTIFICACIÓN DE SOLICITUDES

Cada cálculo debe tener un identificador único.

Por ejemplo:

```text
preview_id
```

o equivalente.

Esto permite evitar que una respuesta antigua sobrescriba una configuración más reciente.

Ejemplo:

```text
Preview 001 → configuración A
Preview 002 → configuración B
Preview 003 → configuración C
```

Si llega primero la respuesta de Preview 001 después de haber solicitado Preview 003, esa respuesta debe descartarse.

---

# 22. RESULTADO DEL PREVIEW

El preview debe representar una geometría real o una aproximación técnicamente válida del resultado.

No mostrar solamente:

* porcentaje;
* estadísticas;
* texto;
* una pieza ficticia.

El usuario debe poder visualizar la evolución geométrica.

---

# 23. RESULTADO FINAL

Al pulsar aceptar:

```text
Pieza original
      ↓
Configuración final
      ↓
Cálculo final
      ↓
Pieza optimizada
      ↓
Resultado incorporado en Onshape
```

No utilizar como solución final:

**"Descargar STEP → importar manualmente."**

El objetivo es que el resultado forme parte del flujo de modelado de Onshape.

Si la API o FeatureScript tienen una limitación que impide completar esto directamente, investigar el mecanismo oficial alternativo y documentarlo.

No inventar capacidades.

---

# 24. COMUNICACIÓN FEATURESCRIPT ↔ BACKEND

La arquitectura debe soportar:

```text
FEATURESCRIPT
      │
      │ Preview Request
      ▼
   FASTAPI
      │
      ▼
Preview Solver
      │
      ▼
   FASTAPI
      │
      │ Preview Response
      ▼
FEATURESCRIPT
      │
      ▼
Preview Onshape
```

Y para el resultado final:

```text
FEATURESCRIPT
      │
      │ Final Request
      ▼
   FASTAPI
      │
      ▼
Final Solver
      │
      ▼
Resultado
      │
      ▼
FEATURESCRIPT / ONSHAPE
```

---

# 25. MANEJO DE ESTADOS

Internamente distinguir:

* `READY`
* `PREVIEW_REQUESTED`
* `PREVIEW_PROCESSING`
* `PREVIEW_READY`
* `FINAL_REQUESTED`
* `FINAL_PROCESSING`
* `FINAL_READY`
* `ERROR`

La interfaz del FeatureScript puede mostrar mensajes simples.

Por ejemplo:

**"Generando previsualización..."**

**"Previsualización actualizada."**

**"Calculando resultado final..."**

---

# 26. RESTRICCIONES OPCIONALES

Validar correctamente todos los casos:

### Caso A

Pieza solamente.

Debe funcionar.

### Caso B

Pieza + obstáculos.

Debe funcionar.

### Caso C

Pieza + anclajes.

Debe funcionar.

### Caso D

Pieza + caras protegidas.

Debe funcionar.

### Caso E

Pieza + todas las restricciones.

Debe funcionar.

Nunca asumir que todas las restricciones están presentes.

---

# 27. VALIDACIÓN

Antes de procesar:

Verificar:

* pieza seleccionada;
* pieza sólida;
* porcentaje válido;
* referencias válidas;
* restricciones compatibles.

No exigir restricciones opcionales.

---

# 28. ERRORES

Todos los errores visibles deben estar en español.

Controlar:

* pieza no seleccionada;
* pieza no sólida;
* selección inválida;
* porcentaje inválido;
* backend desconectado;
* timeout;
* error de comunicación;
* error de geometría;
* error del solver;
* resultado inválido.

---

# 29. PRUEBAS POR ETAPAS

No implementar todo simultáneamente.

### ETAPA A — Comunicación

FeatureScript → Backend → FeatureScript.

### ETAPA B — Pieza

Seleccionar sólido y transmitirlo correctamente.

### ETAPA C — Restricciones

Probar individualmente:

* obstáculos;
* anclajes;
* caras protegidas.

### ETAPA D — Porcentaje

Enviar y validar porcentaje.

### ETAPA E — Preview

Modificar un parámetro y comprobar que el preview cambia.

### ETAPA F — Preview dinámico

Modificar varios parámetros y comprobar:

* debounce;
* cancelación;
* identificación de solicitudes;
* respuesta correcta.

### ETAPA G — Geometría real

Obtener la geometría real.

### ETAPA H — Preview geométrico real

Mostrar una representación válida del resultado.

### ETAPA I — Cálculo final

Ejecutar el procesamiento completo.

### ETAPA J — Resultado

Incorporar la geometría resultante a Onshape.

No avanzar si la etapa anterior no funciona.

---

# 30. NO MODIFICAR INNECESARIAMENTE LA APLICACIÓN EXISTENTE

Conservar:

* OAuth;
* conexión Onshape;
* interfaz web;
* estructura funcional existente.

Modificar solamente lo necesario para integrar el nuevo flujo.

No rehacer el proyecto completo.

---

# 31. AUDITORÍA FINAL

Al finalizar verificar:

### Aplicación

[ ] Backend funciona
[ ] OAuth funciona
[ ] UI simple funciona
[ ] Conexión Onshape funciona

### FeatureScript

[ ] Custom Feature creado
[ ] Nombre en español
[ ] Interfaz en español
[ ] Pieza a modificar
[ ] Validación de sólido
[ ] Obstáculos opcionales
[ ] Anclajes opcionales
[ ] Caras protegidas opcionales
[ ] Porcentaje de optimización

### Comunicación

[ ] FeatureScript → Backend
[ ] Backend → FeatureScript
[ ] Comunicación real
[ ] Errores controlados

### Preview

[ ] Preview inicial
[ ] Preview después de cambios
[ ] Preview actualizado dinámicamente
[ ] No requiere pulsar Aceptar para visualizar
[ ] Debounce/cancelación
[ ] Identificador de solicitudes
[ ] Respuestas antiguas descartadas

### Geometría

[ ] Pieza real
[ ] Geometría real
[ ] Sin datos aleatorios
[ ] Sin mocks

### Resultado

[ ] Preview válido
[ ] Cálculo final separado
[ ] Resultado final real
[ ] Resultado incorporable a Onshape

Si algo no puede completarse:

**COMPLETO / PARCIAL / PENDIENTE / LIMITACIÓN DE ONSHAPE**

explicando exactamente la causa.

---

# REGLAS FUNDAMENTALES

1. La interfaz web externa debe permanecer **simple**.

2. El usuario debe controlar la operación **desde Onshape**.

3. FeatureScript es la interfaz CAD y puente de integración.

4. Python/FastAPI realiza el procesamiento pesado.

5. La comunicación debe ser REAL.

6. No utilizar mocks para ocultar problemas.

7. No utilizar geometría aleatoria.

8. No inventar APIs.

9. Las restricciones son opcionales.

10. El FeatureScript solo acepta sólidos válidos.

11. Todos los textos visibles están en español.

12. El porcentaje debe utilizarse realmente.

13. Debe existir diferencia entre **PREVIEW** y **RESULTADO FINAL**.

14. El preview debe actualizarse mientras el usuario edita el FeatureScript.

15. No esperar al botón Aceptar para mostrar el preview.

16. Priorizar la velocidad del preview sobre la precisión final.

17. Priorizar la precisión en el cálculo final.

18. Evitar cálculos simultáneos innecesarios.

19. Una respuesta antigua nunca debe sobrescribir un preview más reciente.

20. Aprovechar los mecanismos nativos de preview de Onshape siempre que sea técnicamente posible.

21. No bloquear innecesariamente la interfaz de Onshape con cálculos largos.

22. Si una capacidad no es posible mediante FeatureScript/Onshape, no simularla: investigar la alternativa real y documentar la limitación.

23. No rehacer componentes que ya funcionan.

---

## RESULTADO FUNCIONAL DESEADO

El comportamiento final debe aproximarse a:

```text
Onshape
   │
   ▼
Topología Optimizada
   │
   ├── Pieza a modificar
   │
   ├── ☐ Piezas que obstruyen
   │
   ├── ☐ Lugares de anclaje
   │
   ├── ☐ Caras sin modificar
   │
   └── Porcentaje: 50 %
             │
             ▼
        PREVIEW
             │
             ▼
     Usuario sigue editando
             │
             ├── cambia selección
             ├── activa restricción
             ├── modifica porcentaje
             │
             ▼
       PREVIEW actualizado
             │
             ▼
          Aceptar
             │
             ▼
       CÁLCULO FINAL
             │
             ▼
       PIEZA OPTIMIZADA
             │
             ▼
           ONSHAPE
```

**La prioridad inmediata no es conseguir todavía el solver perfecto.**

La prioridad es conseguir una integración técnicamente sólida donde:

**el FeatureScript se comunique realmente con la aplicación, capture correctamente las selecciones y parámetros, pueda solicitar una previsualización y pueda actualizarla durante la edición.**

Después se profundizará en el solver y la generación de la geometría final.
