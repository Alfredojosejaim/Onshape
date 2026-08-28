# TOPOLOGÍA OPTIMIZADA

## Especificación maestra del proyecto

---

## 1. VISIÓN DEL PROYECTO

**Topología Optimizada** es una aplicación **standalone e independiente** de análisis estructural, análisis por elementos finitos (FEA) y optimización topológica para modelos CAD 3D.

La aplicación es el **producto principal del proyecto**.

Su objetivo es permitir que un usuario pueda:

1. Importar un modelo CAD.
2. Preparar un estudio estructural.
3. Generar una malla volumétrica.
4. Ejecutar un análisis FEA.
5. Analizar los resultados.
6. Ejecutar posteriormente una optimización topológica.
7. Visualizar los resultados.
8. Exportar el resultado.

La aplicación debe poder realizar todo este flujo **sin depender de ningún programa CAD externo**.

---

## 2. PRINCIPIO FUNDAMENTAL: APLICACIÓN STANDALONE

La aplicación debe funcionar de forma completamente independiente.

No requiere:

- Onshape.
- SolidWorks.
- Autodesk Fusion.
- FreeCAD.
- AutoCAD.
- ningún otro software CAD.
- ninguna cuenta de una plataforma CAD.
- OAuth de plataformas CAD.
- APIs externas de CAD.
- documentos almacenados en plataformas CAD.
- plugins.
- extensiones de otros programas.
- una sesión activa de otro programa CAD.

### Definición estricta de independencia

Una instalación de Topología Optimizada debe poder ejecutarse en una computadora donde **no exista ningún programa CAD instalado** y permitir al usuario importar un archivo CAD local y utilizar la aplicación.

La aplicación debe poder funcionar sin conexión a ninguna plataforma CAD externa.

---

## 3. PRIMER FORMATO DE ENTRADA

La primera vía de entrada será mediante archivos CAD locales.

El formato prioritario inicial es:

**STEP (`.step` / `.stp`)**

El usuario debe poder seleccionar un archivo STEP almacenado localmente en su computadora.

El flujo inicial es:

```text
ARCHIVO STEP
     │
     ▼
STEP ADAPTER
     │
     ▼
CAD MODEL
     │
     ▼
CORE DE LA APLICACIÓN

El modelo no debe necesitar estar abierto simultáneamente en ningún programa CAD.


---

4. ARQUITECTURA ACTUAL

La arquitectura actual debe mantenerse deliberadamente simple.

APLICACIÓN STANDALONE
                         │
                         ▼
                  IMPORTACIÓN STEP
                         │
                         ▼
                    STEP ADAPTER
                         │
                         ▼
                      CAD MODEL
                         │
                         ▼
                         CORE
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           MALLADO       FEA       TOP. OPT.
             │           │           │
             └───────────┼───────────┘
                         ▼
                     RESULTADOS
                         │
                         ▼
                      EXPORTAR

El Core debe trabajar sobre una representación interna del modelo y no sobre APIs específicas de una plataforma CAD.


---

5. REGLA DE ARQUITECTURA

El Core de la aplicación NO debe conocer ni depender de ninguna plataforma CAD externa.

El Core no debe requerir:

Onshape
OAuth
FeatureScript
Onshape REST API
Document ID
Workspace ID
Element ID
CAD externo

El Core debe recibir los datos necesarios mediante las interfaces internas de la aplicación.


---

6. STEP ADAPTER

La importación STEP debe estar aislada mediante un componente responsable de convertir el archivo CAD en la representación interna utilizada por la aplicación.

Flujo:

Archivo STEP
     │
     ▼
STEP Adapter
     │
     ├── Lectura
     ├── Validación
     ├── Extracción geométrica
     └── Conversión
            │
            ▼
         CADModel

El STEP Adapter pertenece a la capa de entrada de la aplicación.

No debe introducir dependencias de Onshape ni de otros CAD externos.


---

7. CAD MODEL

CADModel representa internamente el modelo importado.

Debe contener la información necesaria para que el resto de la aplicación pueda trabajar con la geometría sin conocer el origen del archivo.

El modelo interno debe ser independiente de:

Onshape.

SolidWorks.

Fusion.

FreeCAD.

cualquier otra plataforma CAD.


Los identificadores internos deben pertenecer a la aplicación.

No se deben utilizar como dependencia arquitectónica:

document_id
workspace_id
element_id
Onshape entity ID
OAuth session


---

8. CORE

El Core contiene la lógica principal de la aplicación.

Su responsabilidad incluye progresivamente:

CADModel
   │
   ├── Geometría
   ├── Mallado
   ├── Materiales
   ├── Cargas
   ├── Restricciones
   ├── FEA
   └── Optimización topológica

El Core debe poder ejecutarse sin:

Internet.

Onshape.

cualquier CAD externo.

credenciales externas de CAD.



---

9. FLUJO FUNCIONAL OBJETIVO

El objetivo final de la aplicación standalone es:

┌──────────────────────┐
│   IMPORTAR MODELO    │
│       STEP           │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      CAD MODEL       │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│   CREAR ESTUDIO      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ MATERIAL Y PROPIEDAD │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ CARGAS Y RESTRIC.    │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│       MALLADO        │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│         FEA          │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      RESULTADOS      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ OPTIMIZACIÓN TOPOL.  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      RESULTADO       │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│       EXPORTAR       │
└──────────────────────┘

Este flujo debe poder ejecutarse sin utilizar ningún software CAD externo.


---

10. ESTADO ACTUAL DEL DESARROLLO

El proyecto se encuentra en desarrollo incremental.

La prioridad es construir primero una base standalone funcional y verificable.

Las etapas principales son:

Etapa 1 — Aplicación Standalone

Objetivo:

Aplicación ejecutable independientemente.

Importación local de STEP.

Representación interna CADModel.

Interfaz inicial.

API y Services.

Persistencia básica.

Arquitectura limpia.


Etapa 2 — Infraestructura FEA

Objetivo:

Generación de malla volumétrica.

Elementos tetraédricos Tet4.

Ensamblaje de matriz de rigidez.

Aplicación de condiciones de frontera.

Aplicación de cargas.

Resolución de:


K · u = F

Cálculo de desplazamientos.

Tensiones.

Compliance.

Validación numérica.


Etapa 3 — Optimización Topológica

Objetivo:

Implementación de SIMP.

Densidades elementales.

Penalización.

Sensibilidades.

Actualización de densidades.

Iteraciones de optimización.

Criterios de convergencia.


Etapa 4 — Visualización y exportación

Objetivo:

Visualización de malla.

Visualización de desplazamientos.

Visualización de tensiones.

Visualización de densidad.

Visualización del resultado optimizado.

Exportación del resultado.



---

11. MALLADO

La solución prevista para la generación de malla volumétrica es Gmsh.

Gmsh será utilizado para:

importar/procesar geometría STEP;

generar malla volumétrica;

generar elementos tetraédricos;

controlar tamaño y calidad de malla;

proporcionar conectividad y nodos al solver FEA.


La implementación definitiva debe validarse durante el desarrollo.


---

12. FEA

La aplicación tendrá un módulo FEA 3D.

La arquitectura está orientada inicialmente a elementos:

Tet4 — tetraedro lineal de 4 nodos

El solver deberá permitir posteriormente:

Malla
 ↓
Elementos Tet4
 ↓
Matrices Ke
 ↓
Ensamblaje K
 ↓
Condiciones de frontera
 ↓
Vector F
 ↓
K · u = F
 ↓
Desplazamientos
 ↓
Tensiones
 ↓
Compliance

El solver debe diseñarse pensando en su futura integración con optimización SIMP.


---

13. PREPARACIÓN PARA SIMP

La arquitectura FEA debe permitir posteriormente modificar la rigidez elemental mediante densidades:

Ke(ρ) = ρᵖ · Ke₀

El solver deberá poder proporcionar:

matriz de rigidez;

desplazamientos;

información elemental;

compliance;

datos necesarios para cálculo de sensibilidades.


La implementación completa de SIMP pertenece a la etapa de optimización topológica.


---

14. VALIDACIÓN NUMÉRICA

Antes de considerar el solver FEA como funcional, deberá validarse mediante:

Viga en voladizo

Comparación entre:

Resultado FEM
      vs.
Solución analítica

Patch Test

Verificación de comportamiento del elemento Tet4 ante campos constantes.

Convergencia de malla

Ejecutar el análisis con diferentes resoluciones de malla y verificar la convergencia del resultado.

No se debe considerar un solver funcional simplemente porque produzca números.

Los resultados deben validarse.


---

15. FUTURAS INTEGRACIONES CAD

La integración con plataformas CAD externas NO forma parte de la aplicación principal actual.

En el futuro podrá desarrollarse un sistema de integración mediante módulos externos.

Conceptualmente:

FUTURO
                │
        ┌───────┴────────┐
        ▼                ▼
   Onshape Plugin   Otro CAD Plugin
        │                │
        └───────┬────────┘
                ▼
      APLICACIÓN STANDALONE

Estos módulos podrán facilitar:

importar modelos;

exportar modelos;

transferir resultados;

automatizar intercambio de información.


Pero serán opcionales.


---

16. REGLA FUNDAMENTAL SOBRE FUTURAS INTEGRACIONES

Una integración futura con Onshape u otro CAD:

NO debe convertirse en una dependencia del Core.

La aplicación debe seguir funcionando si:

el plugin no está instalado;

Onshape no está disponible;

el CAD externo no está instalado;

no existe conexión con el CAD externo.


La aplicación standalone siempre debe ser funcional por sí misma.


---

17. LO QUE NO DEBE IMPLEMENTARSE AHORA

Hasta que la aplicación standalone esté funcional y validada, NO se debe desarrollar:

Plugin de Onshape.

Connector de Onshape.

OAuth de Onshape.

FeatureScript.

App Extension.

iframe de Onshape.

sincronización con Onshape.

integración con SolidWorks.

integración con Fusion.

integración con FreeCAD.

integración con otros CAD.

sistema complejo de plugins.

infraestructura de múltiples conectores.


Estas funcionalidades pertenecen a futuras etapas.


---

18. REGLA CONTRA SOBREDISEÑO

No crear abstracciones únicamente porque podrían ser necesarias en el futuro.

Actualmente el flujo prioritario es:

STEP
 ↓
STEP Adapter
 ↓
CADModel
 ↓
Core

La incorporación de nuevos formatos o integraciones debe realizarse cuando exista una necesidad concreta.

No se debe implementar una infraestructura compleja de múltiples CAD antes de que exista una aplicación standalone funcional.


---

19. INTERFAZ DE USUARIO

La interfaz debe estar orientada a la aplicación standalone.

El flujo principal debe utilizar conceptos como:

Importar modelo
Crear estudio
Configurar material
Definir restricciones
Definir cargas
Generar malla
Ejecutar FEA
Analizar resultados
Optimizar
Exportar

No debe presentar como requisito:

Conectar con Onshape
Iniciar sesión en Onshape
Seleccionar documento de Onshape
Seleccionar Workspace
Seleccionar Element


---

20. PERSISTENCIA

Los estudios deben poder almacenarse independientemente de cualquier plataforma CAD.

Un estudio debe ser propiedad de la aplicación.

No debe depender de:

Onshape Document
Onshape Workspace
Onshape Element
OAuth


---

21. PRINCIPIOS DE DESARROLLO

Todo desarrollo debe respetar:

Independencia

La aplicación debe funcionar sin CAD externo.

Modularidad

Separar:

Frontend
API
Services
Core
CAD Adapter
FEA
Optimization
Export

Trazabilidad

Cada funcionalidad debe poder relacionarse con un requisito concreto.

Validación

No declarar funcionalidades completas sin pruebas.

Simplicidad

No crear complejidad arquitectónica innecesaria.

Evolución

Las futuras integraciones deben poder añadirse sin modificar innecesariamente el Core.


---

22. DEFINICIÓN DE ÉXITO DEL PROYECTO

El proyecto será considerado exitoso cuando pueda realizarse:

Archivo STEP
     ↓
Importación
     ↓
Modelo interno
     ↓
Configuración de estudio
     ↓
Malla
     ↓
FEA
     ↓
Resultados
     ↓
Optimización topológica
     ↓
Resultado optimizado
     ↓
Exportación

Todo ello desde la aplicación standalone.


---

23. PRIORIDAD ABSOLUTA

El orden de prioridad es:

1. APLICACIÓN STANDALONE
2. IMPORTACIÓN STEP
3. MODELO INTERNO
4. MALLADO
5. FEA
6. VALIDACIÓN FEA
7. OPTIMIZACIÓN SIMP
8. VISUALIZACIÓN
9. EXPORTACIÓN
10. INTEGRACIONES CAD EXTERNAS

No invertir este orden.


---

24. ESTADO ARQUITECTÓNICO

La arquitectura actual se considera:

STANDALONE FIRST

La aplicación debe existir y ser funcional independientemente de cualquier ecosistema CAD.

Las integraciones externas son una capa posterior y opcional.


---

25. REGLA FINAL PARA TODA IA QUE TRABAJE EN EL REPOSITORIO

Cualquier IA que modifique este proyecto debe interpretar este README como una especificación arquitectónica.

Antes de implementar una funcionalidad debe comprobar:

1. ¿Es necesaria para la aplicación standalone?


2. ¿Depende de un CAD externo?


3. ¿Requiere Onshape u otra plataforma?


4. ¿Es una funcionalidad de una etapa futura?


5. ¿Existe ya una implementación equivalente?


6. ¿Está contemplada en prompt.md y metodologia.md?



Si una funcionalidad requiere un CAD externo y no pertenece explícitamente a una etapa actual:

NO IMPLEMENTARLA.

La prioridad es siempre:

> Construir primero una aplicación independiente, funcional, verificable y útil por sí misma.



Las integraciones con CAD externos se desarrollarán posteriormente como módulos opcionales, sin convertirlas en una dependencia del producto.

Sí. Lo agregaría como una sección nueva, sin modificar las decisiones anteriores del README. Este es el bloque exacto para copiar y pegar:

---

## 26. DECISIÓN ARQUITECTÓNICA — LENGUAJE Y PROTECCIÓN COMERCIAL

Como resultado de la investigación sobre lenguaje, rendimiento, integración con Kratos Multiphysics y futura protección comercial, se establece la siguiente decisión arquitectónica.

### 26.1 Lenguaje principal

**Python continúa siendo el lenguaje principal de la aplicación.**

No se realizará una migración general de Python a C++.

Python seguirá siendo utilizado para:

- interfaz de usuario;
- orquestación de la aplicación;
- configuración;
- flujo de simulaciones;
- integración de alto nivel con Kratos;
- persistencia;
- reporting;
- importación/exportación cuando no exista una necesidad específica de migración.

Esto permite mantener una alta velocidad de desarrollo sin introducir complejidad innecesaria.

---

### 26.2 C++ como capa nativa

**C++ será el lenguaje de referencia para las partes que requieran integración nativa con Kratos o protección de propiedad intelectual crítica.**

Serán candidatos a implementarse en C++:

- extensiones propias de Kratos;
- algoritmos propietarios de optimización o diseño generativo que no sean proporcionados directamente por Kratos;
- procesamiento geométrico crítico que contenga know-how propio;
- preprocesamiento o postprocesamiento numérico propietario;
- componentes computacionalmente pesados que constituyan una ventaja competitiva;
- lógica crítica que no deba permanecer expuesta en Python.

La migración será **selectiva e incremental**.

No se migrará un componente a C++ únicamente porque técnicamente sea posible.

---

### 26.3 Kratos Multiphysics

**Kratos Multiphysics permanece como el motor principal de cálculo FEA y optimización del proyecto.**

La integración de alto nivel se realizará mediante su interfaz Python.

Cuando sea necesario extender directamente Kratos, se utilizará el mecanismo nativo de **Kratos Applications en C++**, siguiendo la arquitectura utilizada por el propio framework.

Si Kratos cubre una funcionalidad que anteriormente se contemplaba mediante otra biblioteca, dicha biblioteca podrá descartarse cuando la validación técnica confirme que Kratos satisface los requisitos.

---

### 26.4 Rust

**Rust no se incorpora actualmente al stack principal del proyecto.**

Aunque Rust presenta ventajas de seguridad de memoria y puede ser apropiado para módulos aislados, introducirlo actualmente añadiría una tercera tecnología y una capa adicional de interoperabilidad cuando sea necesario interactuar directamente con Kratos.

Podrá evaluarse posteriormente para componentes aislados que no requieran integración profunda con las estructuras internas de Kratos.

Su incorporación futura deberá justificarse por una necesidad técnica concreta.

---

### 26.5 Protección comercial futura

La aplicación podrá comercializarse posteriormente mediante un sistema de suscripción/licenciamiento.

El sistema de licenciamiento **no forma parte de la implementación actual**.

Cuando se implemente, la verificación crítica de licencia y activación no deberá depender exclusivamente de código Python fácilmente modificable.

La arquitectura deberá permitir colocar la lógica crítica de validación en código compilado.

La protección no se considera absoluta: ningún software ejecutado localmente puede impedir completamente el reverse engineering. El objetivo será aumentar significativamente el coste y dificultad de:

- extracción de algoritmos;
- modificación del programa;
- parcheo;
- bypass del licenciamiento;
- reutilización no autorizada del código propietario.

---

### 26.6 Regla de protección de propiedad intelectual

No se desarrollará deliberadamente en Python un algoritmo que ya haya sido identificado como **IP crítica** con la intención de migrarlo posteriormente a C++.

Cuando una funcionalidad sea identificada como parte de la ventaja competitiva o propiedad intelectual crítica del producto, deberá evaluarse su implementación directamente en C++.

Por el contrario, componentes de bajo valor estratégico como UI, reporting u orquestación no deberán migrarse únicamente por motivos de protección.

---

### 26.7 Arquitectura de referencia

La distribución tecnológica prevista queda definida de la siguiente manera:

```text
                    APLICACIÓN STANDALONE
                             │
              ┌──────────────┴──────────────┐
              │                             │
           PYTHON                          C++
              │                             │
       UI / Orquestación              IP propietaria
       Configuración                  Extensiones Kratos
       Flujo de trabajo               Procesamiento crítico
       Reporting                      Algoritmos propios
              │                             │
              └──────────────┬──────────────┘
                             ▼
                    KRATOS MULTIPHYSICS
                             │
                             ▼
                       FEA / OPTIMIZACIÓN

La aplicación continuará siendo standalone y Kratos permanecerá como componente central del motor de cálculo.

Las futuras integraciones CAD externas seguirán siendo opcionales y no deberán convertirse en dependencias del Core.


---

26.8 Decisión de migración

La decisión actual es:

> NO migrar toda la aplicación a C++.



En su lugar:

PYTHON
    ↓
Aplicación + UI + orquestación + lógica no crítica

C++
    ↓
IP crítica + extensiones nativas de Kratos + procesamiento crítico

KRATOS
    ↓
Motor principal FEA / optimización

Esta decisión establece una frontera tecnológica para evitar una migración costosa en el futuro, pero no obliga a modificar inmediatamente el código existente.

Cada nuevo componente deberá evaluarse según su función, rendimiento, integración con Kratos y valor como propiedad intelectual.

Principio rector

> No migrar por migrar ni proteger por proteger. Compilar y proteger únicamente aquello que realmente lo necesite.


