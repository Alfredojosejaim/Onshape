
# AUDITORÍA DE INTEGRACIÓN KRATOS — EXTRACCIÓN Y REGISTRO DE BLOQUEOS

## OBJETIVO

La etapa anterior de integración de Kratos Multiphysics ya fue ejecutada.

Esta intervención NO tiene como objetivo solucionar problemas.

Su único objetivo es:

> **AUDITAR EL ESTADO ACTUAL DE LA INTEGRACIÓN, IDENTIFICAR LOS BLOQUEOS EXISTENTES Y DOCUMENTARLOS CON TODA LA INFORMACIÓN NECESARIA PARA REALIZAR POSTERIORMENTE UNA INVESTIGACIÓN TÉCNICA FOCALIZADA.**

Kratos ya fue evaluado y adoptado.

NO investigar nuevamente su viabilidad.

NO implementar soluciones nuevas.

NO realizar refactorizaciones.

NO continuar desarrollando funcionalidades.

---

# 1. LECTURA OBLIGATORIA

Antes de realizar cualquier acción:

1. Leer `README.md`.
2. Leer `prompt.md`.
3. Leer `metodologia.md`.
4. Leer completamente `resumen_implementacion.md`.
5. Revisar la estructura actual del repositorio.
6. Revisar el código relacionado con la integración de Kratos.
7. Revisar las pruebas existentes.
8. Revisar los resultados de las pruebas.
9. Revisar los experimentos y documentación previa de Kratos.
10. Identificar qué partes de la integración ya fueron implementadas.
11. Identificar qué problemas ya fueron resueltos.
12. Identificar qué problemas continúan abiertos.

NO asumir que la documentación representa necesariamente el estado real.

Contrastar:

```text
DOCUMENTACIÓN
      ↓
CÓDIGO
      ↓
PRUEBAS
      ↓
RESULTADOS


---

2. AUDITAR EL PIPELINE ACTUAL

Analizar el estado real de:

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

Para cada componente determinar:

qué existe;

qué funciona;

qué fue probado;

qué evidencia existe;

qué está incompleto;

qué falla;

qué depende de otro componente;

qué está bloqueado.


Clasificar cada componente como:

COMPLETADO
PARCIAL
PENDIENTE
BLOQUEADO

No utilizar COMPLETADO si no existe evidencia suficiente.


---

3. EJECUTAR ÚNICAMENTE PRUEBAS DE VERIFICACIÓN

Se permite ejecutar pruebas existentes y pruebas mínimas necesarias para confirmar el estado actual.

El objetivo de estas pruebas es:

> REPRODUCIR Y CARACTERIZAR LOS PROBLEMAS EXISTENTES.



NO crear nuevas implementaciones para intentar solucionarlos.

NO modificar el código para hacer que una prueba pase.

NO cambiar la arquitectura.

NO introducir dependencias nuevas.


---

4. REGLA ABSOLUTA ANTE UN ERROR

Cuando aparezca un error:

SI LA CAUSA ES OBVIA

NO corregirlo.

En esta etapa tampoco se permite aplicar la corrección autónoma.

El objetivo actual es exclusivamente documentar el problema.

SI LA CAUSA NO ES OBVIA

DETENER la investigación inmediatamente.

NO intentar otro enfoque.

NO modificar código.

NO generar otro script.

NO probar otra API.

NO cambiar parámetros al azar.

NO realizar ensayo y error.


---

5. PROHIBICIÓN DE RESOLUCIÓN

Durante esta intervención está TERMINANTEMENTE PROHIBIDO intentar resolver los problemas encontrados.

NO hacer:

ERROR
 ↓
HIPÓTESIS
 ↓
CAMBIO
 ↓
ERROR
 ↓
OTRO CAMBIO
 ↓
ERROR

NO hacer múltiples intentos.

NO buscar una solución improvisada.

NO instalar bibliotecas adicionales para intentar solucionar el problema.

NO modificar versiones.

NO cambiar Kratos por otra tecnología.

NO modificar la arquitectura para evitar el error.

La resolución de los bloqueos será una etapa posterior.


---

6. IDENTIFICACIÓN DEL BLOQUEO

Cada problema que impida avanzar debe convertirse en un registro técnico independiente dentro de:

resumen_implementacion.md

NO crear archivos nuevos para cada problema.

NO duplicar trackers en múltiples documentos.


---

7. FORMATO OBLIGATORIO DEL TRACKER

Para cada bloqueo utilizar esta estructura:

## BLOQUEO KRATOS — [ID]

### Estado

BLOQUEADO — REQUIERE INVESTIGACIÓN

### Componente

[Componente afectado]

### Funcionalidad

[Qué se intenta hacer]

### Objetivo

[Qué debería ocurrir]

### Resultado actual

[Qué ocurre realmente]

### Entorno

- Sistema operativo:
- Python:
- Kratos:
- Compilación/instalación:
- Arquitectura:
- Otras versiones relevantes:

### Archivo

[Ruta exacta]

### Función / clase

[Nombre exacto]

### Punto de ejecución

[Dónde ocurre el problema]

### Comando ejecutado

[Comando completo]

### Entrada utilizada

[Datos, archivos, malla, parámetros, etc.]

### Salida obtenida

[Salida relevante completa]

### Traceback

[Traceback completo, si existe]

### Resultado esperado

[Qué debería suceder]

### Resultado observado

[Qué sucedió]

### Hechos comprobados

[Únicamente hechos demostrados]

### Hipótesis

[Posibles causas, claramente marcadas como hipótesis]

### Información desconocida

[Qué todavía no sabemos]

### Intentos realizados previamente

[Únicamente intentos que realmente existan en el historial]

### Soluciones anteriores relacionadas

[Si existe alguna documentada]

### Pregunta técnica para investigación

[Pregunta concreta que deberá responder la investigación]

### Dependencias

[Qué componentes están bloqueados por este problema]

### Prioridad

CRÍTICA / ALTA / MEDIA / BAJA


---

8. TRACEBACK COMPLETO

Cuando exista un traceback:

NO resumirlo.

NO eliminar líneas relevantes.

NO reemplazarlo por:

> "Kratos dio un error."



Conservar el traceback completo.

También registrar:

comando exacto;

versión;

archivo;

función;

entrada utilizada;

salida relevante.


La finalidad es que otra persona o IA pueda investigar el problema sin tener que reproducir primero todo el contexto.


---

9. DIFERENCIAR HECHOS DE HIPÓTESIS

Esto es obligatorio.

Ejemplo:

HECHO:
Kratos lanza RuntimeError al ejecutar X.

HIPÓTESIS:
La configuración Y podría ser incompatible con Z.

NO CONFIRMADO:
No sabemos todavía si Y es realmente la causa.

NO presentar una hipótesis como causa confirmada.


---

10. AGRUPACIÓN Y DEPENDENCIAS

Si varios errores derivan claramente del mismo bloqueo raíz:

No crear múltiples trackers redundantes.

Identificar:

BLOQUEO RAÍZ
      ↓
 ┌────┴────┐
 ↓         ↓
ERROR A   ERROR B

Si existen bloqueos independientes:

BLOQUEO A
BLOQUEO B
BLOQUEO C

registrarlos por separado.


---

11. PRIORIZACIÓN

Asignar prioridad según impacto:

CRÍTICA

Impide continuar con prácticamente toda la integración.

ALTA

Impide completar un componente fundamental.

MEDIA

Afecta una funcionalidad importante pero permite continuar parcialmente.

BAJA

Problema secundario que no bloquea el desarrollo inmediato.

Después determinar el orden recomendado de investigación.


---

12. NO CREAR DOCUMENTACIÓN INNECESARIA

No crear:

nuevos informes;

nuevos archivos de investigación;

nuevos README;

nuevas carpetas;

documentos temporales;

copias de los resultados.


Utilizar exclusivamente:

resumen_implementacion.md

para registrar los bloqueos actuales.

La documentación existente de las pruebas de Kratos debe permanecer como referencia.


---

13. NO MODIFICAR EL CÓDIGO PARA SOLUCIONAR

Durante esta intervención, las modificaciones al código están prohibidas salvo que sean estrictamente necesarias para:

instrumentación temporal;

obtener información diagnóstica;

reproducir un error existente.


Si se realiza una modificación diagnóstica:

1. documentarla;


2. utilizarla únicamente para obtener evidencia;


3. revertirla después, salvo que sea claramente necesaria y permanente.



NO convertir una modificación diagnóstica en una implementación.


---

14. REGLA DE DETENCIÓN

Cuando todos los problemas reproducibles hayan sido:

identificados;

caracterizados;

registrados;

clasificados;

priorizados;


DETENERSE.

No comenzar a resolverlos.

No continuar desarrollando.

No realizar investigación técnica externa en esta etapa.


---

15. AUDITORÍA FINAL

Antes de terminar:

1. Revisar nuevamente el código relevante.


2. Revisar las pruebas ejecutadas.


3. Revisar los resultados.


4. Revisar todos los trackers.


5. Verificar que cada bloqueo tenga suficiente información.


6. Verificar que no existan hipótesis presentadas como hechos.


7. Verificar que los traceback estén completos.


8. Verificar que los comandos puedan reproducirse.


9. Verificar que no se hayan introducido cambios innecesarios.


10. Actualizar resumen_implementacion.md.




---

16. INFORME FINAL

Al finalizar, presentar exclusivamente:

ESTADO DE LA INTEGRACIÓN

COMPLETADO:
[...]

PARCIAL:
[...]

PENDIENTE:
[...]

BLOQUEADO:
[...]

BLOQUEOS ENCONTRADOS

Para cada bloqueo indicar:

ID;

componente;

prioridad;

impacto;

dependencia;

pregunta técnica que debe investigarse.


ORDEN RECOMENDADO DE INVESTIGACIÓN

Indicar:

1. BLOQUEO [...]
2. BLOQUEO [...]
3. BLOQUEO [...]

explicando brevemente por qué ese orden.

CAMBIOS REALIZADOS

Indicar los archivos modificados.

Si no hubo modificaciones:

> No se realizaron modificaciones funcionales.




---

17. CRITERIO DE ÉXITO

Esta intervención será exitosa si:

el estado real de la integración está claramente determinado;

todos los bloqueos relevantes están identificados;

cada bloqueo tiene un tracker completo;

los problemas pueden investigarse sin repetir todo el proceso;

no se desperdiciaron recursos en intentos especulativos;

no se introdujeron soluciones no investigadas;

no se crearon archivos innecesarios;

el repositorio queda listo para la siguiente etapa de investigación focalizada.



---

REGLA SUPREMA

ESTA INTERVENCIÓN NO RESUELVE PROBLEMAS.

ESTA INTERVENCIÓN IDENTIFICA Y DOCUMENTA PROBLEMAS.

El flujo obligatorio es:

AUDITAR
   ↓
REPRODUCIR
   ↓
CARACTERIZAR
   ↓
REGISTRAR
   ↓
PRIORIZAR
   ↓
DETENER

Después de esta etapa:

TRACKER COMPLETO
      ↓
INVESTIGACIÓN TÉCNICA
      ↓
SOLUCIÓN FUNDAMENTADA
      ↓
NUEVO PROMPT DE IMPLEMENTACIÓN

No intentes solucionar ningún bloqueo durante esta intervención.

No realices ensayo y error.

No generes archivos adicionales.

No avances a la siguiente funcionalidad hasta que los bloqueos que la afectan estén correctamente identificados y documentados.