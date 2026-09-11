# Árbol de Operaciones y viewport único multicuerpo

El panel **Árbol de Operaciones** lista en plano todos los cuerpos importados
(sólidos y mallas), sin distinción de archivo. El viewport central muestra
todos los cuerpos a la vez, cada uno con ojo ver/ocultar propio.

## Flujo de datos

```
STEP (disco) → core vendorado (backend/) → Api.getMeshPreview / getSolids
  → surfaceByFile / solidsByFile (App.tsx, clave: filename)
  → bodies: ViewBody[] → CadViewport (un mesh three.js por cuerpo)
```

- `surfaceByFile`: teselación por archivo. Es determinista, así que el caché
  vale aunque el core cambie de modelo activo al re-importar.
- `ViewBody { key, filename, solidId, faceIndices }`: `faceIndices` son los
  `face_index` globales del sólido (`list_solids` vendorado, identidad OCC
  `IsSame`); `null` = archivo entero.
- `solidTriangles()` (`src/lib/faces.ts`): triángulos globales del cuerpo a
  partir de sus caras + rangos `face_triangles`. Cada mesh guarda
  `userData.triMap` (triángulo local → global) para el picking.
- Picking y highlight naranja actúan solo sobre cuerpos **visibles del modelo
  activo**; clic en vacío o hueco conserva la selección (como el desktop).
- La fila MALLA muestra el wireframe de la teselación de su archivo (global
  `showMesh` + ojo propio).

## Selección de caras (copia del desktop, solo lectura)

`src/lib/faces.ts` porta `Topologia_Optimizada` sin modificarlo:

| Función | Origen |
|---|---|
| `parseFaceId` | `core/boundary.py::_FACE_ID_UNIFIED_RE` |
| `triangleToFace` | `desktop/viewport/scene.py::face_index_for_cell` |
| `toggleFace` | `desktop/viewport/software_viewport.py` |
| `faceEntityRef` / `selectionSet` | `core/cad_entity.py` |
| `buildConditionJson` | `core/conditions.py::to_dict()` (load/elasticity/protected_region) |

Con herramienta carga/fijación/preservada, el clic crea/actualiza la condición
del árbol y la envía a `createCondition` con id estable (sobrescribe).

## Limitaciones honestas (fallbacks)

1. **Sólido sin `face_indices`** (caché antigua o subida local): ese archivo se
   renderiza **entero, sin split** (`solidTriangles()` devuelve `null`). Nunca
   se muestran agujeros.
2. **Teselado diezmado**: el backend diezma arrays grandes (`_clean`). Si los
   rangos no cubren todos los triángulos (`rangesCover()` falso), el archivo va
   entero, **sin picking por cara**, y el badge avisa
   ("Caras no disponibles (teselado diezmado)").
3. **Archivo sin superficie en caché**: no se renderiza hasta importarse.
4. **Keep-out**: queda local en la UI; en el core la obstrucción referencia
   **cuerpos**, no caras, así que no se envía a `createCondition`.
5. **Malla volumétrica**: solo existe en el modelo activo del core (se limpia
   al re-importar); el caché `meshByFile` se autocorrige al activar.
6. **Core vendorado** (`backend/core|desktop|adapters|services`): copia del
   2026-09-11. Re-sincronizar según `backend/CORE_VENDORADO.txt`. El proyecto
   origen no se modifica.

## Reversibilidad

Bloques marcados `FACES-`, `MULTI-`, `MULTI-VIEW-`, `NAV-VIEW-`, `SOLIDS-`,
`UI-CLEAN-`, `CHUNK-SPLIT-`, `SELF-CONTAINED-`: borrar el bloque + sus props
para volver al estado anterior (detalle en cada marcador).
