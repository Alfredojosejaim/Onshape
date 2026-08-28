INTEGRACIÓN DEL MOTOR KRATOS EN EL CORE

OBJETIVO

Convertir la integración actual de Kratos Multiphysics en el motor FEA operativo del Core de Topología Optimizada.

Kratos ya fue investigado, probado y adoptado como motor principal. No repetir la investigación ni volver a evaluar si Kratos es viable.

Las pruebas existentes y su documentación deben utilizarse como referencia técnica para implementar la integración definitiva.

---

1. PRIMERA ACCIÓN — AUDITORÍA

Antes de modificar código:

1. Leer "README.md".
2. Leer "metodologia.md".
3. Leer "resumen_implementacion.md".
4. Revisar la estructura actual del proyecto.
5. Revisar "core/".
6. Revisar "adapters/".
7. Revisar "kratos_adapter.py" y las interfaces relacionadas.
8. Revisar las pruebas de Kratos existentes.
9. Identificar qué código corresponde a:
   - implementación real;
   - pruebas;
   - PoC;
   - código temporal;
   - código heredado;
   - código actualmente utilizado por el Core.

No asumir que un archivo es innecesario únicamente por su nombre.

---

2. LIMPIEZA DEL REPOSITORIO

Antes de comenzar la integración definitiva, realizar una limpieza controlada del repositorio.

Eliminar únicamente:

- archivos temporales;
- scripts experimentales que ya no tengan utilidad;
- duplicados;
- artefactos generados;
- código muerto claramente identificado;
- pruebas PoC que hayan sido sustituidas y cuya evidencia ya esté documentada;
- archivos pertenecientes a arquitecturas abandonadas que ya no tengan ninguna dependencia.

Conservar:

- código utilizado por el producto;
- pruebas relevantes;
- documentación técnica necesaria;
- evidencia de validación de Kratos;
- archivos necesarios para reproducir o verificar la integración;
- "README.md";
- "prompt.md";
- "metodologia.md";
- "resumen_implementacion.md".

Regla crítica

No eliminar archivos dudosos.

Si no puede determinarse con seguridad si un archivo sigue siendo necesario:

«conservarlo y documentar la duda.»

No borrar documentación histórica únicamente para hacer el repositorio más pequeño.

---

3. LIMPIEZA DE "resumen_implementacion.md"

Antes de comenzar esta nueva implementación, limpiar "resumen_implementacion.md".

El archivo debe dejar de funcionar como acumulación indiscriminada de iteraciones anteriores.

Conservar únicamente la información histórica estrictamente necesaria para comprender decisiones técnicas importantes, especialmente:

- adopción de Kratos;
- resultados de las pruebas que justificaron su adopción;
- problemas importantes y sus soluciones;
- decisiones arquitectónicas relevantes.

Eliminar:

- repeticiones;
- estados obsoletos;
- resultados duplicados;
- información temporal que ya no represente el estado actual;
- listas antiguas de tareas;
- descripciones de estados que contradigan la implementación actual.

Después de la limpieza, crear una nueva sección:

## ESTADO ACTUAL — INTEGRACIÓN DE KRATOS EN EL CORE

A partir de ese punto registrar exclusivamente lo correspondiente a esta nueva fase.

---

4. INTEGRACIÓN REAL

El objetivo es consolidar el flujo:

STEP REAL
   ↓
STEP ADAPTER
   ↓
CADModel
   ↓
MALLA
   ↓
KRATOS ADAPTER
   ↓
KRATOS
   ↓
FEA
   ↓
RESULTADOS
   ↓
CORE

La integración debe utilizar las interfaces existentes siempre que sean adecuadas.

No crear una segunda arquitectura paralela.

No crear un segundo pipeline independiente únicamente para hacer funcionar Kratos.

Kratos debe convertirse en el solver utilizado por el Core.

---

5. RESPONSABILIDADES

Determinar claramente las responsabilidades de cada capa.

STEP Adapter

Responsable de:

- recibir el STEP;
- extraer la información necesaria;
- producir el modelo interno.

CADModel

Debe representar el modelo de forma independiente de Kratos y del formato STEP.

Malla

Debe proporcionar una representación compatible con el solver.

KratosAdapter

Debe encargarse de traducir el modelo interno hacia Kratos y ejecutar el análisis.

Debe evitarse que el resto del Core dependa directamente de detalles internos de Kratos.

Solver Interface

Debe proporcionar una interfaz abstracta que permita al Core solicitar:

- configuración del análisis;
- condiciones de frontera;
- materiales;
- cargas;
- ejecución;
- resultados.

El Core no debería necesitar conocer detalles específicos de la API interna de Kratos.

---

6. FEA REAL

La integración debe permitir ejecutar un análisis FEA real mediante Kratos.

Debe existir como mínimo el flujo:

modelo
 ↓
malla
 ↓
material
 ↓
condiciones de frontera
 ↓
cargas
 ↓
solver Kratos
 ↓
desplazamientos
 ↓
resultados

No utilizar resultados simulados para ocultar funcionalidades que todavía no estén implementadas.

Los datos sintéticos solo podrán utilizarse cuando sean necesarios para probar componentes aislados.

---

7. PRUEBA DE INTEGRACIÓN

Una vez implementada la integración, ejecutar una prueba utilizando el flujo real existente.

Preferentemente:

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

No crear un STEP artificial para aparentar que la integración funciona si ya existe un STEP real disponible.

La prueba debe demostrar que los datos atraviesan realmente las capas del Core.

---

8. NO REPETIR EL TRABAJO YA VALIDADO

No volver a:

- investigar Kratos;
- comparar Kratos con otros motores;
- demostrar nuevamente que Kratos funciona de forma aislada;
- repetir los PoC históricos;
- reconstruir pruebas ya documentadas.

Las pruebas existentes son evidencia y referencia.

Solo repetir una prueba anterior si resulta estrictamente necesaria para comprobar la integración actual.

---

9. CONTROL DE ERRORES

Aplicar estrictamente el protocolo de "metodologia.md".

Si aparece un problema:

Si la causa es evidente

Se permite una única corrección autónoma y una nueva prueba.

Si la causa no es evidente

DETENER.

No realizar múltiples intentos especulativos.

Registrar inmediatamente:

- error exacto;
- traceback completo;
- archivo;
- línea;
- función;
- entrada utilizada;
- estado del sistema;
- comportamiento esperado;
- comportamiento obtenido;
- hipótesis técnica disponible;
- qué se intentó;
- resultado del intento.

Clasificarlo como:

BLOQUEO TÉCNICO — REQUIERE INVESTIGACIÓN EXTERNA

No continuar intentando soluciones por ensayo y error.

---

10. NO SOBREDISEÑAR

No implementar todavía:

- sistema de licencias;
- suscripciones;
- integración Onshape;
- integración con otros CAD;
- Rust;
- migración general a C++;
- UI avanzada;
- funcionalidades futuras no necesarias para este objetivo.

La tarea actual es exclusivamente:

«hacer que Kratos funcione como motor FEA real dentro del Core existente.»

---

11. CRITERIO DE FINALIZACIÓN

La tarea solo puede considerarse completada si:

- Kratos está integrado realmente en el Core;
- el Core puede invocar el solver mediante una interfaz definida;
- el flujo utiliza datos reales;
- el FEA se ejecuta realmente mediante Kratos;
- los resultados regresan al Core;
- no existen mocks ocultando funcionalidades;
- las pruebas relevantes pasan;
- no se introdujeron dependencias CAD externas;
- no se rompieron funcionalidades previamente verificadas;
- el repositorio quedó limpio;
- "resumen_implementacion.md" refleja el estado real.

Si alguna condición no se cumple:

«NO declarar la integración como COMPLETADA.»

---

12. DOCUMENTACIÓN FINAL

Actualizar "resumen_implementacion.md" con:

- estado inicial;
- limpieza realizada;
- archivos eliminados y motivo;
- archivos modificados;
- arquitectura resultante;
- integración realizada;
- pruebas ejecutadas;
- resultados;
- errores encontrados;
- bloqueos;
- soluciones aplicadas;
- estado final;
- pendientes reales.

No documentar funcionalidades que solamente estén planeadas.

---

REGLA FINAL

Esta intervención no busca producir más código por producirlo.

Busca transformar la integración actualmente existente en una integración real, limpia y mantenible de Kratos dentro del Core.

El resultado esperado es:

STEP REAL
    ↓
CADModel
    ↓
MALLA
    ↓
KRATOS ADAPTER
    ↓
KRATOS FEA
    ↓
RESULTADOS
    ↓
CORE

Si el flujo funciona realmente, documentarlo y detenerse.

Si aparece un bloqueo cuya solución no sea evidente, detenerse y documentarlo siguiendo el protocolo de investigación externa.

No entrar en ciclos de ensayo y error.