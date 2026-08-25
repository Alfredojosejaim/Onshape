
# METODOLOGÍA ESTRICTA DE DESARROLLO Y VALIDACIÓN

## 1. PROPÓSITO

Este archivo define las reglas obligatorias que toda IA o desarrollador debe seguir al modificar el proyecto **Topología Optimizada**.

El proyecto tiene como arquitectura principal:

> **STANDALONE FIRST**

La aplicación debe desarrollarse como un producto independiente de cualquier programa, plataforma o servicio CAD externo.

Estas reglas tienen como objetivo impedir:

- implementaciones incompletas;
- falsas conclusiones de cumplimiento;
- funcionalidades simuladas;
- dependencias innecesarias;
- avance sobre etapas que todavía tienen dependencias sin resolver;
- incorporación prematura de integraciones CAD externas;
- duplicación de funcionalidades;
- regresiones;
- documentación que no represente el estado real del código.

Estas reglas son obligatorias.

---

# 2. ARQUITECTURA FUNDAMENTAL

La aplicación principal debe funcionar de forma completamente independiente.

La arquitectura actual es:

```text
ARCHIVO STEP LOCAL
       ↓
  STEP ADAPTER
       ↓
    CADModel
       ↓
      CORE
       ↓
 ┌─────┼─────┐
 ↓     ↓     ↓
MALLA  FEA  TOP. OPT.
       ↓
   RESULTADOS
       ↓
    EXPORTACIÓN

La aplicación no debe depender de:

Onshape;

SolidWorks;

Fusion;

FreeCAD;

AutoCAD;

ningún otro CAD;

APIs externas de CAD;

OAuth de plataformas CAD;

cuentas externas;

plugins;

extensiones externas.



---

3. REGLA ABSOLUTA DE INDEPENDENCIA

Una implementación solo es válida si la aplicación puede funcionar en una computadora donde:

no exista ningún programa CAD instalado;

no exista una cuenta de una plataforma CAD;

no exista una sesión de CAD abierta;

no exista conexión con un servicio CAD externo.


El modelo de entrada inicial debe provenir de un archivo local.

El formato prioritario actual es:

STEP
.stp
.step

La funcionalidad standalone debe ser siempre prioritaria frente a cualquier integración externa.


---

4. FUTURAS INTEGRACIONES CAD

Las integraciones con CAD externos son funcionalidades futuras.

Podrán existir posteriormente:

Onshape
SolidWorks
Fusion
FreeCAD
otros CAD

mediante módulos, plugins, conectores o adaptadores.

Sin embargo:

> NINGUNA INTEGRACIÓN CAD EXTERNA FORMA PARTE DE LAS DEPENDENCIAS DEL PRODUCTO ACTUAL.



No desarrollar estas integraciones durante las etapas standalone salvo que prompt.md lo indique explícitamente.

Una futura integración debe conectarse a la aplicación, nunca convertirse en requisito de funcionamiento del Core.


---

5. JERARQUÍA DE DOCUMENTOS

El proyecto utiliza como mínimo los siguientes documentos:

README.md

Define:

visión del producto;

arquitectura general;

objetivos;

alcance;

prioridades;

futuras integraciones;

definición de éxito.


Es la referencia arquitectónica general del proyecto.


---

prompt.md

Define:

requisitos de la etapa actual;

objetivos;

arquitectura específica de implementación;

restricciones;

comportamiento esperado;

tareas que deben ejecutarse.


Es la especificación técnica de la intervención actual.


---

metodologia.md

Define:

cómo debe trabajar la IA;

cómo debe auditar;

cómo debe implementar;

cómo debe probar;

cómo debe verificar;

cómo debe documentar;

cuándo puede declarar un requisito cumplido.


Es el reglamento obligatorio de desarrollo.


---

resumen_implementacion.md

Registra:

qué se hizo realmente;

qué se verificó;

qué quedó pendiente;

qué problemas aparecieron;

qué decisiones se tomaron;

cuál es el estado real;

cuál es el siguiente paso.


Es el registro del estado real del proyecto.


---

6. JERARQUÍA EN CASO DE CONFLICTO

Cuando exista una contradicción entre documentos:

1. README.md define la arquitectura y visión general.


2. prompt.md define los requisitos concretos de la etapa actual.


3. metodologia.md define las reglas obligatorias de ejecución y validación.


4. resumen_implementacion.md informa el estado real, pero no modifica los requisitos.



Si existe una contradicción real que impida continuar:

> NO asumir.



Debe documentarse y solicitar una decisión antes de implementar una arquitectura contradictoria.


---

7. AUDITORÍA PREVIA OBLIGATORIA

Antes de modificar cualquier código, la IA debe:

1. Leer README.md.


2. Leer prompt.md.


3. Leer metodologia.md.


4. Leer resumen_implementacion.md.


5. Revisar la estructura actual del repositorio.


6. Identificar componentes existentes.


7. Identificar dependencias.


8. Identificar código heredado.


9. Identificar mocks y simulaciones.


10. Identificar funcionalidades parcialmente implementadas.


11. Identificar pruebas existentes.


12. Determinar qué requisitos están realmente cumplidos.



La IA NO debe asumir que la documentación anterior es correcta.

Debe contrastar:

DOCUMENTACIÓN
      ↓
CÓDIGO
      ↓
PRUEBAS
      ↓
FUNCIONAMIENTO REAL


---

8. DETECCIÓN DE ARQUITECTURA HEREDADA

Durante cada auditoría se debe buscar explícitamente:

referencias a Onshape;

OAuth;

FeatureScript;

App Extension;

iframe de Onshape;

REST API de Onshape;

Document ID;

Workspace ID;

Element ID;

credenciales CAD;

conectores CAD;

plugins;

endpoints que dependan de plataformas CAD;

código muerto;

módulos abandonados;

dependencias innecesarias.


Encontrar una referencia a una tecnología anterior NO significa automáticamente que deba eliminarse.

La IA debe determinar:

1. si todavía es necesaria;


2. si es código heredado;


3. si es documentación histórica;


4. si debe migrarse;


5. si debe eliminarse.



Toda decisión debe documentarse.


---

9. CICLO OBLIGATORIO DE TRABAJO

Toda intervención debe seguir este orden:

1. AUDITAR
      ↓
2. PLANIFICAR
      ↓
3. IMPLEMENTAR
      ↓
4. PROBAR
      ↓
5. VERIFICAR
      ↓
6. DOCUMENTAR
      ↓
7. AUDITAR NUEVAMENTE
      ↓
8. DETERMINAR ESTADO

No se debe saltar directamente a la implementación.


---

10. REGLA FUNDAMENTAL DE CUMPLIMIENTO

La existencia de código NO demuestra el cumplimiento de un requisito.

No es evidencia suficiente:

una función;

una clase;

un endpoint;

una interfaz;

un botón;

un comentario;

un mock;

un fallback;

una estructura de datos;

un archivo creado;

un test que pruebe únicamente datos simulados;

documentación que afirme que una funcionalidad existe.


El cumplimiento debe ser:

> FUNCIONAL + VERIFICABLE + REPRODUCIBLE




---

11. ESTADOS OFICIALES

Cada requisito debe clasificarse únicamente como:

COMPLETADO

Solo cuando:

está implementado;

funciona;

cumple la especificación;

fue probado;

existe evidencia suficiente;

no presenta dependencias ocultas incompatibles.



---

PARCIAL

Cuando:

existe parte de la implementación;

pero todavía falta una condición necesaria.



---

PENDIENTE

Cuando:

todavía no existe una implementación funcional.



---

BLOQUEADO

Cuando:

existe una dependencia técnica;

existe una limitación externa;

falta un requisito previo;

o no puede completarse legítimamente en el estado actual del proyecto.


Nunca utilizar COMPLETADO para una funcionalidad teórica.


---

12. PROHIBICIÓN DE SIMULACIONES

Está prohibido utilizar simulaciones para aparentar cumplimiento.

No utilizar como sustituto de funcionalidad real:

datos ficticios;

geometría ficticia;

mallas ficticias;

resultados FEA ficticios;

resultados TopOpt ficticios;

IDs inventados;

respuestas simuladas;

mocks;

fallbacks que oculten errores.


Los mocks y datos sintéticos pueden utilizarse exclusivamente para:

tests unitarios;

pruebas de componentes aislados;

desarrollo temporal claramente identificado.


Nunca pueden utilizarse como evidencia de funcionamiento real del sistema.


---

13. GEOMETRÍA REAL

La aplicación debe trabajar progresivamente con geometría real importada desde archivos.

La geometría sintética puede utilizarse para:

tests unitarios;

validaciones matemáticas;

pruebas de componentes;

debugging.


Pero no puede utilizarse para afirmar que el pipeline de importación CAD funciona.

Ejemplo:

Cubo generado por código

puede validar el solver.

Pero no demuestra:

STEP
 ↓
STEP Adapter
 ↓
CADModel

funcionando correctamente.


---

14. IMPORTACIÓN STEP

La primera entrada CAD oficial del producto es STEP.

Cuando una tarea involucre importación STEP, la prueba debe utilizar un archivo STEP real.

Debe verificarse como mínimo:

apertura del archivo;

lectura de geometría;

detección de cuerpos;

extracción de geometría relevante;

conversión al modelo interno;

manejo de errores;

modelos inválidos;

archivos inexistentes;

archivos corruptos.


No declarar el importador completado solamente porque el parser pueda abrir un archivo de prueba trivial.


---

15. CADModel

El modelo interno debe ser independiente del formato de entrada.

El Core no debe conocer detalles específicos del archivo STEP.

El flujo correcto es:

STEP
 ↓
STEP Adapter
 ↓
CADModel
 ↓
Core

No:

STEP
 ↓
Core
 ↓
lógica específica STEP

El mismo principio permitirá incorporar formatos adicionales en el futuro.


---

16. MALLADO

El mallado debe utilizar geometría real cuando se valide el pipeline completo.

Las pruebas deben distinguir claramente:

Test unitario

Puede utilizar geometría sintética.

Test de integración

Debe verificar:

CADModel
 ↓
Mallador
 ↓
Malla real

Test E2E

Debe utilizar:

STEP real
 ↓
CADModel
 ↓
Malla

La existencia de una malla generada artificialmente no demuestra que el pipeline CAD → malla funcione.


---

17. FEA

El solver FEA debe validarse de manera independiente del CAD.

Esto permite separar:

VALIDACIÓN GEOMÉTRICA

de:

VALIDACIÓN NUMÉRICA

El solver debe poder recibir una malla válida independientemente de su procedencia.

Debe validarse inicialmente con problemas conocidos.

El objetivo inicial es:

Malla Tet4
 ↓
Ke
 ↓
K
 ↓
F
 ↓
Condiciones de frontera
 ↓
K·u=F
 ↓
u
 ↓
Tensiones
 ↓
Compliance


---

18. VALIDACIÓN NUMÉRICA FEA

Antes de considerar el solver funcional debe superar, como mínimo:

18.1 Viga en voladizo

Comparar:

Resultado FEM
      VS
Solución analítica

Debe registrarse:

geometría;

material;

carga;

condiciones de frontera;

tamaño de malla;

desplazamiento obtenido;

desplazamiento analítico;

error relativo.



---

18.2 Patch Test

Validar el comportamiento del elemento Tet4 ante un campo conocido.


---

18.3 Convergencia de malla

Ejecutar diferentes resoluciones.

Registrar:

tamaño de malla
resultado
error

El comportamiento debe ser coherente con la convergencia esperada.


---

19. TOPOLOGÍA OPTIMIZADA

La optimización topológica no debe considerarse funcional hasta que el FEA subyacente esté validado.

Dependencia obligatoria:

MALLA
 ↓
FEA VALIDADO
 ↓
SENSIBILIDADES
 ↓
SIMP
 ↓
OPTIMIZACIÓN

No implementar TopOpt sobre resultados FEA ficticios.


---

20. PREPARACIÓN PARA SIMP

La arquitectura FEA debe permitir posteriormente:

Ke(ρ) = ρᵖ · Ke₀

El solver debe proporcionar los datos necesarios para:

desplazamientos;

compliance;

energía elemental;

sensibilidades;

actualización de densidades.


La implementación debe diseñarse para evitar reescribir el solver durante la integración de SIMP.


---

21. TESTING

Todo requisito debe probarse con el nivel apropiado.

Unitario

Valida componentes individuales.

Integración

Valida interacción entre componentes.

E2E

Valida el flujo completo.

Manual

Se utiliza cuando la interacción requiere intervención humana.

Una prueba unitaria nunca puede presentarse como prueba E2E.


---

22. EVIDENCIA

Todo requisito marcado como COMPLETADO debe tener evidencia.

La evidencia puede ser:

test automatizado;

test de integración;

test E2E;

prueba manual reproducible;

resultado numérico verificable;

archivo de salida verificable.


La evidencia debe registrarse en:

resumen_implementacion.md


---

23. GATES DE CADA ETAPA

Una etapa no puede considerarse finalizada hasta cumplir:

[ ] Requisitos analizados.

[ ] Arquitectura revisada.

[ ] Implementación realizada.

[ ] Errores controlados.

[ ] Tests realizados.

[ ] Integración verificada.

[ ] Evidencia disponible.

[ ] Documentación actualizada.

[ ] Auditoría final realizada.

[ ] No existen dependencias ocultas.

[ ] No existen funcionalidades críticas simuladas.


Si alguno de estos puntos no se cumple:

> La etapa permanece abierta.




---

24. DEPENDENCIAS ENTRE ETAPAS

No se debe avanzar sobre una etapa que dependa de una funcionalidad incompleta.

El flujo actual de dependencias es:

STEP
 ↓
CADModel
 ↓
MALLA
 ↓
FEA
 ↓
VALIDACIÓN FEA
 ↓
SIMP / TOPOPT
 ↓
RESULTADO
 ↓
EXPORTACIÓN

Ejemplos:

Si STEP no funciona:

> No declarar completo el pipeline de importación.



Si CADModel no está correctamente construido:

> No declarar completa la integración con el Core.



Si la malla real no existe:

> No declarar FEA integrado.



Si FEA no está validado:

> No declarar TopOpt funcional.




---

25. CONTROL DEL ALCANCE

La IA debe trabajar únicamente sobre los requisitos de la etapa actual.

No debe implementar funcionalidades futuras solo porque sean técnicamente posibles.

Si descubre una mejora futura:

1. documentarla;


2. clasificarla;


3. no implementarla;


4. continuar con el objetivo actual.




---

26. REGLA ESPECÍFICA SOBRE CAD EXTERNO

Durante el desarrollo standalone:

NO implementar:

Onshape;

FeatureScript;

OAuth;

App Extension;

iframe de Onshape;

conectores;

plugins;

sincronización CAD;

selección desde viewport de un CAD externo;

APIs de plataformas CAD.


Excepto si el prompt.md de una etapa futura lo solicita explícitamente.

La existencia de código heredado de estas tecnologías no implica que deba mantenerse.

Debe auditarse y clasificarse.


---

27. CONTROL DEL CÓDIGO HEREDADO

Cuando existan componentes pertenecientes a una arquitectura anterior:

1. identificar el componente;


2. determinar su función;


3. comprobar si sigue siendo necesario;


4. comprobar si viola la arquitectura standalone;


5. decidir:

conservar;

adaptar;

aislar;

eliminar;



6. documentar la decisión.



No borrar código automáticamente sin comprender sus dependencias.

Pero tampoco mantener código heredado únicamente por miedo a eliminarlo.


---

28. NO REGRESIÓN

Toda nueva implementación debe preservar las funcionalidades previamente verificadas.

Antes de finalizar una modificación:

ejecutar los tests relevantes;

ejecutar tests existentes;

agregar nuevos tests cuando corresponda;

verificar integración;

comprobar que no se hayan introducido dependencias nuevas.


Si una modificación rompe una funcionalidad existente:

> No declarar la etapa completada.



Debe corregirse o documentarse como bloqueador.


---

29. PROHIBICIÓN DE FALSEAR EL ESTADO

La IA nunca debe:

ocultar errores;

minimizar fallos;

cambiar criterios de aceptación;

reinterpretar requisitos para declarar éxito;

eliminar tests que fallen sin justificarlo;

sustituir funcionalidad real por mocks;

ocultar dependencias;

declarar una funcionalidad completa por intención futura.


La precisión del estado es más importante que aparentar progreso.


---

30. DOCUMENTACIÓN OBLIGATORIA

Después de cada intervención significativa debe actualizarse:

resumen_implementacion.md

Debe incluir:

fecha;

iteración;

objetivo;

auditoría inicial;

archivos modificados;

implementación realizada;

dependencias modificadas;

tests ejecutados;

resultados;

errores encontrados;

problemas;

decisiones;

estado final;

pendientes;

bloqueadores;

próximo paso.



---

31. REGISTRO DE DECISIONES

Cuando una solución sea descartada, debe documentarse.

Ejemplo:

> Se descarta el método X porque no cumple los requisitos de precisión establecidos para la generación de malla.



Esto evita volver a implementar soluciones previamente rechazadas.


---

32. DOCUMENTACIÓN DE ACCIONES DE LA IA

La IA debe documentar las acciones significativas realizadas.

Debe poder responder:

¿Qué modificó?
¿Por qué lo modificó?
¿Qué archivos afectó?
¿Qué dependencias cambió?
¿Qué pruebas ejecutó?
¿Qué resultados obtuvo?
¿Qué quedó pendiente?

No se debe documentar únicamente el resultado final.

Debe existir trazabilidad suficiente para reconstruir el proceso.


---

33. AUDITORÍA FINAL

Antes de declarar finalizada una iteración:

1. Comparar implementación contra README.md.


2. Comparar implementación contra prompt.md.


3. Comprobar cumplimiento de metodologia.md.


4. Revisar código modificado.


5. Ejecutar tests.


6. Revisar resultados.


7. Comprobar evidencia.


8. Actualizar resumen_implementacion.md.


9. Clasificar cada requisito.


10. Identificar bloqueadores.


11. Identificar el siguiente paso.



La IA debe presentar explícitamente:

COMPLETADO
PARCIAL
PENDIENTE
BLOQUEADO


---

34. REGLA DE HONESTIDAD TÉCNICA

Cuando exista duda entre:

COMPLETADO

y:

PARCIAL / PENDIENTE

debe elegirse:

PARCIAL / PENDIENTE

Es preferible declarar una funcionalidad incompleta y continuar trabajando que declarar como terminada una funcionalidad que no puede demostrarse.


---

35. REGLA DE NO SOBREDISEÑO

No implementar infraestructura únicamente porque podría ser necesaria en el futuro.

Especialmente:

múltiples CAD;

plugins;

conectores;

APIs externas;

sistemas distribuidos;

abstracciones innecesarias;

funcionalidades de integración futura.


Primero debe funcionar correctamente:

STEP
 ↓
CADModel
 ↓
Malla
 ↓
FEA
 ↓
TopOpt

Después se amplía.


---

36. CRITERIO DE PROGRESO REAL

El progreso del proyecto se mide mediante:

FUNCIONALIDAD REAL
+
PRUEBAS
+
EVIDENCIA
+
DOCUMENTACIÓN

No mediante:

cantidad de archivos;

cantidad de código;

cantidad de endpoints;

cantidad de clases;

cantidad de commits;

interfaces visualmente terminadas.



---

37. OBJETIVO FINAL DE LA METODOLOGÍA

El proyecto debe avanzar mediante funcionalidad real y verificable:

AUDITAR
   ↓
PLANIFICAR
   ↓
IMPLEMENTAR
   ↓
PROBAR
   ↓
VERIFICAR
   ↓
DOCUMENTAR
   ↓
AUDITAR
   ↓
APROBAR
   ↓
AVANZAR

Nunca:

IMPLEMENTAR
   ↓
ASUMIR QUE FUNCIONA
   ↓
DOCUMENTAR COMO COMPLETO
   ↓
AVANZAR


---

38. PRINCIPIO SUPREMO

> TOPología Optimizada es primero una aplicación standalone.



Toda decisión técnica debe respetar este principio.

El producto debe poder existir, ejecutarse y cumplir su función principal sin depender de ninguna aplicación CAD externa.

Las futuras integraciones CAD serán únicamente:

MÓDULOS OPCIONALES
       ↓
IMPORTAR / EXPORTAR / INTERCAMBIAR DATOS
       ↓
APLICACIÓN STANDALONE

Nunca:

CAD EXTERNO
       ↓
DEPENDENCIA OBLIGATORIA
       ↓
APLICACIÓN

La aplicación standalone siempre debe permanecer como el núcleo y producto principal del proyecto.