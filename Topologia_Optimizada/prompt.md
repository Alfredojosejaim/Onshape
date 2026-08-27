

# INTEGRACIÓN DE KRATOS MULTIPHYSICS EN EL PROYECTO

## OBJETIVO

Kratos Multiphysics ya fue evaluado y se considera **VIABLE** como motor FEA del proyecto.

La etapa de evaluación queda oficialmente **CERRADA**.

A partir de este momento, Kratos deja de ser una tecnología experimental y pasa a formar parte de la arquitectura de producción de **Topología Optimizada**.

El objetivo de esta intervención es:

> **INTEGRAR KRATOS REALMENTE EN EL PROYECTO Y PREPARARLO COMO MOTOR FEA DEL CORE.**

NO volver a investigar si Kratos es viable.

NO repetir experimentos generales de viabilidad.

NO crear una nueva fase de investigación.

---

# 0. INICIALIZACIÓN DEL REGISTRO DE LA NUEVA ETAPA

Antes de comenzar la implementación, preparar `resumen_implementacion.md` para que funcione como registro exclusivo de esta nueva etapa.

## 0.1 Lectura previa obligatoria

Antes de modificarlo:

1. Leer completamente `resumen_implementacion.md`.
2. Identificar la información histórica existente.
3. Determinar qué información ya está documentada en otros archivos.
4. Conservar cualquier información histórica que no exista en otro lugar y que sea necesaria para comprender decisiones técnicas anteriores.

## 0.2 Limpieza controlada

Una vez comprendido el contenido:

- eliminar del resumen operativo la información histórica que ya esté documentada en otros archivos;
- evitar duplicaciones;
- no eliminar documentación técnica de las pruebas de Kratos;
- no eliminar scripts experimentales útiles como referencia;
- no eliminar evidencia utilizada para determinar que Kratos es viable.

El objetivo NO es borrar la historia del proyecto.

El objetivo es separar:

```text
DOCUMENTACIÓN HISTÓRICA
        ↓
REFERENCIA TÉCNICA

de:

RESUMEN_IMPLEMENTACION.md
        ↓
REGISTRO OPERATIVO ACTUAL

0.3 Nuevo punto de partida

resumen_implementacion.md debe quedar preparado como punto cero de:

> INTEGRACIÓN DE KRATOS EN PRODUCCIÓN



Debe registrar inicialmente:

fecha;

nombre de la etapa;

decisión previa: KRATOS VIABLE / ADOPTADO;

documentación de pruebas utilizada como referencia;

objetivo de la integración;

estado inicial del proyecto.


A partir de ese momento, registrar allí únicamente:

acciones realizadas;

archivos modificados;

pruebas ejecutadas;

resultados;

errores actuales;

bloqueos actuales;

investigaciones solicitadas;

soluciones aplicadas;

decisiones tomadas;

estado real;

pendientes actuales.



---

1. LECTURA OBLIGATORIA

Antes de modificar código:

1. Leer README.md.


2. Leer prompt.md.


3. Leer metodologia.md.


4. Leer resumen_implementacion.md después de su preparación.


5. Revisar la estructura actual del repositorio.


6. Revisar la documentación existente de las pruebas de Kratos.


7. Revisar los scripts experimentales utilizados durante la validación.


8. Revisar los resultados obtenidos.


9. Identificar las soluciones que ya fueron encontradas.


10. Identificar qué conocimiento de esos experimentos debe reutilizarse.



NO asumir que un script experimental debe copiarse directamente al proyecto.


---

2. PRINCIPIO DE REUTILIZACIÓN

Las pruebas anteriores de Kratos ya demostraron su viabilidad.

Utilizar esa documentación como referencia para la integración.

Analizar específicamente:

inicialización;

módulos utilizados;

Model;

ModelPart;

nodos;

elementos;

propiedades;

materiales;

condiciones de frontera;

cargas;

DOFs;

solver;

estrategias;

resultados;

extracción de resultados;

configuración;

versiones;

problemas encontrados;

soluciones encontradas.


NO repetir investigaciones que ya fueron resueltas.

NO crear nuevos experimentos simplemente para volver a demostrar que Kratos funciona.


---

3. ARQUITECTURA OBJETIVO

La integración debe respetar estrictamente la arquitectura standalone.

El flujo objetivo es:

STEP
 ↓
STEP ADAPTER
 ↓
CADModel
 ↓
MALLA
 ↓
KRATOS
 ↓
FEA
 ↓
RESULTADOS
 ↓
CORE

Kratos debe actuar como motor FEA interno.

La aplicación NO debe depender de:

Onshape;

SolidWorks;

Fusion;

FreeCAD;

AutoCAD;

APIs CAD externas;

OAuth;

plugins;

extensiones;

servicios CAD externos.



---

4. ANALIZAR LA ARQUITECTURA EXISTENTE

Antes de implementar, determinar:

dónde debe integrarse Kratos;

qué componente será responsable del FEA;

cómo recibe la malla;

cómo recibe materiales;

cómo recibe cargas;

cómo recibe condiciones de frontera;

cómo devuelve resultados al Core.


Si la arquitectura existente ya proporciona una interfaz adecuada, reutilizarla.

Si es necesario crear una interfaz/adaptador, hacerlo de forma simple y justificada.

NO crear abstracciones innecesarias para futuros motores FEA.


---

5. INTEGRACIÓN PROGRESIVA

Implementar en este orden:

ETAPA A — Inicialización

Integrar correctamente Kratos dentro del entorno real del proyecto.

Verificar que los módulos requeridos puedan importarse y utilizarse.


---

ETAPA B — Modelo

Crear correctamente el Model / ModelPart necesario para el cálculo.


---

ETAPA C — Malla

Transferir una malla válida desde la arquitectura del proyecto hacia Kratos.


---

ETAPA D — Material

Configurar propiedades y material de acuerdo con la arquitectura del proyecto.


---

ETAPA E — Condiciones de frontera

Transferir correctamente las restricciones.


---

ETAPA F — Cargas

Transferir correctamente las cargas.


---

ETAPA G — Solver

Configurar y ejecutar el solver correspondiente.


---

ETAPA H — Resultados

Extraer resultados relevantes, como:

desplazamientos;

tensiones;

energía;

compliance;


según corresponda a la implementación actual.


---

ETAPA I — Retorno al Core

Los resultados deben poder ser utilizados por el Core sin depender directamente de detalles innecesarios de Kratos.


---

6. VALIDACIÓN

Cada etapa debe probarse antes de continuar.

Las pruebas deben demostrar funcionamiento real.

NO utilizar como evidencia:

mocks;

resultados inventados;

geometría ficticia para demostrar integración real;

fallbacks que oculten errores;

datos falsificados.


La geometría sintética puede utilizarse únicamente para validar componentes aislados cuando sea técnicamente apropiado.

Cuando se valide integración real, utilizar datos reales del pipeline correspondiente.


---

7. NO REHACER LA VALIDACIÓN DE VIABILIDAD

La pregunta:

> "¿Kratos funciona?"



ya está respondida.

La pregunta actual es:

> "¿Cómo integramos correctamente Kratos en nuestra arquitectura?"



Los experimentos existentes son evidencia y referencia.

No deben convertirse nuevamente en una fase de investigación.


---

8. PROTOCOLO OBLIGATORIO ANTE ERRORES

Aplicar estrictamente el protocolo establecido en metodologia.md.

Corrección autónoma permitida

Si aparece un error y la causa es completamente evidente, se permite:

> UNA única corrección fundamentada.



Después debe ejecutarse nuevamente la prueba.

Si funciona

Continuar.

Si falla

DETENERSE.

Si la causa no es evidente

DETENERSE inmediatamente.

Está prohibido iniciar una cadena de intentos especulativos.

NO hacer:

ERROR
 ↓
nuevo script
 ↓
ERROR
 ↓
otro enfoque
 ↓
ERROR
 ↓
otra modificación


---

9. REGISTRO OBLIGATORIO DE BLOQUEOS

Cuando exista un problema que no pueda resolverse mediante la corrección autónoma permitida, registrarlo inmediatamente en:

resumen_implementacion.md

NO crear un archivo independiente para cada problema.

El registro debe contener:

fecha;

componente afectado;

funcionalidad;

entorno;

versión de Kratos;

versión de Python;

comando ejecutado;

archivo;

función;

traceback completo;

salida relevante;

modificación realizada;

resultado;

hechos comprobados;

hipótesis;

información desconocida;

pregunta técnica concreta que debe investigarse.


Clasificarlo como:

> BLOQUEADO — REQUIERE INVESTIGACIÓN




---

10. REGLA DE NO DESPERDICIO

Una vez registrado un bloqueo:

NO continuar modificando código relacionado con ese problema mediante especulación.

NO generar múltiples scripts alternativos.

NO cambiar de enfoque arbitrariamente.

NO intentar "forzar" una solución.

El objetivo es conservar un tracker técnico preciso que pueda entregarse posteriormente para investigación externa.


---

11. INVESTIGACIÓN EXTERNA

Cuando exista un bloqueo, formular una pregunta técnica concreta.

La investigación deberá priorizar:

1. documentación oficial de Kratos;


2. documentación de la versión instalada;


3. ejemplos oficiales;


4. repositorio oficial;


5. issues oficiales;


6. fuentes técnicas confiables cuando sean necesarias.



La investigación debe buscar:

causa;

comportamiento esperado;

API correcta;

restricciones;

solución compatible con nuestra versión;

ejemplo funcional cuando exista.


La solución encontrada debe poder relacionarse directamente con el tracker registrado.


---

12. EJECUCIÓN DE LA SOLUCIÓN

Una vez obtenida una solución fundamentada:

1. Leer nuevamente el tracker.


2. Comprender la solución.


3. Aplicar únicamente los cambios necesarios.


4. Ejecutar nuevamente la prueba original.


5. Verificar el resultado.


6. Ejecutar las pruebas relevantes de regresión.


7. Actualizar el tracker.


8. Cambiar el estado del bloqueo únicamente cuando exista evidencia.




---

13. NO OCULTAR ERRORES

Está prohibido:

ocultar errores;

minimizar errores;

eliminar tests que fallen;

reemplazar errores por mocks;

introducir fallbacks silenciosos;

marcar como completado algo que no funciona;

cambiar los criterios de aceptación;

modificar la arquitectura únicamente para evitar un error.


La precisión del estado es prioritaria.


---

14. CRITERIO DE COMPLETADO

Una parte de la integración solo puede marcarse como:

> COMPLETADO



cuando:

está implementada;

funciona;

fue probada;

existe evidencia;

es reproducible;

respeta la arquitectura standalone;

no depende de mocks;

no contiene dependencias ocultas;

no rompe funcionalidades previamente verificadas.


Si no se cumplen estas condiciones:

> PARCIAL / PENDIENTE / BLOQUEADO



según corresponda.


---

15. NO REGRESIÓN

Antes de finalizar:

ejecutar las pruebas existentes relevantes;

ejecutar las nuevas pruebas;

verificar integración;

comprobar que no se introdujeron dependencias incompatibles;

comprobar que no se rompieron funcionalidades existentes.


Si aparece una regresión:

> NO declarar la etapa completada.




---

16. CONTROL DEL ALCANCE

Durante esta intervención NO implementar:

interfaz gráfica definitiva;

Onshape;

plugins CAD;

extensiones;

conectores CAD;

otros CAD;

otros motores FEA;

diseño generativo;

funcionalidades futuras no necesarias;

nuevas bibliotecas no justificadas.


El objetivo exclusivo es:

> INTEGRAR KRATOS COMO MOTOR FEA REAL DEL PROYECTO.




---

17. DOCUMENTACIÓN

Actualizar resumen_implementacion.md durante toda la intervención.

Registrar:

objetivo;

auditoría inicial;

análisis de las pruebas existentes;

decisiones;

archivos modificados;

implementación;

pruebas;

resultados;

errores;

bloqueos;

investigaciones;

soluciones;

estado;

pendientes.


NO duplicar innecesariamente la documentación histórica de los experimentos.


---

18. AUDITORÍA FINAL

Antes de finalizar la intervención:

1. Comparar implementación con README.md.


2. Comparar implementación con prompt.md.


3. Verificar cumplimiento de metodologia.md.


4. Revisar código modificado.


5. Ejecutar tests relevantes.


6. Revisar resultados.


7. Revisar bloqueos.


8. Actualizar resumen_implementacion.md.


9. Clasificar cada componente.


10. Identificar pendientes reales.



Presentar:

COMPLETADO
PARCIAL
PENDIENTE
BLOQUEADO


---

19. RESULTADO ESPERADO

Al terminar, Kratos debe haber pasado de:

TECNOLOGÍA VALIDADA

a:

TECNOLOGÍA INTEGRADA EN EL PROYECTO

No es necesario que todo el sistema FEA esté terminado en una sola intervención.

Lo importante es construir progresivamente una integración real, verificable y limpia.


---

REGLA SUPREMA

KRATOS YA FUE VALIDADO COMO VIABLE.

NO volver a investigar su viabilidad.

NO repetir experimentos innecesarios.

A partir de ahora:

ANALIZAR PRUEBAS EXISTENTES
        ↓
INTEGRAR
        ↓
PROBAR
        ↓
¿ERROR?
   ├── CAUSA EVIDENTE
   │      ↓
   │   UNA CORRECCIÓN
   │      ↓
   │   PROBAR
   │      ↓
   │   FALLA → BLOQUEAR
   │
   └── CAUSA NO EVIDENTE
          ↓
       BLOQUEAR
          ↓
       REGISTRAR
          ↓
       INVESTIGAR
          ↓
       SOLUCIÓN
          ↓
       IMPLEMENTAR
          ↓
       VERIFICAR

La prioridad es funcionalidad real, trazabilidad y eficiencia.

No se permite desperdiciar tiempo, tokens ni archivos mediante ciclos de ensayo y error especulativo.