
# INVESTIGACIÓN TÉCNICA FOCALIZADA — KRATOS MULTIPHYSICS
## Validación para decisión arquitectónica del proyecto

### OBJETIVO

Realizar una segunda investigación técnica, profunda y focalizada sobre **Kratos Multiphysics**, utilizando como punto de partida los informes existentes:

- `informe_geminis.md`
- `informe_claude.md`

El objetivo NO es volver a investigar Kratos de forma general.

El objetivo es **verificar las afirmaciones críticas de ambos informes y cerrar las incertidumbres que todavía impiden decidir si Kratos debe convertirse en el motor FEA/optimización del proyecto**.

NO implementar código del proyecto.

NO modificar la arquitectura.

NO instalar Kratos.

NO modificar Gmsh.

NO modificar TopOpt.

NO modificar la GUI.

NO eliminar código existente.

Esta etapa es exclusivamente de investigación, validación y toma de decisión técnica.

---

# 1. CONTEXTO DEL PROYECTO

La aplicación debe ser:

> COMPLETAMENTE STANDALONE E INDEPENDIENTE DE CUALQUIER SOFTWARE CAD.

No debe necesitar:

- Onshape;
- SolidWorks;
- Fusion 360;
- FreeCAD;
- AutoCAD;
- ningún CAD externo;
- ninguna API CAD externa.

El flujo conceptual es:

```text
MODELO CAD / MALLA
        ↓
IMPORTACIÓN
        ↓
PREPROCESAMIENTO
        ↓
MALLADO
        ↓
FEA
        ↓
OPTIMIZACIÓN
        ↓
RESULTADO
        ↓
EXPORTACIÓN

La arquitectura FEA originalmente prevista era:

STEP
 ↓
Gmsh
 ↓
Tet4
 ↓
Solver FEA propio
 ↓
SciPy Sparse / PyPardiso
 ↓
SIMP

Se está evaluando sustituir el solver FEA propio por Kratos Multiphysics.

La decisión debe considerar también el futuro del proyecto:

1. Topology Optimization.


2. SIMP.


3. Shape Optimization.


4. Diseño generativo.


5. Mejora estructural de piezas existentes.


6. Restricciones de superficies protegidas.


7. Posible expansión futura a Multiphysics.




---

2. FUENTES

Priorizar obligatoriamente:

1. Repositorio oficial de Kratos Multiphysics.


2. Documentación oficial.


3. Código fuente oficial.


4. Examples oficiales.


5. Wiki oficial.


6. PyPI oficial.


7. Issues oficiales.


8. Pull Requests oficiales.


9. Papers de los desarrolladores de Kratos.



No aceptar una afirmación solamente porque aparezca en informe_geminis.md o informe_claude.md.

Los informes son material de investigación previo, NO evidencia definitiva.


---

3. REGLA DE VERIFICACIÓN

Cada conclusión debe clasificarse como:

VERIFICADO

Existe evidencia primaria directa.

PARCIALMENTE VERIFICADO

Existe capacidad relacionada pero requiere adaptación o desarrollo.

INFERENCIA

La capacidad parece posible pero no existe evidencia directa suficiente.

NO VERIFICADO

No se pudo confirmar.

NO DISPONIBLE

Se encontró evidencia de que la capacidad no existe.

Nunca transformar una inferencia en un hecho.


---

4. INVESTIGACIÓN CRÍTICA Nº 1

OptimizationApplication VS TopologyOptimizationApplication

Este es uno de los puntos más importantes de toda la investigación.

Determinar exactamente el estado actual de:

OptimizationApplication

y:

TopologyOptimizationApplication

Investigar:

estado actual;

mantenimiento;

versión;

documentación;

ejemplos;

fecha de actividad;

compatibilidad con la versión actual de Kratos;

si está destinada a producción;

si está deprecated;

si está experimental;

diferencias arquitectónicas.


Determinar específicamente:

¿Dónde está actualmente la implementación de topology optimization basada en SIMP?

¿Existe realmente un:

SmallDisplacementSIMPElement

?

Si existe:

localizarlo;

indicar archivo;

explicar su funcionamiento;

verificar la ecuación utilizada;

verificar cómo recibe rho;

verificar cómo obtiene Ke0;

verificar cómo se actualiza rho;

verificar si sigue siendo utilizable actualmente.


Investigar además la relación entre:

TopologyOptimizationApplication

y:

OptimizationApplication

Determinar si una debe considerarse:

legacy;

experimental;

alternativa;

reemplazada;

complementaria.


Resultado obligatorio

Crear una comparación:

Característica	TopologyOptimizationApplication	OptimizationApplication

Estado actual		
Mantenimiento		
SIMP		
Density-based		
Sensibilidades		
Filtros		
Volume constraint		
3D		
Tet4		
Ejemplos actuales		
Recomendación		



---

5. INVESTIGACIÓN CRÍTICA Nº 2

Tet4 REAL

No aceptar simplemente:

> "Kratos soporta tetraedros."



Verificar directamente en el código fuente y/o documentación oficial:

nombre exacto del elemento;

clase;

archivo;

geometría utilizada;

número de nodos;

número de DOFs;

formulación;

integración;

material constitutivo;

pequeñas deformaciones;

grandes deformaciones.


Determinar si realmente podemos utilizar:

Tet4
3D
3 DOF/node
12 DOF/element
linear elasticity

Verificar si existe alguna característica que pueda afectar nuestra futura implementación SIMP.


---

6. INVESTIGACIÓN CRÍTICA Nº 3

ACCESO A Ke

Este punto es fundamental.

Verificar directamente si desde Python podemos hacer algo equivalente a:

element.CalculateLocalSystem(...)

y obtener:

Ke

Determinar:

1. Tipo de objeto devuelto.


2. Si es accesible desde Python.


3. Si podemos convertirlo a NumPy.


4. Si podemos obtener Ke0.


5. Si podemos recorrer todos los elementos.


6. Si podemos hacerlo eficientemente.


7. Si existe un ejemplo oficial.



Determinar si podemos implementar:

Ke(rho) = rho^p * Ke0

sin modificar el código C++ de Kratos.


---

7. INVESTIGACIÓN CRÍTICA Nº 4

MATRIZ GLOBAL K

Determinar:

si podemos acceder a K global;

cómo se ensambla;

si está disponible desde Python;

si podemos modificarla;

si podemos inspeccionarla;

si necesitamos utilizar obligatoriamente el BuilderAndSolver de Kratos.


Comparar dos posibilidades:

OPCIÓN A

Kratos
 ↓
ensamblaje
 ↓
solver

OPCIÓN B

Kratos
 ↓
Ke
 ↓
NumPy/SciPy
 ↓
nuestro ensamblaje
 ↓
solver

Determinar cuál es técnicamente viable y cuál es recomendable.


---

8. INVESTIGACIÓN CRÍTICA Nº 5

SIMP REAL

Verificar si podemos implementar dentro de Kratos:

K(rho)

con:

Ke(rho) = rho^p Ke0

y:

rho_min <= rho <= 1

Investigar:

penalización;

densidad mínima;

filtros;

sensitividades;

volumen;

actualización;

convergencia.


Determinar qué proporciona Kratos directamente.

Determinar qué tendría que desarrollar nuestro proyecto.


---

9. INVESTIGACIÓN CRÍTICA Nº 6

OptimizationApplication EN PROFUNDIDAD

Determinar exactamente:

arquitectura;

Responses;

Controls;

Algorithms;

Constraints;

Objectives;

Filters;

Design Variables.


Investigar un flujo completo real:

FEA
 ↓
Response
 ↓
Sensitivity
 ↓
Filter
 ↓
Update
 ↓
New design

Encontrar, si existe, un ejemplo oficial lo más parecido posible a:

3D
Tet4
Structural Mechanics
Compliance minimization
Volume constraint
Density based

Si no existe exactamente, decirlo.


---

10. INVESTIGACIÓN CRÍTICA Nº 7

SHAPE OPTIMIZATION

Investigar exactamente qué puede hacer Kratos actualmente respecto a:

Shape Optimization

Determinar:

variables de diseño;

sensibilidad de forma;

movimiento de nodos;

smoothing;

mesh morphing;

restricciones;

actualización geométrica;

remallado.


Determinar si modifica:

mesh

o:

CAD geometry

Esto es extremadamente importante.


---

11. INVESTIGACIÓN CRÍTICA Nº 8

SUPERFICIES PROTEGIDAS

Nuestro objetivo futuro es poder decir:

SUPERFICIE PROTEGIDA

y evitar que el algoritmo modifique esa región.

Investigar si Kratos permite:

fijar nodos;

fijar desplazamiento de nodos de diseño;

bloquear regiones;

restringir movimiento;

aplicar design variables únicamente a determinadas regiones;

definir regiones no optimizables.


Determinar si esto funciona para:

Topology Optimization

y:

Shape Optimization

por separado.

NO afirmar que "puede hacerse" simplemente porque matemáticamente sería posible.

Buscar evidencia real.


---

12. INVESTIGACIÓN CRÍTICA Nº 9

MEJORA ESTRUCTURAL DE UNA PIEZA EXISTENTE

Evaluar nuestro concepto:

Pieza existente
       ↓
FEA
       ↓
Identificación de problemas
       ↓
Modificar regiones permitidas
       ↓
FEA nuevamente
       ↓
Mejor diseño

El usuario puede definir:

SUPERFICIES PROTEGIDAS

y:

REGIONES OPTIMIZABLES

Investigar si Kratos proporciona mecanismos que permitan construir esto.

Separar:

Lo que Kratos hace directamente

Lo que Kratos facilita

Lo que debemos desarrollar nosotros


---

13. INVESTIGACIÓN CRÍTICA Nº 10

DISEÑO GENERATIVO

No utilizar "generative design" como término genérico.

Definir técnicamente qué significa para nuestro proyecto.

Investigar si Kratos puede:

generar topologías;

generar formas;

modificar geometría;

explorar múltiples soluciones;

manejar múltiples restricciones;

manejar múltiples objetivos;

generar geometrías orgánicas.


Determinar si Kratos es:

A

un motor de diseño generativo completo;

B

un motor FEA + optimización sobre el cual podemos construir nuestro propio sistema generativo;

C

solamente un componente.


---

14. INVESTIGACIÓN CRÍTICA Nº 11

GMSH + KRATOS

Determinar exactamente cómo funcionaría:

STEP
 ↓
Gmsh
 ↓
.msh
 ↓
Kratos

Verificar:

formato;

conversión;

nodos;

elementos;

grupos;

Physical Groups;

condiciones de frontera;

IDs;

compatibilidad.


Determinar si Gmsh debe mantenerse.

No reemplazar Gmsh simplemente porque Kratos también tenga capacidades de mallado.


---

15. INVESTIGACIÓN CRÍTICA Nº 12

WINDOWS Y DISTRIBUCIÓN

Este es uno de los puntos más importantes para una aplicación comercial/standalone.

Verificar:

wheels oficiales;

Python versions;

Windows versions;

arquitectura x64;

DLLs;

dependencias;

Visual C++ runtime;

OpenMP;

MPI;

MKL;

AMGCL;

Pardiso.


Determinar exactamente qué necesita el usuario final.

La pregunta concreta es:

> ¿Podemos distribuir nuestra aplicación como un instalador standalone que incluya Kratos sin exigir al usuario instalar Python, compiladores, CMake, Visual Studio, MKL u otras herramientas?



Analizar:

PyInstaller
Nuitka

u otros métodos relevantes.

NO asumir que PyInstaller funciona correctamente solo porque Python pueda importar Kratos.

Buscar evidencia.


---

16. INVESTIGACIÓN CRÍTICA Nº 13

TAMAÑO Y DEPENDENCIAS

Determinar:

tamaño de wheels;

tamaño aproximado instalado;

dependencias obligatorias;

dependencias opcionales;

DLLs;

aplicaciones necesarias.


Separar:

Core mínimo

de:

Instalación completa


---

17. INVESTIGACIÓN CRÍTICA Nº 14

LICENCIAS

Verificar individualmente:

Kratos Core
StructuralMechanicsApplication
OptimizationApplication
TopologyOptimizationApplication
LinearSolversApplication
AMGCL
Pardiso
MKL
Gmsh

Para cada uno:

licencia;

uso comercial;

redistribución;

binarios;

obligaciones.


No asumir que todo Kratos tiene exactamente la misma licencia.


---

18. INVESTIGACIÓN CRÍTICA Nº 15

RENDIMIENTO

No inventar benchmarks.

Buscar benchmarks oficiales.

Si no existen comparaciones:

Kratos vs SciPy
Kratos vs PyPardiso

declararlo.

Determinar qué arquitectura debería benchmarkearse posteriormente.

Proponer un benchmark reproducible para nuestro proyecto:

100k elementos
500k elementos
1M elementos

o tamaños razonables según la evidencia disponible.


---

19. COMPARACIÓN CONTRA NUESTRA IMPLEMENTACIÓN PROPIA

Comparar:

OPCIÓN A

Gmsh
+
SciPy
+
PyPardiso
+
FEA propio
+
SIMP propio

contra:

OPCIÓN B

Gmsh
+
Kratos Structural Mechanics
+
Kratos Optimization

contra:

OPCIÓN C

Gmsh
+
Kratos FEA
+
Optimization propio

Analizar:

complejidad;

control;

rendimiento;

mantenimiento;

extensibilidad;

SIMP;

Shape Optimization;

diseño generativo;

distribución;

Windows;

licencias.



---

20. DECISIÓN ARQUITECTÓNICA

Al finalizar, recomendar obligatoriamente una:

OPCIÓN A

Mantener FEA propio.

OPCIÓN B

Migrar completamente a Kratos.

OPCIÓN C

Arquitectura híbrida.

La recomendación debe explicar exactamente:

Gmsh → ?
FEA → ?
Optimization → ?
SIMP → ?
Shape Optimization → ?
Generative → ?
Postprocessing → ?


---

21. MATRIZ FINAL DE DECISIÓN

Crear una tabla:

Requisito	Kratos	Desarrollo propio	Mejor opción

Tet4			
FEA 3D			
Ke			
K			
u			
Stress			
Compliance			
Sensitivities			
SIMP			
TopOpt			
Shape Optimization			
Superficies protegidas			
Diseño generativo			
Multiphysics			
Windows			
Standalone			
Rendimiento			
Mantenimiento			
Licencia			
Extensibilidad			



---

22. INFORME FINAL

Crear:

evaluacion_kratos.md

Este documento debe ser una evaluación técnica complementaria, no una repetición de los informes anteriores.

Debe incluir:

1. Preguntas críticas.


2. Evidencia encontrada.


3. Correcciones a Gemini.


4. Correcciones a Claude.


5. Capacidades confirmadas.


6. Capacidades parcialmente confirmadas.


7. Capacidades no confirmadas.


8. Limitaciones.


9. Riesgos.


10. Arquitecturas posibles.


11. Comparativa.


12. Recomendación final.


13. Decisión sugerida para el Hito 2.




---

23. ACTUALIZACIÓN DE DOCUMENTACIÓN

Actualizar:

RESUMEN_IMPLEMENTACION.md

únicamente indicando que se realizó una evaluación técnica de Kratos.

NO declarar que Kratos fue integrado.

NO declarar que la arquitectura fue modificada.

NO declarar que el Hito 2 fue completado.


---

24. REGLAS ABSOLUTAS

NO implementar.

NO instalar.

NO modificar código funcional.

NO cambiar arquitectura.

NO eliminar dependencias.

NO reemplazar Gmsh.

NO modificar TopOpt.

NO crear pruebas experimentales dentro del proyecto.

NO hacer benchmarks inventados.

NO utilizar afirmaciones promocionales.

NO asumir capacidades.

NO considerar un nombre de clase como prueba suficiente.

NO considerar que una función existe actualmente solamente porque aparece en documentación antigua.


---

25. CRITERIO FINAL

La pregunta que debe responder la investigación es:

> ¿Kratos nos permite construir una aplicación standalone de optimización estructural mucho más potente que nuestro FEA propio, manteniendo suficiente control sobre FEA, SIMP, topology optimization y shape optimization, sin introducir una complejidad de distribución que haga inviable nuestro producto?



Y una segunda pregunta:

> ¿Kratos amplía realmente nuestro proyecto hacia diseño generativo, mejora estructural y eventualmente multiphysics, o solamente reemplaza nuestro solver FEA?



La respuesta debe ser inequívoca.

Al finalizar entregar también un resumen ejecutivo de máximo 15 puntos indicando:

qué descubrimos;

qué estaba equivocado en las investigaciones anteriores;

qué quedó confirmado;

qué sigue siendo incierto;

qué puede reutilizarse;

qué tendríamos que desarrollar;

riesgos principales;

arquitectura recomendada;

y si recomiendas o no adoptar Kratos.


