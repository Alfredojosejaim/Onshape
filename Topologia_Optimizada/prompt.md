
# PRUEBA E2E — MOTOR FEA COMPLETO

## OBJETIVO

Ejecutar el motor FEA completo de extremo a extremo utilizando una entrada real.

La finalidad de esta intervención es comprobar si el sistema puede realizar correctamente todo el flujo de procesamiento desde la entrada hasta la obtención y entrega de los resultados.

La prueba debe realizarse sobre la implementación actual del proyecto.

---

## 1. PREPARACIÓN

Antes de ejecutar:

1. Leer `README.md`.
2. Leer `prompt.md`.
3. Leer `metodologia.md`.
4. Leer `resumen_implementacion.md`.
5. Identificar el procedimiento actual para ejecutar el motor completo.
6. Identificar el archivo STEP real disponible para la prueba.
7. Verificar que el entorno necesario esté disponible.

No modificar el código durante esta preparación.

---

## 2. EJECUCIÓN

Ejecutar el flujo completo utilizando un archivo STEP real.

El procesamiento debe realizarse de forma integral:

```text
ARCHIVO STEP REAL
       ↓
IMPORTACIÓN
       ↓
MODELO INTERNO
       ↓
MALLADO
       ↓
ANÁLISIS FEA
       ↓
SOLVER
       ↓
RESULTADOS
       ↓
SALIDA DEL MOTOR

No sustituir ninguna parte del flujo por datos ficticios o resultados simulados.

No utilizar mocks como sustituto de componentes reales.


---

3. COMPROBACIÓN

Al finalizar la ejecución determinar:

si el archivo STEP fue procesado correctamente;

si el modelo pudo atravesar todo el flujo;

si se generó la malla necesaria;

si se ejecutó realmente el análisis FEA;

si el solver produjo resultados;

si los resultados son válidos;

si los resultados pudieron ser entregados correctamente por el motor.


La prueba debe evaluar el funcionamiento del sistema como un conjunto.


---

4. EVIDENCIA

Registrar:

archivo utilizado;

comando exacto;

entorno de ejecución;

versiones relevantes;

resultado de la ejecución;

resultados obtenidos;

errores producidos, si existen;

archivos de salida generados, si corresponde.


La evidencia debe permitir reproducir posteriormente la prueba.


---

5. REGLA ANTE ERRORES

Esta intervención es exclusivamente de validación.

Si aparece un error:

DETENERSE.

No intentar solucionarlo.

No modificar el código.

No cambiar parámetros arbitrariamente.

No probar enfoques alternativos.

No instalar dependencias nuevas.

No cambiar versiones.

No ejecutar ciclos de ensayo y error.

El error debe registrarse utilizando el protocolo establecido en metodologia.md.


---

6. REGISTRO DE BLOQUEOS

Si el flujo no puede completarse, registrar el problema en:

resumen_implementacion.md

El registro debe contener como mínimo:

punto exacto donde ocurrió;

comando ejecutado;

entrada utilizada;

salida obtenida;

traceback completo, si existe;

resultado esperado;

resultado observado;

hechos comprobados;

hipótesis, separadas claramente de los hechos;

información desconocida;

impacto del problema.


Después de registrar el bloqueo:

> DETENERSE.




---

7. CRITERIO DE ÉXITO

La prueba se considera exitosa únicamente si una entrada STEP real puede recorrer el flujo completo y producir resultados FEA reales.

Debe demostrarse:

ENTRADA REAL
     ↓
PROCESAMIENTO
     ↓
MALLADO
     ↓
FEA REAL
     ↓
RESULTADOS REALES
     ↓
SALIDA

No declarar éxito porque determinados componentes funcionen individualmente.

El criterio es que el flujo completo funcione conjuntamente.


---

8. DOCUMENTACIÓN DEL RESULTADO

Actualizar resumen_implementacion.md.

Si la prueba fue exitosa, registrar:

## VALIDACIÓN E2E — MOTOR FEA

Estado: COMPLETADO

Entrada:
[archivo utilizado]

Comando:
[comando exacto]

Resultado:
[resultado obtenido]

Evidencia:
[evidencia disponible]

Conclusión:
El motor FEA ejecutó correctamente el flujo completo de extremo a extremo.

Si la prueba falla:

Estado: BLOQUEADO

y registrar el bloqueo correspondiente.

No crear archivos adicionales.


---

9. INFORME FINAL

Al finalizar indicar:

RESULTADO

ÉXITO / FALLO / BLOQUEADO

ENTRADA

Archivo utilizado.

EJECUCIÓN

Comando utilizado.

RESULTADOS

Resultados principales obtenidos.

EVIDENCIA

Archivos, registros o resultados que demuestren la ejecución.

CONCLUSIÓN

Determinar claramente si el motor FEA funciona actualmente de extremo a extremo.


---

REGLA SUPREMA

La finalidad de esta intervención es una sola:

> COMPROBAR MEDIANTE UNA EJECUCIÓN REAL QUE EL MOTOR FEA COMPLETO FUNCIONA DE EXTREMO A EXTREMO.



No realizar investigación.

No implementar funcionalidades nuevas.

No solucionar errores durante la prueba.

No realizar ensayo y error.

Ejecutar → observar → documentar → determinar resultado.

Ahora sí: **no hay ninguna referencia a etapas anteriores ni a G/H/I**. La IA recibe una única misión: **poner el motor completo a funcionar y demostrar qué ocurre**.