
````markdown
# PROMPT — DISEÑO Y ESPECIFICACIÓN DE LA INTERFAZ GRÁFICA

## 1. OBJETIVO

Diseñar la arquitectura funcional y UX/UI de la aplicación **Topología Optimizada**.

IMPORTANTE:

En esta etapa NO debes implementar la interfaz gráfica.

El objetivo es producir una especificación técnica suficientemente precisa para que posteriormente pueda implementarse sin decisiones ambiguas.

La aplicación es y seguirá siendo:

> STANDALONE, INDEPENDIENTE DE CUALQUIER SOFTWARE CAD EXTERNO.

No utilizar Onshape ni ningún otro CAD como referencia funcional para la interfaz.

---

# 2. DOCUMENTACIÓN OBLIGATORIA

Antes de comenzar:

1. Leer `README.md`.
2. Leer `metodologia.md`.
3. Leer `prompt.md`.
4. Revisar el código actual para comprender:
   - Core.
   - CADModel.
   - adapters.
   - servicios.
   - API existente.
   - flujo actual de importación.
   - mallado existente.
   - FEA existente, si lo hubiera.
   - tests existentes.
5. Leer `RESUMEN_IMPLEMENTACION.md`.

NO asumir que una funcionalidad existe simplemente porque aparece en la documentación.

La especificación debe basarse en el estado real del repositorio.

---

# 3. REGLA ARQUITECTÓNICA PRINCIPAL

La interfaz gráfica debe ser una capa independiente del Core.

Arquitectura conceptual:

GUI
 ↓
Application / API Layer
 ↓
Services
 ↓
Core
 ↓
CAD / Mesh / FEA / TopOpt

La GUI NO debe contener:

- lógica matemática FEA;
- ensamblaje de matrices;
- algoritmo SIMP;
- lógica de mallado;
- lógica CAD;
- lógica de optimización;
- acceso directo a archivos internos del Core.

La GUI solamente debe:

- presentar información;
- recibir interacción del usuario;
- validar entradas de usuario;
- solicitar operaciones a los servicios;
- mostrar estados y resultados.

---

# 4. OBJETIVO DEL PRODUCTO

Diseñar una aplicación que permita al usuario realizar eventualmente este flujo:

IMPORTAR MODELO CAD
        ↓
PREPARAR GEOMETRÍA
        ↓
GENERAR MALLA
        ↓
DEFINIR MATERIAL
        ↓
DEFINIR RESTRICCIONES
        ↓
DEFINIR CARGAS
        ↓
EJECUTAR FEA
        ↓
VISUALIZAR RESULTADOS
        ↓
CONFIGURAR TOPOLOGÍA
        ↓
EJECUTAR OPTIMIZACIÓN
        ↓
VISUALIZAR RESULTADO
        ↓
EXPORTAR MODELO

La interfaz debe diseñarse teniendo este flujo como objetivo final.

---

# 5. NO IMPLEMENTAR FUNCIONES FUTURAS

Si una funcionalidad todavía no existe en el backend:

NO inventar su API.

NO crear código provisional.

NO crear botones funcionales ficticios.

En la especificación se debe clasificar como:

- DISPONIBLE.
- EN DESARROLLO.
- FUTURA.

Por ejemplo:

Si SIMP todavía no existe:

`Optimización Topológica` debe aparecer como funcionalidad futura en la especificación.

---

# 6. ESTRUCTURA DE LA INTERFAZ

Diseñar como mínimo las siguientes áreas:

## A. Pantalla principal

Debe permitir:

- crear/abrir proyecto;
- importar modelo;
- visualizar estado del proyecto;
- acceder a análisis;
- acceder a resultados;
- guardar/exportar.

---

## B. Visor 3D

Debe contemplar:

- modelo CAD;
- navegación orbital;
- zoom;
- pan;
- selección de geometría;
- mostrar/ocultar geometría;
- mostrar/ocultar malla;
- visualización de resultados FEA;
- selección visual de caras cuando sea técnicamente posible;
- modos de visualización.

IMPORTANTE:

No asumir una tecnología concreta sin analizar primero las necesidades reales.

Evaluar opciones existentes y recomendar una.

---

# 7. IMPORTACIÓN CAD

Diseñar el flujo de:

```text
Importar archivo
      ↓
Validar formato
      ↓
Cargar geometría
      ↓
Construir CADModel
      ↓
Mostrar modelo
````

Definir:

* formatos iniciales;
* mensajes de error;
* estados de carga;
* archivos inválidos;
* geometrías inválidas;
* modelo vacío;
* múltiples cuerpos.

No agregar soporte a formatos que el backend actual no pueda procesar.

---

# 8. MALLADO

Diseñar la interfaz para:

* tamaño de elemento;
* calidad;
* refinamiento;
* generación;
* progreso;
* errores;
* estadísticas de malla.

Mostrar, cuando esté disponible:

* número de nodos;
* número de elementos;
* calidad;
* volumen;
* superficies;
* tiempo de generación.

---

# 9. DEFINICIÓN DEL ANÁLISIS FEA

Diseñar el flujo para:

### Material

Como mínimo contemplar:

* módulo de Young;
* coeficiente de Poisson;
* densidad si resulta necesaria.

### Restricciones

Permitir conceptualmente:

* seleccionar caras;
* seleccionar regiones;
* seleccionar entidades geométricas compatibles;
* definir grados de libertad restringidos.

### Cargas

Contemplar:

* fuerza;
* presión;
* dirección;
* magnitud;
* aplicación sobre geometría.

No inventar implementaciones que todavía no existan.

---

# 10. EJECUCIÓN DEL ANÁLISIS

Diseñar un flujo claro:

```text
Configuración válida
       ↓
Preprocesamiento
       ↓
Mallado
       ↓
Aplicación BC
       ↓
Ensamblaje
       ↓
Resolución
       ↓
Postprocesamiento
       ↓
Resultados
```

La interfaz debe contemplar:

* progreso;
* cancelación;
* errores;
* advertencias;
* análisis completado;
* análisis fallido.

---

# 11. RESULTADOS FEA

Diseñar una pantalla de resultados que contemple:

* desplazamiento;
* tensión;
* Von Mises;
* deformación;
* compliancia;
* reacciones;
* estadísticas.

El visor 3D debe poder representar resultados mediante mapas de valores sobre la geometría o malla.

Definir:

* leyenda;
* escala;
* mínimo;
* máximo;
* unidades;
* deformación amplificada;
* posibilidad de cambiar resultado visualizado.

---

# 12. PREPARACIÓN PARA TOPOLOGÍA OPTIMIZADA

Diseñar la interfaz futura para:

* porcentaje de volumen;
* densidad mínima;
* penalización SIMP;
* filtro;
* número máximo de iteraciones;
* criterio de convergencia;
* restricciones.

PERO:

Si estas funciones todavía no existen:

> especificarlas como FUTURAS.

No implementarlas.

---

# 13. EXPORTACIÓN

Diseñar el flujo:

```text
Resultado
   ↓
Seleccionar formato
   ↓
Exportar
```

Determinar qué formatos tienen sentido para:

* geometría;
* malla;
* resultados;
* modelo optimizado.

No asumir que todos estarán disponibles inmediatamente.

---

# 14. UX

Definir específicamente:

* navegación;
* jerarquía visual;
* estados;
* mensajes;
* errores;
* advertencias;
* confirmaciones;
* estados vacíos;
* progreso;
* acciones bloqueadas;
* dependencias entre pasos.

La aplicación debe impedir que el usuario ejecute operaciones inválidas.

Ejemplo:

```text
No existe modelo
→ no permitir mallado

No existe malla
→ no permitir FEA

FEA no ejecutado
→ no mostrar resultados

FEA no validado
→ no permitir iniciar TopOpt
```

---

# 15. UNIDADES

Diseñar un sistema coherente de unidades.

Como mínimo evaluar:

* mm / m;
* N;
* MPa / Pa;
* kg;
* etc.

La GUI debe mostrar siempre las unidades de cada entrada y resultado.

No permitir valores ambiguos.

---

# 16. ESTADO DEL PROYECTO

Diseñar un modelo conceptual de estado:

```text
EMPTY
 ↓
MODEL_IMPORTED
 ↓
MESH_READY
 ↓
ANALYSIS_CONFIGURED
 ↓
FEA_COMPLETED
 ↓
TOPOLOGY_CONFIGURED
 ↓
OPTIMIZATION_RUNNING
 ↓
OPTIMIZATION_COMPLETED
 ↓
EXPORTED
```

No es necesario implementarlo todavía.

Solo definirlo y explicar las transiciones.

---

# 17. ARQUITECTURA DE LA GUI

Evaluar y recomendar la tecnología de interfaz más apropiada considerando:

* Windows;
* aplicación standalone;
* visor 3D;
* rendimiento;
* integración con Python;
* mantenimiento;
* facilidad de distribución;
* posibilidad futura de empaquetar la aplicación;
* comunicación con el backend;
* visualización de mallas y resultados.

Comparar brevemente las alternativas relevantes.

No seleccionar una tecnología simplemente por popularidad.

Justificar técnicamente la elección.

---

# 18. ENTREGABLES

Crear o actualizar únicamente documentación.

El resultado debe incluir:

## `GUI_SPECIFICATION.md`

Debe contener:

1. Objetivo.
2. Arquitectura.
3. Flujo completo del usuario.
4. Mapa de pantallas.
5. Componentes.
6. Visor 3D.
7. Importación.
8. Mallado.
9. Configuración FEA.
10. Resultados.
11. Preparación TopOpt.
12. Exportación.
13. Estados.
14. Validaciones.
15. Errores.
16. Unidades.
17. Tecnología recomendada.
18. Comunicación GUI ↔ backend.
19. Funcionalidades disponibles/futuras.
20. Roadmap de implementación de GUI.

---

# 19. RESUMEN_IMPLEMENTACION.md

Una vez terminada la especificación, actualizar `RESUMEN_IMPLEMENTACION.md`.

Debe registrar:

* qué se analizó;
* qué se decidió;
* qué documentos se crearon/modificaron;
* tecnología recomendada;
* qué NO se implementó;
* estado de la etapa.

No declarar que la GUI está implementada.

Debe indicar claramente:

> GUI ESPECIFICADA — IMPLEMENTACIÓN PENDIENTE.

---

# 20. VALIDACIÓN FINAL

Antes de finalizar comprobar:

* [ ] No se modificó código funcional.
* [ ] No se modificó el Core.
* [ ] No se modificaron adapters.
* [ ] No se modificó FEA.
* [ ] No se modificó TopOpt.
* [ ] No se modificaron dependencias salvo que sea estrictamente necesario para documentación; preferentemente ninguna.
* [ ] No se creó ninguna integración con Onshape.
* [ ] No se creó ninguna dependencia de otro CAD.
* [ ] La GUI está diseñada para funcionar standalone.
* [ ] La especificación distingue claramente funciones existentes y futuras.
* [ ] No se inventaron APIs inexistentes.
* [ ] La documentación es coherente con `README.md`.
* [ ] La documentación respeta `metodologia.md`.

---

# 21. REGLA FINAL

NO PROGRAMAR LA GUI.

NO IMPLEMENTAR COMPONENTES.

NO INSTALAR FRAMEWORKS PARA "PROBAR".

NO MODIFICAR EL MOTOR.

NO IMPLEMENTAR FEA.

NO IMPLEMENTAR SIMP.

NO AGREGAR ONESHAPE.

NO AGREGAR PLUGINS.

NO AGREGAR INTEGRACIONES CAD.

El objetivo exclusivo de esta etapa es:

> **DISEÑAR Y DOCUMENTAR LA INTERFAZ GRÁFICA DE LA APLICACIÓN STANDALONE PARA QUE SU POSTERIOR IMPLEMENTACIÓN SEA DETERMINISTA Y NO DEPENDA DE SUPOSICIONES.**

Al finalizar, entregar un resumen breve de las decisiones tomadas y de los archivos modificados.

```
```
