# Investigación técnica: arquitectura, algoritmos y UX de software CAD de diseño generativo / optimización topológica

> Documento de referencia técnica compilado para alimentar el desarrollo de **Topología Optimizada** (pipeline Python + C++ sobre Kratos Multiphysics: `StructuralMechanicsApplication` + `OptimizationApplication`, mallado con Gmsh, entrada STEP). Cubre: representación de geometría, selección de caras/sólidos, aplicación de cargas y condiciones de contorno, formulación matemática de la optimización (SIMP, level-set, MMC/moving morphable components), y arquitectura de menú/UI de cada herramienta comercial relevante.

---

## 1. Taxonomía: diseño generativo vs. optimización topológica vs. optimización de forma

Aunque el mercado usa "generative design" como término paraguas, técnicamente son procesos distintos que las herramientas comerciales combinan de formas diferentes:

| Tipo | Variable de diseño | Representación | Ejemplo comercial |
|---|---|---|---|
| **Topology optimization (densidad, SIMP)** | densidad relativa ρ(x) ∈ [0,1] por elemento/vóxel | malla FE fija (hex/tet) o grid cartesiano | Kratos `OptimizationApplication`, Ansys Mechanical, OptiStruct, SolidWorks Topology Study |
| **Level-set topology optimization** | función de nivel ψ(x); el sólido es {x : ψ(x) < 0} | grid cartesiano/vóxel desacoplado de la malla FE | Autodesk Fusion Generative Design (motor "Within"/Autodesk Research) |
| **Generative design (multi-solución)** | combinación de {carga, geometría preservada, material, método de manufactura} × N corridas de topología/forma | orquestación batch en la nube sobre un motor de TO | Fusion 360 Generative Design, Ansys Discovery |
| **Shape optimization (paramétrica/libre)** | posición de nodos de la frontera (shape derivative) sujeta a malla fija topológicamente | malla FE deformable | Altair OptiStruct Free-Shape, Tosca Shape |
| **Field-driven / implicit design** | campos escalares (SDF) combinados algebraicamente; TO es un caso particular | function representation (F-Rep) continua, evaluada bajo demanda | nTopology |

Tu proyecto cae en la primera fila (SIMP clásico basado en densidad sobre malla FE de Gmsh), que es también el método más documentado académicamente y el que usan la mayoría de los solvers de código abierto/Kratos.

---

## 2. Representación geométrica del dominio de diseño

Esta es la decisión arquitectónica más importante porque determina cómo se seleccionan caras, cómo se aplican condiciones de contorno y cómo se reconstruye la salida.

### 2.1 Malla FE conforme a la geometría (SolidWorks, Ansys Mechanical, OptiStruct/Inspire, Kratos+Gmsh)

- El STEP/B-Rep se malla directamente (tet/hex) respetando las caras de origen.
- Cada elemento de la malla queda asociado (por herencia de mallado) a la entidad topológica (cara, arista, cuerpo) de la que proviene.
- Las condiciones de contorno (BC) se definen sobre la **geometría B-Rep** (cara/arista/vértice) y se **propagan a los nodos de la malla en tiempo de solve**, no se definen directamente sobre nodos.
- Ventaja: persistente ante refinamiento de malla, coherente con selección CAD.
- Desventaja: la malla debe re-generarse si la geometría preservada cambia; es exactamente lo que estás resolviendo en Gmsh con `physical groups`.

Esto es **arquitectónicamente lo que ya definiste como el "issue #2" abierto** en `solver_interface.py`: necesitas exportar *physical groups por face tag de STEP* desde Gmsh para poder aplicar BC de forma selectiva en vez de "a todos los nodos".

### 2.2 Grid cartesiano / vóxel desacoplado (Fusion 360 Generative Design — método Autodesk/level-set)

De las patentes de Autodesk (US 11,321,508; US 12,169,398; US 12,353,191; US 12,488,539) surge un patrón consistente:

1. La geometría de entrada (B-Rep de "preserve" + "obstacle" + volumen de diseño) se convierte a **signed distance field (SDF)** sobre un **grid cartesiano regular** independiente de la malla de análisis, usualmente vía `OpenVDB`.
2. El solver de FEA (a menudo un solver de malla sólida separado, tetraédrico) resuelve la física sobre una malla "body-fitted" generada a partir del nivel actual de ψ.
3. Los resultados nodales (energía de deformación, tensión de von Mises) se **mapean de la malla sólida al grid de nivel** mediante dos pasos de interpolación:
   - malla sólida (elemento → nodo) por promediado,
   - nodo de malla sólida → punto de grid vóxel por funciones de forma lineales (interpolación trilineal).
4. Se calculan **velocidades de forma** (shape velocities) en cada punto del level-set a partir del gradiente de la función objetivo/restricciones (ver §4.2), y se actualiza ψ mediante una ecuación de Hamilton-Jacobi:

```
∂ψ/∂t + V(x)|∇ψ| = 0
```

5. Cada cierto número de iteraciones se reconstruye una superficie explícita del sólido actual con **Marching Cubes** (Lorensen & Cline 1987) o **Dual Contouring** (Ju et al. 2002) para visualización y para el resultado final.
6. Al final del proceso, la malla poligonal cruda (voxelizada, con "escalones") se convierte en un **B-Rep editable y watertight** mediante un pipeline separado de post-proceso: suavizado, segmentación de la malla en regiones de curvatura homogénea, y ajuste de superficies NURBS por región (surface fitting), preservando exactamente las caras de "preserve geometry" originales sin remuestrear.

Este es el motivo por el que en Fusion puedes editar el resultado como sólido paramétrico: no es una malla exportada tal cual, es una reconstrucción B-Rep generada algorítmicamente.

**Regiones de control geométrico** (terminología literal de las patentes Autodesk, útil para tu propio diseño de API):
- `keep-in`: Si ⊂ Ω (el sólido optimizado debe contener completamente esta región) → equivale a "Preserve Geometry" en la UI.
- `keep-out`: Si⁰ ⊄ Ω (el interior de esta región debe quedar fuera del sólido) → equivale a "Obstacle Geometry".
- `seed`: región parcialmente incluida, usada como semilla topológica inicial.

### 2.3 Implicit / function representation (F-Rep) — nTopology

- No hay malla de diseño persistente; todo objeto (incluida la salida de un TO) es un **campo escalar evaluado bajo demanda** en cualquier punto (x,y,z): `f(x,y,z) → ℝ`, con la convención `f<0` dentro, `f=0` superficie, `f>0` fuera.
- Operaciones booleanas son triviales: `f_union = min(f_A, f_B)`, `f_intersect = max(f_A, f_B)`.
- La topología resultante de un TO es tratada como **un campo más** que puede combinarse algebraicamente con campos de retícula (lattice), campos de tensión/dirección de fibra, etc. — de ahí el término *field-driven design*.
- Evaluación acelerada por GPU al no requerir malla persistente (se evalúa el campo en los puntos que se necesiten, p. ej. al hacer *slicing* directo a *toolpaths* de impresión 3D sin pasar por STL).
- Programación tipo **grafo de nodos** (dataflow visual), no árbol de features tipo CAD tradicional. Cada "bloque" (`Remap Field`, `Implicit Body`, `FEA Analysis Block`, `Remap Constraint`) es una función pura que consume y produce campos, cuerpos implícitos o resultados de simulación.
- El bloque `Remap Constraint` es notable: permite imponer restricciones geométricas (extrusión, patrón periódico, simetría) sobre el **campo de densidad** de la optimización topológica reutilizando la misma maquinaria del `Remap Field` (deformación de campos por sustitución de coordenadas x,y,z).

### 2.4 Comparativa de representación vs. tu pipeline

| | Malla conforme (tu caso) | Grid cartesiano/level-set (Autodesk) | Implícito F-Rep (nTop) |
|---|---|---|---|
| Independencia de malla | No (¡tu issue #1 y #2!) | Sí (grid propio) | Total |
| Reconstrucción a B-Rep | Directa (ya es B-Rep) | Requiere marching cubes + surface fit | Requiere isosuperficie + retopología |
| Cambios topológicos durante iteración | Limitados (SIMP) salvo densidad→0 | Naturales (nucleación de agujeros vía nivel) | Naturales |
| Costo computacional por iteración | Ensamblaje + solve FE estándar | Doble mapeo malla↔grid | Evaluación de campo (barato, paralelizable) |

---

## 3. Selección de caras/sólidos y el problema del "persistent naming"

Este apartado es crítico porque es exactamente tu segundo issue abierto.

### 3.1 Cómo referencian caras los CAD kernels (ACIS, Parasolid, Open CASCADE)

Un B-Rep no tiene "IDs" estables de fábrica: las caras se identifican por su posición en las listas de topología (`TopoDS_Face` en OCC, `FACE` en ACIS) generadas por el kernel al evaluar el árbol de features. Cuando el modelo se re-evalúa (por edición paramétrica), el kernel puede:
- fusionar dos caras en una,
- dividir una cara en varias,
- reordenar la lista de caras internamente.

Esto es el **persistent naming problem** (Kim & Han 2009, "Identification of topological entities and naming mapping"; Wang & Nnaji 2005 "Geometry-based semantic ID"). Las dos familias de solución:

1. **Topology-based naming**: el nombre de una cara se deriva de la información de la sketch/trayectoria y de las features que la generaron (p. ej. "cara lateral #3 de la extrusión #2"). Es lo que usa SolidWorks internamente (y es la causa de los bugs clásicos de "se movió el fillet a la cara equivocada" tras editar un feature anterior).
2. **Geometry-based / semantic-ID naming**: se asigna un ID basado en continuidad geométrica de la superficie soporte (curvatura, adyacencia estable) en vez de en el historial de construcción — más robusto a cambios de topología pero más caro de calcular.

### 3.2 Cómo lo resuelven los motores de FEA/TO en la práctica

En la práctica, **ningún** motor de FEA opera con el B-Rep directamente durante el solve. El patrón universal es:

```
B-Rep (cara con Tag/ID persistente)
   │  1. Selección en UI: click en cara → kernel devuelve TopoDS_Face / face id
   ▼
Etiquetado ("Physical Group" en Gmsh, "Named Selection" en Ansys,
            "Selection Set" en Fusion, "Selection" en SolidWorks)
   │  2. Este etiquetado se serializa junto con el ID persistente de la cara
   ▼
Mallado: el mallador recorre el B-Rep cara por cara y etiqueta cada
         elemento/cara de elemento generado con el grupo físico heredado
   │  3. Salida: conjuntos de nodos/elementos con el mismo nombre de grupo
   ▼
Solver FE: aplica la condición de contorno al conjunto de nodos con ese
           nombre, NO a coordenadas ni a "todos los nodos"
```

Esto es exactamente el patrón de **Gmsh Physical Groups → submodelparts de Kratos (.mdpa)** que necesitas implementar para resolver tu issue #2. El flujo concreto en Gmsh OCC:

```python
import gmsh
gmsh.initialize()
gmsh.model.occ.importShapes("part.step")   # NO usar gmsh.merge() (issue #1)
gmsh.model.occ.synchronize()

# Identificar las caras STEP por su tag numérico persistente en el kernel OCC
# (los tags de gmsh.model.occ persisten al import si OCCImportLabels=1)
gmsh.option.setNumber("Geometry.OCCImportLabels", 1)

# Crear un Physical Group con las caras seleccionadas (por tag, no por posición)
fixed_face_tags = [5, 12]       # obtenidos de la selección de usuario en tu GUI
load_face_tags  = [7]

gmsh.model.addPhysicalGroup(2, fixed_face_tags, tag=101, name="FIXED_SUPPORT")
gmsh.model.addPhysicalGroup(2, load_face_tags,  tag=102, name="POINT_LOAD_FACE")

gmsh.model.mesh.generate(3)
gmsh.write("part.msh")
```

Al exportar a `.mdpa` (vía `KratosMultiphysics.mdpa` writer o un conversor `.msh`→`.mdpa`), cada Physical Group se convierte en un **SubModelPart** de Kratos, y las condiciones de contorno se asignan por `model_part.GetSubModelPart("FIXED_SUPPORT")` en vez de iterar sobre `model_part.Nodes` completo — esto resuelve directamente el placeholder que identificaste en `solver_interface.py`.

### 3.3 Selección de cara en la UI: qué pasa realmente al hacer clic

En Fusion 360 / SolidWorks / Inspire, cuando el usuario hace clic sobre una cara en el viewport:
1. Un **ray-cast** desde la cámara hasta el modelo intersecta la representación de teselado (tesselation) usada para render (no el B-Rep exacto).
2. El triángulo golpeado tiene un puntero de vuelta ("back-pointer") al `TopoDS_Face`/entidad B-Rep exacta que lo generó (cada motor de teselación —OCC's `BRepMesh_IncrementalMesh`, Parasolid's facet API— mantiene esta correspondencia triángulo→cara).
3. Esa entidad B-Rep exacta es la que se añade al "Selection Set"/"Named Selection", **no** el triángulo ni sus coordenadas.
4. El ID persistente de esa entidad (topology-based o semantic-ID, según el kernel) es lo que se serializa en el archivo del estudio para que sobreviva a la regeneración del modelo.

### 3.4 Non-manifold y ambigüedad de selección

Un problema documentado (ver "Pointer-CAD", arXiv 2603.04337) es que en aristas no-manifold (compartidas por más de dos caras) la selección se vuelve ambigua para operaciones downstream como fillets o para decidir a qué cara pertenece un nodo de frontera en el mallado. Los kernels comerciales prohíben la mayoría de configuraciones no-manifold precisamente para evitar esto; tu pipeline (Gmsh + OCC) hereda la misma restricción — vale la pena validar que el STEP de entrada sea manifold antes de generar physical groups.

---

## 4. Formulación matemática de la optimización

### 4.1 SIMP clásico (el que usa Kratos `OptimizationApplication`, Ansys, SolidWorks, OptiStruct en modo densidad)

**Variables de diseño**: densidad relativa por elemento ρₑ ∈ [ρ_min, 1], ρ_min > 0 (típicamente 1e-3 – 1e-9) para evitar singularidad de la matriz de rigidez.

**Interpolación de material (ley de potencia SIMP)**:

```
E(ρₑ) = E_min + ρₑ^p · (E₀ − E_min)
```

donde `p` es el factor de penalización (típicamente 3), que castiga las densidades intermedias ("grises") empujando la solución hacia 0/1 porque para p>1 el material a densidad intermedia da menos rigidez por unidad de masa que el material sólido.

**Problema de minimización de compliance (caso canónico)**:

```
min_ρ   c(ρ) = Uᵀ K(ρ) U
s.t.    K(ρ) U = F
        Σₑ ρₑ vₑ ≤ V*         (restricción de volumen)
        0 < ρ_min ≤ ρₑ ≤ 1
```

**Sensibilidad (derivada de la compliance respecto a la densidad)**, obtenida por el método adjunto (autoadjunto para compliance):

```
∂c/∂ρₑ = −p · ρₑ^(p−1) · (E₀ − E_min) · uₑᵀ k₀ uₑ
```

donde `uₑ` es el vector de desplazamientos del elemento y `k₀` la matriz de rigidez elemental unitaria. **Esta es exactamente la cantidad que Kratos `OptimizationApplication` necesita exponer como `StrainEnergyResponseFunction` sensitivity** para alimentar el optimizador.

### 4.2 Filtros (para evitar checkerboarding y dependencia de malla)

- **Filtro de sensibilidad (Sigmund 1997)**: promedia `∂c/∂ρₑ` en un radio `r_min` ponderado por distancia.
- **Filtro de densidad (Bruns & Tortorelli 2001, Bourdin 2001)**: filtra ρ directamente antes de evaluar E(ρ); preserva linealidad de la restricción de volumen y permite gradiente analítico exacto — es el preferido en implementaciones modernas (incluida la de Kratos).
- **Proyección de Heaviside**: aplica una función sigmoide/escalón suavizado sobre la densidad filtrada para forzar convergencia 0/1 ("black-and-white") sin perder diferenciabilidad:

```
ρ̃ₑ = tanh(β η) + tanh(β (ρ̄ₑ − η)) / (tanh(β η) + tanh(β (1 − η)))
```

con β creciendo por *continuation* a lo largo de las iteraciones (empezar suave, endurecer progresivamente) — patrón que evita mínimos locales pobres.

### 4.3 Optimizadores: OC vs. MMA/GCMMA

| | Optimality Criteria (OC) | MMA (Svanberg 1987) | GCMMA |
|---|---|---|---|
| Tipo de restricciones | Una restricción simple (volumen) vía multiplicador de Lagrange + bisección | Múltiples restricciones no lineales generales | Igual que MMA + garantía de convergencia global |
| Robustez ante combinaciones de parámetros | Falla si el filtro se aplica sobre densidad en vez de sensibilidad | La más robusta empíricamente (converge en el rango más amplio de p, radio de filtro, condición inicial) | Más lenta, pero única opción robusta si se filtra densidad directamente |
| Uso típico | Código académico "88/99/169-line" MATLAB, algunos módulos legacy | Estándar de facto en software comercial (OptiStruct, Kratos vía `algorithms/mma`) y researh moderna | Casos con muchas restricciones simultáneas (stress + freq + fabricación) |
| Complejidad de implementación | Baja (regla de actualización heurística cerrada) | Media-alta (subproblema convexo separable por iteración, requiere resolver aproximación de segundo orden) | Alta |

Dado que tu roadmap ya apunta a `gradient_projection` dentro de Kratos `OptimizationAnalysis`, vale la pena verificar si Kratos expone también un algoritmo tipo MMA (`algorithms/algorithm_mma.py` en `OptimizationApplication`, si tu versión lo incluye) — es el estándar de facto contra el cual comparar resultados con Ansys/OptiStruct.

### 4.4 Level-set (Autodesk/Fusion) — formulación de velocidad de forma

**Problema elástico lineal continuo** que resuelven internamente (idéntico al que resuelve Kratos, solo cambia la parametrización del dominio):

```
−∇·(D:ε(u)) = f   en Ω
u = 0             en Γ_D  (Dirichlet / fijaciones)
D:ε(u)·n = t      en Γ_N  (Neumann / cargas)
```

con `D` el tensor constitutivo, `ε(u) = ½(∇u + ∇uᵀ)` la deformación.

**Actualización del level-set** vía ecuación de Hamilton-Jacobi (§2.2), donde la **velocidad normal de frontera** `V(x)` se deriva del *shape derivative* de la función objetivo (compliance, masa, factor de seguridad a fatiga, etc.), y se combina con restricciones múltiples mediante un **Lagrangiano aumentado** con controladores adaptativos tipo PID (documentado en la patente de "Generative design shape optimization with controlled convergence"):

```
L(ψ, λ, μ) = J(ψ) + Σᵢ λᵢ gᵢ(ψ) + (μ/2) Σᵢ gᵢ(ψ)²
```

Los controladores PID ajustan dinámicamente `λ`, `μ` observando el histórico de `volumen objetivo vs. volumen real` iteración a iteración (en vez de un simple aumento monótono de la penalización), lo cual permite manejar simultáneamente restricciones de igualdad y desigualdad arbitrarias — útil si en el futuro quieres implementar múltiples restricciones (masa + desplazamiento máx. + factor de seguridad) en tu propio optimizador C++.

### 4.5 Otras parametrizaciones relevantes (contexto, no usadas por tu stack actual)

- **Moving Morphable Components/Voids (MMC/MMV)**: la geometría se parametriza explícitamente como unión de un número fijo de componentes geométricos simples (elipses, superelipses, barras) cuyos parámetros (centro, orientación, longitud, grosor) son las variables de diseño. Da fronteras suaves sin necesidad de filtro/proyección, pero el número de componentes es un hiperparámetro sensible.
- **Gaussian Ensemble Topology (GET, 2026)**: variante explícita/suave donde el campo de densidad se construye como suma de funciones Gaussianas — explícitamente diseñada para ser independiente de malla (igual que MMC) pero con gradiente más regular; competidor académico reciente de MMC.
- **Homogenización (Bendsøe & Kikuchi 1988)**: el método histórico original que dio origen al SIMP; en vez de densidad por elemento, optimiza microestructuras periódicas (celdas unitarias con agujero rectangular parametrizado) cuyo comportamiento efectivo se calcula por homogeneización — hoy resucitado en optimización multiescala (C-HiDeNN-TD, Northwestern 2025).

---

## 5. Aplicación de cargas, restricciones y elasticidad: patrones de API interna

### 5.1 Patrón universal de aplicación de BC (lo que corrigió tu debugging session)

Independientemente del software, el patrón de bajo nivel para aplicar una condición de contorno tipo carga puntual/superficial es:

1. **Namespace de la variable física**: en Kratos, `POINT_LOAD` vive en `StructuralMechanicsApplication` (`SMA.POINT_LOAD`), no en el core — exactamente el bug que resolviste. Esto es equivalente en Ansys APDL a `F, node, FX, value` vs. `SF, face, PRES, value` (nodal vs. superficial), y en Abaqus a la distinción entre `*Cload` (nodal) y `*Dsload` (superficial, requiere normal de cara).
2. **Entidad portadora de la carga**: una fuerza puntual externa requiere una **condición** explícita en la malla (`PointLoadCondition3D1N` en tu caso), no basta con asignar la variable nodal — coincide exactamente con cómo Abaqus requiere un `*Cload` referenciando un `Set`, y cómo Ansys Mechanical crea un objeto "Force" en el árbol que internamente genera elementos de contacto/carga (`SURF154`/`CONTA174` equivalentes) sobre el `Named Selection`.
3. **Orden de inicialización**: `.Initialize(ProcessInfo)` debe llamarse en cada elemento/condición antes del ensamblaje si se usa un `BuilderAndSolver` manual (fuera de un `SolvingStrategy` completo) — es un detalle de bajo nivel que la mayoría de motores comerciales ocultan tras un "Solve" monolítico, pero que es exactamente el control fino que te da la arquitectura híbrida Python+C++ que elegiste.

### 5.2 Cómo los programas comerciales exponen esto en la UI (para inspirar tu propio menú)

| Concepto interno | Fusion 360 | Altair Inspire | SolidWorks Simulation | Ansys Mechanical | PTC Creo (GTO) | Siemens NX |
|---|---|---|---|---|---|---|
| Fijación / Dirichlet | "Structural Constraint" → tipo Fixed/Pin/Ball | "Supports" (fixed, non-designable) | "Fixtures" (Fixed Geometry, Roller/Slider, etc.) | "Fixed Support", "Displacement" | "Constraints" dentro del Structural Study | Condiciones de restricción sobre cara/edge en Topology Optimizer |
| Carga puntual/superficial | "Structural Loads" (Force, Pressure, Torque) sobre cara(s) de Preserve Geometry | "Loads" (force, pressure, gravity, acceleration, temperature) | "External Loads" (Force, Pressure, Torque, Gravity) | "Force", "Pressure", "Moment" (Environment tree) | "Loads" con soporte multi-load-case | Cargas definidas sobre el modelo unificado facet+B-Rep |
| Material/elasticidad | Selector de biblioteca (E, ν, ρ, σ_y) por resultado candidato (multi-material batch) | Biblioteca de materiales + definición custom | Biblioteca SOLIDWORKS Materials (isotrópico/ortotrópico) | Engineering Data workbench (curvas completas, plasticidad, fatiga) | Definición de material dentro de "Design criteria" | Biblioteca de materiales NX + NX Nastran |
| Región no-optimizable | "Preserve Geometry" (cuerpo separado, booleano con dominio) | "Non-Design Space" | "Preserved Region" (Manufacturing Control) | "Exclusion Region" en Topology Optimization branch | "Design Spaces" con cuerpos a preservar | Región no-optimizable definida sobre B-Rep base |
| Región prohibida | "Obstacle Geometry" | (implícito vía non-design regions con densidad forzada a 0) | — (se modela restando geometría antes del estudio) | "Exclusion Region" combinado con `keep-out` | "Design Spaces" con cuerpos a excluir | (equivalente vía exclusión en Design Space Explorer) |
| Motor de optimización | Level-set propio (Autodesk Research) sobre grid cartesiano | OptiStruct (SIMP/densidad, malla FE) | SIMP-like, integrado en Simulation | SIMP clásico (Mechanical) / GPU vóxel (Discovery) | TrueSOLID (Frustum, densidad/GPU sobre vóxel) | NX Nastran + Convergent Modeling (facet nativo) |
| Reconstrucción de salida | Automática: level-set → marching cubes → NURBS fitting (B-Rep editable) | PolyNURBS (edición manual asistida) | "Export Smoothed Mesh" (STL o Solid Body aproximado) | Reconstrucción manual/semi-automática | Malla suavizada nativa de TrueSOLID | Ninguna requerida: el cuerpo convergente ya es editable (facet+B-Rep) |

**Patrón de diseño de UI común**: los cinco programas separan estrictamente en el árbol de features/estudio:
```
Study/Setup
├── Design Space (geometría base a optimizar)
├── Preserve/Non-Design Regions   ← nunca se elimina material aquí
├── Obstacle/Exclusion Regions    ← nunca se coloca material aquí
├── Structural Constraints (Dirichlet)   → aplicadas SOLO sobre caras de Preserve
├── Structural Loads (Neumann)           → aplicadas SOLO sobre caras de Preserve
├── Material assignment
├── Manufacturing Controls (simetría, draw direction, min/max thickness, overhang)
├── Objective + Constraint (mass target / stiffness-to-weight / stress ≤ σ_max)
└── Mesh settings (density, element order)
```

Esto sugiere para tu GUI de Qt (ya inspirada en Onshape) una jerarquía de árbol equivalente: separar explícitamente `Design Space`, `Preserve`, `Obstacle`, `Loads`, `Supports`, `Material`, `Manufacturing Constraints`, `Objective`, en vez de un único panel plano — reduce errores de usuario (el error más citado en todos los tutoriales es "preservar demasiada geometría y dejar sin margen al algoritmo").

### 5.3 "Keep-out zone" automática alrededor de cargas/apoyos (SolidWorks)

Dato específico útil: SolidWorks Topology Study crea automáticamente una **zona de exclusión (keep-out)** alrededor de cada cara con carga o fijación aplicada, editable por el usuario, para evitar que el algoritmo intente eliminar material justo donde se transmiten fuerzas concentradas (lo cual generaría singularidades de tensión sin sentido físico). Es una buena práctica a replicar: forzar `ρₑ = 1` (elementos "activos"/no-optimizables) en un halo de N capas de elementos alrededor de cada `SubModelPart` de carga/apoyo.

---

## 6. Reconstrucción de geometría y exportación (post-proceso)

| Etapa | SIMP sobre malla FE (tu caso) | Level-set/vóxel (Autodesk) | F-Rep (nTopology) |
|---|---|---|---|
| Resultado crudo | Campo escalar ρₑ por elemento | Función de nivel ψ sobre grid | Campo implícito |
| Extracción de isosuperficie | Umbral ρₑ > 0.5 + extracción de caras de frontera de la malla, o "Material Mass Plot" con isosuperficie (SolidWorks) | **Marching Cubes** / **Dual Contouring** sobre el grid cartesiano | Muestreo del campo + Marching Cubes bajo demanda |
| Suavizado | Laplacian smoothing / Taubin smoothing sobre malla STL resultante | Suavizado + segmentación por curvatura | Suavizado nativo del campo (blending implícito, sin operación discreta) |
| Reconstrucción a B-Rep editable | Manual (reimportar STL, remallar con superficies) o mesh-to-BREP add-ins | Automática: ajuste de superficies NURBS por región + preservación exacta de caras "Preserve" | Exportación directa a STL/3MF o retopología manual; filosofía "diseña para no necesitar B-Rep" |
| Formato de salida típico | STL (impresión 3D) / mesh body (mecanizado tras retopología manual) | Sólido paramétrico editable en Fusion + STL | STL, 3MF, o G-code/toolpaths directos (bypass de malla) |

Para tu pipeline, dado que usas Gmsh + Kratos, el análogo más cercano es: **umbral de densidad → extracción de superficie de frontera de los elementos "sólidos" → export STL o remalla con superficies para reimportar a un modelador**. Vale la pena investigar `pymeshlab` o `PyVista`'s `marching_cubes`/`contour` sobre el campo ρₑ interpolado a un grid auxiliar si quieres una reconstrucción más limpia que "extraer caras de elementos activos" (que produce escalones tipo vóxel si la malla es gruesa).

---

## 6.5 Aplicación de cargas sobre malla vóxel: mecanismo exacto (patente, aplicable a Fusion/Creo-Frustum)

Este apartado documenta con precisión de implementación cómo se resuelve el problema de aplicar una BC definida sobre una **cara B-Rep exacta** cuando el solver internamente usa una **malla vóxel/hexaédrica estructurada que no conforma exactamente esa cara** (el "problema opuesto" al tuyo: tú tienes malla conforme vía Gmsh, pero el razonamiento matemático de distribución de carga es reutilizable si en algún momento exploras un solver vóxel/Cartesiano para acelerar iteraciones).

**Paso 1 — Identificación de vóxeles y nodos de superficie.** Dada una cara B-Rep `S` sobre la que el usuario definió la BC:
- Se identifican los vóxeles cuyo centroide está a distancia mínima de `S` (vóxeles "de superficie").
- De esos vóxeles, se seleccionan únicamente los **nodos** cuya distancia proyectada a `S` es menor a **la mitad del tamaño de vóxel** — este es el criterio exacto de pertenencia al conjunto de nodos de frontera.

**Paso 2 — Restricciones de desplazamiento (Dirichlet), aplicación cinemáticamente exacta.**
En vez de un método de penalización (que permite un desplazamiento residual no nulo, físicamente incorrecto), se calcula un **sistema de coordenadas local (LCS)** anclado a la cara real (no al vóxel aproximado): normal exacta de la superficie en el punto más cercano al centroide del vóxel. La restricción de desplazamiento (fija, deslizante, cilíndrica) se aplica como *single point constraint* en ese LCS — así el nodo no puede moverse en la dirección prohibida **exactamente**, aunque la malla vóxel solo aproxime la geometría real (efecto "escalón" de vóxeles sobre una cara inclinada). Esto es superior a fijar los grados de libertad en coordenadas globales XYZ, que sí introduce error en caras no alineadas con los ejes.

**Paso 3 — Cargas puntuales/momentos (Neumann), vía elemento de interpolación (RBE3-like).**
1. Se coloca un **nodo de referencia** en el centroide de los nodos de superficie identificados.
2. Se conecta ese nodo de referencia a todos los nodos de superficie mediante un **elemento de restricción por interpolación** (equivalente a un `RBE3`/`Distributing Coupling` de Nastran/Abaqus): el movimiento del nodo de referencia se restringe como **promedio ponderado** de los nodos reales.
3. La fuerza/momento total especificado por el usuario se aplica **únicamente en el nodo de referencia**; el elemento de interpolación la reparte automáticamente entre los nodos reales de forma físicamente consistente (evita crear energía espuria, principio de trabajo virtual).

Esto es preferible a "dividir la fuerza total entre N nodos por igual", que no es exacto cuando la distribución de nodos sobre la cara vóxelizada es irregular.

**Paso 4 — Carga de presión uniforme, con corrección de residuo.**
```
F_i = -(P·A / N) · n̂_i        (fuerza por vóxel de superficie i, N = nº de vóxeles de superficie)
```
repartida entre los 8 vértices del hexaedro; opcionalmente con normal individual por vértice (8 normales por vóxel) para mayor precisión:
```
F_i^v = -(P·A / 8N) · n̂_i^v
```
Como la suma de estas fuerzas discretas casi nunca iguala exactamente `P·A` (por la aproximación de la normal en superficies curvas), se calcula un **residuo**:
```
F_residual = F_exacta_total − Σ F_i (aplicadas)
```
y ese residuo se inyecta **también** vía el nodo de referencia + elemento de interpolación del Paso 3, garantizando que la carga total resultante en la simulación coincide exactamente con la especificada por el usuario, incluso con una malla vóxel gruesa.

**Paso 5 — Carga de rodamiento/cojinete (bearing load, distribución parabólica)** sobre superficie cilíndrica:
```
F_y = F₀ Σᵢ sin³θᵢ ,     F₀ = F_y / Σᵢ sin³θᵢ
F_i = F₀ [sin²θᵢ cosθᵢ , sin³θᵢ]   (componentes en el sistema de coordenadas del rodamiento)
```
con `θᵢ` el ángulo entre la línea centro-del-rodamiento→vóxel y el eje local X — mismo patrón de corrección por residuo que el Paso 4.

**Justificación física del margen de error tolerado — Principio de Saint-Venant.** El documento invoca explícitamente que el error de discretización en la aplicación de la BC sobre la geometría preservada **se disipa** a una distancia de pocas veces el tamaño característico de la malla, entrando al dominio de diseño con una distribución de tensiones prácticamente idéntica a la exacta. Esto es lo que permite usar una malla vóxel/Cartesiana **más gruesa** que una malla tetraédrica conforme sin perder fidelidad en el resultado de la optimización — y es la justificación formal para no perseguir una conformidad exacta malla-geometría cuando el objetivo es la distribución de material, no la tensión exacta en el punto de aplicación de la carga.

**Validación cuantitativa reportada** (malla vóxel vs. malla tetraédrica de referencia, mismo caso): diferencias del orden de 0.2%–2.3% en desplazamiento/tensión máxima lejos de la zona de aplicación de carga, usando entre 1/3 y 1/7 del número de elementos de la malla tetraédrica equivalente — el ahorro computacional es sustancial y el error, despreciable, precisamente gracias a Saint-Venant.

---

## 7. Resumen por producto (arquitectura + motor + UI)

### Autodesk Fusion 360 — Generative Design
- **Motor**: nube (Autodesk cloud compute), múltiples solvers en paralelo por combinación material×método de manufactura×condición de carga.
- **Algoritmo**: level-set sobre grid cartesiano (Autodesk Research "Dreamcatcher" / adquisición de Within Technologies), Lagrangiano aumentado con control PID adaptativo para restricciones múltiples (fatiga, factor de seguridad, múltiples casos de carga).
- **Selección de geometría**: `Preserve Geometry` (keep-in) y `Obstacle Geometry` (keep-out) como cuerpos B-Rep separados, booleanos contra el `Design Space`.
- **UI**: workspace dedicado "Generative Design" separado del CAD paramétrico normal; wizard de 4 pasos (Preserve → Obstacle → Structural Constraints → Study/Explore resultados en galería comparable por peso/rigidez/manufactura).
- **Salida**: sólido B-Rep editable + malla STL, reconstruido automáticamente desde el level-set.

### Altair Inspire (motor OptiStruct)
- **Motor**: OptiStruct (solver de EF propio de Altair, no basado en malla cartesiana, sino en la malla FE directa).
- **Algoritmos disponibles en un mismo entorno**: topología (densidad/SIMP), topografía (beads sobre shells), calibre/gauge (espesor), lattice, **PolyNURBS shape optimization** (ajuste de superficies NURBS de control directamente sobre el resultado, para "reingeniería" manual rápida del resultado de TO).
- **Restricciones de manufactura nativas**: simetría, dirección de desmoldeo (draw direction, con gradiente de espesor desde OptiStruct 2024), evitar cavidades internas (constraint de fundición, `casting direction` no-decreciente en densidad — implementado como level-set topológico aumentado en literatura reciente), ángulo de voladizo (overhang) para AM, restricción de fresado a 5 ejes.
- **UI**: un único árbol "Structure" con carpetas Optimización/Cargas/Soportes/Materiales; el resultado de TO es directamente editable con **PolyNURBS** (herramienta de modelado orgánico basado en subdivisión, no B-Rep clásico) para iterar manualmente sobre el resultado crudo.

### nTopology
- **Motor**: propio, evaluación de campos GPU-aceleradas + FEA embebido (no depende de mallado persistente para geometría).
- **Algoritmo**: TO como "caso simple de field-driven design"; combina topología + retícula + campos de dirección de tensión/frecuencia mediante operaciones algebraicas sobre campos.
- **Selección/paradigma**: no hay "seleccionar cara" en sentido CAD tradicional; el diseño es un **grafo de bloques** (dataflow) donde geometría, campos de simulación y restricciones son nodos conectables. `Remap Constraint` impone restricciones geométricas directamente sobre el campo de densidad de la optimización.
- **UI**: editor de nodos (similar a Grasshopper/Houdini), no un árbol de features lineal.
- **Salida**: geometría implícita, exportable a STL/3MF o directo a G-code (bypass de malla intermedia para impresión).

### Ansys (Mechanical: batch tradicional; Discovery: interactivo GPU)
- **Ansys Mechanical Topology Optimization**: SIMP clásico sobre malla FE completa, integrado al flujo Workbench estándar (Named Selections para BC, igual patrón que descrito en §3.2).
- **Ansys Discovery**: solver GPU-nativo (no CPU/malla refinada tradicional), física "Live" con feedback en milisegundos; usa una discretización interna optimizada para GPU (aproximación tipo vóxel/malla adaptativa automática) — el usuario nunca mira ni controla la malla. TO interactivo: el usuario arrastra un slider de "target mass reduction" y ve el resultado converger en tiempo real (~segundos), pensado para fase de concepto, no para validación final (esa se hace después en Ansys Mechanical con mayor fidelidad).
- **UI de Discovery**: "Live" toolbar contextual sobre el modelador directo tipo SpaceClaim; no hay "estudio" separado, la física corre continuamente mientras se edita geometría.

### PTC Creo — Generative Topology Optimization Extension (GTO), motor Frustum/TrueSOLID
- **Origen del motor**: Creo no desarrolló su optimizador internamente — PTC **adquirió Frustum Inc. en 2018 (~USD 70M)**, una startup de Boulder, Colorado, cuyo producto "Generate" corría sobre un kernel propietario llamado **TrueSOLID**, descrito por analistas independientes (DEVELOP3D) como "un motor de optimización topológica acelerado por GPU que produce una pieza suavemente mallada" — es decir, **densidad-based sobre grid vóxel** (no level-set explícito como Autodesk), con reconstrucción de malla suave como salida directa. La etiqueta "AI" en el marketing de PTC es, según la misma cobertura de la industria, principalmente narrativa comercial más que aprendizaje automático real en el núcleo del solver.
- **Integración con Ansys**: PTC mantiene una alianza estratégica con Ansys (anterior a la adquisición de Frustum) que permite que Creo recomiende un enfoque de diseño generativo, y que la **validación final a mayor fidelidad se delegue a Ansys Discovery Live** (el mismo motor GPU descrito en la sección Ansys de este documento) — un patrón de "optimización rápida en Creo → validación de mayor fidelidad en Ansys" que separa explícitamente el rol de exploración conceptual del de verificación estructural.
- **Flujo de trabajo en la UI** (`Applications > Generative Design`, confirmado en la documentación oficial de PTC):
  1. Se crea un **Structural Study** (o Modal/Thermal Study) por defecto al entrar al workspace.
  2. **Design Spaces**: se indica el cuerpo a optimizar y los cuerpos a preservar/excluir — mismo patrón `keep-in/keep-out` que el resto de la industria.
  3. **Constraints, loads, and boundary conditions** — soporta múltiples casos de carga (`load cases`) por estudio.
  4. **Design criteria**: objetivo de diseño + definición de material; opcionalmente restricciones de manufactura y geométricas.
  5. La optimización corre como **proceso en segundo plano dentro de la sesión de Creo**: si se cierra la aplicación de Generative Design la optimización se pausa (se puede reanudar); si se cierra Creo Parametric completo antes de converger, el progreso **no se guarda** y hay que reiniciar — a diferencia de Fusion (donde el cómputo vive en la nube y persiste independientemente del cliente).
- **Diferenciador de integración**: Creo ejecuta el ciclo FEA-driven de reducción de masa **dentro del árbol de historial paramétrico** (a diferencia de Fusion, que usa un workspace separado desconectado del modelo paramétrico) — dimensiones, ecuaciones y tablas de familia permanecen editables mientras el solver itera, y las condiciones de contorno "se propagan entre dominios sin fricción de exportación/importación" dentro del multiphysics workspace unificado de Creo.
- **Salida**: malla suavizada reconstruida directamente por TrueSOLID (voxel → superficie suave), integrable de vuelta al modelo paramétrico de Creo.

### Siemens NX — Topology Optimizer + Convergent Modeling (kernel Parasolid)
- **Diferenciador arquitectónico central: Convergent Modeling™**. Es una extensión del **kernel Parasolid** (el mismo núcleo geométrico que usa Siemens NX, y que licencian terceros como SolidWorks vía otros kernels — aquí es Parasolid nativo) que permite que **facetas/malla (mesh) y B-Rep preciso coexistan como ciudadanos de primera clase en el mismo modelo**, sin conversión de datos ni reingeniería inversa. Es la única solución revisada en este informe donde el resultado bruto de la optimización topológica (una malla de facetas) se puede **editar directamente con las mismas herramientas push/pull de modelado directo** (Synchronous Technology) que el resto del modelo B-Rep, sin necesidad de reconstruir superficies NURBS antes de poder tocarlo.
- **Por qué importa para el pipeline estándar de la industria**: en Fusion/Creo/Ansys/SolidWorks, el resultado de TO es una malla que debe **reconstruirse a B-Rep** (marching cubes + fitting NURBS, o exportación STL para manufactura directa) antes de poder editarse como CAD paramétrico — es un paso de post-proceso no trivial, frecuentemente descrito en la literatura como "más lento que la optimización misma". NX evita ese paso: el cuerpo "convergente" resultante ya es directamente editable, y las regiones optimizadas orgánicas pueden conservarse **como geometría de facetas en el centro de la pieza** mientras el resto del modelo permanece B-Rep preciso (p. ej. roscas, interfaces de montaje).
- **NX Topology Optimizer** (release moderno dentro del portfolio Xcelerator): genera piezas a partir de requisitos funcionales y de espacio de diseño puros, produciendo **"convergent bodies" completamente editables**; cambios de diseño posteriores se propagan automáticamente a la optimización y a features aguas abajo (manufactura, mecanizado final) — integración de ciclo de vida completo (diseño → optimización → AM → mecanizado de acabado) dentro de una sola sesión.
- **Design Space Explorer**: combina exploración del espacio de diseño con ingeniería generativa multiobjetivo — el análogo de NX al "wizard de resultados comparables" de Fusion, pero operando sobre combinaciones de objetivos en vez de combinaciones de material/manufactura.
- **Solver**: NX Nastran (solver FEA propio de Siemens, de los más establecidos de la industria) para la física subyacente de la optimización.
- **Flujo de UI**: no hay un "workspace" separado tipo Fusion; el Topology Optimizer es una función más dentro del entorno de modelado NX estándar, coherente con la filosofía de Convergent Modeling de que optimización y modelado directo/paramétrico son **el mismo espacio de trabajo**, no etapas separadas de un pipeline.

### SolidWorks Simulation — Topology Study
- **Motor**: integrado nativamente en SolidWorks Simulation Professional/Premium.
- **Algoritmo**: densidad-based (SIMP-like), descrito como "elimina elementos de la malla FE iterativamente" — formulación de eliminación de elementos más que densidad continua pura en su descripción de marketing, pero el resultado se maneja como campo continuo en el "Material Mass Plot".
- **Controles de manufactura**: `Preserved Region`, `Thickness Control` (min/max), `Symmetry` (½, ¼, ⅛), `De-Mold Pull Direction` (fundición).
- **Post-proceso característico**: "Material Mass Plot" con **slider interactivo** que recalcula la isosuperficie (`Calculate Smoothed Mesh`) para distintos umbrales de densidad sin re-resolver el problema de optimización — solo re-extrae la isosuperficie del campo de densidad ya calculado. Exporta vía "Export Smoothed Mesh" a Solid Body (reconstrucción B-Rep aproximada) o Surface Body (STL).
- **UI**: un estudio más dentro del árbol estándar `Simulation` de SolidWorks (mismo paradigma que un estudio estático), con "Manufacturing Controls" como subcarpeta.

---

## 8. Insights directamente accionables para Topología Optimizada

1. **Physical Groups de Gmsh como solución al issue #2** — replica exactamente el patrón `B-Rep face tag → Physical Group → SubModelPart` usado universalmente por la industria; no hay atajo alternativo válido en ningún producto revisado.
2. **Halo de elementos no-optimizables alrededor de cargas/apoyos** (patrón SolidWorks) evita singularidades de sensibilidad — fácil de implementar como paso de post-proceso sobre las Physical Groups antes de pasar a `OptimizationApplication`.
3. **Separar en tu árbol de features de Qt**: Design Space / Preserve / Obstacle / Loads / Supports / Material / Manufacturing Constraints / Objective, replicando el patrón de los 5 programas revisados — reduce el error más común reportado en toda la literatura (preservar demasiada geometría).
4. **Filtro de densidad (no de sensibilidad)** es la elección más robusta si en algún momento migras de OC a MMA/GCMMA (ver §4.3) — confírmalo contra `GetDefaultParameters()` de tu instalación local de Kratos como ya vienes haciendo.
5. **Reconstrucción de salida**: dado que ya tienes VTK en el pipeline, `marching_cubes` sobre un campo ρ interpolado a grid auxiliar (vía PyVista/VTK `vtkFlyingEdges3D` o `vtkMarchingCubes`) te da una ruta de exportación STL de calidad comparable a la de SolidWorks/Ansys sin necesidad de escribir tu propio contornado — evita reinventar Marching Cubes en C++ salvo que la IP específica esté ahí.
6. **Terminología `keep-in`/`keep-out`/`seed`** (Autodesk) es un vocabulario más preciso que "Preserve/Obstacle" para tu propia documentación interna/API si defines una interfaz programática (JSON de configuración) para las regiones de diseño.
7. **Protección de IP (tu preocupación arquitectónica)**: ningún competidor expone el optimizador SIMP/nivel de conjunto en scripting de usuario final — Altair expone PolyNURBS (post-proceso manual) pero no el núcleo de OptiStruct; nTopology expone el grafo de bloques pero el solver interno es una caja negra compilada; PTC/Frustum mantiene TrueSOLID como kernel propietario cerrado incluso tras la adquisición. Esto confirma tu decisión de mantener el algoritmo propietario en C++ compilado y exponer solo orquestación en Python, consistente con el patrón de toda la industria.
8. **Elemento de interpolación (RBE3-like) para reparto de cargas**: el mecanismo descrito en §6.5 (nodo de referencia en el centroide + elemento de interpolación que reparte la carga como promedio ponderado) es exactamente lo que resuelve tu bug de "carga puntual sin `PointLoadCondition3D1N`" de forma generalizable a cargas repartidas sobre múltiples nodos — útil si en el futuro necesitas aplicar una fuerza resultante sobre una cara completa (no solo un punto) sin recurrir a `SF`/superficies de presión.
9. **Convergent Modeling (Siemens NX) como referencia de "mejor UX posible"**: si a futuro te interesa reducir la fricción entre "resultado de optimización" y "modelo editable" (hoy tu roadmap contempla VTK para visualización y Blender para render — ambos de solo lectura/presentación), vale la pena evaluar si Open CASCADE permite una estrategia híbrida similar (mezclar facetas de malla optimizada con B-Rep exacto en el mismo documento) en vez de forzar una reconstrucción NURBS completa cada vez que el usuario quiere iterar manualmente sobre un resultado de TO.

---

## 9. Referencias primarias consultadas

- Patentes Autodesk (level-set generative design y aplicación de BC en malla vóxel): US 11,321,508 B2; US 12,169,398; US 12,223,238; US 12,353,191; US 12,367,643; US 12,488,539; US 12,430,483 (mecanismo detallado de §6.5).
- PTC / Frustum Inc.: cobertura de adquisición (VoxelMatters, 3D Printing Industry, TCT Magazine, Digital Engineering 24/7, DEVELOP3D) y documentación oficial `support.ptc.com` (Generative Design Workflow, Creo).
- Siemens: `siemens.com/en-us/technology/generative-design`, blogs oficiales NX Design sobre Convergent Modeling, CompositesWorld sobre NX Topology Optimizer.
- Svanberg, K. (1987). *The Method of Moving Asymptotes*.
- Sigmund, O. (1997, 2001). Filtros de sensibilidad/densidad para TO.
- Bendsøe, M.P. & Kikuchi, N. (1988). Método de homogeneización, origen de TO moderna.
- Andreassen et al. (2011). *"An efficient 3D topology optimization code written in Matlab"* (top3D, referencia de facto para SIMP+OC/MMA).
- Kim, Han (2009); Wang, Nnaji (2005) — persistent naming problem en B-Rep.
- Documentación pública: Altair (`altair.com/topology-optimization`), nTop (`ntop.com`, `support.ntop.com`), Autodesk (`help.autodesk.com` generative design), Ansys Discovery product pages, SolidWorks/Hawk Ridge/GoEngineer blogs sobre Topology Study.
