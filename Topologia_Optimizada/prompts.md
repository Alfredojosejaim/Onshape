AUDITORÍA Y AVANCE — FLUJO CAE COMPLETO

Audita directamente el repositorio "Alfredojosejaim/Onshape", carpeta "Topologia_Optimizada", sobre el estado ACTUAL de "master".

OBJETIVO

Determinar qué tan funcional y conectado está realmente el flujo:

CAD → Condiciones → Mallado → FEA → Topología → Reconstrucción CAD → Resultado

No rehagas arquitectura ni investigues tecnologías alternativas. El objetivo es detectar únicamente funcionalidades declaradas como implementadas que todavía estén incompletas, desconectadas o simuladas.

1. AUDITORÍA

Revisa especialmente:

- "core/conditions.py"
- "core/meshing.py"
- "core/fea*"
- "core/topology*"
- "core/generative*"
- "core/cad_reconstruction.py"
- "services/"
- "desktop/pipeline/"
- "desktop/ui/"
- tests relacionados.

Verifica:

Condiciones

- Las condiciones creadas desde la UI llegan realmente al estudio.
- Las caras/entidades seleccionadas mantienen referencias CAD válidas.
- Cargas, restricciones, elasticidad, obstrucciones y regiones protegidas conservan sus parámetros.
- No existen datos ficticios o hardcodeados sustituyendo selecciones reales.

Mallado

- El mallado recibe realmente la geometría CAD actual.
- Las entidades CAD seleccionadas pueden convertirse en grupos/regiones utilizables por FEA.
- Los grupos físicos o equivalentes conservan la correspondencia con las caras/zonas CAD.
- El mallado no utiliza geometría artificial cuando debería utilizar la pieza real.

FEA

- El estudio recibe geometría, malla, material y condiciones reales.
- Las condiciones se traducen correctamente a las entidades de la malla.
- El solver utilizado está realmente conectado al flujo.
- Los resultados son reales y no valores simulados para completar la interfaz.
- Los resultados pueden volver a asociarse con la geometría/malla visualizada.

Topología

- La optimización consume realmente los resultados/condiciones del estudio FEA.
- El porcentaje de optimización y demás parámetros afectan el cálculo.
- El resultado de la optimización representa una geometría/densidad derivada del problema real.
- No aceptar como “implementado” un algoritmo que solamente genere datos de demostración.

Reconstrucción CAD

- Existe una ruta real desde el resultado optimizado hasta geometría CAD.
- La geometría reconstruida puede convertirse en un "CADModel".
- El resultado puede volver al "Document", viewport, historial y Design Tree.
- Se invalidan correctamente malla, resultados y estudios cuando corresponde.

2. INTEGRACIÓN

Comprueba especialmente los puntos donde un módulo entrega datos al siguiente.

Para cada etapa indica:

Entrada → procesamiento real → salida → consumidor

Si existe una desconexión, identifícala con archivo, clase/método y causa.

3. CLASIFICACIÓN

Clasifica cada hallazgo:

- CRÍTICO: impide ejecutar el flujo.
- ALTO: el flujo aparenta funcionar pero una etapa importante está simulada, desconectada o produce resultados incorrectos.
- MEDIO: funcionalidad incompleta que no bloquea el flujo principal.
- BAJO: deuda técnica o mejora futura.

No conviertas scaffolds intencionales en errores. Thermal/Modal y otras funciones explícitamente planificadas como futuras deben permanecer como tales si su arquitectura es correcta.

4. REGLA IMPORTANTE

NO vuelvas a auditar como problemas abiertos:

- Transform
- Mirror
- Pattern
- centro de Circular Pattern
- sincronización básica "Document" después de operaciones CAD
- resolución Face → Solid sin fallback arbitrario

Solo revísalos si detectas una regresión real en el código actual.

5. IMPLEMENTACIÓN

Después de la auditoría:

1. Corrige únicamente los problemas CRÍTICOS y ALTOS que puedan resolverse con la arquitectura existente.
2. No reemplaces sistemas funcionales.
3. No migres Python a C++ salvo que exista una imposibilidad técnica demostrada.
4. No rediseñes visualmente la aplicación.
5. Mantén PySide6 + VTK y la arquitectura actual.
6. Añade o corrige tests para cada problema solucionado.
7. Ejecuta la suite completa de tests.
8. Corrige cualquier regresión encontrada.
9. Actualiza "PROJECT_STATUS.md" únicamente con el estado realmente comprobado.

6. RESULTADO OBLIGATORIO

Al finalizar informa:

- qué estaba realmente implementado;
- qué estaba desconectado o incompleto;
- qué corregiste;
- archivos modificados;
- tests ejecutados y resultado;
- qué bloquea todavía el flujo CAE completo;
- cuál es el siguiente paso técnico más lógico.

No declares una etapa como IMPLEMENTADA solamente porque existan clases, interfaces o UI para ella. Debe existir integración funcional verificable de extremo a extremo.