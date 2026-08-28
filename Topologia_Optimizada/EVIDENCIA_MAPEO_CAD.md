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
bloque estructurado `CAD FACE MAPPING FAILED` antes de permitir el fallback (casos A–E).
