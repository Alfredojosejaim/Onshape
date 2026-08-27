## PROTOCOLO OBLIGATORIO DE BLOQUEO TÉCNICO E INVESTIGACIÓN EXTERNA

Este protocolo es de cumplimiento OBLIGATORIO para cualquier problema técnico que aparezca durante la implementación, especialmente cuando intervengan bibliotecas, frameworks, APIs, motores de cálculo, dependencias externas o tecnologías cuya documentación no esté completamente disponible en el contexto actual.

### 1. Principio fundamental

La IA ejecutora NO debe resolver problemas complejos mediante ensayo y error ilimitado.

El ciclo:

    ERROR → hipótesis → modificación → ERROR → nueva hipótesis → modificación → ...

queda PROHIBIDO cuando la causa del problema no pueda determinarse con suficiente certeza.

El objetivo no es producir rápidamente otra versión del código, sino identificar correctamente la causa del bloqueo antes de modificar nuevamente la implementación.

---

### 2. Corrección autónoma permitida

Cuando aparezca un error, la IA ejecutora podrá realizar UNA única corrección autónoma únicamente si:

- la causa es evidente;
- la solución está respaldada por el código existente;
- la solución está respaldada por documentación ya disponible;
- no requiere especulación;
- no implica cambiar la arquitectura;
- y puede verificarse mediante una prueba concreta.

Después de aplicar la corrección, deberá volver a ejecutar la prueba.

---

### 3. Regla de bloqueo inmediato

Si la corrección autónoma falla, o si desde el primer momento la causa no es evidente, la IA debe:

1. DETENER inmediatamente la implementación relacionada con el problema.
2. NO generar otro enfoque alternativo por ensayo y error.
3. NO crear múltiples scripts intentando encontrar una solución por fuerza bruta.
4. NO modificar la arquitectura para esquivar el problema.
5. NO reemplazar una biblioteca o tecnología sin autorización.
6. NO declarar que una tecnología es incompatible únicamente porque una implementación haya fallado.
7. NO continuar desarrollando funcionalidades que dependan del componente bloqueado.

El estado debe pasar inmediatamente a:

    BLOQUEADO — REQUIERE INVESTIGACIÓN

---

### 4. Tracker obligatorio del bloqueo

El bloqueo debe documentarse DENTRO de `resumen_implementacion.md`.

NO crear un archivo independiente para cada error.

El tracker debe contener como mínimo:

#### Identificación

- componente afectado;
- funcionalidad que se intentaba implementar;
- fecha;
- estado actual.

#### Entorno

- sistema operativo;
- versión de Python;
- versión de la biblioteca o framework;
- versiones de dependencias relevantes;
- entorno virtual utilizado;
- arquitectura del sistema cuando sea relevante.

#### Reproducción

- comando exacto ejecutado;
- script utilizado;
- archivo afectado;
- función o sección;
- línea aproximada del error;
- condiciones necesarias para reproducirlo.

#### Evidencia

- traceback COMPLETO;
- mensaje de error COMPLETO;
- salida relevante de consola;
- resultado de las pruebas anteriores;
- archivos o configuraciones involucradas.

No resumir el error si el resumen elimina información útil para diagnosticarlo.

#### Acciones realizadas

Registrar cronológicamente:

1. qué se intentó;
2. qué se modificó;
3. qué resultado produjo;
4. qué hipótesis quedó descartada.

No ocultar intentos fallidos.

#### Hipótesis

Separar claramente:

- hechos comprobados;
- hipótesis;
- información desconocida.

La IA NO debe presentar una hipótesis como hecho.

#### Pregunta de investigación

El tracker debe terminar indicando exactamente qué debe investigarse.

Ejemplo:

    ¿Cuál es la forma oficialmente soportada de inicializar X
    utilizando la versión Y de la biblioteca Z?

La pregunta debe ser lo suficientemente precisa para que otra IA pueda investigarla directamente en documentación oficial, ejemplos oficiales, repositorios oficiales o fuentes técnicas confiables.

---

### 5. Investigación externa

Cuando el problema quede bloqueado, la investigación debe realizarse como una actividad separada de la implementación.

La IA investigadora debe determinar:

- causa real del problema;
- API o mecanismo correcto;
- compatibilidad de versiones;
- configuración necesaria;
- limitaciones reales de la tecnología;
- solución recomendada;
- referencias utilizadas.

La investigación NO debe modificar el repositorio.

Su función es producir conocimiento y una solución técnicamente fundamentada.

---

### 6. Separación estricta de roles

Se establece la siguiente separación:

    IA EJECUTORA
    ↓
    implementa, ejecuta y verifica

    IA INVESTIGADORA
    ↓
    investiga documentación, causa y solución

La IA ejecutora NO debe intentar sustituir una investigación externa mediante múltiples intentos especulativos.

La IA investigadora NO debe modificar directamente la implementación salvo que se le solicite expresamente.

---

### 7. Fuentes para resolver bloqueos

Cuando sea necesaria investigación externa, se debe priorizar:

1. documentación oficial;
2. documentación de la versión específica utilizada;
3. ejemplos oficiales;
4. repositorio oficial;
5. issues oficiales;
6. fuentes técnicas secundarias únicamente cuando las anteriores no sean suficientes.

No utilizar una solución encontrada en Internet como definitiva sin comprobar su compatibilidad con las versiones utilizadas por el proyecto.

---

### 8. Prohibición de declarar incompatibilidad prematuramente

Un error de:

- implementación;
- configuración;
- API;
- versión;
- dependencia;
- importación;
- inicialización;
- uso incorrecto;
- documentación incompleta;

NO constituye evidencia de que una tecnología sea incompatible con el proyecto.

Para declarar:

    TECNOLOGÍA NO VIABLE
    o
    TECNOLOGÍA INCOMPATIBLE

debe existir evidencia técnica suficiente que demuestre una limitación real.

La documentación debe distinguir siempre entre:

    ERROR DE IMPLEMENTACIÓN

    ERROR DE CONFIGURACIÓN

    ERROR DE INTEGRACIÓN

    LIMITACIÓN DOCUMENTAL

    LIMITACIÓN DE LA TECNOLOGÍA

    INFORMACIÓN NO DETERMINADA

---

### 9. Prohibición de acumulación de experimentos improductivos

Cuando varios intentos consecutivos persigan resolver el MISMO error sin nueva información técnica, deben detenerse.

No se permite crear:

- scripts alternativos innecesarios;
- pruebas duplicadas;
- implementaciones paralelas;
- soluciones temporales sin justificación;
- archivos de diagnóstico redundantes.

Antes de crear un nuevo experimento debe existir una pregunta técnica concreta que dicho experimento pueda responder.

Si no existe una pregunta concreta, NO se crea el experimento.

---

### 10. Reanudación después de un bloqueo

La IA ejecutora solo podrá continuar cuando se disponga de una solución técnicamente fundamentada.

Antes de implementar deberá:

1. leer nuevamente el tracker;
2. revisar la solución obtenida;
3. identificar exactamente qué debe modificarse;
4. implementar únicamente la corrección necesaria;
5. ejecutar nuevamente la prueba que produjo el bloqueo;
6. verificar que el error desapareció;
7. comprobar que no se introdujeron regresiones.

Si la solución investigada vuelve a fallar, NO se inicia automáticamente otro ciclo de ensayo y error.

Se vuelve a aplicar este protocolo desde el punto 3.

---

### 11. Cierre obligatorio del bloqueo

Un bloqueo solo puede cambiar de:

    BLOQUEADO

a:

    RESUELTO

cuando exista evidencia ejecutable que demuestre que:

1. la causa fue identificada;
2. la solución fue aplicada;
3. la prueba original ahora funciona;
4. el resultado es reproducible;
5. la solución está documentada.

El resumen de implementación debe conservar el historial suficiente para entender qué ocurrió y cómo se resolvió.

---

### 12. Principio de economía de tokens y recursos

La IA debe priorizar:

    DIAGNÓSTICO → EVIDENCIA → INVESTIGACIÓN → SOLUCIÓN → EJECUCIÓN

y evitar:

    ERROR → CÓDIGO ALEATORIO → ERROR → CÓDIGO ALEATORIO

El consumo de tokens, tiempo de ejecución y generación de archivos debe considerarse un recurso limitado.

Una investigación externa correctamente planteada es preferible a múltiples intentos especulativos.

---

### 13. Regla de autoridad

En caso de conflicto entre una suposición de la IA ejecutora y evidencia obtenida posteriormente de documentación oficial, prevalece la evidencia documentada.

Toda corrección importante derivada de una investigación externa debe quedar registrada en `resumen_implementacion.md`.

---

### 14. Regla final

ANTE UN BLOQUEO COMPLEJO:

    NO ADIVINAR.
    NO INSISTIR INDEFINIDAMENTE.
    NO MULTIPLICAR SCRIPTS.
    NO CAMBIAR LA ARQUITECTURA.
    NO DECLARAR INCOMPATIBILIDAD SIN EVIDENCIA.

    DETENER.
    DOCUMENTAR.
    CREAR TRACKER.
    INVESTIGAR.
    OBTENER SOLUCIÓN.
    EJECUTAR.
    VERIFICAR.
    CONTINUAR.

Este protocolo tiene prioridad sobre cualquier instrucción de "continuar intentando" cuando el problema no pueda resolverse con evidencia suficiente.