# Kratos Multiphysics como base para una app standalone de Topology Optimization
### Investigación técnica basada en fuentes oficiales — Agosto 2026

---

## 1. Resumen ejecutivo

Kratos Multiphysics (BSD‑4‑Clause, C++ con interfaz Python) es un framework FEA maduro, distribuible por `pip` con wheels precompilados para Windows, que **sí** ofrece los tres bloques que la arquitectura necesita: elementos sólidos 3D (incluido Tet4), acceso a `Ke`/`K`/`u`/resultados desde Python, y una aplicación de optimización (`OptimizationApplication`) con sensibilidades adjoint y filtrado density-based orientada a TopOpt/ShapeOpt. Sin embargo, no es una "caja negra de topología optimizada": es un **motor FEA + optimización genérico** sobre el cual hay que construir la lógica SIMP concreta del proyecto (penalización `rho^p`, densidad mínima, filtro, bucle de actualización) usando piezas que Kratos expone, no una función `TopologyOptimize()` lista para producción.

Existen **dos rutas** dentro de Kratos para SIMP:
- **`TopologyOptimizationApplication`**: aplicación histórica (TUM, ~2016), reactivada dentro del repo principal, con un elemento `SmallDisplacementSIMPElement` ya implementado (`Ke(ρ)=ρᵖKe0`). Evidencia de que su reactivación tuvo fricciones técnicas no triviales (issue #8328).
- **`OptimizationApplication`**: la aplicación activa, "Production/Stable", con sensibilidades adjoint, filtrado y soporte multi-física, pero de propósito más general (shape/thickness/topology) y con una API menos "out of the box" para SIMP puro que la legacy.

Ninguna de las dos resuelve out-of-the-box: (a) importación CAD/STEP independiente (eso siempre corre por fuera, vía Gmsh), (b) una superficie "protegida" de usuario con reglas de fabricación, ni (c) exportación a geometría CAD válida tras la optimización. Esas tres piezas son desarrollo propio en cualquiera de los escenarios (con o sin Kratos).

**Recomendación adelantada** (justificada en la sección 26): **arquitectura híbrida** — mantener STEP→Gmsh bajo control propio, pero reemplazar el solver FEA propio con SciPy por Kratos (Core + StructuralMechanicsApplication + LinearSolversApplication), y construir el bucle SIMP propio en Python usando las primitivas de bajo nivel de Kratos (`CalculateLocalSystem`, `CalculateOnIntegrationPoints`, `ProcessInfo`) en lugar de depender enteramente de `OptimizationApplication` o de la legacy `TopologyOptimizationApplication`.

---

## 2. Contexto y requisitos del proyecto

Pipeline objetivo: `STEP → Gmsh → Tet4 → Solver FEA → SIMP`, dentro de una app de escritorio **standalone, sin dependencia de ningún CAD**. La pregunta no es "qué hace Kratos" sino si puede sustituir o complementar el solver FEA propio sin comprometer la independencia de CAD ni la distribuibilidad en Windows.

---

## 3. Qué es Kratos

Repositorio oficial: `github.com/KratosMultiphysics/Kratos`. <cite index="3-1">Kratos provee un núcleo que define el marco de trabajo común y varias aplicaciones que funcionan como plug-ins extensibles en diversos campos, incluyendo mecánica estructural, dinámica de fluidos, interacción fluido-estructura, DEM y contacto</cite>. Es <cite index="4-1">un framework escrito en C++ con una extensa interfaz Python, libre bajo licencia BSD-4 y utilizable incluso en software comercial; multiplataforma (Windows, Linux, macOS) y paralelo mediante OpenMP y MPI, escalable a miles de núcleos</cite>. **VERIFICADO.**

---

## 4. FEA estructural 3D

`StructuralMechanicsApplication` <cite index="61-1">contiene una serie de elementos estructurales, así como elementos sólidos, las estrategias, solvers y la Constitutive Laws Application correspondientes dentro de Kratos Multiphysics</cite>. Los elementos sólidos publicados en PyPI incluyen <cite index="70-1">elementos de pequeño desplazamiento (Small displacement elements) y elementos Lagrangianos totales (Total Lagrangian elements)</cite>, cubriendo pequeñas y grandes deformaciones. **VERIFICADO.**

## 5. Tet4

- **Elemento**: `SmallDisplacementElement3D4N` (nomenclatura estándar Kratos `<Formulación><Dim>N`: 4 nodos → tetraedro lineal). Confirmado indirectamente por la convención de nombres de Kratos y por el uso de tetraedros Tet4 en los ejemplos oficiales de conversión de malla (`Tetrahedra3D4` en archivos `.mdpa` generados desde Gmsh). **VERIFICADO** en cuanto a existencia del tipo geométrico Tetrahedra3D4 en el formato nativo; **PARCIALMENTE VERIFICADO** en cuanto al nombre exacto de clase C++ del elemento estructural asociado (no se accedió al código fuente línea por línea del `.cpp`, sino a evidencia indirecta vía wiki/PyPI).
- **DOFs**: 3 por nodo (`DISPLACEMENT_X/Y/Z`) → 12 DOFs por elemento Tet4 lineal.
- **Formulación**: pequeñas deformaciones, teoría infinitesimal, con leyes constitutivas intercambiables (elástico lineal, plasticidad, daño).
- **Fuente**: `applications/StructuralMechanicsApplication/README.md`, wiki `[KratosStructuralMechanicsAPI] Constitutive laws in Structural Mechanics Application`.

No se debe asumir que "Kratos soporta tetraedros" equivale automáticamente a "el Tet4 concreto del proyecto (con su formulación exacta)"; la formulación de pequeño desplazamiento estándar de `SmallDisplacement` coincide conceptualmente con un Tet4 clásico de elasticidad lineal, pero cualquier término particular (integración reducida, hourglass control, etc.) debería verificarse en el `.cpp` si el proyecto lo requiere con precisión numérica exacta.

---

## 6. Matrices y control del solver desde Python

Este es el punto más crítico para decidir si Kratos permite implementar SIMP propio, y la evidencia es clara y directa:

- `Element.CalculateLocalSystem(LHS, RHS, ProcessInfo)` — <cite index="31-1">método expuesto en Python que calcula la matriz del lado izquierdo (Ke) y el vector del lado derecho de un elemento</cite>. **VERIFICADO.**
- `Element.CalculateOnIntegrationPoints(...)` — permite leer variables (tensión, energía de deformación, etc.) en los puntos de Gauss desde Python. **VERIFICADO.**
- `Element.CalculateSensitivityMatrix(...)` — expuesto para cálculo de sensibilidades. **VERIFICADO** (aparece en la wiki de la clase `Element`, truncado en los resultados pero presente).
- Acceso a DOFs: `node.pGetDof(VARIABLE)`, `GetDofList` en la definición del elemento (nivel C++, pero reflejado en Python a través de `ModelPart`). **VERIFICADO.**
- Acceso a resultados nodales: `node.GetSolutionStepValue(DISPLACEMENT)` — <cite index="95-1">la interfaz Python provee acceso completo a la base de datos nodal; GetSolutionStepValue y SetSolutionStepValue permiten leer y escribir cualquier variable registrada, incluyendo históricos de pasos anteriores</cite>. **VERIFICADO.**
- `block_for_each(model_part.Elements(), ...)` con `CalculateLocalSystem` dentro del lambda — patrón oficial documentado para recorrer todos los elementos y extraer sus matrices locales en paralelo (OpenMP) desde C++/Python. **VERIFICADO.**

**Respuesta a la pregunta crítica de la sección 7 del prompt**: sí, hay control suficiente. Es posible, elemento por elemento, invocar `CalculateLocalSystem` para obtener `Ke0` (con densidad de referencia), aplicar la penalización `ρ_e^p` en Python o en una `Properties` custom, y ensamblar `K` global uno mismo con SciPy si se prefiere no depender del `Builder&Solver` interno de Kratos — o bien dejar que el `Builder&Solver` de Kratos ensamble y resuelva, y limitarse a modificar la propiedad de densidad por elemento (`Properties[DENSITY]` o una variable custom) entre iteraciones. Ambas vías son técnicamente viables; la segunda es la más "kratos-idiomática" y la que usa el propio elemento `SmallDisplacementSIMPElement` (ver sección 11).

---

## 7. Solvers y rendimiento

`LinearSolversApplication` (wrapper de Eigen) ofrece <cite index="38-1">varios solvers directos dispersos, y en caso de tener instalado MKL, también permite usar los solvers Pardiso</cite>. <cite index="40-1">El core de Kratos incluye además un `AMGCLSolver`</cite> (multigrid algebraico, útil como precondicionador de CG/BiCGStab/GMRES) sin necesidad de MKL. Existe además un `LinearSolverFactory` para construir el solver desde un JSON de configuración sin tocar código. **VERIFICADO.**

Distribución en PyPI (wheels): <cite index="38-1">`KratosLinearSolversApplication-9.1.1-cp39-cp39-win_amd64.whl`</cite> confirma binarios Windows precompilados — no requiere compilar Eigen ni AMGCL manualmente. **VERIFICADO.**

Pardiso vía MKL requiere que el usuario final tenga MKL instalado y activado en la configuración de solver (`solver_type: "pardiso"`); AMGCL, en cambio, viene siempre disponible sin dependencias adicionales. Para una app standalone, **AMGCL es la opción sin fricción**; Pardiso/MKL añade una dependencia de terceros con licencia propia de Intel que complica la distribución "un solo instalador".

Comparación cuantitativa Kratos vs. SciPy+PyPardiso: **NO ENCONTRADO**. No existen benchmarks oficiales publicados por el equipo de Kratos que comparen directamente su stack de solvers contra SciPy Sparse o PyPardiso en el mismo hardware/malla. Cualquier cifra de rendimiento que se ofrezca sin medición propia sería inventada; se recomienda benchmarking propio con la malla real del proyecto antes de decidir.

---

## 8. Resultados FEA

Accesibles desde Python vía `GetSolutionStepValue` (nodales: desplazamientos, reacciones) y `CalculateOnIntegrationPoints` (en puntos de Gauss: `VON_MISES_STRESS`, `PK2_STRESS_TENSOR`, energía de deformación). El propio proceso de salida oficial de la `StructuralMechanicsApplication` declara explícitamente listas de <cite index="97-1">resultados nodales (desplazamiento, aceleración de volumen, normal, reacción) y resultados en puntos de Gauss (tensión de Von Mises, tensor de tensión PK2)</cite> en sus archivos de parámetros oficiales (`ProjectParameters.json` de ejemplo). Compliance no es una variable nativa con ese nombre exacto, pero se deriva trivialmente como `u·F` (energía de deformación / trabajo externo), ambos accesibles. **VERIFICADO.**

---

## 9. Sensibilidades

- La `StructuralMechanicsApplication` <cite index="50-1">provee el marco para calcular sensibilidades de respuestas estructurales (desplazamientos, energía de deformación o tensiones) respecto a distintos tipos de variables de diseño (coordenadas nodales, propiedades materiales o de sección, o intensidad de carga) mediante el enfoque adjoint</cite>. **VERIFICADO.**
- Existe una wiki dedicada `(Sensitivity analysis) Adjoint-API.md`, confirmando que hay una API pública documentada para esto, no solo código interno. **VERIFICADO.**
- En un estudio académico independiente que usa Kratos para FSI, se detalla que <cite index="49-1">en Kratos el análisis de sensibilidad de forma basado en adjoint para fluidos y estructuras se realiza mediante método analítico discreto y método discreto semi-analítico respectivamente</cite> — es decir, las derivadas parciales de forma se calculan analíticamente donde es posible y por diferencias finitas donde no. **VERIFICADO** (fuente secundaria con detalle técnico consistente con lo oficial).
- Existe evidencia de **fragilidad práctica**: un pull request oficial (#5682) documenta un bug real donde <cite index="98-1">la función que calcula tensión de Von Mises en puntos de integración a veces devuelve valores sin sentido cuando se llama a través de las funciones de gradiente dentro de la clase de respuesta adjunta de tensión agregada, aunque los valores son correctos cuando se llaman directamente desde un elemento primal</cite>. Esto es señal de que el pipeline adjoint para respuestas de tensión (no solo compliance/desplazamiento) tiene aristas y requiere validación cuidadosa antes de confiar en él para producción. **PARCIALMENTE VERIFICADO** (funciona para compliance/desplazamiento; el camino de tensiones agregadas ha tenido bugs documentados).

**Qué calcula Kratos directamente**: sensibilidad de compliance/desplazamiento respecto a densidad (vía `OptimizationApplication`, sección 10) y sensibilidad de forma vía adjoint en `StructuralMechanicsApplication`.
**Qué habría que implementar o validar**: cualquier función objetivo custom (p. ej. combinaciones multi-carga, restricciones de tensión local con agregación KS/p-norm) requiere extender o validar las respuestas existentes.

---

## 10. Topology Optimization — `OptimizationApplication`

Descripción oficial: <cite index="13-1">framework para resolver problemas de optimización en mecánica de medios continuos, capaz de manejar tanto métodos basados en gradiente (adjoint) como métodos libres de gradiente, con técnicas de última generación para optimización de forma, espesor y material/topología, técnicas de filtrado eficientes y consistentes para parametrización libre de forma/espesor/topología, una formulación abstracta del problema que permite problemas de optimización concurrentes y anidados multinivel/multiescala, una técnica adaptativa de proyección de gradiente para problemas con un número arbitrariamente grande de variables de diseño de distintas escalas, e implementación modular que permite análisis y optimización de problemas multi-física</cite>. Adicionalmente <cite index="20-1">soporta la realización de restricciones de manufactura aditiva, como condiciones de voladizo (estructuras de soporte), apilabilidad y limitaciones geométricas</cite>. Estado en PyPI: **Development Status 5 – Production/Stable**, con releases activos hasta julio 2025. **VERIFICADO.**

**¿Qué resuelve directamente?**
- Minimización de compliance sujeta a restricción de volumen: SÍ, es el caso de uso canónico density-based de la aplicación (consistente con la literatura general de SIMP, sección 12).
- Cálculo de sensibilidades (adjoint) del objetivo respecto a la densidad por elemento: SÍ.
- Filtrado de densidad/sensibilidad (para evitar checkerboarding): SÍ, mencionado explícitamente ("efficient and consistent filtering techniques").
- Restricciones geométricas de manufactura aditiva: SÍ (parcialmente, como "realization").

**¿Qué habría que desarrollar o adaptar?**
- La extracción de `rho_e` por elemento en cada iteración: técnicamente posible (es una variable de diseño interna a la que Python tiene acceso, dado que todo el framework opera sobre `ModelPart`/`Properties`/variables de Kratos), pero **no hay un ejemplo oficial mínimo, autocontenido y actualizado tipo "cantilever 3D con Tet4 exportando rho_e a un array numpy"** en la documentación pública indexada. **INFERENCIA** en cuanto a la facilidad real de extracción con el código actual — se recomienda validar con un ejemplo propio antes de comprometer arquitectura.
- Integración con `StructuralMechanicsApplication`: SÍ, es una integración de primera clase — `OptimizationApplication` está diseñada explícitamente para envolver un `AnalysisStage` de otra aplicación (típicamente Structural) como "solver primal". **VERIFICADO** conceptualmente por el diseño modular descrito; **PARCIALMENTE VERIFICADO** en el detalle de la API concreta, que no se pudo inspeccionar línea por línea.

**No es un botón "TopologyOptimize()"**: es un framework de optimización general (shape + thickness + topology) donde el usuario define en JSON/Python: el analysis primal, la(s) función(es) objetivo, restricciones, filtro, y el algoritmo de actualización (gradient projection). Construir el caso concreto "minimizar compliance sujeto a volumen, dominio Tet4 importado de STEP" requiere trabajo de integración no trivial, aunque de mucha menor magnitud que escribir SIMP desde cero.

---

## 11. SIMP

Existen **dos implementaciones de SIMP** dentro del ecosistema Kratos:

1. **`TopologyOptimizationApplication` (histórica/TUM)**. Un paper académico de la TU München describe que <cite index="12-1">esta aplicación de topology optimization de código abierto dentro del framework Kratos usa el enfoque density-based SIMP (Solid Isotropic Material with Penalization), con minimización de compliance como objetivo, y es una reimplementación de una versión previa no publicada que ya permitía optimizar geometrías arbitrarias con enlace a software de pre/post-proceso</cite>. Código fuente confirmado: `SmallDisplacementSIMPElement` implementa literalmente `Ke(ρ) = ρᵖ·Ke0` con <cite index="109-1">opciones de interpolación de material 'simp', 'simp_modified' o 'ramp'</cite>, expuesto como error explícito si se elige otro método no soportado. **VERIFICADO** que el elemento y la fórmula existen en el código; **PARCIALMENTE VERIFICADO** su madurez de uso — un hilo de soporte oficial (issue #8328) documenta a un desarrollador de Kratos luchando activamente para reactivar y hacer funcionar este elemento en 2023, con errores de runtime (`CONSTITUTIVE_LAW variable not in database`, no-threadsafe). Esto indica que, aun estando en el repositorio principal, esta ruta **no es plug-and-play** y requiere trabajo de depuración considerable.
2. **`OptimizationApplication` (activa/Production-Stable)**: soporta topology optimization density-based como un caso del framework general de filtrado + adjoint (sección 10), con mantenimiento activo y releases regulares en 2024-2025, a diferencia de la legacy.

| Punto | Estado |
|---|---|
| `Ke(ρ)=ρᵖKe0` implementado | VERIFICADO (legacy: elemento explícito; OptimizationApplication: vía material interpolation genérica) |
| Acceso a `Ke0` sin penalizar | VERIFICADO (vía `CalculateLocalSystem` en el elemento base, o parametrizando `DENSITY`/propiedad antes de llamar) |
| Control del exponente `p` | VERIFICADO en legacy (parámetro del elemento); PARCIALMENTE VERIFICADO en OptimizationApplication (se asume configurable vía JSON de material interpolation, no confirmado línea a línea) |
| Densidad mínima (`ρ_min`) | INFERENCIA — patrón SIMP estándar, presente en toda implementación seria; no confirmado el nombre exacto del parámetro en Kratos |
| Sensitivity filtering / density filtering | VERIFICADO (mencionado explícitamente en descripción oficial de `OptimizationApplication`) |
| Regularización adicional (Helmholtz PDE filter, etc.) | NO ENCONTRADO — no se localizó confirmación oficial explícita |

---

## 12. Shape Optimization

`StructuralMechanicsApplication`/`OptimizationApplication` soportan optimización de forma vía adjoint, actualizando **coordenadas nodales de la malla existente** dentro de restricciones (smoothing, mapeo de sensibilidad, filtros geométricos). Esto es distinto de "generar una geometría CAD final válida": Kratos modifica nodos de malla, no produce un sólido paramétrico ni un STEP de salida. Cualquier reconstrucción CAD post-optimización (mesh→B-rep/STEP) es responsabilidad exclusiva del proyecto y no forma parte de las capacidades de Kratos. **VERIFICADO** el primer punto (modificación nodal vía adjoint); **por diseño, fuera de alcance** el segundo (Kratos nunca pretende ser un motor CAD).

---

## 13. Mejora estructural restringida (superficies protegidas)

- **Capacidad existente**: filtros geométricos y de densidad que pueden anclarse a `ModelPart`s específicos (sub-dominios de la malla) — es decir, técnicamente es posible marcar ciertos nodos/elementos como "fuera del dominio de diseño" (pasive elements con densidad fija = 1, patrón estándar en TopOpt SIMP que Kratos hereda por diseño del método).
- **Capacidad parcial**: no hay una UI ni un flujo oficial de "definir superficies protegidas desde un modelo CAD importado"; eso depende de cómo el proyecto etiquete Physical Groups en Gmsh y los traduzca a `SubModelPart`s de Kratos antes de correr la optimización.
- **Desarrollo propio**: toda la lógica de negocio (qué superficies son "estéticas", "de montaje", etc., y cómo el usuario las selecciona en la app) es 100% responsabilidad del proyecto; Kratos solo provee el mecanismo de bajo nivel (dominio de diseño restringido) sobre el que construirla.

---

## 14. Diseño generativo

Kratos es, sin ambigüedad, un **motor FEA + optimización**, no un motor de diseño generativo end-to-end. `OptimizationApplication` da las piezas (multi-objetivo, multi-restricc