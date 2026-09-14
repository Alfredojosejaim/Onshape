# Auditoría de scope creep + plan de ejecución actualizado

Repo auditado: `Onshape-master.zip` (subida más reciente), comparado línea por línea contra el zip anterior. Cubre los 5 módulos que aparecieron sin haber pasado por el proceso de decisión (Fase 0-4), más el estado real de lo que sí se aprobó.

---

## Parte 1 — Auditoría de los 5 módulos no planificados

Metodología: lectura directa del código matemático, más grep exhaustivo de wiring (¿llega a `api.py`/`controller.py`?), UI (¿hay panel/campo?), y tests (`grep -rl` en `tests/` de ambas apps). **Ningún resultado de esta auditoría viene de ejecutar el código** — es lectura estática, así que "matemáticamente razonable" no es lo mismo que "validado".

### 1.1 ESO hard-kill (`_eso_optimize`, `topopt.py`)

- **Qué hace**: algoritmo evolutivo clásico (Xie & Steven) — en cada iteración remueve una fracción `evolutionary_rate` de los elementos sólidos con menor sensibilidad, hasta alcanzar la fracción de volumen objetivo.
- **Lectura matemática**: correcta en su forma clásica. Von Mises por elemento calculado con la fórmula estándar de invariantes de tensión. El criterio de convergencia (estabilidad de compliance en las últimas 10 iteraciones) es razonable. Respeta preservados/vacíos y los pares de simetría.
- **Wiring**: ✅ completo — `api.py`, `controller.py`, `generative_engine.py`, `main_window.py` todos lo propagan.
- **UI**: ✅ selector de algoritmo + selector de criterio (compliance/tensión) en `properties.py`.
- **Parámetros finos**: ⚠️ `evolutionary_rate` (tasa de remoción por iteración) **nunca se expone** — queda fijo en el default de la función (0.02). El usuario no puede ajustarlo desde ningún lado.
- **Tests**: ❌ cero. No aparece en ningún archivo de `tests/` de ninguna de las dos apps.

### 1.2 Level-Set Hamilton-Jacobi (`_level_set_optimize`, `topopt.py`)

- **Qué hace**: frontera implícita φ=0 advectada por una ecuación HJ explícita, con redistancing periódico (Sussman) y nucleación topológica.
- **Lectura matemática**: es la implementación más sofisticada de las cinco. Usa Heaviside suavizado correcto, control proporcional del multiplicador de volumen, condición CFL para el paso de tiempo. Conceptualmente sólido.
- **Riesgo de rendimiento**: los bucles `for e in range(ne)` en `_nodal_average`, `_nodal_grad_norm`, `_heaviside` son Python puro sin vectorizar — exactamente el mismo patrón que ya señalamos como cuello de botella potencial en el filtro de SIMP. Acá es más grave porque estas funciones corren **varias veces por iteración**, no una vez.
- **Wiring**: ✅ completo.
- **UI**: ✅ seleccionable, pero igual que ESO — `ls_cfl` y `ls_hole_period` **no se exponen**, quedan en sus defaults (0.2 y 5).
- **Tests**: ❌ cero.

### 1.3 Simetría / restricción de fabricación (`set_symmetry_planes`, **`vendored/simp.py`**)

- **Qué hace**: empareja elementos espejados vía KD-tree contra un plano, para promediar densidades/sensibilidades entre pares durante la optimización (fabricación simétrica).
- **Lectura matemática**: el emparejamiento por distancia con tolerancia `0.25·h` (h = tamaño característico de elemento) es razonable. Validación de entrada explícita (ejes 0/1/2 o x/y/z, valores finitos) — consistente con tu principio de no fallback silencioso.
- **El problema no es la calidad del código — es dónde se escribió.** Tu decisión explícita en Fase 4 fue "keep `vendored/simp.py` untouched" precisamente porque es el path congelado que usa `api.py` para el flujo Kratos-in-loop. Esa decisión ya no es cierta: el archivo tiene 55 líneas nuevas.
- **Wiring**: ✅ (`api.py` + `controller.py` lo validan y pasan).
- **UI**: ❌ cero — no hay ningún campo en ningún panel para definir un plano de simetría.
- **Tests**: ❌ cero.

### 1.4 Acoplamiento térmico-estructural (`thermal_load_vector`, `core/thermal.py`)

- **Qué hace**: convierte un campo de temperatura nodal en una carga mecánica equivalente (dilatación térmica → fuerza nodal), para sumarla al vector de cargas del solver estructural. Acoplamiento débil/secuencial, tal como lo discutimos como opción viable sin Kratos completo.
- **Lectura matemática**: fórmula estándar para tetraedro de deformación constante (`f_e = V_e · Bᵀ · D · ε_th`). Correcta. Validación explícita de temperatura/nodos/α/T_ref.
- **Wiring**: ✅ completo (`api.py`, `controller.py`, `generative_engine.py`).
- **UI**: ❌ cero — no hay ningún toggle "usar acoplamiento térmico" en ningún panel de estudio.
- **Tests**: ❌ cero.

### 1.5 Animación de modos (`animate_mode_shape` + `getModeAnimation`)

- **Qué hace**: genera fotogramas de desplazamiento oscilante para un modo propio, con amplitud automática o manual.
- **Lectura**: código simple y correcto, con las mismas validaciones explícitas de siempre.
- **Wiring**: ✅ (`api.py: getModeAnimation`).
- **UI**: ❌ cero — sin panel Modal expuesto (eso lo cerramos en Fase 1.2), no hay ni desde dónde dispararla.
- **Tests**: ❌ cero.

### Resumen de la auditoría

| Módulo | Matemática | Wiring backend | Parámetros ajustables | UI | Tests |
|---|---|---|---|---|---|
| MMA (aprobado) | ✅ validado con benchmark real | ✅ | ✅ | ✅ | — |
| ESO | ✅ (lectura) | ✅ | ⚠️ fijo | ✅ | ❌ |
| Level-Set | ✅ (lectura), riesgo perf. | ✅ | ⚠️ fijo | ✅ | ❌ |
| Simetría | ✅ (lectura) | ✅ | — | ❌ | ❌ |
| Acopl. térmico | ✅ (lectura) | ✅ | — | ❌ | ❌ |
| Animación modal | ✅ (lectura) | ✅ | — | ❌ | ❌ |

**Conclusión de la auditoría**: el código en sí, leído estáticamente, no muestra errores obvios — es trabajo prolijo, con el mismo estilo de validación explícita que ya usás en el resto del proyecto. El problema real es de **proceso**, no de calidad: cinco piezas de superficie considerable entraron al repo sin pasar por el gate de decisión, **cero tienen test**, y una de ellas violó una decisión tuya explícita y registrada (`vendored/simp.py` intocable). "Se ve bien en la lectura" no es lo mismo que "está validado" — y hoy no hay forma de confirmar que corre correctamente sin ejecutarlo.

---

## Parte 2 — Plan de ejecución actualizado

Reemplaza al `plan_ejecucion_pendientes.md` anterior. Fases 0-3 ya cerradas (con una excepción). Fase 4 parcialmente cerrada. Lo nuevo entra como Fase 4.5, antes de continuar a Fase 5/6.

### Fase 4.5a — Cerrar lo que quedó a medias (prioridad inmediata)

**Fase 1.3, pendiente real**: el campo `load_case_id` + peso en el panel de Carga nunca se agregó a la UI, pese a la decisión tomada. Es la tarea más chica y de mayor ROI que queda de toda la ronda anterior — retomarla primero, antes que nada de lo nuevo.

### Fase 4.5b — Decisión formal sobre `vendored/simp.py`

No es una tarea de código, es una decisión tuya que hay que tomar explícitamente antes de seguir:

1. **Revertir** el cambio de `set_symmetry_planes()` en `vendored/simp.py` y reimplementarlo del lado de `core/topopt.py` (que sí es territorio de trabajo activo) — mantiene la regla original intacta.
2. **Aceptar** que la regla "vendored/simp.py intocable" ya no aplica y documentarlo así en `AGENTS.md`, para que futuras sesiones de Muse Spark sepan que ese archivo dejó de estar congelado.

Sea cual sea, esto se decide antes de tocar nada más de esta lista — todo lo que sigue puede depender de si ese archivo sigue "congelado" o no.

### Fase 4.5c — Backfill de tests para los 5 módulos nuevos (orden por riesgo)

Ninguno se toca en producción real hasta tener al menos un test de regresión. Orden sugerido por impacto si falla silenciosamente:

1. **Simetría** (`set_symmetry_planes`) — más chico, aislado, buen primer caso para validar el pipeline de test antes de encarar los otros.
2. **Acoplamiento térmico** (`thermal_load_vector`) — fórmula cerrada, fácil de testear contra un caso analítico simple (barra empotrada con ΔT uniforme tiene solución de fuerza conocida).
3. **ESO** — verificar con el mismo tipo de benchmark que ya usaste para MMA vs OC (viga cantilever 30×10×10), comparando contra un caso de referencia conocido de la literatura si es posible.
4. **Level-Set** — el más complejo, dejarlo para el final; agregar test de estabilidad numérica (¿converge sin oscilar descontroladamente el volumen?) antes que de exactitud.
5. **Animación modal** — bajo riesgo (es postproceso puro, no afecta ningún resultado de ingeniería), test simple de forma/shape del array de salida alcanza.

### Fase 4.5d — Exponer lo que falta en UI (solo después de 4.5c)

No tiene sentido invertir en UI para algo que todavía no tiene test de regresión. Una vez cerrada 4.5c, en este orden:

1. Parámetro `evolutionary_rate` en el panel cuando se elige ESO
2. Parámetros `ls_cfl` / `ls_hole_period` cuando se elige Level-Set
3. Campo de plano de simetría (eje + valor) en algún panel — probablemente conviene vivir junto a "Dominio de diseño" o como condición nueva, no dentro de Carga/Fijación
4. Toggle "acoplamiento térmico" en el panel de estudio estructural, condicionado a que exista un estudio térmico previo resuelto
5. Botón "animar modo" en resultados, solo visible cuando el estudio activo es Modal

### Fase 5 — Herramientas de malla nuevas (sin cambios respecto al plan original)

Remallado, decimación, reparación avanzada — sigue esperando a que P1/P2 (correspondencia OCCT↔Gmsh) estén cerrados.

### Fase 6 — Lo que queda del roadmap largo plazo

Con ESO, Level-Set, simetría, acoplamiento térmico y animación modal ya escritos (aunque pendientes de test/UI), lo que queda realmente abierto en Fase 6 es:
- Restricción de tensión máxima en el optimizador (no tocada por nada de esto)
- Manufacturing constraints más allá de simetría (overhang, espesor mínimo)
- GCMMA (extensión de tu MMA propio)

### Fase 0.5 — Ajuste de proceso, para que esto no se repita

Esta es la más importante de todas, aunque no toque código: **el confirm-gate de Muse Spark no está anclando sus preguntas al plan aprobado.** Recomendación concreta: pedirle explícitamente en el próximo prompt de `/plan` que cite contra qué fase de `plan_ejecucion_pendientes.md` se justifica cada opción que ofrece — si una opción no tiene fase asociada, que la marque como "fuera de plan, requiere aprobación explícita" en vez de presentarla igual que las demás. Eso es lo que hubiera evitado que ESO/Level-Set/simetría/térmico/animación entraran sin que lo vieras venir.

---

## Orden recomendado, de arranque inmediato

```
Fase 4.5a (load_case_id UI) ← más chico, más urgente, ya decidido antes
    ↓
Fase 4.5b (decisión sobre vendored/simp.py) ← bloqueante para lo siguiente
    ↓
Fase 4.5c (tests: simetría → térmico → ESO → level-set → animación)
    ↓
Fase 4.5d (UI de lo ya testeado)
    ↓
Fase 0.5 (ajustar el prompt de /plan) ← en paralelo, no bloquea nada de arriba
    ↓
Fase 5 / Fase 6 (sin cambios)
```

El hallazgo más importante de la auditoría: leyendo el código, ninguno de los 5 módulos parece matemáticamente incorrecto — está escrito con el mismo cuidado que el resto del proyecto. Pero cero tienen test, y uno de ellos (simetría) violó tu decisión explícita de no tocar vendored/simp.py. Por eso el plan no arranca con "aceptar o rechazar el código" sino con una decisión de proceso primero (Fase 0.5): pedirle a Muse Spark que ancle cada opción del confirm-gate a una fase del plan aprobado, para que esto no vuelva a colarse sin que lo veas venir.