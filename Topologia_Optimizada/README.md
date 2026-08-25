TOPOLOGÍA OPTIMIZADA

Especificación maestra del proyecto

---

1. VISIÓN DEL PROYECTO

Topología Optimizada es una aplicación independiente de análisis y optimización topológica orientada a modelos CAD 3D.

El objetivo principal del proyecto es desarrollar una aplicación CAD/CAE capaz de recibir una geometría CAD, preparar un análisis estructural, ejecutar un análisis por elementos finitos (FEA) y posteriormente realizar optimización topológica mediante métodos como SIMP.

La aplicación debe ser completamente funcional de forma independiente de cualquier plataforma CAD externa.

La primera vía de entrada será mediante archivos CAD, inicialmente STEP.

La integración con plataformas externas como Onshape se considera una extensión futura y no debe ser una dependencia del núcleo de la aplicación.

---

2. OBJETIVO PRINCIPAL

El objetivo es conseguir un flujo completo y verificable:

ARCHIVO CAD
    │
    ▼
IMPORTACIÓN
    │
    ▼
MODELO CAD INTERNO
    │
    ▼
VISUALIZACIÓN 3D
    │
    ▼
DEFINICIÓN DEL ESTUDIO
    │
    ├── Design Space
    ├── Keep-out
    ├── Material
    ├── Cargas
    └── Restricciones
    │
    ▼
MALLADO FEM
    │
    ▼
MALLA TET4
    │
    ▼
ANÁLISIS FEA
    │
    ├── Desplazamientos
    ├── Deformaciones
    ├── Tensiones
    ├── Reacciones
    └── Compliance
    │
    ▼
OPTIMIZACIÓN TOPOLÓGICA
    │
    ▼
RESULTADO OPTIMIZADO
    │
    ▼
VISUALIZACIÓN Y VALIDACIÓN
    │
    ▼
EXPORTACIÓN

Este flujo debe poder ejecutarse sin conexión con Onshape.

---

3. PRINCIPIO ARQUITECTÓNICO FUNDAMENTAL

La arquitectura del proyecto debe seguir el principio:

«CAD-AGNOSTIC CORE + CAD ADAPTERS + FUTURE CONNECTORS»

El núcleo matemático y de procesamiento no debe depender de ningún CAD específico.

La aplicación debe poder trabajar con un modelo procedente de:

STEP
  ↓
CAD Adapter
  ↓
Core

y en el futuro:

Onshape
  ↓
Connector
  ↓
CAD Adapter / CADModel
  ↓
Core

La misma lógica deberá poder reutilizarse posteriormente con otras plataformas CAD.

---

4. PRIORIDAD ACTUAL DEL PROYECTO

La prioridad absoluta es:

«Construir una aplicación standalone técnicamente funcional.»

Actualmente NO son prioridad:

- integración con Onshape;
- plugins;
- extensiones para CAD;
- sincronización bidireccional;
- modificación del Feature Tree de Onshape;
- soporte para múltiples plataformas CAD.

Estas funcionalidades podrán desarrollarse posteriormente.

La aplicación debe tener valor y utilidad incluso si nunca se instala un plugin.

---

5. ARQUITECTURA GENERAL

La aplicación se dividirá conceptualmente en las siguientes capas:

┌─────────────────────────────────────┐
│             FRONTEND                │
│       Interfaz + Visor 3D           │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│           APPLICATION               │
│ API + Servicios + Estudios + Jobs   │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│               CORE                  │
│                                     │
│ Geometría                           │
│ Malla                               │
│ Materiales                          │
│ Cargas                              │
│ Restricciones                       │
│ FEA                                 │
│ Optimización                        │
└──────────────────┬──────────────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
     CAD ADAPTERS       FUTURE CONNECTORS
          │                 │
        STEP             Onshape
        IGES             Otros CAD
        ...              ...

---

6. CORE

El Core constituye el núcleo técnico del proyecto.

Debe ser completamente independiente del origen de la geometría.

Debe contener las funcionalidades relacionadas con:

- modelo CAD interno;
- geometría;
- malla;
- materiales;
- cargas;
- restricciones;
- condiciones de frontera;
- análisis FEA;
- resultados;
- optimización topológica.

Regla estricta

Ningún módulo del Core puede depender directamente de:

- Onshape;
- OAuth;
- API REST de Onshape;
- Document ID;
- Workspace ID;
- Element ID;
- App Extensions;
- APIs específicas de otros CAD.

El Core debe poder probarse y ejecutarse sin conexión a ninguna plataforma CAD externa.

---

7. MODELO CAD INTERNO

La aplicación debe utilizar una representación interna independiente del CAD de origen.

Conceptualmente:

CADModel
├── model_id
├── units
├── solids
├── faces
├── edges
├── vertices
└── metadata

Las entidades deben disponer de identificadores internos propios.

No se deben utilizar identificadores específicos de Onshape como IDs internos del Core.

El origen de una entidad podrá conservarse como metadata, pero nunca debe convertirse en una dependencia arquitectónica.

---

8. IMPORTACIÓN CAD

La primera entrada soportada oficialmente será:

STEP

El flujo será:

Archivo STEP
     ↓
STEP Adapter
     ↓
Validación
     ↓
CADModel
     ↓
Core

La importación debe validar como mínimo:

- existencia del archivo;
- formato;
- integridad;
- unidades;
- existencia de sólidos;
- geometría válida;
- errores de importación.

No se deben utilizar geometrías ficticias para reemplazar una geometría CAD real.

Las geometrías sintéticas únicamente podrán utilizarse en tests controlados.

---

9. VISOR 3D

La aplicación debe disponer de un visor 3D independiente.

Debe permitir como mínimo:

- rotación;
- zoom;
- desplazamiento;
- centrado;
- ajuste a pantalla;
- inspección desde diferentes orientaciones;
- selección de entidades cuando la funcionalidad correspondiente esté implementada.

El modelo mostrado debe proceder del CAD importado.

El visor debe funcionar sin conexión con Onshape.

---

10. DEFINICIÓN DEL ESTUDIO

El usuario debe poder crear un estudio de análisis sobre el modelo importado.

Un estudio deberá poder representar conceptualmente:

Study
├── CADModel
├── Design Space
├── Keep-out
├── Material
├── Loads
├── Constraints
├── Mesh
├── FEA configuration
└── Optimization configuration

La implementación puede evolucionar progresivamente, pero la arquitectura debe evitar mezclar estas responsabilidades.

---

11. DESIGN SPACE

El Design Space representa el volumen de material sobre el cual puede actuar la optimización.

Debe estar asociado a geometría real del modelo.

Conceptualmente:

CADModel
   ↓
Design Space
   ↓
Región optimizable

No debe asumirse que todo el modelo CAD constituye automáticamente el Design Space si el estudio permite definir regiones diferentes.

---

12. KEEP-OUT

Los Keep-out representan regiones que deben permanecer protegidas durante la optimización.

Pueden existir:

- cero Keep-out;
- uno;
- múltiples.

El sistema debe conservar la relación entre la región CAD y la región correspondiente de la malla.

CAD Keep-out
     ↓
Malla
     ↓
Elementos protegidos
     ↓
Restricción TopOpt

---

13. MALLADO FEM

La aplicación debe generar una malla volumétrica apta para análisis estructural 3D.

La primera implementación objetivo será una malla de:

Tetraedros lineales de 4 nodos — Tet4.

La herramienta de mallado deberá seleccionarse y validarse técnicamente.

La solución prevista para el pipeline principal es:

Gmsh + OpenCASCADE

pero su utilización definitiva deberá validarse mediante pruebas reales.

La malla debe permitir identificar:

- nodos;
- elementos;
- conectividad;
- superficies;
- regiones;
- correspondencia CAD → FEM.

No se considera válido un mallador provisional como solución FEM definitiva.

---

14. MAPEO CAD → FEM

Debe existir una relación verificable entre:

Entidad CAD
     ↓
Superficie / región FEM
     ↓
Nodos / elementos

Esto será necesario para aplicar:

- cargas;
- restricciones;
- Design Space;
- Keep-out.

El sistema deberá utilizar identificadores topológicos o geométricos robustos.

La proximidad espacial no debe utilizarse como único mecanismo cuando pueda generar ambigüedades.

---

15. MATERIALES

El sistema debe disponer de una representación de material.

Como mínimo:

- nombre;
- módulo de Young;
- coeficiente de Poisson.

Posteriormente podrá incluir:

- densidad;
- límite elástico;
- propiedades térmicas;
- materiales personalizados;
- biblioteca ampliada.

La primera versión debe implementar únicamente las propiedades realmente utilizadas por el solver.

---

16. CARGAS

El sistema debe permitir definir cargas físicas reales.

Inicialmente deben contemplarse cargas compatibles con el solver implementado.

La arquitectura debe permitir definir:

- magnitud;
- unidad;
- dirección;
- sentido;
- región de aplicación.

El flujo será:

Carga
  ↓
Región CAD
  ↓
Superficie FEM
  ↓
Nodos / DOFs
  ↓
Vector F

No se deben utilizar cargas aleatorias o ficticias en producción.

---

17. RESTRICCIONES

El usuario debe poder definir condiciones de frontera.

El flujo será:

Restricción
     ↓
Región CAD
     ↓
Malla
     ↓
Nodos
     ↓
DOFs restringidos
     ↓
FEA

Solo deben mostrarse como disponibles las restricciones realmente soportadas por el solver.

---

18. FEA

La primera implementación objetivo será:

Elasticidad lineal estática 3D.

El solver debe trabajar sobre la malla real y resolver el sistema:

K · u = F

Como mínimo deberá poder obtener:

- desplazamientos;
- deformaciones;
- tensiones;
- reacciones;
- compliance.

No se consideran resultados válidos:

- valores aleatorios;
- valores estimados sin cálculo FEM;
- placeholders;
- simulaciones visuales;
- resultados generados artificialmente.

Una funcionalidad FEA solo se considera implementada cuando el resultado proviene del solver real y ha sido validado.

---

19. VALIDACIÓN FEA

Antes de utilizar el solver para optimización topológica deberá superar pruebas numéricas.

Como mínimo:

Cantilever Beam

Comparación contra una solución analítica conocida.

Patch Test

Verificación del comportamiento del elemento Tet4.

Convergencia de malla

Comparación de resultados con refinamiento progresivo.

Los resultados deberán documentar:

- error;
- condiciones;
- tamaño de malla;
- resultado analítico;
- resultado FEM;
- criterio de aceptación.

---

20. OPTIMIZACIÓN TOPOLÓGICA

Una vez validado el FEA se implementará la optimización topológica.

El método inicial objetivo será:

SIMP — Solid Isotropic Material with Penalization

Flujo:

Densidad inicial
      ↓
FEA
      ↓
Compliance
      ↓
Sensibilidades
      ↓
Actualización de densidades
      ↓
Filtro / regularización
      ↓
Nueva iteración
      ↓
FEA
      ↓
...

La optimización debe utilizar resultados provenientes del solver FEA real.

---

21. OBJETIVO DE VOLUMEN

El usuario podrá definir una fracción de volumen objetivo.

Por ejemplo:

0.30

representa el objetivo de conservar aproximadamente el 30 % del volumen de diseño.

El sistema debe diferenciar entre:

- volumen objetivo;
- volumen obtenido;
- error respecto al objetivo.

No se debe declarar alcanzado un porcentaje si el algoritmo no lo alcanzó.

---

22. ITERACIONES Y CONVERGENCIA

Cada iteración debe registrar como mínimo:

- número de iteración;
- volumen;
- compliance;
- cambio de densidad;
- criterio de convergencia;
- estado.

La aplicación debe permitir determinar si la optimización:

- convergió;
- alcanzó el máximo de iteraciones;
- falló;
- fue cancelada.

---

23. VISUALIZACIÓN DE RESULTADOS

El visor debe permitir inspeccionar:

- geometría original;
- Design Space;
- Keep-out;
- restricciones;
- cargas;
- malla;
- desplazamientos;
- tensiones;
- densidades;
- resultado optimizado.

La visualización debe representar datos calculados realmente.

No se deben generar representaciones que puedan confundirse con resultados FEA reales.

---

24. EXPORTACIÓN

La aplicación debe poder exportar resultados cuando la funcionalidad correspondiente esté implementada.

Inicialmente se priorizará:

Resultado
   ↓
Formato CAD / malla compatible

Los formatos específicos se decidirán según las capacidades reales del pipeline.

La exportación debe producir archivos válidos y verificables.

---

25. PROYECTOS Y ESTUDIOS

La arquitectura debe permitir guardar y recuperar estudios.

Un proyecto podrá contener:

Project
├── CADModel
├── Study
├── Material
├── Loads
├── Constraints
├── Mesh
├── FEA Results
└── Optimization Results

La persistencia debe estar desacoplada de cualquier autenticación de CAD externo.

---

26. ONESHAPE Y OTROS CAD

La integración con Onshape no forma parte de la prioridad actual.

Cuando el Core standalone sea funcional, podrán desarrollarse conectores externos.

Conceptualmente:

Onshape
    ↓
Connector
    ↓
CADModel
    ↓
Core

El connector podrá posteriormente encargarse de:

- importar geometría;
- exportar resultados;
- sincronizar contexto;
- autenticación;
- comunicación con la plataforma CAD.

Pero estas funcionalidades NO deben introducir dependencias de Onshape dentro del Core.

La misma arquitectura deberá permitir incorporar posteriormente otras plataformas CAD.

---

27. PRIORIDADES DEL DESARROLLO

El orden de desarrollo recomendado es:

H1 — Infraestructura

- aplicación standalone;
- arquitectura Core;
- modelo CAD interno;
- frontend;
- backend;
- importación STEP.

H2 — FEM

- Gmsh;
- Tet4;
- mapeo CAD → FEM;
- materiales;
- cargas;
- restricciones;
- solver FEA;
- validación.

H3 — Optimización

- SIMP;
- sensibilidades;
- filtros;
- control de volumen;
- convergencia;
- validación.

H4 — Resultado

- visualización avanzada;
- exportación;
- persistencia de estudios;
- mejoras de rendimiento.

H5 — Integraciones

- Onshape;
- otros CAD;
- plugins;
- sincronización.

Este orden puede modificarse únicamente mediante una decisión técnica documentada.

---

28. REGLAS DE DESARROLLO

La implementación debe respetar estrictamente "metodologia.md".

Además:

1. El Core debe ser independiente del CAD.
2. No se deben introducir dependencias de Onshape en el Core.
3. No se deben implementar placeholders como si fueran funcionalidades terminadas.
4. No se deben generar resultados físicos ficticios.
5. No se debe declarar una etapa completada solo porque existe código.
6. Toda funcionalidad debe estar implementada, integrada, probada y documentada.
7. Las hipótesis deben diferenciarse de los hechos verificados.
8. Las dependencias deben justificarse técnicamente.
9. Las pruebas deben ejecutarse sobre el código real.
10. Los resultados numéricos deben poder reproducirse.
11. Los fallos deben documentarse y corregirse, no ocultarse.
12. Las funcionalidades futuras no deben adelantarse si ponen en riesgo la estabilidad del Core.

---

29. CRITERIO DE "APLICACIÓN FUNCIONAL"

El proyecto no se considerará una aplicación funcional completa hasta que sea capaz de ejecutar de forma real y verificable:

STEP
 ↓
CADModel
 ↓
Malla Tet4
 ↓
Material
 ↓
Cargas
 ↓
Restricciones
 ↓
FEA
 ↓
Desplazamientos / Tensiones / Compliance
 ↓
SIMP
 ↓
Resultado optimizado
 ↓
Visualización
 ↓
Exportación

Cada etapa debe utilizar datos reales provenientes de la etapa anterior.

No se acepta simular una etapa para aparentar que el pipeline está terminado.

---

30. ESTADO DEL PROYECTO

Este documento representa la visión y arquitectura objetivo del proyecto.

El estado real de implementación debe mantenerse actualizado en:

"RESUMEN_IMPLEMENTACION.md"

La metodología y las reglas de cumplimiento se mantienen en:

"metodologia.md"

El prompt de desarrollo vigente se mantiene exclusivamente en:

"prompt.md"

La documentación de investigación técnica se mantiene en sus respectivos archivos de investigación.

El README describe qué debe ser el producto.

Los demás documentos describen cómo se desarrolla, qué se investigó y qué está realmente implementado.