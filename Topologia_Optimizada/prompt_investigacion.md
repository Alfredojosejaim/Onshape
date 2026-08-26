
---

INVESTIGACIÓN TÉCNICA FOCALIZADA — KRATOS MULTIPHYSICS

Validación para decisión arquitectónica

ROL

Actúa como investigador técnico especializado en Kratos Multiphysics, FEA, optimización estructural y software científico.

Tu única tarea es realizar una investigación técnica profunda, crítica y actualizada sobre Kratos Multiphysics para determinar si realmente encaja con nuestra aplicación de optimización estructural.

NO tienes acceso a nuestro repositorio, código fuente del proyecto ni archivos internos.

Por lo tanto:

NO intentes acceder a ningún repositorio privado.

NO intentes modificar archivos.

NO intentes crear archivos.

NO intentes instalar Kratos.

NO intentes ejecutar nuestro proyecto.

NO implementes código.

NO propongas cambios directamente sobre nuestro repositorio.


Tu trabajo consiste exclusivamente en:

> INVESTIGAR → VERIFICAR → CONTRASTAR → ANALIZAR → RECOMENDAR



El resultado debe ser un informe técnico entregado directamente en tu respuesta.


---

1. CONTEXTO DEL PROYECTO

Estamos desarrollando una aplicación:

> STANDALONE E INDEPENDIENTE DE CUALQUIER SOFTWARE CAD.



No debe depender de:

Onshape;

SolidWorks;

Fusion 360;

FreeCAD;

AutoCAD;

ningún CAD externo;

ninguna API CAD externa.


El flujo conceptual es:

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

La arquitectura FEA inicialmente prevista es:

STEP
 ↓
Gmsh
 ↓
Tet4
 ↓
FEA propio
 ↓
SciPy Sparse / PyPardiso
 ↓
SIMP

Estamos evaluando si Kratos Multiphysics puede sustituir total o parcialmente nuestro FEA y proporcionar además capacidades útiles para:

1. Topology Optimization.


2. SIMP.


3. Shape Optimization.


4. Mejora estructural de piezas existentes.


5. Superficies protegidas.


6. Regiones optimizables.


7. Diseño generativo futuro.


8. Multiphysics futuro.




---

2. OBJETIVO REAL DE LA INVESTIGACIÓN

NO queremos una descripción general de Kratos.

Queremos responder:

> ¿Kratos realmente puede convertirse en una base sólida para nuestro FEA + optimización, manteniendo suficiente control técnico para construir nuestro propio sistema?



Y:

> ¿Kratos aporta capacidades reales de Topology Optimization, SIMP, Shape Optimization y diseño generativo, o principalmente nos proporciona un framework FEA sobre el cual tendríamos que desarrollar esas funciones?



La investigación debe centrarse en las capacidades que puedan cambiar nuestra decisión arquitectónica.


---

3. FUENTES

Utilizar prioritariamente fuentes primarias:

1. Repositorio oficial de Kratos Multiphysics.


2. Documentación oficial.


3. Código fuente público oficial.


4. Examples oficiales.


5. Wiki oficial.


6. API/documentación Python.


7. PyPI.


8. Issues oficiales.


9. Pull Requests oficiales.


10. Papers de los desarrolladores.



También puedes utilizar fuentes secundarias para complementar, pero las afirmaciones críticas deben contrastarse con fuentes primarias siempre que sea posible.

Priorizar información correspondiente a la versión actual de Kratos.

No utilizar documentación antigua como evidencia de una capacidad actual sin comprobar primero su vigencia.


---

4. REGLA DE EVIDENCIA

Clasifica las conclusiones como:

VERIFICADO

Existe evidencia primaria directa y actual.

PARCIALMENTE VERIFICADO

Existe infraestructura relacionada, pero requiere adaptación o desarrollo propio.

INFERENCIA

La capacidad parece técnicamente posible, pero no existe evidencia directa suficiente.

NO VERIFICADO

No se pudo confirmar.

NO DISPONIBLE

Existe evidencia suficiente de que la capacidad no está disponible de la manera necesaria.

Nunca conviertas una inferencia en un hecho.


---

5. INVESTIGACIÓN CRÍTICA Nº 1

OptimizationApplication VS TopologyOptimizationApplication

Investigar profundamente el estado actual de:

OptimizationApplication

y:

TopologyOptimizationApplication

Determinar:

existencia;

estado actual;

mantenimiento;

actividad;

versión;

documentación;

ejemplos;

compatibilidad;

producción;

experimental;

deprecated;

legacy;

relación entre ambas.


Investigar específicamente:

> ¿Dónde está actualmente la implementación de topology optimization basada en SIMP?



Verificar si existe:

SmallDisplacementSIMPElement

Si existe:

ubicación;

clase;

formulación;

ecuación;

funcionamiento;

entrada de rho;

tratamiento de Ke0;

actualización de rho;

estado actual;

compatibilidad con las versiones actuales.


Determinar si TopologyOptimizationApplication es:

legacy;

experimental;

alternativa;

reemplazada;

complementaria;


respecto de OptimizationApplication.

Tabla obligatoria

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

6. INVESTIGACIÓN CRÍTICA Nº 2

Tet4 REAL

No aceptar simplemente:

> "Kratos soporta tetraedros."



Verificar directamente:

nombre exacto;

clase;

archivo;

geometría;

número de nodos;

DOFs;

formulación;

integración;

material;

pequeñas deformaciones;

grandes deformaciones.


Determinar específicamente si podemos utilizar:

Tet4
3 DOF/node
12 DOF/element
linear elasticity

Indicar claramente la evidencia encontrada.


---

7. INVESTIGACIÓN CRÍTICA Nº 3

ACCESO A Ke

Investigar si desde Python es posible acceder a la matriz elemental mediante mecanismos equivalentes a:

element.CalculateLocalSystem(...)

Determinar:

1. Qué devuelve.


2. Si es accesible desde Python.


3. Si puede convertirse a NumPy.


4. Si podemos obtener Ke0.


5. Si podemos recorrer los elementos.


6. Si es razonablemente eficiente.


7. Si existe un ejemplo oficial.



Pregunta fundamental:

> ¿Podemos implementar Ke(rho) = rho^p Ke0 sin modificar el C++ de Kratos?




---

8. INVESTIGACIÓN CRÍTICA Nº 4

MATRIZ GLOBAL K

Determinar:

si podemos acceder a K;

cómo se ensambla;

si es accesible desde Python;

si puede inspeccionarse;

si puede modificarse;

papel de BuilderAndSolver.


Comparar:

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

Determinar cuál es viable y cuál sería recomendable.


---

9. INVESTIGACIÓN CRÍTICA Nº 5

SIMP REAL

Verificar si podemos implementar:

Ke(rho) = rho^p Ke0

con:

rho_min <= rho <= 1

Investigar:

penalización;

densidad mínima;

filtros;

sensibilidades;

volumen;

actualización;

convergencia.


Separar:

Proporcionado directamente por Kratos

Facilitado por Kratos

Desarrollo propio requerido


---

10. INVESTIGACIÓN CRÍTICA Nº 6

OptimizationApplication

Investigar la arquitectura real de:

Responses;

Controls;

Algorithms;

Constraints;

Objectives;

Filters;

Design Variables.


Explicar el flujo real:

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

Buscar un ejemplo oficial lo más cercano posible a:

3D
Tet4
Structural Mechanics
Compliance minimization
Volume constraint
Density based

Si no existe exactamente, indicarlo.


---

11. INVESTIGACIÓN CRÍTICA Nº 7

SHAPE OPTIMIZATION

Investigar exactamente qué proporciona Kratos actualmente para:

Shape Optimization

Determinar:

variables de diseño;

shape sensitivities;

adjoint;

movimiento nodal;

smoothing;

mesh morphing;

restricciones;

actualización;

remallado.


Pregunta fundamental:

> ¿Kratos modifica una malla o puede modificar directamente geometría CAD?



Diferenciar ambas cosas claramente.


---

12. INVESTIGACIÓN CRÍTICA Nº 8

SUPERFICIES PROTEGIDAS

Nuestro futuro sistema necesitará:

SUPERFICIES PROTEGIDAS

y:

REGIONES OPTIMIZABLES

Investigar evidencia real sobre:

nodos bloqueados;

regiones no optimizables;

design variables restringidas;

restricciones de movimiento;

superficies fijas;

exclusión de regiones.


Analizar separadamente:

Topology Optimization

Shape Optimization

No asumir que una restricción FEA puede utilizarse automáticamente como restricción de optimización.


---

13. INVESTIGACIÓN CRÍTICA Nº 9

MEJORA ESTRUCTURAL DE PIEZAS EXISTENTES

Nuestro concepto futuro es:

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

Investigar si Kratos proporciona infraestructura para construir esto.

Separar:

Kratos hace directamente

Kratos facilita

Nuestro software tendría que desarrollar


---

14. INVESTIGACIÓN CRÍTICA Nº 10

DISEÑO GENERATIVO

Definir técnicamente qué significaría "diseño generativo" para nuestro proyecto.

Investigar si Kratos puede:

generar topologías;

generar formas;

modificar geometría;

explorar múltiples soluciones;

manejar múltiples restricciones;

manejar múltiples objetivos;

producir geometrías orgánicas.


Determinar si Kratos es:

A — Motor generativo completo

B — Motor FEA + optimización sobre el cual construiríamos nuestro sistema generativo

C — Solamente un componente

Justificar con evidencia.


---

15. INVESTIGACIÓN CRÍTICA Nº 11

GMSH + KRATOS

Investigar el flujo:

STEP
 ↓
Gmsh
 ↓
.msh
 ↓
Kratos

Verificar:

formato;

nodos;

elementos;

conectividad;

grupos;

Physical Groups;

IDs;

condiciones de frontera;

compatibilidad.


Determinar si Gmsh debería mantenerse.


---

16. INVESTIGACIÓN CRÍTICA Nº 12

WINDOWS

Investigar específicamente:

wheels;

versiones Python;

Windows;

x64;

DLL;

Visual C++ runtime;

OpenMP;

MPI;

MKL;

AMGCL;

Pardiso.


Determinar qué necesitaría el usuario final.

Pregunta:

> ¿Es técnicamente viable distribuir una aplicación standalone que incluya Kratos sin exigir al usuario instalar Python, compiladores, CMake, Visual Studio, MKL u otras herramientas?



Analizar:

PyInstaller;

Nuitka;

otros mecanismos relevantes.


No asumir que funcionan.

Buscar evidencia.


---

17. INVESTIGACIÓN CRÍTICA Nº 13

TAMAÑO Y DEPENDENCIAS

Determinar:

tamaño de wheels;

tamaño instalado;

dependencias;

DLL;

Applications necesarias;

componentes opcionales.


Diferenciar:

Core mínimo

de:

Instalación necesaria para nuestro caso


---

18. INVESTIGACIÓN CRÍTICA Nº 14

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

distribución binaria;

obligaciones.


No asumir que todos tienen la misma licencia.


---

19. INVESTIGACIÓN CRÍTICA Nº 15

RENDIMIENTO

No inventar benchmarks.

Buscar benchmarks oficiales.

Si no existen comparaciones fiables:

Kratos vs SciPy
Kratos vs PyPardiso

indicarlo.

Determinar qué benchmark debería realizarse posteriormente para nuestro proyecto.

Proponer un benchmark reproducible para comparar las alternativas.


---

20. COMPARACIÓN ARQUITECTÓNICA

Comparar:

OPCIÓN A

Gmsh
+
FEA propio
+
SciPy
+
PyPardiso
+
SIMP propio

OPCIÓN B

Gmsh
+
Kratos Structural Mechanics
+
Kratos Optimization

OPCIÓN C

Gmsh
+
Kratos FEA
+
Optimization propio

Comparar:

control;

complejidad;

rendimiento;

mantenimiento;

extensibilidad;

SIMP;

Topology Optimization;

Shape Optimization;

diseño generativo;

Windows;

distribución;

licencias.



---

21. MATRIZ FINAL

Requisito	Kratos	Desarrollo propio	Mejor opción	Estado de evidencia

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
Regiones optimizables				
Diseño generativo				
Multiphysics				
Windows				
Standalone				
Rendimiento				
Mantenimiento				
Licencia				
Extensibilidad				



---

22. SI SE PROPORCIONAN INFORMES PREVIOS

Si el usuario proporciona informe_geminis.md y/o informe_claude.md, utilizarlos únicamente como material de comparación.

No considerarlos evidencia definitiva.

Crear:

CORRECCIONES A GEMINI

y:

CORRECCIONES A CLAUDE

Para cada afirmación relevante:

Afirmación
↓
Evidencia encontrada
↓
Conclusión
↓
Impacto arquitectónico

Si una afirmación está correctamente respaldada:

> CONFIRMADA.



Si no se proporcionan los informes, simplemente omitir estas secciones y continuar con la investigación independiente.


---

23. DECISIÓN ARQUITECTÓNICA

Al finalizar debes recomendar una:

OPCIÓN A

Mantener FEA propio.

OPCIÓN B

Migrar completamente a Kratos.

OPCIÓN C

Arquitectura híbrida.

Si recomiendas arquitectura híbrida, especificar:

Importación → ?
Mallado → ?
FEA → ?
Solver → ?
SIMP → ?
Topology Optimization → ?
Shape Optimization → ?
Postprocessing → ?
Diseño generativo → ?
Exportación → ?

La recomendación debe basarse en evidencia técnica.


---

24. IMPACTO SOBRE EL PROYECTO

Determinar:

Qué podemos reutilizar de Kratos

Qué tendríamos que desarrollar nosotros

Qué control perderíamos

Qué complejidad añadiríamos

Qué problemas de distribución aparecerían

Qué riesgos técnicos existirían

Qué ventajas obtendríamos a largo plazo


---

25. REGLAS ABSOLUTAS

NO:

implementar código;

instalar Kratos;

modificar ningún proyecto;

crear archivos;

acceder a repositorios privados;

asumir acceso a nuestro código;

inventar APIs;

inventar benchmarks;

asumir capacidades;

utilizar nombres de clases como única evidencia;

utilizar documentación obsoleta sin verificar;

confundir FEA con Topology Optimization;

confundir Topology Optimization con Shape Optimization;

confundir modificación de malla con modificación CAD;

afirmar que algo es posible simplemente porque matemáticamente podría implementarse.


SÍ:

investigar;

buscar fuentes primarias;

contrastar información;

verificar código/documentación pública;

identificar contradicciones;

identificar limitaciones;

comparar alternativas;

analizar riesgos;

recomendar una arquitectura.



---

26. FORMATO DEL INFORME FINAL

La respuesta debe contener:

1. Resumen ejecutivo


2. Estado actual de Kratos


3. OptimizationApplication vs TopologyOptimizationApplication


4. Tet4


5. Acceso a Ke


6. Matriz K


7. SIMP


8. Sensibilidades


9. Topology Optimization


10. Shape Optimization


11. Superficies protegidas


12. Mejora estructural


13. Diseño generativo


14. Gmsh + Kratos


15. Windows


16. Distribución standalone


17. Dependencias


18. Licencias


19. Rendimiento


20. Comparación arquitectónica


21. Matriz final de decisión


22. Riesgos


23. Recomendación final



Todas las afirmaciones críticas deben indicar:

> VERIFICADO / PARCIALMENTE VERIFICADO / INFERENCIA / NO VERIFICADO / NO DISPONIBLE



y proporcionar la fuente correspondiente.


---

27. CONCLUSIÓN OBLIGATORIA

Terminar con una decisión clara:

> UTILIZAR KRATOS



o:

> NO UTILIZAR KRATOS



o:

> UTILIZAR ARQUITECTURA HÍBRIDA



Explicar:

qué descubrimos;

qué capacidades están realmente disponibles;

qué afirmaciones anteriores eran incorrectas;

qué capacidades requieren desarrollo propio;

qué ventajas proporciona Kratos;

qué riesgos introduce;

qué impacto tendría sobre nuestra arquitectura.


La conclusión debe responder especialmente:

> ¿Kratos es realmente una ventaja estratégica para nuestro proyecto o solamente un solver FEA más potente?



Y:

> ¿Kratos nos acerca de manera significativa a nuestro objetivo futuro de Topology Optimization + Shape Optimization + mejora estructural + diseño generativo?




---

28. RESUMEN EJECUTIVO FINAL

Cerrar con máximo 15 puntos, indicando:

principales descubrimientos;

capacidades confirmadas;

capacidades parciales;

capacidades inexistentes o no verificadas;

errores encontrados en investigaciones anteriores, si fueron proporcionadas;

qué tendríamos que desarrollar;

principales riesgos;

ventajas;

desventajas;

impacto arquitectónico;

arquitectura recomendada;

decisión final sobre Kratos.


No realizar ninguna acción fuera de la investigación.

Tu único entregable es la información técnica investigada y la recomendación fundamentada.


---