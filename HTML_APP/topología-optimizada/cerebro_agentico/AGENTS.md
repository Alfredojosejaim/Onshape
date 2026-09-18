# AGENTS.md — Manual de uso del Cerebro Agéntico

> Este archivo es la primera lectura obligatoria para cualquier IA que opere
> sobre esta carpeta. Léelo antes de tocar cualquier archivo.

## Qué es esto

Un "cerebro agéntico" es una memoria externa en disco, organizada por capas,
pensada para que una IA (o varias, en distintos proyectos) lea contexto,
escriba lo que aprende, y mantenga trazabilidad de sus acciones — sin
depender de la memoria interna del modelo ni de una sola conversación.

Esta carpeta nace **vacía de contenido** (solo con esta estructura e
instrucciones). Se va llenando sola a medida que se usa. No completes
carpetas "por las dudas" ni inventes contenido de ejemplo salvo que se te
pida explícitamente: la neutralidad inicial es una característica, no un
descuido.

## Las 6 capas y su función

```
cerebro_agentico/
├── inbox/        # 1. Entrada cruda, sin procesar, de un solo uso
├── raw/          # 2. Fuentes originales, ya archivadas, de referencia permanente
├── wiki/         # 3. Conocimiento compilado, sintetizado, reutilizable
├── verdad/       # 4. Hechos inmutables o de alta confianza (fuente de verdad)
├── proyectos/    # 5. Trabajo activo, uno por proyecto/objetivo
└── log/          # 6. Registro cronológico de acciones (bitácora)
```

### 1. `inbox/` — Entrada cruda
Todo lo que llega sin clasificar: pegado de un chat, un link, una idea suelta,
un archivo que el usuario acaba de subir. Es una sala de espera, no un
archivo definitivo.

**Regla de vida útil:** nada debe quedarse en `inbox/` más de una sesión de
trabajo. Al procesar algo de `inbox/`, la IA debe:
1. Decidir si es una fuente (→ mover/copiar a `raw/`), un hecho verificado
   (→ resumir en `verdad/`), conocimiento útil (→ sintetizar en `wiki/`), o
   parte de un proyecto activo (→ mover a `proyectos/<nombre>/`).
2. Borrar o archivar el original de `inbox/` una vez procesado.
3. Dejar una línea en `log/` explicando qué se hizo con eso.

### 2. `raw/` — Fuentes originales
Material de referencia ya clasificado y conservado tal cual: PDFs, capturas,
transcripciones, datasets, código fuente de terceros, exports. No se edita
el contenido de estos archivos, solo se referencia desde `wiki/` o
`proyectos/`.

Organizar por subcarpetas temáticas a medida que aparezcan (ej.
`raw/documentacion_api/`, `raw/entrevistas/`). No crear subcarpetas vacías
de antemano.

### 3. `wiki/` — Conocimiento compilado
Acá vive el conocimiento ya digerido: notas de síntesis, decisiones de
diseño con su razonamiento, glosarios, patrones aprendidos, "lecciones
aprendidas". Es el lugar al que la IA debe ir primero para entender un tema
antes de ponerse a trabajar.

Cada archivo de `wiki/` debe poder responder "¿qué sé sobre X?" sin que haga
falta leer `raw/`. Si `raw/` es la materia prima, `wiki/` es el producto
elaborado.

### 4. `verdad/` — Datos inmutables
Hechos que no cambian, o que cambian muy raramente, y que sirven como
referencia de verificación: credenciales de acceso a herramientas (nunca
secretos reales, solo referencias/nombres), convenciones fijas del proyecto,
decisiones ya cerradas y no revisables, glosario de términos con definición
única y acordada, restricciones de negocio o técnicas que no son negociables.

**Regla de oro:** nada entra en `verdad/` sin confirmación explícita del
usuario. Si la IA no está segura de si algo es realmente inmutable, va a
`wiki/`, no a `verdad/`.

### 5. `proyectos/` — Trabajo activo
Una subcarpeta por proyecto u objetivo activo, nombrada de forma clara y
estable (slug corto, sin espacios: `proyectos/app-topologia/`,
`proyectos/busqueda-laboral/`). Dentro de cada proyecto:

```
proyectos/<nombre-proyecto>/
├── estado.md       # snapshot actual: qué se hizo, qué falta, decisiones abiertas
├── notas/          # notas de trabajo del día a día (opcional, se crea si hace falta)
└── entregables/    # archivos finales producidos para este proyecto (opcional)
```

Un proyecto que queda inactivo por mucho tiempo no se borra: se deja tal
cual, es historial válido. Solo se archiva explícitamente si el usuario lo
pide.

### 6. `log/` — Bitácora
Registro cronológico, append-only, de acciones relevantes tomadas sobre el
cerebro: qué se movió, qué se creó en `verdad/`, qué proyecto se abrió o
cerró, qué decisión importante se tomó. Un archivo por mes
(`log/2026-09.md`) para que ningún archivo crezca sin límite.

Formato de cada línea:
```
YYYY-MM-DD HH:MM — [acción] — descripción breve — (proyecto, si aplica)
```

No se anota cada micro-paso, solo lo que alguien querría poder reconstruir
después: decisiones, archivos creados/movidos entre capas, cierres de
proyecto.

## Reglas generales para la IA que opera acá

1. **Lee antes de escribir.** Antes de crear algo nuevo, revisa si ya existe
   contenido relacionado en `wiki/`, `verdad/` o el proyecto correspondiente.
   No dupliques.
2. **Cada capa tiene un dueño de contenido claro.** Si dudás en qué carpeta
   va algo, usá el criterio: ¿es materia prima sin procesar? `inbox/` o
   `raw/`. ¿Es conocimiento ya masticado? `wiki/`. ¿Es un hecho fijo y
   confirmado? `verdad/`. ¿Es trabajo de un proyecto puntual? `proyectos/`.
3. **No inventes estructura de más.** No crees subcarpetas, archivos de
   plantilla ni contenido "por si acaso". La estructura crece por necesidad
   real, no por anticipación.
4. **Nombrá todo en minúsculas, con guiones, sin espacios ni tildes en los
   nombres de archivo** (el contenido sí puede llevar tildes normalmente).
5. **Registrá en `log/` los cambios que importan**, no cada operación
   trivial.
6. **`verdad/` es sagrada.** No se edita ni se agrega ahí sin confirmación
   explícita del usuario en la conversación.
7. **Un proyecto nuevo = una carpeta nueva en `proyectos/` con su
   `estado.md`.** No mezcles proyectos distintos en un mismo archivo.
8. **Esta jerarquía es genérica a propósito.** No la adaptes a un dominio
   específico (ej. no la conviertas en "cerebro para diseño CAD") salvo que
   el usuario lo pida para un uso puntual; debe seguir sirviendo para
   cualquier proyecto futuro.

## Flujo típico de una sesión

1. La IA lee `AGENTS.md` (este archivo) si es la primera vez que opera acá.
2. Revisa `inbox/` — ¿hay algo pendiente de clasificar?
3. Si el usuario trae una tarea sobre un proyecto existente, va directo a
   `proyectos/<proyecto>/estado.md` para tomar contexto.
4. Si es un proyecto nuevo, lo crea en `proyectos/`.
5. Al cerrar la sesión (o cuando corresponda), actualiza `estado.md` del
   proyecto, procesa lo que quedó en `inbox/`, y deja constancia en `log/`.
