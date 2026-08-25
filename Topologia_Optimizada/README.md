
# TOPOLOGÍA OPTIMIZADA PARA ONSHAPE

## Especificación maestra del proyecto

---

# 1. VISIÓN DEL PROYECTO

**Topología Optimizada** es una aplicación privada/personal integrada con Onshape cuyo objetivo es permitir realizar optimización topológica de piezas CAD utilizando la geometría real del modelo, condiciones físicas definidas por el usuario y un motor externo de cálculo.

La aplicación combina:

- Onshape como entorno CAD de origen y destino.
- Una App Extension integrada dentro de Onshape para seleccionar geometría.
- Una aplicación externa como interfaz principal de trabajo.
- Un backend Python/FastAPI para procesamiento y coordinación.
- Un sistema de procesamiento geométrico CAD.
- Un sistema de mallado FEM.
- Un solver de elementos finitos.
- Un algoritmo de optimización topológica.
- Un visor 3D interactivo.
- La API REST de Onshape para intercambio de datos.

El objetivo final es que el usuario pueda seleccionar una pieza dentro de Onshape, definir las condiciones necesarias desde la aplicación externa, ejecutar una optimización topológica y devolver el resultado a Onshape.

---

# 2. OBJETIVO PRINCIPAL

El flujo completo objetivo es:

```text
ONSHAPE
   │
   │ Selección de sólidos
   ▼
APP EXTENSION
   │
   │ Identificación de geometría
   ▼
BACKEND PYTHON
   │
   │ API REST Onshape
   ▼
GEOMETRÍA CAD REAL
   │
   ▼
PROCESAMIENTO GEOMÉTRICO
   │
   ▼
MALLA FEM
   │
   ├── Design Space
   ├── Keep-out
   ├── Regiones de carga
   └── Regiones de restricción
   │
   ▼
APLICACIÓN EXTERNA
   │
   ├── Material
   ├── Fuerzas
   ├── Restricciones
   ├── Porcentaje de optimización
   └── Parámetros del cálculo
   │
   ▼
FEA
   │
   ▼
TOPOLOGICAL OPTIMIZATION
   │
   ▼
RESULTADO OPTIMIZADO
   │
   ▼
VISUALIZACIÓN 3D
   │
   ▼
ACEPTAR
   │
   ▼
ONSHAPE
````

---

# 3. PRINCIPIO ARQUITECTÓNICO FUNDAMENTAL

La aplicación está dividida en dos interfaces con responsabilidades diferentes.

## 3.1. Interfaz dentro de Onshape

La App Extension integrada en Onshape tiene una función deliberadamente simple:

> Seleccionar los sólidos que participan en la optimización.

No debe convertirse en la interfaz principal de configuración de TopOpt.

Su responsabilidad principal es proporcionar contexto geométrico real.

Debe permitir seleccionar como mínimo:

* Pieza a optimizar.
* Piezas que funcionan como obstáculos/Keep-out.

La interfaz interna debe ser:

* simple;
* rápida;
* clara;
* integrada;
* orientada a selección.

---

# 4. APLICACIÓN EXTERNA

La aplicación externa es la **interfaz principal y más potente del sistema**.

Aquí se realiza la configuración de la optimización.

Debe comportarse visualmente como una aplicación CAD/CAE moderna.

El usuario debe poder:

* visualizar la pieza;
* rotarla;
* hacer zoom;
* desplazarla;
* inspeccionarla desde cualquier ángulo;
* visualizar obstáculos;
* configurar fuerzas;
* configurar restricciones;
* configurar materiales;
* establecer el grado de optimización;
* ejecutar el cálculo;
* visualizar el resultado;
* aceptar o cancelar el resultado.

---

# 5. VISOR 3D

La aplicación externa debe disponer de un visor 3D interactivo.

El visor debe permitir como mínimo:

* Orbit/rotación.
* Zoom.
* Pan/desplazamiento.
* Ajustar a pantalla.
* Centrar modelo.
* Visualización desde cualquier orientación.

La geometría mostrada debe corresponder a la geometría CAD real obtenida desde Onshape.

No se deben utilizar geometrías ficticias como sustituto de la pieza real en producción.

Las geometrías auxiliares sí pueden utilizar representaciones simplificadas exclusivamente para visualización.

---

# 6. FLUJO DE SELECCIÓN

El usuario comienza trabajando en Onshape.

## 6.1. Pieza principal

El usuario selecciona el sólido que desea optimizar.

Esta selección representa el:

**DESIGN SPACE**

El Design Space es la región de material sobre la cual el algoritmo de optimización puede actuar.

---

## 6.2. Obstáculos / Keep-out

El usuario puede seleccionar uno o varios sólidos adicionales.

Estos representan regiones que:

* no deben ser invadidas;
* no deben eliminarse;
* deben permanecer fuera del volumen optimizado.

Estas regiones se denominan:

**KEEP-OUT**

La selección de Keep-out es opcional.

Si no se selecciona ningún Keep-out, la optimización debe trabajar únicamente con el Design Space.

---

# 7. DESIGN SPACE

El Design Space representa el volumen inicial sobre el cual se ejecutará la optimización.

Debe estar asociado a geometría real.

El flujo correcto es:

```text
Selección en Onshape
        ↓
Identificación del sólido
        ↓
Obtención de geometría CAD
        ↓
Procesamiento geométrico
        ↓
Malla
        ↓
Elementos pertenecientes al Design Space
```

El sistema no debe asumir que descargar un Part Studio completo equivale automáticamente a obtener el sólido seleccionado.

Debe existir una identificación correcta de la geometría correspondiente.

---

# 8. KEEP-OUT

Los Keep-out representan geometría que debe quedar protegida.

El flujo es:

```text
Selección del obstáculo
        ↓
Geometría CAD
        ↓
Malla
        ↓
Región Keep-out
        ↓
Restricción de TopOpt
```

El sistema debe soportar:

* cero Keep-out;
* un Keep-out;
* múltiples Keep-out.

---

# 9. GEOMETRÍA CAD

La aplicación debe trabajar con geometría CAD real.

El flujo general será:

```text
Onshape
   ↓
API REST
   ↓
Exportación CAD
   ↓
STEP / Parasolid / formato equivalente
   ↓
OpenCASCADE / CadQuery
   ↓
Geometría sólida
```

El sistema debe validar:

* respuesta HTTP;
* existencia del archivo;
* integridad del archivo;
* formato;
* existencia de sólidos;
* errores de importación;
* geometría inválida.

No se deben utilizar geometrías ficticias en producción.

---

# 10. PROCESAMIENTO GEOMÉTRICO

La geometría CAD debe convertirse en una representación adecuada para cálculo numérico.

El procesamiento debe conservar información suficiente para relacionar:

* sólidos;
* caras;
* regiones;
* elementos de malla;
* nodos.

Debe ser posible determinar qué parte de la malla corresponde a:

* Design Space;
* Keep-out;
* superficies de aplicación de fuerzas;
* superficies de restricciones.

---

# 11. MALLA FEM

El sistema debe generar una malla volumétrica adecuada para análisis estructural 3D.

La malla debe estar formada por elementos compatibles con el solver FEA utilizado.

La implementación debe validar como mínimo:

* conectividad;
* orientación;
* elementos degenerados;
* calidad geométrica;
* volumen;
* Jacobiano;
* aspect ratio;
* estabilidad numérica;
* representación de la geometría.

El método de mallado será elegido en función de la solución técnicamente más adecuada.

Pueden evaluarse herramientas como:

* Gmsh;
* Netgen;
* TetGen;
* otras herramientas equivalentes.

No se debe incorporar una dependencia simplemente por existir.

La elección debe justificarse técnicamente.

---

# 12. MAPEO CAD → MALLA

La aplicación debe mantener una relación entre geometría CAD y malla.

Debe ser posible pasar de:

```text
Cara CAD
   ↓
Región geométrica
   ↓
Elementos / nodos
```

Esto será necesario para aplicar:

* fuerzas;
* restricciones;
* Keep-out;
* condiciones de frontera.

El sistema debe evitar falsos positivos producidos únicamente por proximidad espacial cuando la geometría sea compleja.

Cuando sea necesario se podrán utilizar:

* normales;
* proyección;
* intersección;
* proximidad;
* bounding boxes;
* información B-Rep;
* regiones físicas del mallador.

---

# 13. FUERZAS

Las fuerzas se configurarán desde la aplicación externa.

El usuario debe poder definir:

* magnitud;
* unidad;
* dirección X;
* dirección Y;
* dirección Z;
* sentido;
* región/cara de aplicación.

La arquitectura debe permitir múltiples cargas.

El flujo será:

```text
Fuerza configurada
       ↓
Región CAD
       ↓
Superficie de malla
       ↓
Nodos
       ↓
Vector de cargas
       ↓
FEA
```

Las fuerzas deben representar condiciones físicas reales.

No se deben utilizar fuerzas aleatorias o simuladas en producción.

---

# 14. RESTRICCIONES

El usuario debe poder definir las condiciones de frontera necesarias para el análisis.

Las restricciones se asocian a regiones geométricas.

El flujo será:

```text
Restricción
      ↓
Región CAD
      ↓
Malla
      ↓
Nodos
      ↓
Grados de libertad
      ↓
Condición FEA
```

Inicialmente se implementarán únicamente los tipos de restricciones realmente soportados por el solver.

No mostrar como funcional una restricción que todavía no esté conectada al solver real.

---

# 15. MATERIAL

La aplicación debe estar preparada para utilizar una biblioteca de materiales.

Como mínimo, la arquitectura debe permitir definir:

* nombre;
* módulo de Young;
* coeficiente de Poisson;
* densidad cuando corresponda;
* otras propiedades necesarias para futuras extensiones.

La biblioteca inicial podrá incluir materiales comunes como:

* aluminio;
* acero;
* titanio.

La arquitectura debe permitir posteriormente:

* crear materiales personalizados;
* editar materiales;
* guardar materiales;
* importar materiales;
* ampliar la biblioteca.

La biblioteca avanzada de materiales no es requisito para la primera versión funcional del solver.

---

# 16. FEA

El sistema debe disponer de un análisis estructural mediante elementos finitos.

La primera implementación objetivo será:

**Elasticidad lineal estática 3D.**

Debe permitir resolver:

* desplazamientos;
* fuerzas;
* restricciones;
* reacciones;
* deformaciones;
* tensiones;
* compliance.

El solver debe utilizar la malla volumétrica real.

No se permiten:

* desplazamientos aleatorios;
* fuerzas aleatorias;
* resultados ficticios;
* solver simulado.

---

# 17. OPTIMIZACIÓN TOPOLÓGICA

El sistema debe utilizar un algoritmo real de optimización topológica.

La arquitectura debe permitir implementar métodos como:

**SIMP — Solid Isotropic Material with Penalization**

El flujo general será:

```text
Malla
   ↓
Material
   ↓
Condiciones de frontera
   ↓
Cargas
   ↓
FEA
   ↓
Compliance
   ↓
Actualización de densidades
   ↓
Nueva geometría/material distribuido
   ↓
Nueva iteración FEA
```

---

# 18. PORCENTAJE DE OPTIMIZACIÓN

La interfaz debe permitir definir un objetivo de volumen.

Por ejemplo:

```text
30 %
```

representa un objetivo aproximado de conservar el 30 % del volumen inicial de diseño.

La arquitectura debe distinguir entre:

* porcentaje introducido por el usuario;
* fracción de volumen utilizada por el solver;
* resultado final realmente obtenido.

No se debe afirmar que una pieza fue optimizada al porcentaje solicitado si el algoritmo no alcanzó ese objetivo.

---

# 19. ITERACIONES

La optimización debe trabajar mediante iteraciones.

Cada iteración podrá incluir:

```text
1. Distribución de densidad
2. FEA
3. Cálculo de compliance
4. Actualización
5. Verificación de convergencia
```

La aplicación debe poder informar al usuario del estado del cálculo.

Como mínimo:

* iteración actual;
* número total de iteraciones;
* porcentaje de volumen;
* compliance;
* estado;
* errores.

---

# 20. VISUALIZACIÓN DEL RESULTADO

La aplicación externa debe mostrar visualmente la evolución del resultado.

El usuario debe poder observar:

* geometría inicial;
* Design Space;
* Keep-out;
* restricciones;
* cargas;
* resultado optimizado.

El resultado debe poder inspeccionarse mediante el visor 3D.

La visualización no debe ser solamente una representación abstracta de datos.

---

# 21. FLUJO DE ACEPTACIÓN

El resultado optimizado no debe enviarse inmediatamente a Onshape sin confirmación.

El usuario debe poder:

```text
CALCULAR
   ↓
VISUALIZAR
   ↓
INSPECCIONAR
   ↓
ACEPTAR / CANCELAR
```

Si selecciona:

### ACEPTAR

El sistema inicia el proceso de devolución a Onshape.

### CANCELAR

El resultado no modifica el modelo de Onshape.

---

# 22. DEVOLUCIÓN A ONSHAPE

Después de aceptar el resultado:

```text
Resultado TopOpt
      ↓
Reconstrucción / conversión CAD
      ↓
Formato compatible
      ↓
API REST Onshape
      ↓
Importación
      ↓
Resultado dentro de Onshape
```

La arquitectura debe permitir devolver la geometría optimizada como un resultado CAD utilizable.

La solución concreta para la reconstrucción e importación debe utilizar mecanismos reales soportados por Onshape.

No se debe simular una modificación del Feature Tree.

---

# 23. SINCRONIZACIÓN

La aplicación externa debe mantener el contexto del documento de trabajo:

* Document ID;
* Workspace ID;
* Element ID;

cuando corresponda.

El contexto debe provenir de la integración real con Onshape.

No se debe depender de introducir manualmente IDs como mecanismo principal de uso.

---

# 24. AUTENTICACIÓN

La aplicación utilizará:

**OAuth 2.0 de Onshape.**

El flujo objetivo será:

```text
Aplicación
   ↓
Login
   ↓
Onshape OAuth
   ↓
Autorización
   ↓
Callback
   ↓
Authorization Code
   ↓
Token
   ↓
Sesión autenticada
```

Los secretos deben permanecer exclusivamente en el backend.

El frontend nunca debe recibir:

* Client Secret;
* Refresh Token;
* credenciales privadas.

---

# 25. SESIÓN

La aplicación debe mantener la sesión mediante persistencia local.

Se podrá utilizar:

* SQLite;
* otra persistencia local adecuada.

Debe almacenarse únicamente la información necesaria.

Los tokens deben almacenarse de forma segura.

El sistema debe soportar renovación automática del Access Token.

Si Onshape devuelve HTTP 401:

```text
Access Token expirado
        ↓
Refresh Token
        ↓
Nuevo Access Token
        ↓
Repetir petición
```

Si la renovación falla:

```text
Sesión expirada
        ↓
Solicitar nueva autenticación
```

---

# 26. SEGURIDAD

Las credenciales sensibles no deben estar hardcodeadas.

Debe utilizarse `.env` o un mecanismo seguro equivalente.

El repositorio debe incluir:

`.env.example`

pero nunca:

`.env`

con secretos reales.

La aplicación debe validar:

* OAuth state;
* sesiones;
* errores HTTP;
* payloads;
* permisos;
* entradas de usuario.

---

# 27. BACKEND

El backend principal estará desarrollado en:

**Python + FastAPI**

Sus responsabilidades incluyen:

* autenticación;
* comunicación con Onshape;
* gestión de sesiones;
* recepción de selecciones;
* descarga de geometría;
* procesamiento CAD;
* generación de malla;
* asociación CAD/malla;
* preparación FEA;
* ejecución FEA;
* ejecución TopOpt;
* gestión de jobs;
* resultados;
* comunicación con frontend.

El backend no debe contener lógica de presentación innecesaria.

---

# 28. FRONTEND

La aplicación externa podrá utilizar:

* HTML;
* CSS;
* JavaScript;
* TypeScript;
* Three.js;

o tecnologías equivalentes adecuadamente justificadas.

La interfaz debe ser:

* limpia;
* profesional;
* responsive;
* clara;
* orientada a CAD/CAE.

No debe convertirse en una interfaz excesivamente compleja si una función puede representarse de forma más simple.

---

# 29. ESTADOS DEL PROCESO

La aplicación debe manejar estados claros.

Ejemplo:

```text
NO CONECTADO
      ↓
CONECTANDO
      ↓
CONECTADO
      ↓
ESPERANDO SELECCIÓN
      ↓
GEOMETRÍA RECIBIDA
      ↓
PREPARANDO MALLA
      ↓
CONFIGURACIÓN
      ↓
CALCULANDO
      ↓
RESULTADO DISPONIBLE
      ↓
ACEPTAR
      ↓
EXPORTANDO
      ↓
COMPLETADO
```

Los errores deben tener estados diferenciados.

---

# 30. MANEJO DE ERRORES

Los errores deben ser reales y explicables.

Ejemplos:

* OAuth fallido;
* sesión expirada;
* documento inexistente;
* permiso insuficiente;
* selección inválida;
* pieza no sólida;
* STEP inválido;
* geometría corrupta;
* mallado fallido;
* malla degenerada;
* FEA sin convergencia;
* TopOpt sin convergencia;
* exportación fallida;
* error de API.

No ocultar errores detrás de mensajes genéricos.

---

# 31. VALIDACIÓN DE PIEZA

La pieza principal debe ser válida para el proceso.

Como mínimo:

* debe representar un sólido;
* debe poder obtenerse desde Onshape;
* debe poder procesarse geométricamente;
* debe poder mallarse.

Si no cumple las condiciones:

```text
Pieza no válida para optimización
```

y explicar el motivo.

---

# 32. LIMITACIONES DE ONSHAPE

La arquitectura debe respetar las limitaciones reales de Onshape.

FeatureScript no se utilizará como canal de comunicación de red.

FeatureScript:

* funciona en sandbox;
* no realiza HTTP;
* no utiliza sockets;
* no ejecuta Python;
* no ejecuta C++;
* no utiliza librerías externas arbitrarias.

Por lo tanto, la comunicación externa se realizará mediante:

**App Extension + JavaScript + Backend + API REST de Onshape.**

No se debe intentar convertir FeatureScript en un servidor o cliente HTTP.

---

# 33. FEATURESCRIPT

FeatureScript no forma parte de la arquitectura actual de comunicación.

No debe utilizarse para:

* enviar datos al backend;
* recibir datos del backend;
* ejecutar FEA;
* ejecutar TopOpt;
* transferir geometría mediante HTTP.

Si en el futuro se utiliza FeatureScript para alguna función CAD nativa específica, deberá ser una decisión arquitectónica independiente y documentada.

---

# 34. PERSISTENCIA

La aplicación debe poder almacenar localmente:

* sesión;
* contexto de trabajo;
* configuraciones;
* jobs;
* estados;
* resultados;
* cache cuando sea conveniente.

La persistencia debe diseñarse para poder migrarse posteriormente a una arquitectura cloud.

---

# 35. LICENCIAMIENTO FUTURO

Aunque inicialmente la aplicación será privada/personal, la arquitectura debe permitir agregar posteriormente un sistema de:

* usuarios;
* licencias;
* suscripciones;
* permisos.

La lógica principal debe poder aislarse de la validación de licencia.

No implementar un sistema comercial completo mientras no sea necesario.

---

# 36. RENDIMIENTO

Los cálculos pesados no deben ejecutarse dentro de:

* navegador;
* App Extension;
* interfaz de Onshape.

Los cálculos deben realizarse en el backend.

La interfaz debe permanecer disponible para mostrar:

* progreso;
* estado;
* errores;
* resultados.

---

# 37. JOBS

Las operaciones de FEA y TopOpt deben tratarse como jobs.

Un job debería poder representar:

* ID;
* usuario;
* contexto Onshape;
* geometría;
* parámetros;
* estado;
* progreso;
* resultado;
* errores;
* timestamps.

Estados posibles:

```text
PENDING
PREPARING
MESHING
SOLVING
OPTIMIZING
COMPLETED
FAILED
CANCELLED
```

---

# 38. CANCELACIÓN

La arquitectura debe permitir posteriormente cancelar un cálculo.

Una cancelación debe:

* detener el job cuando sea posible;
* liberar recursos;
* conservar información del estado;
* no modificar Onshape si el usuario no aceptó el resultado.

---

# 39. CACHE

La aplicación puede utilizar cache para reducir llamadas innecesarias a Onshape.

Se podrá cachear:

* geometría;
* malla;
* resultados intermedios;

siempre que exista una estrategia para invalidar datos obsoletos.

No utilizar cache de forma que se trabaje accidentalmente con una versión antigua del modelo.

---

# 40. TESTING

Debe existir una separación clara entre:

## Tests unitarios

Pueden utilizar:

* geometría sintética;
* mocks;
* fixtures.

## Tests de integración

Deben comprobar componentes reales.

## Tests end-to-end

Deben recorrer realmente el flujo correspondiente.

No llamar "end-to-end" a un test que solamente genera una pieza local con CadQuery.

Los tests deben validar comportamiento, no solamente existencia de funciones.

---

# 41. REGLA CONTRA MOCKS EN PRODUCCIÓN

Está prohibido utilizar mocks o datos ficticios para representar funcionalidades reales en producción.

No utilizar:

* fuerzas aleatorias;
* desplazamientos aleatorios;
* geometría ficticia;
* resultados TopOpt inventados;
* solver falso;
* piezas simuladas.

Los mocks solamente son aceptables dentro de tests controlados.

---

# 42. CRITERIO DE "IMPLEMENTADO"

Una funcionalidad solo se considera implementada cuando:

1. Existe el código necesario.
2. Está integrada con el flujo correspondiente.
3. Utiliza datos reales cuando corresponda.
4. Maneja errores.
5. Tiene pruebas apropiadas.
6. El comportamiento está validado.

Crear una función no significa automáticamente que la funcionalidad esté terminada.

---

# 43. CRITERIO DE "COMPLETO"

Una etapa se considera completa solamente cuando todas sus dependencias necesarias están funcionando.

Ejemplo:

No considerar:

```text
TOPTOPOLOGÍA COMPLETA
```

si:

```text
FEA = simulación
```

o:

```text
MALLA = inválida
```

o:

```text
CARGAS = datos ficticios
```

---

# 44. ROADMAP DEL PROYECTO

El proyecto se desarrollará progresivamente.

## HITO 1 — INTEGRACIÓN Y GEOMETRÍA

Objetivo:

```text
Onshape
↓
App Extension
↓
Selección real
↓
Backend
↓
Geometría CAD real
↓
Visor 3D
```

---

## HITO 2 — MALLADO Y REGIONES

Objetivo:

```text
Geometría
↓
Malla volumétrica
↓
Design Space
↓
Keep-out
↓
Mapeo CAD → malla
```

Debe existir una malla técnicamente adecuada para el solver.

---

## HITO 3 — FEA

Objetivo:

```text
Malla
↓
Material
↓
Fuerzas
↓
Restricciones
↓
FEA 3D
↓
Resultados
```

---

## HITO 4 — TOPOPT

Objetivo:

```text
FEA
↓
Compliance
↓
SIMP / TopOpt
↓
Iteraciones
↓
Convergencia
↓
Geometría optimizada
```

---

## HITO 5 — VISUALIZACIÓN Y EXPERIENCIA

Objetivo:

* visor CAD/CAE completo;
* evolución del resultado;
* parámetros;
* indicadores;
* inspección;
* comparación inicial/final.

---

## HITO 6 — RETORNO A ONSHAPE

Objetivo:

```text
Resultado
↓
Reconstrucción CAD
↓
API Onshape
↓
Resultado dentro de Onshape
```

---

## HITO 7 — MATERIALES Y EXTENSIONES

Objetivo:

* biblioteca de materiales;
* materiales personalizados;
* configuraciones avanzadas;
* análisis adicionales.

---

## HITO 8 — PREPARACIÓN PARA NUBE

Objetivo:

* usuarios;
* licencias;
* jobs remotos;
* almacenamiento;
* escalabilidad;
* seguridad;
* despliegue cloud.

---

# 45. ARQUITECTURA DE COMPONENTES

La estructura conceptual es:

```text
┌──────────────────────────────────────────┐
│                  ONSHAPE                 │
│                                          │
│  Documento / Part Studio / Geometría    │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│             APP EXTENSION                │
│                                          │
│ Selección de sólidos                     │
│ Contexto                                  │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│            BACKEND FASTAPI               │
│                                          │
│ OAuth                                    │
│ API Onshape                              │
│ Geometría                                │
│ Malla                                    │
│ FEA                                      │
│ TopOpt                                   │
│ Jobs                                     │
└──────────────┬───────────────┬───────────┘
               │               │
               ▼               ▼
┌────────────────────┐  ┌──────────────────┐
│ PROCESAMIENTO CAD  │  │ SOLVER FEM/TOPOPT│
│                    │  │                  │
│ STEP               │  │ FEA              │
│ OpenCASCADE        │  │ SIMP             │
│ CadQuery           │  │ Optimización     │
└──────────┬─────────┘  └────────┬─────────┘
           │                     │
           └──────────┬──────────┘
                      ▼
┌──────────────────────────────────────────┐
│          APLICACIÓN EXTERNA              │
│                                          │
│ Visor 3D                                │
│ Parámetros                               │
│ Fuerzas                                  │
│ Restricciones                            │
│ Material                                 │
│ Optimización                             │
│ Resultados                               │
└──────────────────┬───────────────────────┘
                   │
                   │ Aceptar
                   ▼
┌──────────────────────────────────────────┐
│                  ONSHAPE                 │
│                                          │
│ Resultado optimizado                     │
└──────────────────────────────────────────┘
```

---

# 46. TECNOLOGÍAS OBJETIVO

Las tecnologías pueden evolucionar si existe una razón técnica.

La arquitectura inicial contempla:

### Backend

* Python 3.10+
* FastAPI
* Uvicorn

### Frontend

* HTML/CSS
* JavaScript/TypeScript
* Three.js

### CAD

* OpenCASCADE
* CadQuery

### Persistencia

* SQLite inicialmente

### Integración

* Onshape REST API
* OAuth 2.0

### FEA

* Solver FEM compatible con Python
* scikit-fem u otra alternativa técnicamente adecuada

### Optimización

* Implementación TopOpt/SIMP adecuada para el modelo FEA utilizado

---

# 47. CONFIGURACIÓN DE ONSHAPE

La aplicación debe utilizar una OAuth Application privada configurada en el Developer Portal.

Debe configurarse:

* Client ID;
* Client Secret;
* Redirect URI;
* App URL cuando corresponda;
* Scopes necesarios.

Los scopes deben limitarse a los permisos realmente necesarios.

---

# 48. DESARROLLO LOCAL

La aplicación debe poder ejecutarse inicialmente en entorno local.

Ejemplo conceptual:

```bash
python -m venv .venv
```

Activar entorno.

Instalar dependencias.

Configurar:

```text
.env
```

Ejecutar FastAPI mediante Uvicorn.

Cuando sea necesario para integración OAuth/iFrame:

utilizar un túnel HTTPS compatible.

---

# 49. EXPERIENCIA DE USUARIO OBJETIVO

El usuario final debería experimentar algo similar a:

```text
1. Abrir Onshape.

2. Abrir Topología Optimizada.

3. Seleccionar la pieza.

4. Seleccionar opcionalmente obstáculos.

5. Enviar selección.

6. La aplicación externa recibe la geometría.

7. La pieza aparece en el visor 3D.

8. El usuario inspecciona la pieza.

9. Configura restricciones.

10. Configura fuerzas.

11. Selecciona material.

12. Define porcentaje objetivo.

13. Ejecuta optimización.

14. Visualiza el proceso.

15. Inspecciona el resultado.

16. Decide:
       ACEPTAR
       o
       CANCELAR

17. Si acepta:
       resultado → Onshape.
```

---

# 50. PRINCIPIOS DE DISEÑO

El proyecto debe seguir estos principios:

### Simplicidad

La interfaz debe ser tan sencilla como sea posible sin sacrificar funcionalidad.

### Separación de responsabilidades

Onshape selecciona.

La aplicación externa configura.

El backend calcula.

Onshape recibe el resultado.

### Datos reales

La producción debe trabajar con datos reales.

### Seguridad

Los secretos nunca se exponen al frontend.

### Trazabilidad

Cada cálculo debe poder relacionarse con:

* usuario;
* contexto;
* geometría;
* parámetros;
* resultado.

### Validación

Nada debe declararse completo sin validación.

### Modularidad

Cada componente debe poder evolucionar independientemente.

### Extensibilidad

La arquitectura debe permitir agregar:

* nuevos materiales;
* nuevos tipos de carga;
* nuevos tipos de restricciones;
* nuevos algoritmos;
* nuevos solvers;
* funcionalidades cloud.

---

# 51. LIMITACIONES Y DECISIONES

## FeatureScript

No se utilizará como mecanismo de comunicación con el backend.

## App Extension

Su función principal es la selección y el contexto.

## Aplicación externa

Es la interfaz principal.

## Cálculos

Se ejecutan fuera de Onshape.

## API

La comunicación con Onshape se realiza mediante mecanismos oficiales.

---

# 52. ESTADO DEL README

Este documento representa la:

**ARQUITECTURA OBJETIVO DEL PROYECTO.**

No representa el estado actual de implementación.

El estado real debe determinarse mediante una auditoría independiente del repositorio.

---

# 53. REGLA FUNDAMENTAL PARA FUTURAS AUDITORÍAS

Toda auditoría futura debe comparar el repositorio contra este documento.

El proceso será:

```text
README.md
     ↓
Requisitos objetivo
     ↓
Auditoría del repositorio
     ↓
Estado real
     ↓
Diferencias
     ↓
prompt.md
     ↓
Implementación
     ↓
Tests
     ↓
Nueva auditoría
```

El README debe considerarse la referencia arquitectónica principal.

Los prompts son instrucciones temporales de implementación.

El código es la implementación actual.

La auditoría determina la diferencia entre ambos.

---

# 54. REGLA DE CAMBIO DE ARQUITECTURA

Si durante el desarrollo se determina que una decisión arquitectónica de este documento es técnicamente incorrecta o que existe una alternativa considerablemente mejor:

NO modificar silenciosamente la arquitectura.

Primero:

1. Identificar el problema.
2. Explicar la limitación.
3. Proponer la alternativa.
4. Evaluar impacto.
5. Actualizar este README.
6. Recién entonces modificar los prompts y el código.

Esto evita que la arquitectura real del proyecto se desvíe progresivamente de su objetivo original.

---

# 55. DEFINICIÓN FINAL DEL PRODUCTO

La aplicación terminada debe permitir transformar una pieza CAD real de Onshape en una pieza optimizada mediante un flujo integrado:

```text
SELECCIONAR
     ↓
VISUALIZAR
     ↓
CONFIGURAR
     ↓
SIMULAR
     ↓
OPTIMIZAR
     ↓
INSPECCIONAR
     ↓
ACEPTAR
     ↓
DEVOLVER A ONSHAPE
```

El objetivo no es únicamente generar una distribución matemática de densidades.

El objetivo final es proporcionar un flujo práctico de:

**CAD → FEA → Optimización Topológica → CAD**

manteniendo una conexión coherente entre la geometría original de Onshape, el cálculo externo y el resultado final.

```

**Este README pasa a ser nuestra referencia principal.** A partir de ahora, cuando hagamos la auditoría del repositorio, no voy a preguntarme "¿qué dijo el prompt anterior que había que hacer?", sino **"¿qué exige el README y qué parte de eso existe realmente en el código?"**.
```
