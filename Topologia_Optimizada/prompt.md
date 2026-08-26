# VALIDACIÓN DEFINITIVA — KRATOS COMO MOTOR FEA + TOPOLOGICAL OPTIMIZATION

## OBJETIVO

Este es el ÚLTIMO EXPERIMENTO antes de tomar una decisión arquitectónica sobre Kratos Multiphysics.

Debes leer nuevamente:

- `README.md`
- `metodología.md`
- `prompt.md`
- `RESUMEN_IMPLEMENTACION.md`

y revisar todo el contenido existente de:

`experimentos/kratos_topopt_poc/`

El objetivo NO es investigar nuevamente si Kratos posee determinadas clases o capacidades.

El objetivo es DEMOSTRAR MEDIANTE EJECUCIÓN REAL si Kratos puede funcionar como motor de:

1. FEA estructural 3D Tet4.
2. SIMP.
3. Cálculo de respuesta estructural.
4. Sensibilidades.
5. Filtrado.
6. Actualización de densidades.
7. Restricción de volumen.
8. Iteración completa de optimización topológica.

Al finalizar debes emitir un VEREDICTO TÉCNICO FINAL que determine si Kratos puede reemplazar el solver FEA + SIMP propio que inicialmente estaba previsto para el proyecto.

---

# 1. REGLA FUNDAMENTAL

NO aceptar como evidencia:

- que una clase exista;
- que una API esté documentada;
- que un ejemplo exista;
- que un script se haya creado;
- que una variable cambie;
- que una prueba termine sin error.

Una capacidad solamente se considera:

`PASS / VERIFICADA`

si fue ejecutada realmente y existe evidencia cuantitativa o verificable de su funcionamiento.

Diferenciar estrictamente:

- `PASS — VERIFICADO`
- `PARTIAL — PARCIALMENTE VERIFICADO`
- `FAIL — FALLÓ`
- `NOT VERIFIED — NO VERIFICADO`
- `NOT APPLICABLE`

NO convertir un `PARTIAL` o `NOT VERIFIED` en `PASS`.

---

# 2. AISLAMIENTO ABSOLUTO

Todo trabajo experimental debe permanecer exclusivamente dentro de:

`experimentos/kratos_topopt_poc/`

Puedes modificar o reemplazar archivos dentro de esa carpeta si es necesario.

NO modificar:

- `README.md`
- `metodología.md`
- `prompt.md`
- arquitectura principal;
- código productivo;
- documentación histórica;
- otros experimentos;
- archivos fuera del PoC.

La ÚNICA excepción es:

`RESUMEN_IMPLEMENTACION.md`

porque debe contener el resultado final de esta validación.

---

# 3. PRIMER PASO — AUDITORÍA DEL POC EXISTENTE

Antes de modificar código:

1. Leer todos los scripts existentes.
2. Identificar qué pruebas ya funcionan.
3. Ejecutar nuevamente las pruebas existentes.
4. Identificar cuáles son solamente pruebas de disponibilidad de API.
5. Identificar cuáles son pruebas numéricas reales.
6. Identificar qué pruebas están incompletas.
7. No asumir que los resultados anteriores siguen siendo válidos.

Documentar internamente el estado inicial antes de corregir nada.

---

# 4. ENTORNO REAL

Registrar exactamente:

- Sistema operativo.
- Python.
- Kratos.
- StructuralMechanicsApplication.
- OptimizationApplication.
- Gmsh.
- versión de cada dependencia.

Verificar que las pruebas utilizan realmente esas versiones.

No utilizar simulaciones falsas ni mocks para sustituir Kratos.

---

# 5. MODELO FÍSICO DEFINITIVO

Utilizar una viga en voladizo 3D.

Geometría:

- L = 100 mm
- ancho = 10 mm
- alto = 10 mm

Material:

- E = 68.9 GPa
- ν = 0.33

Carga:

- Fz = -100 N

La geometría debe estar en unidades coherentes.

Documentar claramente el sistema de unidades utilizado.

---

# 6. MALLA DEFINITIVA

Generar la malla mediante Gmsh.

Debe ser:

- volumétrica;
- tetraédrica;
- Tet4;
- reproducible.

Registrar:

- nodos;
- elementos;
- tamaño aproximado;
- tipo de elemento;
- grupos físicos.

Verificar que los elementos importados a Kratos sean realmente los elementos utilizados por el solver.

NO aceptar:

"se generó una malla Tet4"

sin demostrar que esa malla fue la utilizada por el análisis.

---

# 7. PRUEBA 1 — FEA REAL SIN OPTIMIZACIÓN

Esta prueba es OBLIGATORIA.

Ejecutar:

Gmsh
→ Tet4
→ Kratos ModelPart
→ Structural Mechanics
→ condiciones de contorno
→ carga
→ solver
→ desplazamientos

Debe obtenerse una solución numérica real.

Registrar:

- desplazamiento máximo;
- desplazamiento en el extremo libre;
- reacciones;
- energía/compliance si está disponible.

---

# 8. VALIDACIÓN ANALÍTICA

Calcular la solución analítica de Euler-Bernoulli:

δ = F L³ / (3 E I)

donde:

I = b h³ / 12

Comparar:

δ_FEM

contra:

δ_analítica

Calcular:

error_relativo =
abs(δ_FEM - δ_analítica) / abs(δ_analítica)

IMPORTANTE:

No exigir arbitrariamente menos del 5 % para una única malla Tet4 si la discretización no lo permite.

Si el error supera el 5 %:

1. refinar la malla;
2. volver a ejecutar;
3. registrar el comportamiento.

La conclusión debe basarse en convergencia.

---

# 9. ESTUDIO DE CONVERGENCIA

Ejecutar al menos tres niveles:

- malla gruesa;
- malla media;
- malla fina.

Registrar:

| Malla | Elementos | δ FEM | δ analítica | Error |
|---|---:|---:|---:|---:|

Determinar si el resultado converge hacia la solución analítica.

Esto es obligatorio para validar el solver.

---

# 10. PRUEBA 2 — SIMP REAL

Después de validar FEA, ejecutar la optimización.

Utilizar la infraestructura REAL de:

`OptimizationApplication`

y preferentemente:

`SimpControl`

si es compatible con el caso.

NO implementar un simulador artificial de SIMP.

NO reducir la prueba a:

ρ = [1.0, 0.5, 0.3...]

sin que esas densidades sean utilizadas por el FEA.

La densidad debe modificar realmente las propiedades estructurales.

Debe cumplirse conceptualmente:

E(ρ) = E0 · ρ^p

con:

p = 3

o el valor equivalente configurado por Kratos.

---

# 11. CICLO DE OPTIMIZACIÓN REAL

Demostrar el siguiente ciclo:

ρ
↓
FEA
↓
respuesta
↓
sensibilidad
↓
filtro
↓
actualización
↓
ρ nueva
↓
FEA nuevamente

Debe ejecutarse realmente durante varias iteraciones.

Mínimo recomendado:

10 iteraciones.

Preferiblemente continuar hasta que:

- se alcance convergencia;
- o se alcance un máximo razonable de iteraciones.

---

# 12. PRUEBA CRÍTICA — DEMOSTRAR QUE LA DENSIDAD AFECTA AL FEA

Esta prueba es obligatoria.

Seleccionar elementos con densidades distintas.

Demostrar que cambiar:

ρ = 1.0

a:

ρ < 1.0

produce una modificación real de la respuesta estructural.

Registrar:

- densidad;
- Young efectivo;
- respuesta;
- compliance;
- desplazamiento.

Esto elimina el riesgo de tener una optimización que solamente modifica una variable visual sin afectar el análisis.

---

# 13. RESPONSE

Utilizar:

`LinearStrainEnergyResponseFunction`

si es compatible con la configuración.

Demostrar que la respuesta:

- se calcula;
- cambia cuando cambia el diseño;
- se utiliza durante la optimización.

Registrar el valor de la función objetivo por iteración.

---

# 14. SENSIBILIDADES REALES

Verificar que las sensibilidades se calculan a partir del estado FEA real.

Por cada iteración registrar:

- mínimo;
- máximo;
- promedio;
- cantidad de NaN;
- cantidad de Inf.

Debe cumplirse:

NaN = 0
Inf = 0

salvo que exista una explicación numérica específica y documentada.

---

# 15. FILTRO

Utilizar un filtro real de OptimizationApplication si es compatible.

Demostrar que:

- existe;
- se aplica;
- participa en el ciclo;
- no es simplemente declarado pero nunca utilizado.

Documentar:

- tipo;
- parámetros;
- radio/tamaño;
- dónde se aplica.

---

# 16. RESTRICCIÓN DE VOLUMEN

Esta prueba es OBLIGATORIA.

Objetivo:

fracción volumétrica ≈ 40 %

o el valor técnicamente más apropiado para el modelo.

Registrar:

V_inicial

V_objetivo

V_por_iteración

V_final

error_final

Crear una tabla:

| Iteración | Volumen relativo | Objetivo | Error |
|---:|---:|---:|---:|

Demostrar que la restricción realmente participa en la optimización.

La existencia de `MassOptResponse` NO constituye evidencia suficiente.

---

# 17. TABLA MAESTRA DE ITERACIONES

Generar obligatoriamente:

| Iteración | Objective | Volumen | Min ρ | Max ρ | Mean ρ | Δρ |
|---:|---:|---:|---:|---:|---:|---:|

Los valores deben proceder de la ejecución real.

NO inventar valores.

NO escribir manualmente una tabla que no provenga de los resultados.

---

# 18. CRITERIOS DE CONVERGENCIA

Determinar:

- cambio de densidad;
- cambio de objetivo;
- estabilidad del volumen.

Definir criterios explícitos.

Por ejemplo:

Δρ < tolerancia

durante varias iteraciones consecutivas.

Si no converge:

marcar:

`NOT VERIFIED`

y explicar por qué.

NO declarar éxito solamente porque se ejecutaron N iteraciones.

---

# 19. RESULTADO VISUAL

Generar un resultado visual de la distribución final de densidad.

El resultado debe proceder de las densidades obtenidas por el optimizador REAL.

Puede utilizarse:

- VTK;
- ParaView;
- GiD;
- cualquier formato verificable.

Debe ser posible comprobar que:

- existen regiones de alta densidad;
- existen regiones de baja densidad;
- la distribución corresponde a los datos finales.

---

# 20. PRUEBA DE REPRODUCIBILIDAD

Eliminar resultados temporales si es necesario.

Ejecutar nuevamente:

`python run_poc.py`

o el comando definitivo.

Comprobar que:

1. genera la malla;
2. ejecuta FEA;
3. ejecuta optimización;
4. genera resultados;
5. termina correctamente.

Si requiere pasos manuales, documentarlos.

---

# 21. AUDITORÍA DE "FAKE PASS"

Antes de concluir, revisar específicamente que NO haya:

- densidades modificadas manualmente para aparentar optimización;
- resultados hardcodeados;
- respuestas ficticias;
- matrices ficticias;
- sensitivities ficticias;
- resultados copiados de ejemplos;
- valores escritos manualmente;
- mocks;
- simulaciones que no utilizan Kratos;
- scripts que solamente comprueban que una clase existe.

Si encuentras alguno:

ELIMINARLO O AISLARLO COMO PRUEBA DE API.

Nunca presentarlo como validación del pipeline.

---

# 22. RESULTADO FINAL OBLIGATORIO

Actualizar:

`RESUMEN_IMPLEMENTACION.md`

No limitarse a describir qué código se creó.

Debe documentar:

## 22.1 Entorno

Versiones exactas.

## 22.2 Pruebas realizadas

Lista completa.

## 22.3 Resultados FEA

Resultados numéricos.

## 22.4 Convergencia

Tabla de mallas.

## 22.5 SIMP

Evidencia de que la densidad afecta realmente al FEA.

## 22.6 Sensibilidades

Resultados y estadísticas.

## 22.7 Filtro

Configuración y evidencia.

## 22.8 Volumen

Resultados por iteración.

## 22.9 Optimización

Tabla completa de iteraciones.

## 22.10 Resultado visual

Archivo generado y descripción.

---

# 23. MATRIZ DE VEREDICTO

Al final de `RESUMEN_IMPLEMENTACION.md` crear exactamente una matriz similar a:

| Capacidad | Estado | Evidencia |
|---|---|---|
| Gmsh Tet4 | PASS/PARTIAL/FAIL | ... |
| Importación a Kratos | ... | ... |
| FEA 3D | ... | ... |
| Euler-Bernoulli | ... | ... |
| Convergencia | ... | ... |
| SIMP real | ... | ... |
| Densidad → Young | ... | ... |
| Response | ... | ... |
| Sensibilidades | ... | ... |
| Filtro | ... | ... |
| Actualización | ... | ... |
| Restricción de volumen | ... | ... |
| Iteraciones reales | ... | ... |
| Convergencia TopOpt | ... | ... |
| Resultado visual | ... | ... |
| Reproducibilidad | ... | ... |

---

# 24. VEREDICTO FINAL

El informe DEBE terminar con uno de estos tres veredictos:

## VEREDICTO A — VIABLE

Solamente si:

- FEA funciona;
- Tet4 funciona;
- validación analítica es razonable;
- existe convergencia;
- SIMP es real;
- sensitivities son reales;
- filtro funciona;
- volumen funciona;
- las densidades afectan el FEA;
- existe optimización real;
- el resultado es reproducible.

Entonces concluir:

> Kratos puede utilizarse como motor FEA + optimización topológica de la aplicación standalone y puede reemplazar el desarrollo de un solver FEA/SIMP propio para esta etapa.

---

## VEREDICTO B — VIABLE CON LIMITACIONES

Si Kratos funciona pero alguna capacidad crítica requiere desarrollo adicional.

Especificar exactamente:

- qué funciona;
- qué no;
- qué debemos implementar nosotros;
- impacto arquitectónico.

---

## VEREDICTO C — NO VIABLE

Si no puede demostrarse el flujo necesario.

Explicar:

- dónde falla;
- evidencia;
- causa;
- alternativa.

---

# 25. DECISIÓN ARQUITECTÓNICA

Solamente si el resultado es:

`VIABLE`

o:

`VIABLE CON LIMITACIONES`

indicar qué arquitectura recomienda el experimento.

Ejemplo:

Gmsh
↓
Kratos Structural Mechanics
↓
Kratos OptimizationApplication
↓
SIMP
↓
Resultados

y especificar qué componentes seguirían siendo responsabilidad de nuestra aplicación.

---

# 26. REGLA SOBRE README

NO modificar `README.md`.

Aunque el resultado sea positivo.

La decisión arquitectónica se realizará posteriormente, después de auditar este informe.

---

# 27. AUDITORÍA FINAL DE CAMBIOS

Antes de finalizar:

Ejecutar una revisión equivalente a:

`git diff`

Confirmar que:

- únicamente se modificaron archivos del PoC;
- `RESUMEN_IMPLEMENTACION.md` es la única excepción;
- no se modificó README;
- no se modificó metodología;
- no se modificó prompt;
- no se modificó código productivo.

Si existe cualquier cambio fuera de esas ubicaciones:

REVERTIRLO.

---

# 28. CONDICIÓN DE TERMINACIÓN

NO declares la tarea completada hasta que:

1. El FEA real haya sido ejecutado.
2. La validación analítica haya sido realizada.
3. El estudio de convergencia haya sido ejecutado.
4. SIMP real haya sido ejecutado.
5. Las densidades hayan afectado realmente al FEA.
6. Las sensibilidades hayan sido calculadas.
7. El filtro haya sido utilizado.
8. La restricción de volumen haya sido demostrada.
9. Existan iteraciones reales de optimización.
10. Exista evidencia numérica.
11. Exista resultado visual.
12. El experimento pueda reproducirse.
13. `RESUMEN_IMPLEMENTACION.md` contenga el veredicto final.
14. No existan contradicciones entre resultados y conclusión.

Si alguna condición no puede cumplirse:

NO ocultarla.

Marcarla explícitamente como:

`NOT VERIFIED`

y explicar exactamente qué impide su validación.

# OBJETIVO FINAL

Al terminar, debemos poder responder con evidencia y sin especulación:

"¿Kratos Multiphysics puede reemplazar nuestro solver FEA + SIMP propio como motor científico de nuestra aplicación standalone?"

Esta prueba debe producir la evidencia necesaria para tomar esa decisión arquitectónica de forma definitiva.