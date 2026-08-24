# METODOLOGÍA ESTRICTA DE DESARROLLO Y VALIDACIÓN

## 1. PROPÓSITO

Este archivo define las reglas obligatorias que toda IA o desarrollador debe seguir al modificar el proyecto de Topología Optimizada para Onshape.

Su objetivo es impedir implementaciones incompletas, falsas conclusiones de cumplimiento, funcionalidades simuladas y avances sobre etapas que todavía tienen dependencias sin resolver.

Estas reglas son obligatorias.

---

# 2. JERARQUÍA DE DOCUMENTOS

El proyecto utiliza tres documentos principales:

### `prompt.md`

Define:

- requisitos;
- arquitectura;
- objetivos;
- restricciones;
- comportamiento esperado.

Es la especificación técnica principal.

### `metodologia.md`

Define:

- cómo debe trabajar la IA;
- cómo debe auditar;
- cómo debe implementar;
- cómo debe probar;
- cómo debe documentar;
- cuándo puede declarar un requisito cumplido.

Es el reglamento obligatorio de desarrollo.

### `resumen_implementacion.md`

Registra:

- qué se hizo realmente;
- qué se verificó;
- qué quedó pendiente;
- qué problemas aparecieron;
- cuál es el siguiente paso.

Es el registro del estado real del proyecto.

---

# 3. REGLA FUNDAMENTAL

La existencia de código NO demuestra el cumplimiento de un requisito.

No se considera evidencia suficiente:

- una función;
- una clase;
- un endpoint;
- una interfaz;
- un botón;
- un comentario;
- un mock;
- un fallback;
- una estructura de datos;
- un test que pruebe únicamente datos simulados;
- documentación que afirme que una funcionalidad existe.

El cumplimiento debe ser funcional y verificable.

---

# 4. CICLO OBLIGATORIO DE TRABAJO

Toda etapa debe seguir este orden:

1. AUDITAR
2. PLANIFICAR
3. IMPLEMENTAR
4. PROBAR
5. VERIFICAR
6. DOCUMENTAR
7. AUDITAR NUEVAMENTE
8. DETERMINAR ESTADO

No se debe saltar directamente a la implementación.

---

# 5. AUDITORÍA PREVIA OBLIGATORIA

Antes de modificar código, la IA debe:

- leer `prompt.md`;
- leer `metodologia.md`;
- leer `resumen_implementacion.md`;
- revisar el código relacionado;
- identificar dependencias;
- identificar implementaciones existentes;
- detectar aproximaciones o mocks;
- determinar qué requisitos están realmente cumplidos.

La IA no debe asumir que la documentación anterior es correcta.

El código y las pruebas deben ser contrastados con la especificación.

---

# 6. ESTADOS OFICIALES

Cada requisito debe tener uno de estos estados:

## COMPLETADO

Solo cuando:

- está implementado;
- funciona;
- cumple la especificación;
- fue probado;
- existe evidencia suficiente.

## PARCIAL

Cuando:

- existe parte de la implementación;
- pero todavía falta una condición necesaria.

## PENDIENTE

Cuando todavía no existe una implementación funcional.

## BLOQUEADO

Cuando no puede completarse debido a una dependencia externa, limitación técnica o requisito previo.

Nunca utilizar `COMPLETADO` para un requisito que solo tiene una implementación teórica.

---

# 7. PROHIBICIÓN DE SIMULACIONES

Está prohibido utilizar simulaciones para aparentar cumplimiento.

No utilizar como sustituto de funcionalidad real:

- datos ficticios;
- respuestas simuladas de APIs;
- IDs inventados;
- geometría artificial;
- mallas artificiales;
- resultados FEA ficticios;
- resultados TopOpt ficticios;
- mocks en pruebas de integración;
- fallbacks que oculten errores.

Los mocks y datos sintéticos pueden utilizarse únicamente en tests unitarios claramente identificados como tales.

Nunca deben presentarse como prueba de funcionamiento E2E.

---

# 8. GEOMETRÍA

Cuando el requisito implique geometría real de Onshape:

La geometría utilizada para demostrar funcionamiento debe provenir realmente de Onshape.

Una caja creada mediante CadQuery, un cubo Three.js o una geometría hardcodeada puede utilizarse para pruebas unitarias.

No puede utilizarse como sustituto del modelo CAD real.

---

# 9. SELECCIÓN CAD

Cuando el requisito indique selección desde Onshape:

La selección debe provenir realmente de la interfaz de Onshape.

No se considera selección real:

- escribir un ID en un input;
- copiar manualmente un ID;
- utilizar un ID hardcodeado;
- enviar un ID ficticio al backend.

Si la API o mecanismo oficial de Onshape no ha sido verificado, la funcionalidad debe permanecer como PENDIENTE o BLOQUEADA.

---

# 10. APIs EXTERNAS

Antes de implementar una integración con una API externa:

1. verificar documentación oficial;
2. confirmar endpoints;
3. confirmar parámetros;
4. confirmar mecanismo de autenticación;
5. confirmar limitaciones;
6. verificar que el mecanismo utilizado corresponde a la versión actual.

Nunca inventar endpoints o protocolos.

---

# 11. TESTING

Todo requisito debe probarse con el nivel de prueba apropiado.

### Unitario

Valida componentes individuales.

### Integración

Valida la interacción entre componentes.

### E2E

Valida el flujo completo.

### Manual

Se utiliza cuando la interacción depende de una interfaz externa o de acciones humanas.

Una prueba unitaria nunca puede presentarse como prueba E2E.

---

# 12. CRITERIO DE EVIDENCIA

Toda funcionalidad marcada como COMPLETADA debe tener evidencia.

La evidencia puede ser:

- test automatizado exitoso;
- prueba de integración;
- prueba E2E;
- prueba manual reproducible;
- resultado verificable del sistema.

La evidencia debe registrarse en `resumen_implementacion.md`.

---

# 13. GATES DE CADA ETAPA

Una etapa no puede considerarse finalizada hasta cumplir:

- [ ] Requisitos analizados
- [ ] Implementación realizada
- [ ] Errores controlados
- [ ] Tests realizados
- [ ] Integración verificada
- [ ] Evidencia disponible
- [ ] Documentación actualizada
- [ ] Auditoría final realizada

Si alguno de estos puntos no se cumple, la etapa permanece abierta.

---

# 14. DEPENDENCIAS ENTRE ETAPAS

No se debe avanzar a una etapa que dependa de otra etapa incompleta.

Ejemplo:

Onshape
↓
Selección
↓
Geometría
↓
Malla
↓
Condiciones de frontera
↓
FEA
↓
TopOpt
↓
Reconstrucción

Si la selección real no funciona, no se debe declarar completa la integración geométrica.

Si la malla real no existe, no se debe implementar FEA sobre una malla ficticia.

Si FEA no funciona, no se debe declarar TopOpt funcional.

---

# 15. PROHIBICIÓN DE FALSEAR EL ESTADO

La IA nunca debe:

- ocultar errores;
- minimizar fallos;
- cambiar criterios de aceptación;
- reinterpretar requisitos para declarar éxito;
- eliminar pruebas que fallen sin documentar el motivo;
- sustituir una implementación real por un mock;
- marcar una funcionalidad como completa por intención futura.

La precisión del estado es más importante que aparentar progreso.

---

# 16. DOCUMENTACIÓN OBLIGATORIA

Después de cada intervención significativa debe actualizarse:

`resumen_implementacion.md`

Debe incluir:

- fecha;
- iteración;
- objetivo;
- auditoría inicial;
- archivos modificados;
- implementación realizada;
- pruebas;
- resultados;
- problemas;
- estado final;
- pendientes;
- bloqueadores;
- próximo paso.

---

# 17. REGISTRO DE DECISIONES

Cuando una implementación sea descartada, debe documentarse.

Ejemplo:

> Se descarta el mallado basado en bounding box como solución FEM definitiva porque no representa adecuadamente la frontera CAD y no cumple el criterio establecido para malla volumétrica.

Esto evita volver a implementar soluciones previamente rechazadas.

---

# 18. CONTROL DEL ALCANCE

La IA debe trabajar únicamente sobre los requisitos necesarios para la etapa actual.

No debe implementar funcionalidades futuras solo porque sean técnicamente posibles.

Si descubre una mejora futura:

1. documentarla;
2. no implementarla;
3. continuar con el objetivo actual.

---

# 19. AUDITORÍA FINAL

Antes de declarar finalizada una iteración:

1. comparar código contra `prompt.md`;
2. comprobar metodología;
3. revisar pruebas;
4. comprobar evidencia;
5. actualizar `resumen_implementacion.md`;
6. clasificar cada requisito.

La IA debe declarar explícitamente:

- COMPLETADO
- PARCIAL
- PENDIENTE
- BLOQUEADO

---

# 20. REGLA DE HONESTIDAD TÉCNICA

Cuando exista duda entre:

"COMPLETADO"

y

"PARCIAL/PENDIENTE"

debe elegirse:

"PARCIAL/PENDIENTE".

Es preferible declarar una funcionalidad incompleta y continuar trabajando que declarar como terminada una funcionalidad que no puede demostrarse.

---

# 21. REGLA DE NO REGRESIÓN

Una nueva implementación no debe romper funcionalidades previamente verificadas.

Antes de finalizar una modificación:

- ejecutar los tests existentes relevantes;
- agregar o modificar tests cuando corresponda;
- verificar que las funcionalidades anteriores continúen funcionando.

Si una modificación rompe una funcionalidad anterior, debe documentarse y corregirse antes de declarar la etapa completada.

---

# 22. OBJETIVO FINAL DE LA METODOLOGÍA

El proyecto debe avanzar mediante funcionalidad real y verificable:

AUDITAR
↓
IMPLEMENTAR
↓
PROBAR
↓
VERIFICAR
↓
DOCUMENTAR
↓
APROBAR ETAPA
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