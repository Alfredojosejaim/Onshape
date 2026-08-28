# EVIDENCIA — MAPEO CAD FACE → NODOS (PRUEBA OBLIGATORIA)

Generada por `test_cad_face_mapping_evidence.py` sobre el STEP real del proyecto.
Método verificado: **CAD_FACE_MAPPING**.

## Datos de la prueba

- **STEP utilizado:** `cono.step` (real, presente en el proyecto)
- **Número de caras B-Rep del STEP:** 3
- **Número total de nodos de la malla:** 1476
- **Tolerancia de mapeo:** 0.5 (model units, consistente con la escala de malla, elementos ~5 mm)

## Restricción

- **Cara:** disco inferior (z≈0)
- **Face ID:** `face_1`
- **Face index:** 1
- **Nodos seleccionados:** 268
- **Método utilizado:** **CAD_FACE_MAPPING**

## Carga

- **Cara:** disco superior (z≈zmax)
- **Face ID:** `face_2`
- **Face index:** 2
- **Nodos seleccionados:** 108
- **Método utilizado:** **CAD_FACE_MAPPING**

## Criterio de éxito

- **NODOS_SELECCIONADOS (268 restricción, 108 carga) ≠ TODOS_LOS_NODOS (1476):** `True`
- No se aplicó la condición a todos los nodos; cada condición se aplicó exclusivamente a los nodos de su cara real.
- **Resultado FEA (Kratos):** `success = True`

## Nota sobre el fallback

El fallback por coordenadas **no** se activó en este flujo: existía `cad_shape` y un
`location_face_id` / `application_face_id` válido, por lo que se usó exclusivamente el
mapeo geométrico `CAD_FACE_MAPPING`. Cualquier fallo del mapeo se registra ahora con el
bloque estructurado `CAD FACE MAPPING FAILED` (casos A–E).

### Control del fallback (corrección posterior por auditoría)

El fallback por coordenadas **no es automático** cuando se especificó una cara CAD:
solo se ejecuta en el **Caso A** (`NO_FACE_ID`: no hay `cad_shape` ni `location_face_id` / `application_face_id`).

Cuando se especifica un `face_id` pero el mapeo falla:

- **Caso B** (`INVALID_FACE_ID`): identificador no resoluble → se registra el motivo, **fallback NO aplicado**.
- **Caso C** (`OUT_OF_RANGE`): índice fuera del rango de caras → error de datos, **fallback NO aplicado**.
- **Caso D** (`NO_NODES_MATCHED`): cara válida sin nodos → bloque `CAD FACE MAPPING FAILED`, **fallback NO aplicado**.

Esto garantiza la REGLA FINAL: cuando existe una cara CAD válida, la condición FEA se
resuelve mediante esa cara, y un fallo del mapeo **no** se oculta aplicando silenciosamente
coordenadas a una región no intencionada. Verificado por
`test_fallback_not_applied_when_valid_face_fails_mapping` (casos B/C) y
`test_fallback_applied_only_when_no_face_id` (caso A).
