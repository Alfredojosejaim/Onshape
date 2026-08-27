

# VALIDACIÓN E2E DEL MOTOR FEA — KRATOS

## OBJETIVO

La integración de Kratos Multiphysics en el Core ya fue implementada hasta la Etapa I.

Las etapas A–I deben considerarse implementadas según el estado documentado actualmente.

El objetivo de esta intervención es exclusivamente:

> **EJECUTAR Y VALIDAR EL PIPELINE FEA COMPLETO DE EXTREMO A EXTREMO.**

No realizar una nueva implementación arquitectónica.

No volver a investigar la viabilidad de Kratos.

No repetir los experimentos anteriores.

No modificar funcionalidades que no sean necesarias para ejecutar esta validación.

---

# 1. LECTURA OBLIGATORIA

Antes de ejecutar cualquier prueba:

1. Leer `README.md`.
2. Leer `prompt.md`.
3. Leer `metodologia.md`.
4. Leer `resumen_implementacion.md`.
5. Revisar la implementación actual de las etapas A–I.
6. Revisar la solución aplicada para la Etapa I.
7. Revisar las pruebas existentes.
8. Identificar el procedimiento correcto para ejecutar el pipeline completo.

No asumir que la documentación está actualizada.

Contrastar documentación, código y pruebas.

---

# 2. OBJETIVO DE LA PRUEBA

Ejecutar el flujo real completo:

```text
ARCHIVO STEP REAL
        ↓
STEP ADAPTER
        ↓
CADModel
        ↓
MALLA
        ↓
KRATOS
        ↓
MODEL / MODELPART
        ↓
MATERIAL
        ↓
CONDICIONES DE FRONTERA
        ↓
CARGAS
        ↓
SOLVER FEA
        ↓
DESPLAZAMIENTOS
        ↓
TENSIONES / RESULTADOS
        ↓
COMPLIANCE
        ↓
RESULTADOS ELEMENTALES
        ↓
CORE

La prueba debe utilizar, cuando el pipeline lo permita, datos reales y no mocks.


---

3. PREPARACIÓN

Antes de ejecutar:

1. Verificar el entorno.


2. Verificar la versión de Python.


3. Verificar la versión de Kratos.


4. Verificar que las dependencias necesarias estén disponibles.


5. Verificar que el código actual pueda ejecutarse.


6. Identificar el archivo STEP de prueba utilizado.


7. Verificar que dicho archivo sea válido.


8. Registrar cualquier condición especial necesaria para reproducir la prueba.



No modificar el entorno innecesariamente.


---

4. EJECUCIÓN DEL PIPELINE

Ejecutar el pipeline real en el orden correspondiente.

Verificar individualmente:

4.1 STEP

Confirmar:

apertura correcta;

lectura de geometría;

detección de cuerpos;

generación del modelo interno.



---

4.2 CADModel

Confirmar:

creación correcta;

datos geométricos disponibles;

ausencia de dependencia directa del Core respecto del formato STEP.



---

4.3 MALLA

Confirmar:

generación de la malla;

nodos;

elementos;

conectividad;

transferencia correcta hacia Kratos.



---

4.4 KRATOS

Confirmar:

creación de Model;

creación de ModelPart;

nodos;

elementos;

propiedades;

DOFs;

material.



---

4.5 CONDICIONES DE FRONTERA

Confirmar que las restricciones sean transferidas correctamente.

Verificar que los grados de libertad correspondientes queden correctamente fijados.


---

4.6 CARGAS

Confirmar que las cargas lleguen correctamente al modelo de Kratos.

Verificar:

magnitud;

dirección;

ubicación;

tipo de carga.



---

4.7 SOLVER

Ejecutar el solver real.

Registrar:

configuración;

convergencia;

errores;

tiempo de ejecución, si está disponible;

estado final.



---

4.8 RESULTADOS

Extraer y verificar, según lo implementado:

desplazamientos;

tensiones;

compliance;

energía elemental;

cualquier otro resultado disponible para el Core.


Confirmar que los valores sean numéricamente válidos.

No aceptar:

NaN;

Inf;

valores faltantes;

resultados vacíos;

resultados desconectados del cálculo real.



---

4.9 RETORNO AL CORE

Verificar específicamente la Etapa I.

Los resultados obtenidos por Kratos deben regresar correctamente al Core mediante la interfaz/adaptador implementado.

Confirmar que el Core pueda consumir los resultados sin acceder innecesariamente a detalles internos de Kratos.


---

5. VALIDACIÓN DE EXTREMO A EXTREMO

La prueba se considera exitosa únicamente si puede demostrarse:

STEP REAL
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

No es suficiente que cada componente funcione individualmente.

Debe demostrarse que los datos atraviesan correctamente todo el pipeline.


---

6. VALIDACIONES NUMÉRICAS

Comparar los resultados con las referencias disponibles de las pruebas anteriores.

Cuando exista una referencia conocida:

comparar desplazamientos;

comparar compliance;

comparar resultados relevantes;

calcular diferencia o error cuando sea posible.


No inventar tolerancias.

Utilizar las tolerancias ya establecidas en la documentación existente.

Si no existe una referencia aplicable, indicarlo explícitamente.


---

7. REGLA ESTRICTA ANTE ERRORES

Esta es una VALIDACIÓN, no una sesión de ensayo y error.

Si aparece un error:

ERROR EVIDENTE Y YA CONOCIDO

Si corresponde exactamente a un problema cuya solución ya fue investigada y documentada:

aplicar únicamente la solución ya conocida;

ejecutar nuevamente la prueba;

documentar el resultado.


No buscar otra solución.

ERROR NUEVO

Si aparece un problema que no está contemplado:

> DETENER.



No intentar múltiples soluciones.

No cambiar arbitrariamente el código.

No crear scripts alternativos.

No instalar dependencias para probar soluciones.

No cambiar versiones.

No modificar la arquitectura.

Registrar el problema siguiendo el protocolo de metodologia.md.


---

8. REGISTRO DE ERRORES

Todo error nuevo que impida completar la prueba debe registrarse en:

resumen_implementacion.md

Incluir como mínimo:

componente;

comando;

entorno;

archivo;

función;

entrada;

salida;

traceback completo;

resultado esperado;

resultado observado;

hechos comprobados;

hipótesis;

información desconocida;

impacto;

prioridad.


Estado:

> BLOQUEADO — REQUIERE INVESTIGACIÓN



No crear documentos adicionales.


---

9. NO ALTERAR EL ALCANCE

Durante esta intervención NO implementar:

TopOpt;

diseño generativo;

GUI;

integraciones CAD;

nuevos motores;

nuevas bibliotecas;

funcionalidades futuras.


El objetivo es únicamente:

> VALIDAR EL MOTOR FEA ACTUAL COMPLETO.




---

10. CRITERIO DE ÉXITO

El motor FEA será considerado validado E2E si:

el STEP real es procesado;

el CADModel se genera correctamente;

la malla se genera;

la malla llega a Kratos;

el modelo FEA se configura;

material, cargas y restricciones se aplican;

el solver ejecuta;

los resultados se generan;

los resultados son válidos;

los resultados regresan al Core;

el pipeline completo puede reproducirse.



---

11. DOCUMENTACIÓN

Actualizar resumen_implementacion.md después de la prueba.

Registrar:

fecha;

prueba E2E;

archivo utilizado;

entorno;

versiones;

comando;

etapas ejecutadas;

resultados;

validaciones numéricas;

errores;

bloqueos;

estado final.


No reescribir innecesariamente la documentación histórica.


---

12. AUDITORÍA FINAL

Al terminar:

1. Revisar el resultado completo.


2. Confirmar que todas las etapas A–I participaron.


3. Confirmar que no existieron mocks en el pipeline real.


4. Confirmar que los resultados provienen del solver real.


5. Confirmar que los resultados llegaron al Core.


6. Revisar cualquier error.


7. Actualizar resumen_implementacion.md.



Clasificar:

MOTOR FEA E2E

COMPLETADO
PARCIAL
BLOQUEADO


---

13. INFORME FINAL

Al finalizar, presentar:

PIPELINE

STEP → CADModel → Malla → Kratos → FEA → Resultados → Core

Indicar el estado de cada etapa.

RESULTADOS

Indicar los valores principales obtenidos.

VALIDACIÓN

Indicar las comparaciones realizadas y sus errores.

PROBLEMAS

Indicar cualquier error encontrado.

BLOQUEOS

Indicar únicamente los bloqueos que realmente impidieron completar alguna parte.

VEREDICTO

Responder claramente:

> ¿El motor FEA de Topología Optimizada funciona actualmente de extremo a extremo?



Responder:

SÍ
NO
PARCIALMENTE

y justificarlo únicamente mediante evidencia obtenida durante esta prueba.


---

REGLA SUPREMA

Esta intervención tiene una finalidad:

> DEMOSTRAR, NO SUPONER, QUE EL MOTOR FEA FUNCIONA.



No declarar éxito porque cada componente exista.

No declarar éxito porque las pruebas individuales hayan funcionado.

El éxito requiere:

ENTRADA REAL
    ↓
PIPELINE COMPLETO
    ↓
SOLVER REAL
    ↓
RESULTADOS REALES
    ↓
CORE

Si funciona:

> documentar evidencia y cerrar la validación E2E.



Si falla:

> registrar el bloqueo y detenerse.



No convertir esta validación en otra sesión de ensayo y error.