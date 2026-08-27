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

extensiones externas;

servicios CAD externos.



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

Onshape;

SolidWorks;

Fusion;

FreeCAD;

otros CAD.


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

21. PROTOCOLO OBLIGATORIO DE BLOQUEO TÉCNICO E INVESTIGACIÓN EXTERNA

Este protocolo es de cumplimiento OBLIGATORIO para cualquier problema técnico que aparezca durante la implementación, especialmente cuando intervengan:

bibliotecas;

frameworks;

APIs;

motores de cálculo;

dependencias externas;

herramientas científicas;

incompatibilidades de versiones;

tecnologías cuya documentación no esté completamente disponible en el contexto actual.


21.1 Principio fundamental

La IA ejecutora NO debe resolver problemas complejos mediante ensayo y error ilimitado.

El ciclo:

ERROR
 ↓
HIPÓTESIS
 ↓
MODIFICACIÓN
 ↓
ERROR
 ↓
NUEVA HIPÓTESIS
 ↓
MODIFICACIÓN
 ↓
...

queda PROHIBIDO cuando la causa del problema no pueda determinarse con suficiente certeza.

El objetivo no es producir rápidamente otra versión del código, sino identificar correctamente la causa del bloqueo antes de modificar nuevamente la implementación.


---

21.2 Corrección autónoma permitida

Cuando aparezca un error, la IA ejecutora podrá realizar UNA única corrección autónoma únicamente si:

la causa es evidente;

la solución está respaldada por el código existente;

la solución está respaldada por documentación ya disponible;

no requiere especulación;

no implica cambiar la arquitectura;

puede verificarse mediante una prueba concreta.


Después de aplicar la corrección, deberá volver a ejecutar la prueba.


---

21.3 Regla de bloqueo inmediato

Si la corrección autónoma falla, o si desde el primer momento la causa no es evidente, la IA debe:

1. DETENER inmediatamente la implementación relacionada con el problema.


2. NO generar otro enfoque alternativo por ensayo y error.


3. NO crear múltiples scripts intentando encontrar una solución por fuerza bruta.


4. NO modificar la arquitectura para esquivar el problema.


5. NO reemplazar una biblioteca o tecnología sin autorización.


6. NO declarar que una tecnología es incompatible únicamente porque una implementación haya fallado.


7. NO continuar desarrollando funcionalidades que dependan del componente bloqueado.



El estado debe pasar inmediatamente a:

BLOQUEADO — REQUIERE INVESTIGACIÓN


---

21.4 Tracker obligatorio del bloqueo

El bloqueo debe documentarse DENTRO de resumen_implementacion.md.

NO crear un archivo independiente para cada error.

El tracker debe contener como mínimo:

Identificación

componente afectado;

funcionalidad que se intentaba implementar;

fecha;

estado actual.


Entorno

sistema operativo;

versión de Python;

versión de la biblioteca o framework;

versiones de dependencias relevantes;

entorno virtual utilizado;

arquitectura del sistema cuando sea relevante.


Reproducción

comando exacto ejecutado;

script utilizado;

archivo afectado;

función o sección;

línea aproximada del error;

condiciones necesarias para reproducirlo.


Evidencia

traceback COMPLETO;

mensaje de error COMPLETO;

salida relevante de consola;

resultado de las pruebas anteriores;

archivos o configuraciones involucradas.


No resumir el error si el resumen elimina información útil para diagnosticarlo.

Acciones realizadas

Registrar cronológicamente:

1. qué se intentó;


2. qué se modificó;


3. qué resultado produjo;


4. qué hipótesis quedó descartada.



No ocultar intentos fallidos.

Hipótesis

Separar claramente:

hechos comprobados;

hipótesis;

información desconocida.


La IA NO debe presentar una hipótesis como hecho.

Pregunta de investigación

El tracker debe terminar indicando exactamente qué debe investigarse.

Ejemplo:

¿Cuál es la forma oficialmente soportada de inicializar X
utilizando la versión Y de la biblioteca Z?

La pregunta debe ser suficientemente precisa para que otra IA pueda investigarla directamente en documentación oficial, ejemplos oficiales, repositorios oficiales o fuentes técnicas confiables.


---

21.5 Investigación externa

Cuando el problema quede bloqueado, la investigación debe realizarse como una actividad separada de la implementación.

La IA investigadora debe determinar:

causa real del problema;

API o mecanismo correcto;

compatibilidad de versiones;

configuración necesaria;

limitaciones reales de la tecnología;

solución recomendada;

referencias utilizadas.


La investigación NO debe modificar el repositorio.

Su función es producir conocimiento y una solución técnicamente fundamentada.


---

21.6 Separación estricta de roles

Se establece la siguiente separación:

IA EJECUTORA
    ↓
implementa, ejecuta y verifica

IA INVESTIGADORA
    ↓
investiga documentación, causa y solución

La IA ejecutora NO debe intentar sustituir una investigación externa mediante múltiples intentos especulativos.

La IA investigadora NO debe modificar directamente la implementación salvo que se le solicite expresamente.


---

21.7 Fuentes para resolver bloqueos

Cuando sea necesaria investigación externa, se debe priorizar:

1. documentación oficial;


2. documentación de la versión específica utilizada;


3. ejemplos oficiales;


4. repositorio oficial;


5. issues oficiales;


6. fuentes técnicas secundarias únicamente cuando las anteriores no sean suficientes.



No utilizar una solución encontrada en Internet como definitiva sin comprobar su compatibilidad con las versiones utilizadas por el proyecto.


---

21.8 Prohibición de declarar incompatibilidad prematuramente

Un error de:

implementación;

configuración;

API;

versión;

dependencia;

importación;

inicialización;

uso incorrecto;

documentación incompleta;


NO constituye evidencia de que una tecnología sea incompatible con el proyecto.

Para declarar:

TECNOLOGÍA NO VIABLE

o:

TECNOLOGÍA INCOMPATIBLE

debe existir evidencia técnica suficiente que demuestre una limitación real.

La documentación debe distinguir siempre entre:

ERROR DE IMPLEMENTACIÓN

ERROR DE CONFIGURACIÓN

ERROR DE INTEGRACIÓN

LIMITACIÓN DOCUMENTAL

LIMITACIÓN DE LA TECNOLOGÍA

INFORMACIÓN NO DETERMINADA


---

21.9 Prohibición de acumulación de experimentos improductivos

Cuando varios intentos consecutivos persigan resolver el MISMO error sin nueva información técnica, deben detenerse.

No se permite crear:

scripts alternativos innecesarios;

pruebas duplicadas;

implementaciones paralelas;

soluciones temporales sin justificación;

archivos de diagnóstico redundantes.


Antes de crear un nuevo experimento debe existir una pregunta técnica concreta que dicho experimento pueda responder.

Si no existe una pregunta concreta:

> NO se crea el experimento.




---

21.10 Reanudación después de un bloqueo

La IA ejecutora solo podrá continuar cuando se disponga de una solución técnicamente fundamentada.

Antes de implementar deberá:

1. leer nuevamente el tracker;


2. revisar la solución obtenida;


3. identificar exactamente qué debe modificarse;


4. implementar únicamente la corrección necesaria;


5. ejecutar nuevamente la prueba que produjo el bloqueo;


6. verificar que el error desapareció;


7. comprobar que no se introdujeron regresiones.



Si la solución investigada vuelve a fallar:

> NO se inicia automáticamente otro ciclo de ensayo y error.



Se vuelve a aplicar este protocolo desde el punto 21.3.


---

21.11 Cierre obligatorio del bloqueo

Un bloqueo solo puede cambiar de:

BLOQUEADO

a:

RESUELTO

cuando exista evidencia ejecutable que demuestre que:

1. la causa fue identificada;


2. la solución fue aplicada;


3. la prueba original ahora funciona;


4. el resultado es reproducible;


5. la solución está documentada.



El resumen de implementación debe conservar el historial suficiente para entender qué ocurrió y cómo se resolvió.


---

21.12 Principio de economía de tokens y recursos

La IA debe priorizar:

DIAGNÓSTICO
    ↓
EVIDENCIA
    ↓
INVESTIGACIÓN
    ↓
SOLUCIÓN
    ↓
EJECUCIÓN
    ↓
VERIFICACIÓN

y evitar:

ERROR
 ↓
CÓDIGO ALEATORIO
 ↓
ERROR
 ↓
CÓDIGO ALEATORIO

El consumo de tokens, tiempo de ejecución y generación de archivos debe considerarse un recurso limitado.

Una investigación externa correctamente planteada es preferible a múltiples intentos especulativos.


---

21.13 Regla de autoridad

En caso de conflicto entre una suposición de la IA ejecutora y evidencia obtenida posteriormente de documentación oficial:

> PREVALECE LA EVIDENCIA DOCUMENTADA.



Toda corrección importante derivada de una investigación externa debe quedar registrada en resumen_implementacion.md.


---

21.14 Regla final del protocolo

ANTE UN BLOQUEO COMPLEJO:

NO ADIVINAR.
NO INSISTIR IND