# Documentación de OptimizationParameters para Kratos 10.4.3

## Fecha: 2026-08-27
## Versión de Kratos: 10.4.3
## Objetivo: Configurar optimización SIMP real usando OptimizationAnalysis

---

## 1. SCHEMAS DE GetDefaultParameters() LEÍDOS DEL CÓDIGO FUENTE

### 1.1 SIMP CONTROL (`simp_control.py`)

```python
default_settings = Kratos.Parameters("""{
    "controlled_model_part_names"       : [""],
    "output_all_fields"                 : true,
    "echo_level"                        : 0,
    "consider_recursive_property_update": false,
    "density_projection_settings"       : {},
    "young_modulus_projection_settings" : {},
    "filter_settings"                   : {},
    "list_of_materials"                 : [
        {
            "density"      : 1.0,
            "young_modulus": 1.0
        }
    ]
}""")
```

**Observaciones:**
- Controla tanto DENSITY como YOUNG_MODULUS
- Usa proyecciones para mapear entre variables físicas y variable de control φ
- Requiere elementos con propiedades específicas (element_specific_properties)
- Soporta filtrado de sensibilidades

---

### 1.2 ALGORITHM GRADIENT PROJECTION (`algorithm_gradient_projection.py`)

```python
default_settings = Kratos.Parameters("""{
    "module"            : "KratosMultiphysics.OptimizationApplication.algorithms",
    "type"              : "PLEASE_PROVIDE_AN_ALGORITHM_CLASS_NAME",
    "objective"         : {},
    "constraints"       : [],
    "controls"          : [],
    "echo_level"        : 0,
    "settings"          : {
        "echo_level"      : 0,
        "line_search"     : {},
        "conv_settings"   : {},
        "linear_solver_settings" : {},
        "correction_size" : 0.0
    }
}""")
```

**Observaciones:**
- `"controls"` es un array de strings con nombres de controles
- Usa MasterControl para coordinar múltiples controles
- Soporta corrección para manejar restricciones activas
- Requiere solver lineal para proyección de restricciones

---

### 1.3 LINEAR STRAIN ENERGY RESPONSE (`linear_strain_energy_response_function.py`)

```python
default_settings = Kratos.Parameters("""{
    "primal_analysis_name"           : "",
    "perturbation_size"              : 1e-8,
    "evaluated_model_part_names"     : [
        "PLEASE_PROVIDE_A_MODEL_PART_NAME"
    ]
}""")
```

**Observaciones:**
- Calcula compliance (energía de deformación lineal)
- Requiere un análisis primal previo (StructuralMechanicsAnalysis)
- Soporta sensibilidades para: SHAPE, YOUNG_MODULUS, THICKNESS, POISSON_RATIO
- NOTA: No soporta DENSITY directamente (esto es manejado por SIMP control)

---

### 1.4 MASS RESPONSE (`mass_response_function.py`)

```python
default_settings = Kratos.Parameters("""{
    "evaluated_model_part_names"     : [
        "PLEASE_PROVIDE_A_MODEL_PART_NAME"
    ],
    "perturbation_size": 1e-6
}""")
```

**Observaciones:**
- Calcula masa total del model part
- Soporta sensibilidades para: SHAPE, DENSITY, THICKNESS, CROSS_AREA
- Útil como restricción de volumen en optimización topológica

---

### 1.5 KRATOS ANALYSIS EXECUTION POLICY (`kratos_analysis_execution_policy.py`)

```python
default_settings = Kratos.Parameters("""{
    "model_part_names" : [],
    "analysis_module"  : "KratosMultiphysics",
    "analysis_type"    : "",
    "analysis_settings": {},
    "analysis_output_settings": {
             "nodal_solution_step_data_variables"         : [],
             "nodal_data_value_variables"                 : [],
             "element_data_value_variables"               : [],
             "element_properties_value_variables"         : [],
             "element_integration_point_value_variables"  : [],
             "condition_data_value_variables"             : [],
             "condition_properties_value_variables"       : [],
             "condition_integration_point_value_variables": []
    }
}""")
```

**Observaciones:**
- Ejecuta cualquier AnalysisStage de Kratos como sub-análisis
- `"analysis_settings"` debe contener el JSON completo del análisis (ej: ProjectParameters.json)
- `"analysis_output_settings"` controla qué variables se exportan al OptimizationProblem
- **IMPORTANTE:** Probablemente requiere `"input_type": "use_input_model_part"` en el ProjectParameters.json para evitar duplicación de malla

---

### 1.6 MDPA MODEL PART CONTROLLER (`mdpa_model_part_controller.py`)

```python
default_settings = Kratos.Parameters("""{
    "model_part_name": "",
    "input_filename" : "",
    "domain_size"    : -1,
    "read_data"      : false
}""")
```

**Observaciones:**
- Lee archivos .mdpa (formato nativo de Kratos)
- `"domain_size"` debe ser 1, 2 o 3
- `"read_data"` controla si se leen solo la malla o también datos (condiciones, propiedades, etc.)

---

### 1.7 STANDARDIZED OBJECTIVE (`standardized_objective.py`)

```python
default_parameters = Kratos.Parameters("""{
    "response_expression": "",
    "type"               : "",
    "scaling"            : 1.0
}""")
```

**Observaciones:**
- Usa `"response_expression"` en lugar de `"response_name"` (con backward compatibility)
- `"type"` soporta: `"minimization"`, `"maximization"`
- `"scaling"` debe ser siempre positivo
- Si `"type"` es `"maximization"`, aplica scaling negativo internamente

---

### 1.8 STANDARDIZED CONSTRAINT (`standardized_constraint.py`)

```python
default_parameters = Kratos.Parameters("""{
    "response_expression" : "",
    "type"                : "",
    "scaling"             : 1.0,
    "violation_scaling"   : 1.0,
    "scaled_ref_value"    : "initial_value"
}""")
```

**Observaciones:**
- Usa `"response_expression"` en lugar de `"response_name"` (con backward compatibility)
- `"type"` soporta: `"="`, `"<"`, `"<="`, `">"`, `">="`
- `"scaled_ref_value"` puede ser: `"initial_value"` o un valor numérico específico
- `"violation_scaling"` controla la penalización de violaciones
- Para `"<="` y `"="`: scaling positivo
- Para `">="`: scaling negativo (invierte el problema)

---

### 1.9 EXPLICIT FILTER (`explicit_filter.py`)

```python
default_parameters = Kratos.Parameters("""{
    "filter_type"               : "explicit_filter",
    "node_cloud_mesh"           : false,
    "filter_function_type"      : "linear",
    "max_items_in_bucket"       : 10,
    "echo_level"                : 0,
    "store_filter_matrix"       : false,
    "filter_radius_settings":{
        "filter_radius_type": "constant",
        "filter_radius"     : 0.2
    },
    "filtering_boundary_conditions": {
        "damping_type"              : "nearest_entity",
        "damping_function_type"     : "cosine",
        "damped_model_part_settings": {}
    }
}""")
```

**Observaciones:**
- Mi suposición original de `"type": "explicit"` era incorrecta
- `"filter_type"` debe ser `"explicit_filter"`
- `"filter_radius"` está anidado dentro de `"filter_radius_settings"`
- Tiene configuración de boundary conditions para damping

---

## 2. JSON COMPLETO CORREGIDO

Basado en los schemas anteriores, aquí está el `OptimizationParameters.json` corregido:

```json
{
    "problem_data": {
        "echo_level": 1
    },
    "model_parts": [
        {
            "model_part_name": "Structure",
            "settings": {
                "type": "mdpa_model_part_controller",
                "model_part_name": "Structure",
                "input_filename": "model/cantilever_beam.mdpa",
                "domain_size": 3,
                "read_data": true
            }
        }
    ],
    "analyses": [
        {
            "name": "structural_mechanics_analysis",
            "settings": {
                "type": "kratos_analysis_execution_policy",
                "model_part_names": ["Structure"],
                "analysis_module": "KratosMultiphysics.StructuralMechanicsApplication",
                "analysis_type": "StructuralMechanicsAnalysis",
                "analysis_settings": {},
                "analysis_output_settings": {
                    "element_properties_value_variables": ["YOUNG_MODULUS", "DENSITY"]
                }
            }
        }
    ],
    "responses": [
        {
            "name": "compliance",
            "settings": {
                "type": "linear_strain_energy",
                "primal_analysis_name": "structural_mechanics_analysis",
                "perturbation_size": 1e-8,
                "evaluated_model_part_names": ["Structure"]
            }
        },
        {
            "name": "mass",
            "settings": {
                "type": "mass",
                "perturbation_size": 1e-6,
                "evaluated_model_part_names": ["Structure"]
            }
        }
    ],
    "controls": [
        {
            "name": "simp_density_control",
            "settings": {
                "type": "simp",
                "controlled_model_part_names": ["Structure"],
                "list_of_materials": [
                    {
                        "density": 0.001,
                        "young_modulus": 68.9e6
                    },
                    {
                        "density": 1.0,
                        "young_modulus": 68.9e9
                    }
                ],
                "filter_settings": {
                    "filter_type": "explicit_filter",
                    "filter_radius_settings": {
                        "filter_radius_type": "constant",
                        "filter_radius": 1.5
                    }
                }
            }
        }
    ],
    "algorithm_settings": {
        "module": "KratosMultiphysics.OptimizationApplication.algorithms",
        "type": "algorithm_gradient_projection",
        "objective": {
            "response_expression": "compliance",
            "type": "minimization",
            "scaling": 1.0
        },
        "constraints": [
            {
                "response_expression": "mass",
                "type": "<=",
                "scaling": 1.0,
                "violation_scaling": 1.0,
                "scaled_ref_value": 0.4
            }
        ],
        "controls": ["simp_density_control"],
        "echo_level": 1,
        "settings": {
            "echo_level": 1,
            "line_search": {},
            "conv_settings": {
                "max_iter": 50
            },
            "linear_solver_settings": {
                "solver_type": "LinearSolversApplication.dense_col_piv_householder_qr"
            },
            "correction_size": 0.0
        }
    },
    "processes": {
        "kratos_processes": {},
        "optimization_data_processes": {}
    }
}
```

---

## 3. CORRECCIONES REALIZADAS

### 3.1 Objective
- ✅ Cambié `"response_name"` a `"response_expression"`
- ✅ Agregué `"scaling": 1.0`

### 3.2 Constraint
- ✅ Cambié `"response_name"` a `"response_expression"`
- ✅ Agregué parámetros completos: `"scaling"`, `"violation_scaling"`, `"scaled_ref_value"`
- ✅ Usé `"scaled_ref_value": 0.4` en lugar de `"bound"` (formato correcto para valor específico)
- ✅ Usé `"type": "<="` (formato correcto para restricción de volumen)

### 3.3 Filter
- ✅ Corregí `"type"` a `"filter_type": "explicit_filter"`
- ✅ Anidé `"filter_radius"` dentro de `"filter_radius_settings"`
- ✅ Agregué `"filter_radius_type": "constant"`

---

## 4. PENDIENTES

### 4.1 ProjectParameters.json (PRIORIDAD ALTA)
- **PENDIENTE:** Necesito el `ProjectParameters.json` actual para integrarlo en `analysis_settings`
- **IMPORTANTE:** Verificar si necesita `"input_type": "use_input_model_part"` en `model_import_settings` para evitar duplicación de malla cuando el `KratosAnalysisExecutionPolicy` invoque el `StructuralMechanicsAnalysis`

### 4.2 Conversión de malla (PRIORIDAD BAJA)
- **PENDIENTE:** Conversión `.msh` → `.mdpa` usando herramientas de Kratos
- El `MdpaModelPartController` solo lee archivos `.mdpa`, no `.msh`

---

## 5. REFERENCIAS

Todos los schemas fueron extraídos directamente de:
- `C:\Users\alfre\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\KratosMultiphysics\OptimizationApplication\`

Archivos revisados:
- `controls/material/simp_control.py`
- `algorithms/algorithm_gradient_projection.py`
- `algorithms/standardized_objective.py`
- `algorithms/standardized_constraint.py`
- `responses/linear_strain_energy_response_function.py`
- `responses/mass_response_function.py`
- `execution_policies/kratos_analysis_execution_policy.py`
- `model_part_controllers/mdpa_model_part_controller.py`
- `filtering/explicit_filter.py`
- `optimization_analysis.py`

---

## 6. ESTADO

✅ **COMPLETADO:** Recopilación de schemas GetDefaultParameters()
✅ **COMPLETADO:** JSON corregido basado en schemas reales
⏳ **PENDIENTE:** Integración de ProjectParameters.json
⏳ **PENDIENTE:** Conversión de malla .msh → .mdpa