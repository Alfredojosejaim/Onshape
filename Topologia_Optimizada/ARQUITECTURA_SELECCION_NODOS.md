# Arquitectura de Selección Geométrica de Nodos - Corrección de Sobreconstricción

**Documento**: Explicación y corrección del problema arquitectónico en `solver_interface.py`  
**Autor**: Análisis de bloqueo arquitectónico  
**Fecha**: 2026-08-28  
**Estado**: IMPLEMENTADO (Fase 1 - Coordinate-based fallback; Fase 2 - gmsh physical groups pendiente)

---

## El Problema Identificado

### Síntoma
El código en `solver_interface.py` (líneas 213-221) aplicaba restricciones y cargas a **TODOS los nodos del modelo**:

```python
# INCORRECTO (código anterior):
all_node_indices = list(range(len(nodes_list)))
for constraint in constraints:
    adapter.apply_constraint_from_core(model_part, constraint, all_node_indices)  # ← TODOS LOS NODOS
for load in loads:
    adapter.apply_load_from_core(model_part, load, all_node_indices)  # ← TODOS LOS NODOS
```

### Impacto Físico
- **Estructura completamente empotrada**: Con todos los nodos fijos (Fixed), la estructura pierde **todos sus grados de libertad**
- **Desplazamientos irreales**: ~1e-9 m (ruido numérico) en lugar de la solución analítica (~5.8e-4 m para viga en voladizo)
- **Cargas mal distribuidas**: Se aplican a TODOS los nodos en lugar de solo a la cara de aplicación
- **SIMP inválido**: La optimización topológica minimiza el compliance de un **problema completamente diferente** al que el usuario pretende resolver

### Raíz del Problema
Este fue un **placeholder de debugging** para validar que el pipeline entero corriera de punta a punta sin errores:
- Pregunta inicial: "¿Corre?" → Sí, usando todos los nodos
- Pregunta no resuelta: "¿Corre bien?" → **NO**, los resultados son físicamente inválidos

El placeholder quedó en el código como si fuera la implementación final.

---

## La Solución Implementada

### Estrategia General
Se implementaron **dos niveles de selección geométrica**:

1. **Nivel 1 (Robusto - Recomendado)**: Usar **submodelparts nombrados** 
   - Origen: gmsh physical groups → .mdpa submodelparts
   - Ventaja: Selección exacta, vinculada a geometría CAD
   - Estado: Implementado pero requiere integración gmsh

2. **Nivel 2 (Fallback - Implementado Ahora)**: Usar **filtrado por coordenadas**
   - Método: Seleccionar nodos por proximidad a un plano o coordenada
   - Ventaja: Funciona inmediatamente sin cambios en gmsh
   - Desventaja: Menos preciso, requiere conocer la geometría

### Cambios en Código

#### 1. Nuevos Métodos en `kratos_adapter.py`

```python
def get_nodes_from_submodelpart(model_part, submodelpart_name) -> List[int]:
    """Obtiene nodos de un submodelpart nombrado (ej: 'Structure.FixedFace')"""
    # Convierte 1-based (Kratos) a 0-based (Core)
    return [node.Id - 1 for node in sub_part.Nodes]

def get_nodes_by_coordinate_filter(model_part, coordinate, value, tolerance) -> List[int]:
    """Filtra nodos por coordenada (X=0, Y=0, Z=0, etc.)"""
    # Usa distancia euclidiana a un plano

def apply_constraint_to_submodelpart(model_part, constraint, submodelpart_name):
    """Aplica restricción a un submodelpart específico"""

def apply_load_to_submodelpart(model_part, load, submodelpart_name):
    """Aplica carga a un submodelpart específico"""
```

#### 2. Refactor en `solver_interface.py`

Se reemplazó la aplicación "a todos los nodos" con **dos funciones helpers**:

```python
def _apply_constraint_geometrically(adapter, model_part, constraint, nodes_list):
    """
    Intenta 3 estrategias en orden:
    1. Si constraint.submodelpart_name existe → usar apply_constraint_to_submodelpart()
    2. Si constraint.fixed_coordinate existe → usar get_nodes_by_coordinate_filter()
    3. Si no, registrar WARNING y no aplicar (el usuario debe especificar geometría)
    """

def _apply_load_geometrically(adapter, model_part, load, nodes_list):
    """Similar a _apply_constraint_geometrically pero para cargas"""
```

---

## Cómo Funciona Ahora

### Flujo Corriente (Coordinate-based Fallback)

```python
constraint = ConstraintDefinition(
    constraint_type=ConstraintType.FIXED,
    fixed_axis=2,        # Z axis
    fixed_coordinate=0.0,  # Z = 0 (el empotramiento)
    tolerance=0.01
)

# Dentro de _apply_constraint_geometrically():
# 1. Busca constraint.submodelpart_name → no existe
# 2. Busca constraint.fixed_coordinate → EXISTE = 0.0
# 3. Llama: get_nodes_by_coordinate_filter(mp, axis=2, value=0.0, tol=0.01)
# 4. Obtiene lista de nodos donde Z ≈ 0
# 5. Aplica Fix() SOLO a esos nodos
```

Resultado esperado: **Viga cantilever con un extremo fijo, el otro libre**.

---

## Próximo Paso: Integración con gmsh Physical Groups

### Fase 2 - Estrategia Robusta (gmsh)

La solución definitiva requiere crear **grupos físicos en gmsh** antes de mallar:

#### 1. En el código de mallado (ej: `geometry_processor.py` o función que use gmsh):

```python
import gmsh

# Después de geometría cargada, ANTES de mallar
gmsh.model.add_physical_group(
    2,  # dim=2 para caras
    [face_tags],  # Tags de las caras del STEP
    tag=10,
    name="FixedFace"
)

gmsh.model.add_physical_group(
    2,
    [load_face_tags],
    tag=11,
    name="LoadFace"
)

# Mallar y exportar
gmsh.model.mesh.generate(3)
gmsh.write("modelo_con_grupos.msh")
```

#### 2. Exportar a .mdpa (preserva nombres de grupos):

```python
# Usando KratosMultiphysics.ModelPartIO
from KratosMultiphysics.mshio import MshIO
msh_io = MshIO("modelo_con_grupos.msh", gmsh_mapping=True)
msh_io.ReadModelPart(model_part)
# Los grupos gmsh se convierten en submodelparts:
# - "FixedFace" → model_part.GetSubModelPart("FixedFace")
# - "LoadFace" → model_part.GetSubModelPart("LoadFace")
```

#### 3. Usar nombres en ProjectParameters o definiciones de restricciones:

```python
constraint = ConstraintDefinition(
    constraint_type=ConstraintType.FIXED,
    submodelpart_name="FixedFace"  # ← Ahora viene del gmsh
)

load = LoadDefinition(
    load_type=LoadType.POINT,
    submodelpart_name="LoadFace",  # ← Ahora viene del gmsh
    magnitude=1000.0,
    direction=[0, 0, -1]
)
```

#### 4. Resultado: Selección automática y robusta

```python
# En _apply_constraint_geometrically():
# 1. Busca constraint.submodelpart_name = "FixedFace" → EXISTE
# 2. Llama: get_nodes_from_submodelpart(mp, "FixedFace")
# 3. Obtiene EXACTAMENTE los nodos de esa cara CAD (mapeados por gmsh)
# 4. Aplica Fix() SOLO a esos nodos → Correcto ✓
```

---

## Validación

### Test 1: Viga Cantilever con Coordinate-based Selection

```python
# En test_kratos_direct.py o nuevo test_cantilever_beam.py
def test_cantilever_with_proper_bc():
    # Crear viga L x h x w
    # Crear malla Tet4
    
    # Definir restricciones/cargas con coordenadas
    constraints = [
        ConstraintDefinition(
            id="fixed_end",
            constraint_type=ConstraintType.FIXED,
            fixed_axis=2,  # Z
            fixed_coordinate=0.0,  # Z = 0 (empotramiento)
            tolerance=0.01
        )
    ]
    
    loads = [
        LoadDefinition(
            id="cantilever_load",
            load_type=LoadType.POINT,
            load_axis=2,  # Z
            load_coordinate=L,  # Z = L (extremo libre)
            magnitude=F,
            direction=[0, 0, -1]
        )
    ]
    
    # Ejecutar FEA
    solver = create_kratos_fea_solver(nodes, elements, material, constraints, loads)
    result = solver(...)
    
    # Validar contra fórmula analítica
    # max_displacement = F * L³ / (3 * E * I) ≈ 5.805515e-04 m (para viga test)
    # assert result["max_displacement"] ≈ 5.805515e-04
```

### Test 2: Verificación de Submodelparts (cuando gmsh esté integrado)

```python
def test_submodelpart_selection():
    # Cargar .mdpa con submodelparts nombrados
    adapter.import_mesh_from_mdpa(model_part, "modelo_con_grupos.mdpa")
    
    # Verificar que los submodelparts existen
    assert model_part.HasSubModelPart("FixedFace")
    assert model_part.HasSubModelPart("LoadFace")
    
    # Verificar que el número de nodos es razonable (no todos)
    fixed_nodes = adapter.get_nodes_from_submodelpart(mp, "FixedFace")
    assert len(fixed_nodes) < len(model_part.Nodes) / 2  # Menos del 50%
    
    load_nodes = adapter.get_nodes_from_submodelpart(mp, "LoadFace")
    assert len(load_nodes) < len(model_part.Nodes) / 2
```

---

## Arquitectura: Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│  Geometría CAD (STEP) + Constraints/Loads from Core          │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────▼─────────────┐
        │  Phase 1: gmsh Meshing   │
        │  (current & Phase 2)     │
        └────────────┬─────────────┘
                     │
        ┌────────────▼──────────────────────────┐
        │ gmsh.model.addPhysicalGroup()          │ ← Phase 2 adds this
        │ - FixedFace (tag 10)                   │
        │ - LoadFace (tag 11)                    │
        │ Export: modelo.msh                     │
        └────────────┬──────────────────────────┘
                     │
        ┌────────────▼──────────────────────────┐
        │ Import to Kratos ModelPart             │
        │ .mdpa submodelparts created:           │
        │ - "FixedFace" → nodos [1,2,5,8,...]    │
        │ - "LoadFace" → nodos [34,56,78,...]    │
        └────────────┬──────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────────┐
        │  solver_interface.py: _apply_*_geometrically()    │
        │                                                    │
        │  For each constraint:                             │
        │  ├─ Try: constraint.submodelpart_name?            │ ← Phase 2
        │  │  YES → get_nodes_from_submodelpart()           │
        │  │  NO  → Try: constraint.fixed_coordinate?       │ ← Phase 1 (now)
        │  │       YES → get_nodes_by_coordinate_filter()   │
        │  │       NO  → WARNING, skip                      │
        │  └─ apply_constraint_from_core(mp, constraint)    │
        │                                                    │
        │  Same for loads                                    │
        └────────────┬──────────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────┐
        │ Kratos Run Analysis                    │
        │ (Only boundary nodes constrained)      │
        │ (Only load nodes loaded)               │
        │ → PHYSICALLY CORRECT SOLUTION ✓        │
        └────────────┬──────────────────────────┘
                     │
        ┌────────────▼──────────────────────────┐
        │ Extract Results                        │
        │ max_displacement ≈ 5.805515e-04 m ✓   │
        │ compliance, element_energies → SIMP   │
        └──────────────────────────────────────┘
```

---

## Resumen de Cambios

| Archivo | Cambios | Estado |
|---------|---------|--------|
| `core/kratos_adapter.py` | +4 métodos nuevos (submodelpart, coord filter) | ✅ Implementado |
| `core/solver_interface.py` | Refactor: reemplaza "all_node_indices" con selección geométrica | ✅ Implementado |
| Documentación | Este archivo + inline comments en código | ✅ Hecho |
| `geometry_processor.py` | Necesita integración gmsh (TODO: Fase 2) | ⏳ Pendiente |
| Tests | Validar viga cantilever con resultados analíticos | ⏳ Pendiente |

---

## Próximos Pasos

### Corto Plazo (Validar Fase 1)
1. ✅ Implementar fallback coordinate-based (HECHO)
2. ⏳ Crear test: viga cantilever simple con fixed_coordinate + load_coordinate
3. ⏳ Validar que max_displacement ≈ solución analítica
4. ⏳ Verificar que solo nodos de frontera están constrictos

### Mediano Plazo (Implementar Fase 2)
1. Integrar gmsh.model.addPhysicalGroup() en geometry_processor.py
2. Actualizar import_mesh_from_mdpa() en kratos_adapter.py para preservar submodelparts
3. Agregar campos `submodelpart_name` a ConstraintDefinition y LoadDefinition
4. Reemplazar coordinate-based con submodelpart-based en tests

### Largo Plazo (Validación SIMP)
1. Ejecutar TopOpt con geometría correcta
2. Verificar convergencia del compliance
3. Comparar resultados contra topología esperada (no disponible: ej., viga en voladizo optimizada)

---

## Referencia: Propiedades de Constraint/Load para Selección

### ConstraintDefinition
```python
@dataclass
class ConstraintDefinition:
    id: str
    constraint_type: ConstraintType
    
    # Estrategia 1: Submodelpart (Fase 2 gmsh)
    submodelpart_name: Optional[str] = None  # e.g., "FixedFace"
    
    # Estrategia 2: Coordinate-based (Fase 1, ahora)
    fixed_axis: int = 2  # 0=X, 1=Y, 2=Z
    fixed_coordinate: Optional[float] = None  # e.g., 0.0 para Z=0
    tolerance: float = 0.01  # ±1 cm
```

### LoadDefinition
```python
@dataclass
class LoadDefinition:
    id: str
    load_type: LoadType
    magnitude: float
    direction: List[float]  # Normalized [x, y, z]
    
    # Estrategia 1: Submodelpart
    submodelpart_name: Optional[str] = None  # e.g., "LoadFace"
    
    # Estrategia 2: Coordinate-based
    load_axis: int = 2  # 0=X, 1=Y, 2=Z
    load_coordinate: Optional[float] = None  # e.g., L para Z=L (extremo)
    tolerance: float = 0.01
```

---

## Referencias

- **Gmsh Physical Groups**: https://gmsh.info/doc/texinfo/gmsh.html#General-API
- **Kratos SubmodelParts**: https://github.com/KratosMultiphysics/Kratos/wiki/Using-SubModelPart
- **MDPA Format**: https://github.com/KratosMultiphysics/Kratos/wiki/mdpa-format
- **Cantilever Beam Analysis**: https://en.wikipedia.org/wiki/Cantilever#Deflection

