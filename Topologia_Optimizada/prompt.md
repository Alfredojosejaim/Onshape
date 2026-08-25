
# AUDITORÍA Y LIMPIEZA ESTRICTA DEL REPOSITORIO

## ROL

Actúa como ingeniero senior especializado en Git, GitHub, Python y saneamiento de repositorios.

Tu única misión en esta iteración es auditar y limpiar estrictamente el repositorio:

`Alfredojosejaim/Onshape`

dentro de:

`Topologia_Optimizada/`

NO debes implementar nuevas funcionalidades del proyecto.

NO debes modificar la arquitectura.

NO debes implementar FEA.

NO debes implementar TopOpt.

NO debes modificar el pipeline CAD salvo que sea estrictamente necesario para eliminar archivos basura, generados o accidentalmente versionados.

---

# DOCUMENTOS DE REFERENCIA

Antes de realizar cualquier modificación debes leer:

1. `README.md`
2. `prompt.md`
3. `metodologia.md`
4. `RESUMEN_IMPLEMENTACION.md`

Respeta obligatoriamente `metodologia.md`.

`README.md` representa la visión/especificación general del proyecto.

`prompt.md` representa la tarea técnica vigente.

`metodologia.md` representa las reglas obligatorias de trabajo.

`RESUMEN_IMPLEMENTACION.md` representa el estado real documentado.

No alteres estos documentos salvo que sea estrictamente necesario para registrar los resultados de esta limpieza.

---

# OBJETIVO

Dejar el repositorio:

- limpio;
- reproducible;
- seguro;
- liviano;
- correctamente versionado;
- libre de secretos;
- libre de archivos generados;
- libre de entornos locales;
- libre de binarios innecesarios;
- preparado para GitHub;
- preparado para que otra PC pueda clonar el proyecto y reconstruir su entorno.

---

# FASE 1 — AUDITORÍA DEL ESTADO REAL DE GIT

Antes de borrar o modificar cualquier archivo, audita el repositorio REAL.

No te limites a leer `.gitignore`.

Debes comprobar:

- `git status`
- `git ls-files`
- archivos trackeados;
- archivos no trackeados;
- archivos ignorados;
- archivos grandes;
- archivos binarios;
- archivos generados;
- archivos duplicados;
- historial reciente;
- posibles secretos;
- archivos que GitHub no permite subir por tamaño;
- archivos que estén siendo omitidos por `.gitignore`;
- archivos que hayan sido trackeados anteriormente y ahora estén ignorados.

IMPORTANTE:

`.gitignore` NO significa que un archivo haya dejado de estar trackeado.

Debes distinguir claramente:

TRACKED
UNTRACKED
IGNORED

---

# FASE 2 — AUDITORÍA DE ARCHIVOS PESADOS

Buscar archivos grandes dentro del repositorio.

Como mínimo investigar:

- archivos mayores a 10 MB;
- archivos mayores a 50 MB;
- archivos mayores a 100 MB;
- binarios;
- modelos CAD;
- STEP;
- STL;
- mallas;
- certificados;
- ejecutables;
- instaladores;
- bases de datos;
- caches;
- entornos virtuales;
- archivos temporales.

Para cada archivo pesado determinar:

1. qué es;
2. si es necesario para el proyecto;
3. si debe estar versionado;
4. si puede regenerarse;
5. si debe ignorarse;
6. si debe almacenarse mediante Git LFS;
7. si debe eliminarse.

NO borrar archivos importantes sin identificar previamente su función.

---

# FASE 3 — ARCHIVOS QUE NO DEBEN ESTAR EN GIT

Auditar específicamente:

- `.env`
- secretos OAuth
- tokens
- API keys
- certificados privados
- claves privadas
- `certs/`
- `mkcert.exe`
- `.venv/`
- `venv/`
- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `.idea/`
- `.vscode/` cuando contenga configuración específica de máquina
- `node_modules/`
- archivos temporales
- logs
- dumps
- archivos generados por IDE
- archivos de sistema
- archivos de compilación
- archivos de cache.

---

# FASE 4 — SECRETOS

Auditar TODO el repositorio buscando:

- `ONSHAPE_OAUTH_CLIENT_SECRET`
- tokens
- passwords
- API keys
- private keys
- certificados
- credenciales
- URLs con credenciales embebidas.

Revisar también el historial Git si existe evidencia de que un secreto estuvo previamente versionado.

Si encuentras un secreto REAL:

1. NO lo copies al informe;
2. NO lo vuelvas a mostrar;
3. indícalo solamente como `SECRET DETECTADO`;
4. eliminarlo del estado actual;
5. comprobar si permanece en el historial;
6. si permanece en el historial, documentar que requiere rotación y/o limpieza histórica.

NO inventes credenciales.

---

# FASE 5 — `.GITIGNORE`

Auditar el `.gitignore` actual.

Debe cubrir correctamente como mínimo:

## Python

- `.venv/`
- `venv/`
- `__pycache__/`
- `*.py[cod]`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`

## Entorno

- `.env`
- `.env.*`

EXCEPCIÓN:

`.env.example` debe permanecer versionado.

## HTTPS local

- `certs/`
- certificados generados
- claves privadas
- CA local

## mkcert

`mkcert.exe`

## IDE

- `.idea/`
- configuraciones locales de VS Code cuando corresponda.

## Sistema operativo

- `Thumbs.db`
- `.DS_Store`

## Logs

- `*.log`

## Builds / temporales

Agregar únicamente patrones apropiados al proyecto.

NO agregar patrones excesivamente amplios que puedan ocultar archivos fuente importantes.

---

# FASE 6 — ARCHIVOS IMPORTANTES

Antes de eliminar cualquier archivo, clasificarlo:

### NECESARIO Y VERSIONADO

Ejemplo:

- `.py`
- `.js`
- `.html`
- `.md`
- `.toml`
- `.json`
- `.bat`
- `.ps1`
- `.gitignore`
- `.env.example`

### NECESARIO PERO NO VERSIONADO

Ejemplo:

- `.env`
- certificados;
- CA;
- archivos locales;
- dependencias instaladas;
- mkcert descargado.

### GENERABLE

Ejemplo:

- caches;
- bytecode;
- builds;
- certificados;
- entorno virtual.

### INNECESARIO

Archivos basura, duplicados o temporales.

---

# FASE 7 — ARCHIVOS PESADOS NECESARIOS

Si encuentras un archivo pesado que REALMENTE sea necesario para el proyecto:

NO lo elimines automáticamente.

Determina primero si:

### Opción A

Puede regenerarse.

→ Ignorarlo.

### Opción B

Debe ser compartido pero no pertenece al código.

→ Evaluar almacenamiento externo.

### Opción C

Debe estar versionado.

→ Evaluar Git LFS.

Si recomiendas Git LFS:

- no implementarlo automáticamente;
- documentar qué archivo lo requiere;
- explicar por qué;
- indicar tamaño;
- indicar impacto.

NO convertir automáticamente todo archivo grande en Git LFS.

---

# FASE 8 — MKCERT

El proyecto utiliza mkcert para HTTPS local.

`mkcert.exe` NO debe versionarse si la arquitectura actual permite descargarlo automáticamente.

Los certificados tampoco deben versionarse.

El repositorio debe conservar únicamente:

- scripts;
- configuración;
- documentación;
- hashes/versiones necesarias para reconstruir el entorno.

La PC del usuario debe poder reconstruir esos archivos localmente.

---

# FASE 9 — ENTORNO PYTHON

NO versionar:

- `.venv`
- `venv`
- `site-packages`
- caches.

El repositorio debe contener los archivos necesarios para reconstruir el entorno, por ejemplo:

- `pyproject.toml`
- `requirements.txt`
- `poetry.lock`
- `uv.lock`

según la arquitectura existente.

NO crear innecesariamente otro sistema de dependencias.

---

# FASE 10 — NO BORRAR A CIEGAS

Antes de ejecutar cualquier eliminación:

1. identificar el archivo;
2. explicar por qué no debe versionarse;
3. comprobar que existe una forma de reconstruirlo;
4. comprobar que no es código fuente;
5. comprobar que no contiene información necesaria para ejecutar el proyecto.

Si existe duda:

NO eliminar.

Marcar como `REVISIÓN MANUAL`.

---

# FASE 11 — LIMPIEZA DEL ÍNDICE GIT

Si un archivo está:

TRACKED + IGNORED

debe corregirse.

Agregarlo a `.gitignore` NO es suficiente.

Debe retirarse del índice Git utilizando el procedimiento apropiado.

IMPORTANTE:

Eliminar del índice NO significa necesariamente eliminar el archivo de la PC del usuario.

Distinguir:

- eliminar del repositorio;
- eliminar del índice;
- eliminar físicamente.

No eliminar físicamente archivos necesarios para el entorno local salvo que sea seguro hacerlo.

---

# FASE 12 — HISTORIAL GIT

Determinar si existen archivos sensibles o pesados que hayan sido versionados previamente.

Especialmente:

- `.env`
- secretos;
- certificados;
- `mkcert.exe`;
- `.venv`;
- archivos >100 MB.

Si existen en el historial:

NO reescribir automáticamente el historial.

Primero documentar:

- archivo;
- tamaño;
- motivo;
- riesgo;
- si requiere `git filter-repo`, BFG u otra herramienta;
- si requiere rotación de secretos.

Si existe un secreto histórico, marcar:

`ACCIÓN DE SEGURIDAD REQUERIDA`

---

# FASE 13 — VALIDACIÓN FINAL

Después de la limpieza comprobar:

```text
git status
git ls-files
git check-ignore

y realizar una nueva auditoría.

Verificar específicamente que NO estén trackeados:

.env

.venv/

__pycache__/

certs/

mkcert.exe

secretos

caches

archivos temporales.


También verificar que SÍ estén trackeados:

código fuente;

documentación;

scripts;

configuración necesaria;

.env.example;

pyproject.toml y/o archivo de dependencias correspondiente;

.gitignore.



---

FASE 14 — PRUEBA DE REPRODUCIBILIDAD

Después de limpiar:

Determinar si una PC nueva podría reconstruir el entorno utilizando únicamente:

1. repositorio;


2. documentación;


3. scripts;


4. dependencias declaradas;


5. conexión a Internet cuando sea necesaria para descargar dependencias.



No es necesario crear una máquina virtual.

Pero debes verificar que no exista una dependencia accidental de archivos locales que ya no estarán en Git.


---

FASE 15 — NO MODIFICAR FUNCIONALIDAD

Esta iteración NO debe:

modificar APIs;

modificar OAuth;

modificar selección;

modificar STEP;

modificar tessellación;

modificar FEA;

modificar TopOpt;

modificar el visor;

cambiar arquitectura;

agregar funcionalidades nuevas.


Solo se permite modificar scripts/configuración/documentación cuando sea necesario para:

limpieza;

reproducibilidad;

seguridad;

instalación;

control de dependencias.



---

FASE 16 — DOCUMENTACIÓN

Actualizar RESUMEN_IMPLEMENTACION.md.

Registrar:

Auditoría

Estado inicial del repositorio.

Archivos eliminados del índice

Lista y motivo.

Archivos ignorados

Lista y motivo.

Archivos pesados

Indicar:

nombre;

tamaño;

decisión;

motivo.


Secretos

Indicar únicamente:

NINGUNO DETECTADO


o:

SECRET DETECTADO — REQUIERE ROTACIÓN


Nunca escribir el secreto.

Historial

Indicar si se encontraron archivos sensibles/pesados en commits anteriores.

Git LFS

Indicar si se recomienda o no y por qué.

Estado final

Clasificar:

COMPLETADO

PARCIAL

PENDIENTE

BLOQUEADO



---

FASE 17 — INFORME FINAL

Antes de terminar debes entregar un informe estructurado:

Estado del repositorio

🟢 LIMPIO 🟡 REQUIERE ACCIÓN MANUAL 🔴 PROBLEMAS CRÍTICOS

Archivos eliminados del índice

...


Archivos ignorados

...


Archivos pesados encontrados

...


Secretos

...


Problemas históricos

...


Git LFS

...


Archivos que requieren revisión manual

...


Pruebas realizadas

...


Estado final

...



---

REGLAS ABSOLUTAS

1. NO borrar código fuente.


2. NO borrar archivos necesarios sin verificar.


3. NO modificar funcionalidades.


4. NO ocultar archivos mediante .gitignore indiscriminadamente.


5. NO asumir que .gitignore elimina archivos trackeados.


6. NO publicar secretos.


7. NO copiar secretos al informe.


8. NO subir certificados.


9. NO subir .venv.


10. NO subir caches.


11. NO subir binarios innecesarios.


12. NO usar Git LFS sin justificarlo.


13. NO reescribir historial automáticamente.


14. NO alterar la arquitectura.


15. NO avanzar al Hito 2.



La prioridad absoluta es:

SEGURIDAD ↓ INTEGRIDAD DEL CÓDIGO ↓ REPRODUCIBILIDAD ↓ LIMPIEZA ↓ REDUCCIÓN DE PESO

### Una cosa especialmente importante

Como me decís que **en tu PC Git está omitiendo archivos por peso u otras razones**, quiero que la IA no se limite a mirar GitHub. El punto crítico es que haga la distinción:

> **“GitHub no muestra el archivo” ≠ “Git lo está ignorando” ≠ “el archivo no existe localmente”.**

Por eso incluí explícitamente `git status`, `git ls-files` y `git check-ignore`.

También le prohibí hacer un `git add .` indiscriminado después de limpiar. Primero tiene que **auditar qué va a entrar al índice**.

Y, sobre todo, **no le permití borrar automáticamente archivos pesados**. Primero tiene que clasificarlos. Si resulta que, por ejemplo, tenés un modelo STEP de 150 MB que necesitamos conservar, no quiero que la IA lo elimine simplemente porque GitHub no lo acepta.

Cuando termine esta limpieza, el siguiente paso que haría yo es revisar **el estado de GitHub + el estado de tu copia local**, y recién ahí definir qué archivos pesados realmente necesitamos y si alguno merece Git LFS.