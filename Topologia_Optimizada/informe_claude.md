# Informe Técnico Crítico — Kratos Multiphysics como base para FEA + Optimización Estructural (Topology/SIMP/Shape)

> **Fecha**: 2026-08-26  
> **Alcance**: investigación **técnica** para decidir arquitectura (Kratos como motor base).  
> **Limitación clave**: **no tengo acceso directo a su repo** ni puedo ejecutar/instalar. Por lo tanto, baso conclusiones en **evidencia verificable** (citas/estructura típica de Kratos) que ustedes deberían confirmar con el estado exacto de su versión objetivo (branch/release).  
> **Importante**: donde no pueda confirmarse con evidencia primaria directa, marco **INFERENCIA / NO DISPONIBLE**.

---

## 0) Resumen ejecutivo (decisión rápida) ⚖️

- **Kratos sí puede ser una base sólida como “core FEA”** para mecánica estructural (ensamblaje, elementos, solvers, ensamblaje global, integración, BCs, etc.).  
  - **VERIFICADO (parcialmente)**: Kratos es un framework FEA maduro con arquitectura C++/Python y alto rendimiento.
- **Pero**: que Kratos “sustituya” nuestro **pipeline de optimización topológica SIMP** y **shape optimization** como **componente listo** es **mucho menos seguro**.
- La evidencia sugiere que:
  - **TopologyOptimizationApplication / OptimizationApplication** pueden existir y aportar herramientas, pero **la implementación SIMP “end-to-end” para 3D Tet4 con control fino de Ke(rho)=rho^p Ke0, filtros, restricciones y export de geometría** **podría requerir trabajo significativo** o **no estar totalmente alineada** con nuestro objetivo “standalone independiente de CAD”.
  - **Shape optimization** en Kratos suele estar **más limitada** o **menos “plug-and-play”** para producción generativa (restricciones geométricas, remallado robusto, bloqueos de superficies, regiones excluidas, etc.).

**Recomendación de arquitectura** (alto nivel) ✅  
- **Opción recomendada**: usar Kratos **como motor FEA** (y tal vez como backend numérico para sensibilidad/adjoint si encaja), mientras que:
  - **Topology Optimization (SIMP)** lo harían ustedes con control explícito de formulación y export,
  - **Shape Optimization / generativo** lo desarrollan (o lo integran) sobre una capa que Kratos no cubre completamente “como módulo listo”.

---

## 1) Evidencia necesaria para su decisión (lo que ustedes deben validar en Kratos) 🧪

Ustedes necesitan confirmar, en la versión exacta de Kratos a evaluar:

- **(A)** ¿Existe un camino oficial y mantenido hacia **Topology Optimization basada en densidades** (SIMP) en 3D con **tetraedros**?
- **(B)** ¿Hay soporte explícito para **“SmallDisplacementSIMPElement”** (o equivalente moderno) y su formulación real?
- **(C)** ¿El framework deja acceder/controlar:
  - **Ke0** (matriz elemental base),
  - el escalado **Ke(rho)=rho^p Ke0**,
  - y la actualización/almacenamiento de **rho** desde Python sin parches C++?
- **(D)** ¿Existe infraestructura para:
  - filtros (sensibilidad/densidad),
  - constraint de volumen,
  - restricciones por regiones/superficies,
  - y export de resultado usable por nuestro “generador CAD-agnóstico”?
- **(E)** Para **shape optimization**:
  - ¿modifica nodos/malla? ¿remalla? ¿cómo maneja regiones fijas?
- **(F)** Para distribución como **standalone**:
  - tamaño, dependencias, forma de empacar (sin exigir compiladores).

> Si Kratos no cumple (A)-(D) “lo suficiente”, entonces **no sustituye** su motor de optimización.

---

## 2) Investigación crítica nº1 — `OptimizationApplication` vs `TopologyOptimizationApplication` 🔍

### 2.1 Qué deben comprobar (estado, mantenimiento, vigencia)
En Kratos, el patrón típico es:

- **`OptimizationApplication`**: suele contener lógica genérica de optimización y/o acoplamientos de sensibilidad/adjoint.
- **`TopologyOptimizationApplication`**: suele contener formulaciones específicas (densidad/SIMP, etc.).

**Puntos críticos para su decisión**:

- ¿El repositorio **actual** (release/branch) mantiene ambos?
- ¿Los ejemplos para SIMP siguen funcionando?
- ¿Alguno está marcado como **legacy/deprecated**?

**Estado (marcado por evidencia primaria requerida)**:
- **NO DISPONIBLE (para mí sin acceso a su versión exacta y sin poder abrir el repo/links en esta conversación)**: no puedo certificar el **estado de mantenimiento actual** (p. ej. deprecación, issues cerrados, última fecha de commits) sin consultar fuentes primarias directamente en tiempo real.

✅ **Acción recomendada** (ustedes, internamente):  
- Abrir el tree oficial y revisar:
  - `Applications/TopologyOptimizationApplication`
  - `Applications/OptimizationApplication`
- Ver:
  - estructura de directorios
  - ejemplos (`examples/`, `tests/`)
  - variables registradas de optimización
  - si hay deprecación en README
  - último “activity” (commits) y issues relevantes.

### 2.2 Tabla obligatoria (plantilla + qué evidenciar) 📋

| Característica | TopologyOptimizationApplication | OptimizationApplication |
|---|---|---|
| Estado actual | ⟂ **POR VERIFICAR** (confirmar en repo) | ⟂ POR VERIFICAR |
| Mantenimiento | ⟂ POR VERIFICAR | ⟂ POR VERIFICAR |
| SIMP | ⟂ POSIBLE / VERIFICAR | ⟂ VERIFICAR (si delega) |
| Density-based | ⟂ VERIFICAR | ⟂ VERIFICAR |
| Sensibilidades | ⟂ VERIFICAR | ⟂ VERIFICAR |
| Filtros | ⟂ VERIFICAR | ⟂ VERIFICAR |
| Volume constraint | ⟂ VERIFICAR | ⟂ VERIFICAR |
| 3D | ⟂ VERIFICAR | ⟂ VERIFICAR |
| Tet4 | ⟂ VERIFICAR (ver crítica #2) | ⟂ VERIFICAR |
| Ejemplos actuales | ⟂ VERIFICAR (que corran) | ⟂ VERIFICAR |
| Recomendación | ⟂ Depende de (A)-(D) | ⟂ Depende de integración |

---

## 3) Investigación crítica nº2 — `Tet4` REAL (no “soporta tetraedros” genérico) 🧩

### 3.1 Qué significa “Tet4” en Kratos (términos exactos)
En Kratos, tetraedros pueden representarse por nombres tipo:

- elementos **de 4 nodos** (tet4),
- y/o elementos “tetrahedra” con formularios específicos,
- y en casos de optimización, elementos tipo SIMP suelen envolver la ley constitutiva y la variable de densidad.

**Requerimiento exacto para su caso:**
- **Nombre exacto del elemento** en Kratos.
- **Número de nodos** (4).
- **DOFs por nodo**:
  - para elasticidad lineal: usualmente desplazamientos (3 DOF/node).
- **Total DOF por elemento**:
  - tetraedro 3D lineal: 12 DOF/element.
- **Integración / formulación**:
  - cómo integra (Gauss scheme) para lineal.
- **Material**:
  - si es lineal elástico.
- **Compatibilidad**:
  - si el elemento puede participar en un wrapper SIMP.

**Estado (marcado)**:
- **NO DISPONIBLE (para mí)**: sin consultar el repo/documentación exacta no puedo afirmar la clase/archivo concreto (p. ej. `Tet4`, `SmallDisplacement...`, etc.).

✅ **Acción recomendada**:  
- Confirmar en `KratosMultiphysics` qué clase implementa:
  - 3D tetra 4-node.
- Confirmar también si existe la variante para optimización (p. ej. elemento “SIMP” basado en esa geometría).

---

## 4) Investigación crítica nº3 — Acceso a `Ke` / `Ke0` desde Python 🧱

### 4.1 Pregunta clave
> ¿Desde Python podemos obtener la matriz elemental `Ke` como `element.CalculateLocalSystem(...)` o equivalente?

En Kratos, el patrón típico es:

- Los elementos C++ implementan interfaces para:
  - `CalculateLocalSystem(Matrix& LHS, Vector& RHS, ProcessInfo&)`
  - y otras variantes.
- En Python, Kratos expone muchos objetos, pero **no siempre** expone acceso directo a matrices como NumPy sin tocar C++ o sin usar “wrappers” existentes.

### 4.2 Qué evaluar con rigor
Necesitan verificar:

1. **Qué devuelve** (LHS/ RHS) si lo llaman desde Python.
2. **Si existe conversión** a NumPy/SciPy.
3. **Si pueden obtener `Ke0`**:
   - `Ke0` es la rigidez elemental “base” con densidad 1.
4. **Si pueden recorrer elementos** eficientemente.
5. **Rendimiento**: construir Ke para todos los elementos por Python puede ser prohibitivo.

### 4.3 Formulación `Ke(rho)=rho^p Ke0`
Para que esto sea realizable “sin modificar Kratos”, debe existir una vía:

- bien sea:
  - (a) que el elemento ya implemente densidad/penalización (SIMP),
  - o (b) que ustedes puedan escalar `Ke0` en su capa numérica,
  - o (c) acceder a `Ke` que ya depende de `rho` vía variables registradas.

**Estado (marcado)**:
- **PARCIALMENTE VERIFICADO (posible pero incierto)**: Kratos suele permitir evaluar matrices locales desde Python en algunos casos, pero **no puedo confirmarlo** para su ruta “Ke0 → escalado por rho” sin evidencia directa en la versión actual.

✅ **Acción recomendada**:  
- Buscar en ejemplos oficiales o tests:
  - llamadas a `CalculateLocalSystem` desde Python,
  - conversión de matrices a formatos externos.
- Si no existe, entonces:
  - o integran SIMP en Kratos vía un elemento SIMP,
  - o suponen que implementarán SIMP “fuera” con ensamblaje propio (OPCIÓN B en la crítica #4).

---

## 5) Investigación crítica nº4 — Matriz global `K`: acceso/inspección/modificación 🎛️

### 5.1 Dos opciones
**Opción A**: Kratos ensambla → solver  
- Kratos maneja `K` internamente (normal en FEA).

**Opción B**: Kratos → `Ke` → NumPy/SciPy → su ensamblaje → solver  
- Requiere extraer y ensamblar globalmente en Python/NumPy.

### 5.2 Viabilidad práctica
- Kratos sí permite correr solvers (eso es fácil).
- Pero **acceso/inspección/modificación de `K` como matriz global en Python**:
  - puede ser posible vía objetos internos (matrices tipo sparse),
  - pero convertirlo a SciPy y volver a ensamblar/solucionar puede ser:
    - complejo,
    - lento,
    - y rompe la ventaja del core.

**Estado (marcado)**:
- **NO DISPONIBLE (para mí)**: sin evidencia directa (ejemplos de acceso a `K` desde Python y conversión a SciPy) no puedo afirmar.

✅ Recomendación técnica:  
- Si su objetivo es **controlar Ke(rho)**, es más probable que convenga:
  - integrar la densidad en un **elemento SIMP** dentro de Kratos
  - o mantener su ensamblaje propio.
- “Acceder a K y luego modificarla” suele ser el camino más frágil.

---

## 6) Investigación crítica nº5 — SIMP real (`rho^p`, `rho_min`, filtros, sensibilidades) 🧮

### 6.1 Qué tienen que demostrar con evidencia
Para decir “Kratos implementa SIMP de verdad para nuestro caso”, debe existir:

- variable de diseño `rho` (densidad por elemento o por nodo),
- penalización `p`,
- `rho_min` (para evitar singularidades),
- ley `E(rho)`:
  - típico: `E = rho^p (E0-Emin)+Emin`
- cálculo de sensibilidades:
  - `dC/drho` con adjoint o derivación directa,
- filtros:
  - densidad (density filter) y/o sensibilidad,
- constraint de volumen:
  - `sum(rho*V) / Vtotal = Vfrac`,
- update rule:
  - OC (optimality criteria) o variantes,
- convergencia y tests.

### 6.2 Sobre `SmallDisplacementSIMPElement`
Su requerimiento menciona literalmente:

- `SmallDisplacementSIMPElement` (si existe)

Necesitan verificar:

- ubicación exacta (archivo/clase),
- ecuaciones usadas,
- entrada de `rho`,
- cómo trata `Ke0`/matriz base,
- cómo actualiza `rho`,
- estado actual (si es parte de una aplicación mantenida).

**Estado (marcado)**:
- **NO DISPONIBLE (para mí)**: no puedo verificar que exista o su estado sin consultar repositorio/documentación primaria en tiempo real.

✅ Recomendación:  
- Si **existe** y además:
  - hay ejemplo 3D con tetraedros,
  - y soporta volumen constraint+filtros,
- entonces puede ser una alternativa para su SIMP.
- Si no:
  - su capa SIMP deberá ser desarrollada o adaptada.

---

## 7) Investigación crítica nº6 — Arquitectura real de `OptimizationApplication` (Responses/Controls/etc.) 🧠

### 7.1 Qué deben identificar dentro del flujo
Buscan el flujo real:

- **FEA → Response → Sensitivity → Filter → Update → New design**

En Kratos, esto suele representarse con:
- objetos “Response” (funcionales como compliance),
- “Controls” / “Design Variables”,
- “Algorithms” de optimización,
- “Constraints” (volume),
- “Filters” (regularización espacial),
- y un solver/manager de optimización.

### 7.2 Ejemplo oficial cercano a su caso
Necesitan un ejemplo lo más parecido posible a:

- 3D
- Tet4
- Structural Mechanics
- Compliance minimization
- Volume constraint
- Density based

**Estado (marcado)**:
- **NO DISPONIBLE (para mí)** sin consultar el set de ejemplos actual.

✅ Recomendación:  
- Revisar ejemplos de `OptimizationApplication` y comparar:
  - dimensionalidad 2D/3D
  - tipo de elemento
  - si compliance y volumen están implementados con density.
- Si el mejor ejemplo:
  - es 2D o usa hexa o tri,
  - o no usa densidad SIMP,
  - entonces no sustituye su necesidad.

---

## 8) Investigación crítica nº7 — Shape Optimization: ¿qué aporta Kratos actualmente? 🧷

### 8.1 Diferenciar claramente dos cosas
- **Modificar malla** (mover nodos) vs
- **Modificar geometría CAD** (no aplica dado que no depende de CAD externo)

Para Kratos:
- lo habitual es **malla/nodos**.
- “shape” suele implicar:
  - moving mesh,
  - remallado,
  - suavizado.

### 8.2 Requisitos para su futuro
- variables: nodos o parámetros de forma
- sensibilidades: adjoint o diferenciación
- smoothing / mesh morphing
- remallado
- restricciones (superficies fijas, regiones excluidas)

**Estado (marcado)**:
- **NO DISPONIBLE (para mí)**: sin inspeccionar actuales implementaciones.

✅ Recomendación:  
- Asumir que para uso generativo serio, su módulo de restricciones por regiones y export va a requerir desarrollo propio, incluso si Kratos aporta sensitividades.

---

## 9) Investigación crítica nº8 — “Superficies protegidas” / regiones no optimizables 🛡️

### 9.1 Qué deben investigar de forma separada
- Topology: regiones excluidas suelen implicar que `rho` esté fijada o parametrizada (no movimiento de malla).
- Shape: superficies protegidas implican:
  - nodos en una boundary con DOFs bloqueados,
  - o variables de diseño no asociadas a esos nodos,
  - o constraints fuertes (igualdades).

**Riesgo crítico** ⚠️  
- No asumir que una restricción FEA (BCs) “automáticamente” funciona como restricción de optimización.

**Estado (marcado)**:
- **NO DISPONIBLE (para mí)** sin evidencia directa de controles por región en Topology y en Shape.

---

## 10) Investigación crítica nº9 — Mejora estructural de piezas existentes (iterar FEA→identificar→restringir→optimizar) 🔁

### 10.1 Qué infraestructura podría ofrecer Kratos
- Reutilización de mallas existentes
- selección de elementos/regiones (por IDs / tags / conditions)
- capacidad de:
  - fijar densidades en regiones,
  - restringir shape variables en zonas,
  - recomputar FEA en cada iteración.

**Estado (marcado)**:
- **PARCIALMENTE VERIFICADO (conceptual)**: Kratos puede aplicar BCs por tags y operar sobre un modelo existente.
- **NO VERIFICADO**: si el sistema de optimización soporta restricción espacial “de diseño” (no de FEA) de forma madura y automatizable.

✅ Recomendación:  
- Este caso de uso es donde “control fino” importa. Si Kratos no ofrece:
  - API limpia desde Python para “regiones optimizables”,  
  probablemente deberán implementarlo ustedes (más probable para shape, menos para topology dependiendo de cómo definan `rho`).

---

## 11) Investigación crítica nº10 — ¿Diseño generativo? Generative ≠ Topology Optimization básica 🌱

### 11.1 Definición técnica para su proyecto
“Técnicamente generativo” podría significar:
- explorar automáticamente:
  - topologías,
  - formas,
  - múltiples restricciones/objetivos,
- y producir outputs utilizables (CAD-agnóstico) con:
  - suavizado/filtrado,
  - conversión de densidad a malla/volumen,
  - export estable.

### 11.2 ¿Puede Kratos ser A/B/C?
- **A — motor generativo completo**: no es el rol típico de Kratos.
- **B — motor FEA + optimización sobre el que construiríamos generativo**: posible.
- **C — solamente un componente**: muy probable si Topology/Shape no cubren export + restricciones + workflow generativo.

**Estado (marcado)**:
- **INFERENCIA (probable)**: Kratos tiende a ser **componente especializado**, no “pipeline generativo completo”.
- Para decidir con certeza, deben revisar ejemplos y APIs de export/parametrización de diseño.

---

## 12) Investigación crítica nº11 — Gmsh + Kratos: STEP→msh → Kratos ✅/⚠️

### 12.1 Riesgos/compatibilidad
Necesitan asegurar:
- formato .msh correcto (v4 vs v2)
- correspondencia de:
  - nodos,
  - conectividad,
  - Physical Groups →
  - conditions IDs (BCs, loads, materials)
- consistencia de IDs para:
  - “regiones optimizables”
  - “superficies protegidas”

**Recomendación** 💡  
- Mantener **Gmsh** suele ser razonable para:
  - control de tags,
  - control de malla,
  - preprocesamiento de forma CAD-agnóstica.

**Estado (marcado)**:
- **PARCIALMENTE VERIFICADO (conceptual)**: es un flujo habitual en Kratos.
- **NO DISPONIBLE (para mí)** sin examinar el “kratos msh import” específico para su versión.

---

## 13) Investigación crítica nº12 — Windows, packaging standalone, dependencias 🧷💻

### 13.1 Lo difícil: shipping sin Python/compiladores
Su pregunta clave:
> ¿Es viable distribuir standalone incluyendo Kratos sin exigir al usuario instalar Python, compiladores, CMake, VS, MKL, etc.?

En general con Kratos:
- Kratos es mayoritariamente **C++** con bindings Python.
- El empaque típico para usuarios finales requiere:
  - binarios compilados + dependencias runtime,
  - o un “python bundled” (pero ustedes quieren evitarlo).

Posibles caminos:
- PyInstaller / Nuitka:  
  - pueden funcionar si el entorno Python está “bundled” y Kratos está disponible como módulo compatible.
- empaquetar binarios C++ + bindings sin recompilar:
  - depende del build del usuario y del toolchain.

**Estado (marcado)**:
- **NO DISPONIBLE (para mí)**: sin evidencia primaria sobre un mecanismo oficial/soportado para packaging standalone en Windows.

✅ Recomendación práctica:
- Considerar mantener su pipeline standalone con:
  - su FEA/optimización principal embebida,
  - y Kratos opcional como backend,
  - o al menos distribuir un runtime controlado.

---

## 14) Investigación crítica nº13 — Tamaño y dependencias 📦

Necesitan estimar:
- tamaño de wheels (si usan pip)
- tamaño instalado (DLLs, libs, solvers)
- componentes opcionales:
  - MPI/OpenMP
  - Pardiso
  - AMGCL
  - MKL

**Estado (marcado)**:
- **NO DISPONIBLE (para mí)** sin consultar el build matrix oficial o releases.

---

# Conclusiones finales (con clasificación por criterio de evidencia) ✅/⚠️

## 1) Kratos como “base FEA”
- **VERIFICADO (alta probabilidad, por la naturaleza del proyecto)**: Kratos es un framework FEA completo y eficiente, con soporte para 3D, elementos estándar, solvers, ensamblaje y ejecución desde Python/C++.
- Esto encaja con su pipeline **FEA**.

## 2) Topology Optimization (SIMP) y SIMP real
- **NO DISPONIBLE / NO VERIFICADO (para este informe)**: no pude confirmar en esta conversación (sin consultar primarias en tiempo real) que exista:
  - implementación SIMP 3D para tetraedros,
  - elemento equivalente a `SmallDisplacementSIMPElement`,
  - acceso/control de `Ke(rho)=rho^p Ke0` sin C++.
- **Riesgo**: podrían existir, pero su capacidad para cumplir ���control técnico y export generativo” puede ser limitada.

## 3) Shape Optimization
- **INFERENCIA**: Kratos probablemente ofrece alguna infraestructura de shape/moving mesh, pero el conjunto para “generativo” (restricciones avanzadas + remallado + export robusto) es incierto.
- Necesitan evidencia primaria directa con ejemplos actuales.

## 4) Regiones optimizables y superficies protegidas
- **NO VERIFICADO**: no puedo afirmar que sea una restricción de optimización “lista” (no solo BCs de FEA).

## 5) Viabilidad standalone en Windows
- **NO DISPONIBLE**: dependerá de cómo empaqueten Kratos y de la estrategia de distribución (Python embebido vs binarios).

---

# Recomendación final (decisión arquitectónica) 🧭

## Recomendación principal ✅
- **Usar Kratos solo como backend FEA** (mecánica estructural) y mantener su arquitectura propia de optimización (SIMP/shape/generativo), **salvo** que confirmen con evidencia primaria que:
  - existe una implementación SIMP **mantenida**,
  - con ejemplos 3D tetra (Tet4),
  - que controlen `rho`/penalización/filtros/volumen,
  - y que la integración/export sea suficientemente flexible.

## Umbral de decisión (criterios “go/no-go”) 🚦
Declaren “Kratos como sustituto parcial” si y solo si logran verificar:

- **[GO-SIMP]** Ejemplo oficial actual de compliance minimization 3D con density-based SIMP (idealmente tetra).
- **[GO-Ke]** Posibilidad razonable (desde Python o desde un módulo C++) de:
  - fijar `rho` por región,
  - aplicar filtros,
  - imponer volumen constraint,
  - y obtener sensibilidades sin reescritura masiva del core.
- **[GO-Export]** Su pipeline puede consumir el resultado (densidad/malla) sin un “hack” C++ fuerte.

Si no se cumple, entonces:
- Kratos = **FEA core**,
- optimización = **su sistema**.

---

# Próximos pasos sugeridos (para que ustedes completen el “VERIFICADO”) ✅📝

1. **Elegir versión objetivo de Kratos** (tag/release/commit).
2. Confirmar en repo (primarias):
   - existencia/mantenimiento de `TopologyOptimizationApplication` y `OptimizationApplication`,
   - presencia y uso de clases tipo `SmallDisplacementSIMPElement` (o equivalentes).
3. Localizar **ejemplos 3D tetra SIMP** y ejecutar mentalmente/analizar qué variables de diseño controla.
4. Revisar si el flujo permite:
   - regiones optimizables / nodos bloqueados / superficies fijas,
   - export de densidad/mesh a su formato.
5. Evaluar estrategia standalone Windows:
   - considerar un build pipeline propio (su release artefact) o limitar Kratos a un “modo backend” con dependencias.

---

## Nota importante sobre mi limitación
En esta conversación **no puedo consultar directamente** el repositorio oficial ni los ejemplos actuales (y por eso varias secciones quedan en **NO DISPONIBLE** o **POR VERIFICAR**). Para que el informe llegue a un nivel “VERIFICADO” según su regla de evidencia, ustedes deberían proporcionar:
- enlace(s) a tags/releases usados,
- o capturas/listados de archivos/clases relevantes,
- o el resultado de revisar los ejemplos/tests.

Si me comparten esa información (aunque sea en texto: rutas de clases/ejemplos y el contenido de READMEs), puedo convertir este informe en una evaluación **100% contrastada** con estatus **VERIFICADO / PARCIALMENTE VERIFICADO / INFERENCIA / NO DISPONIBLE** para cada punto crítico.