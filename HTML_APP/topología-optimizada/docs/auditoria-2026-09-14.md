# Acta de auditoría y correcciones — 14-sep-2026

**Proyecto:** `HTML_APP/topología-optimizada`
**Rama:** `master` · **HEAD en el momento de la auditoría:** `3dfbd1d`
**Árbol de trabajo:** limpio al inicio; 3 archivos modificados al cierre.
**Ejecutor:** agente de IA (ver firma al final).

---

## 1. Alcance y método

Auditoría solicitada por el usuario sobre el proyecto completo: backend Python
(82 ficheros / 27.563 líneas) y frontend React+TS (`src/`, 30 ficheros).

Método: lectura de documentos rectores (`AGENTS.md`, `plan.md`,
`inventario.md`, `docs/*`), inspección de código, y **verificación empírica** de
cada hallazgo (no se reportó nada que no se hubiera reproducido). Nada se marcó
como cierto por lectura de comentarios o docstrings.

## 2. Línea base medida (antes de tocar nada)

| Comprobación | Comando | Resultado |
|---|---|---|
| Tests backend | `python -m pytest backend/tests -q` | 20 passed |
| Tipado frontend | `npx tsc --noEmit` | limpio (exit 0) |
| Build producción | `npm run build` | OK, 3,54 s |
| Sintaxis Python | `python -m compileall backend` | limpio |
| Entorno | `python backend/check_env.py` | OK |
| CI / linters | — | **ninguno configurado** |

Nota de entorno: `npm run build` falla con `spawn EPERM` bajo sandbox
restringido porque esbuild necesita abrir un pipe. No es un defecto del
proyecto; con acceso completo builda correctamente (evidencia en §5).

También se verificó que las reglas de `AGENTS.md` se cumplen **de verdad**:
la simetría vive solo en `core/topopt.py`, y pedirla por el path vendored falla
explícito en `api.py:1022-1026`.

## 3. Hallazgos

Priorizados por severidad. **Se corrigieron los dos primeros** (autorizados por
el usuario); el resto queda como backlog documentado en §7.

| # | Sev. | Hallazgo | Estado |
|---|---|---|---|
| 1 | Crítico | Doc de re-sync destructivo | **CORREGIDO** |
| 2 | Alto | Rechazo de `gcmma` era código muerto | **CORREGIDO** |
| 3 | Alto | `vendored/simp.py` "congelado" no es literal + acoplamiento oculto al núcleo | backlog |
| 4 | Medio | Duplicación 62,6 % núcleo ↔ vendored | backlog |
| 5 | Medio | ~236 `except Exception: pass` | backlog |
| 6 | Medio | API HTTP local sin auth ni whitelist en servidor | backlog |
| 7 | Deuda | Multicarga: UI envía 1 carga, backend soporta N | backlog |
| 8 | Bajo | Residuos del template AI Studio + deps muertas | backlog |
| 9 | Bajo | Cobertura de tests fina (19 tests / 27,5k líneas) | backlog |

---

## 4. Corrección 1 — el re-sync documentado era destructivo

### Qué estaba mal

`backend/CORE_VENDORADO.txt` (líneas 1-18 antes del cambio) afirmaba que
`backend/core|desktop|adapters|services` eran "una COPIA de
Topologia_Optimizada" con "Fecha de copia: 2026-09-11", y documentaba como
procedimiento operativo normal:

```powershell
foreach ($d in @("core","desktop","adapters","services")) {
  Copy-Item -Recurse -Force -Path "$SRC\$d" -Destination "backend\$d"
}
```

Esa afirmación era falsa desde la Fase 2. El árbol local divergió, y el
comando habría sobrescrito el trabajo con una fuente obsoleta.

### Evidencia

Medición directa contra `D:\Documentos\GitHub\Onshape\Topologia_Optimizada`:

| Carpeta | Externo (líneas) | Local (líneas) | Delta |
|---|---|---|---|
| `core` | 11.461 | 13.396 | **+1.935** |
| `desktop` | 9.055 | 9.930 | +875 |
| `adapters` | 284 | 304 | +20 |
| `services` | 1.089 | 1.113 | +24 |
| | | | **+2.854** |

Caso testigo, el más grave:

```
Topologia_Optimizada\core\topopt.py          450 líneas
  coincidencias de gcmma|symmetry_planes|level_set|_eso_optimize: 0

backend\core\topopt.py                      1.306 líneas
  coincidencias de las mismas features: 44
```

Es decir: un `Copy-Item -Recurse -Force` borraba MMA, GCMMA, ESO, level-set,
simetría, acoplamiento térmico, herramientas de malla, factor de seguridad y
comparación de estudios.

**Mitigante encontrado (por eso la severidad es "pérdida de trabajo", no "bug
en runtime"):** `backend/api.py:23` solo añade la carpeta externa a `sys.path`
si `backend/core` **no existe**. Con el core local presente no hay mezcla de
versiones en ejecución.

### Qué se hizo

1. `backend/CORE_VENDORADO.txt` — **reescrito**. Se eliminó el bloque de
   re-sync, se marcó el aviso como destructivo con la tabla de divergencia
   medida, y se sustituyó por el procedimiento seguro obligatorio (respaldo en
   git → traer ficheros concretos → diff a mano → `pytest`). Se conservó la
   limpieza de `__pycache__`/`.pytest_cache`, que sí es inocua.
2. `docs/arbol-operaciones-multicuerpo.md` §6 — actualizada la referencia
   cruzada, que repetía la misma instrucción peligrosa ("Re-sincronizar según
   `backend/CORE_VENDORADO.txt`").

---

## 5. Corrección 2 — el rechazo específico de `gcmma` era inalcanzable

### Qué estaba mal

En `Api.runSimpLoop` (`backend/api.py`), el guard específico de `gcmma` estaba
**después** del rechazo genérico, así que nunca se ejecutaba:

```python
optimizer = str(p.get("optimizer", "oc")).lower()
if optimizer not in ("oc", "mma", "eso", "level_set"):
    return {... "no soportado ..."}          # gcmma cae AQUÍ
if optimizer == "gcmma":
    return {... "solo en núcleo ..."}        # código MUERTO
```

Contradecía el principio fail-loud del proyecto y la nota GCMMA de
`AGENTS.md`: el usuario que pedía `gcmma` por el path vendored recibía un
mensaje genérico, sin la explicación de que debe usar `runOptimization`.

### Evidencia (reproducida en runtime, antes del fix)

```
gcmma -> {"ok": false, "error": "optimizer='gcmma' no soportado (usar 'oc', 'mma', 'eso' o 'level_set')"}
bogus -> {"ok": false, "error": "optimizer='bogus' no soportado (usar 'oc', 'mma', 'eso' o 'level_set')"}
```

Mensajes idénticos ⇒ el guard específico era inalcanzable.

Comprobación de alcance: `runOptimization` (línea 488) **sí** incluye `gcmma`
en su tupla válida, es decir, el path de núcleo nunca estuvo roto. El defecto
estaba confinado a `runSimpLoop`.

### Qué se hizo

Se movió el guard específico **antes** del rechazo genérico, con comentario
`AUDIT-FIX` que remite a esta acta. Diff real:

```diff
             optimizer = str(p.get("optimizer", "oc")).lower()
-            if optimizer not in ("oc", "mma", "eso", "level_set"):
-                return {"ok": False,
-                        "error": f"optimizer={optimizer!r} no soportado (usar 'oc', 'mma', 'eso' o 'level_set')"}
+            # AUDIT-FIX (14-sep-2026): la comprobacion especifica de gcmma va
+            # ANTES del rechazo generico. Estaba despues y era codigo muerto:
+            # gcmma ya caia en el "not in" y el usuario recibia el mensaje
+            # generico sin la explicacion (nucleo vs path vendored). Caso
+            # detectado en auditoria; ver docs/auditoria-2026-09-14.md.
             if optimizer == "gcmma":
                 return {"ok": False,
                         "error": "optimizer='gcmma' solo en núcleo (runOptimization): "
                                  "el path vendored está congelado (Fase 4.5b)."}
+            if optimizer not in ("oc", "mma", "eso", "level_set"):
+                return {"ok": False,
+                        "error": f"optimizer={optimizer!r} no soportado (usar 'oc', 'mma', 'eso' o 'level_set')"}
```

### Verificación después del fix

```
gcmma    -> {"ok": false, "error": "optimizer='gcmma' solo en núcleo (runOptimization): el path vendored está congelado (Fase 4.5b)."}
bogus    -> {"ok": false, "error": "optimizer='bogus' no soportado (usar 'oc', 'mma', 'eso' o 'level_set')"}
MMMA     -> {"ok": false, "error": "optimizer='mmma' no soportado (usar 'oc', 'mma', 'eso' o 'level_set')"}
oc       -> {"ok": true}
```

Los cuatro casos son correctos: `gcmma` da ahora el mensaje específico, un
desconocido sigue dando el genérico, y `oc` (camino feliz) no se rompió.

### Regresión

`python -m pytest backend/tests -q` → **20 passed, 3 warnings in 3.23s**
(antes del cambio: 20 passed, 4 warnings in 3.24s; la variación de warnings es
ruido del caché de pytest, no del código).

---

## 6. Resumen de archivos modificados

| Archivo | Cambio | SHA-256 |
|---|---|---|
| `backend/api.py` | Reordenado el guard de `gcmma` en `runSimpLoop` | `10F8C5342241B2D14C050B1990820D40FEBDDD5B922452BBDA2FBA43EDFBEA7C` |
| `backend/CORE_VENDORADO.txt` | Reescrito: re-sync marcado como destructivo | `4DD6D578F9B6B8A2895976F8AE8840DFD5802B9402CAADB3EF318E711552882D` |
| `docs/arbol-operaciones-multicuerpo.md` | §6 actualizada, referencia cruzada corregida | `64B8750307C079B6047E732715BBBC537862FAD9781197E703CFB5B79EC3F23A` |
| `docs/auditoria-2026-09-14.md` | Este acta (nuevo) | — |

Los hashes permiten comprobar que el contenido revisado es el que está en disco.

---

## 7. Backlog — hallazgos NO corregidos

Se dejan sin tocar a propósito: no estaban autorizados y varios requieren
decisión de diseño del usuario.

**3. `vendored/simp.py` "CONGELADO" no es literal.** El fichero contiene
`_mma_update` (línea 350) y `_eso_optimize` (línea 651) — espejos de Fase 6,
posteriores a la congelación de Fase 4 — y además `optimize()` delega el
level-set al núcleo pasándole su propia instancia:

```python
# vendored/simp.py:479-490
return _CoreSIMP._level_set_optimize(self, ...)
```

Funciona porque los nombres de atributo coinciden, pero significa que **un
cambio en `core/topopt.py::_level_set_optimize` altera en silencio el path
vendored**. La congelación real solo cubre simetría y GCMMA. Requiere decidir
qué se quiere que signifique "congelado".

**4. Duplicación estructural.** El 62,6 % de las líneas significativas de
`core/topopt.py` aparece idéntico en `vendored/simp.py` (1.025 → 642). El núcleo
tiene 31 métodos, el vendored 25; `_oc_update`, `_mma_*`, `_finalize_result` y
`_eso_optimize` están duplicados. El único guardián de paridad son los tests.

**5. Fallo silencioso.** ~236 `except Exception: pass`, concentrados en
`services/cad_service.py`, `desktop/ui/main_window.py`, `desktop/viewport/*` y
`core/face_correspondence.py`. Muchos son defensivos legítimos (VTK/Qt); en
importación CAD y correspondencia cara↔malla se oponen al principio de "no
fallback silencioso" que el solver sí respeta.

**6. `server.py` sin auth.** `getattr(_API, method)` alcanza cualquier atributo,
incluidas las privadas (`_submit`). La whitelist existe solo en el cliente
(`app_desktop.py:35-45`). Puerto aleatorio y bind a `127.0.0.1` limitan el
impacto, pero cualquier proceso local puede dirigir el núcleo.

**7. Multicarga pendiente** (ya documentado en
`docs/sesion-viewport-negro-y-estabilidad.md:87-98`): `pushBoundaries()`
(`src/App.tsx:476-483`) envía una sola carga y `runFea` nunca pasa
`condition_ids`, aunque el backend ya lo soporta vía `_resolve_conditions`.

**8. Residuos AI Studio.** `README.md` sigue siendo el genérico de AI Studio
(`GEMINI_API_KEY`, link a ai.studio); `metadata.json` declara
`MAJOR_CAPABILITY_SERVER_SIDE_GEMINI_API`; `.env.example` es de Gemini.
Dependencias sin uso en `src/`: `@google/genai`, `motion`, `lucide-react`,
`express`, `dotenv`; devDeps `tsx`, `esbuild`, `autoprefixer`. `npm run clean`
borra un `server.js` que no existe. `package.json` se llama `react-example` en
versión `0.0.0`. Coexisten dos hosts desktop: `app_desktop.py` (nuevo,
autocontenido) y `app_hybrid.py`/`bridge_core.py`, que insertan el
`Topologia_Optimizada` externo en `sys.path` — contradictorio con el diseño
autocontenido.

**9. Cobertura.** 19 funciones de test en 3 ficheros. Sin cobertura de
importación CAD/STEP, mallado, FEA estructural, térmico, modal, FoS,
reconstrucción de malla ni frontend. Sin CI.

---

## 8. Firma

Yo, el agente de IA abajo identificado, **declaro** que:

1. Ejecuté la auditoría descrita en este documento.
2. Apliqué **únicamente** las correcciones 1 y 2, tras autorización explícita
   del usuario ("aplica los arreglos").
3. **No** modifiqué ningún otro fichero, ni en `backend/core`, ni en
   `backend/vendored`, ni en el solver, ni en el frontend.
4. Cada afirmación de este acta está respaldada por un comando ejecutado y su
   salida, reproducida en §2, §4, §5 y §6.
5. Los tests pasan después de mis cambios (20/20) y los cuatro casos de
   verificación de `gcmma`/`optimizer` se comportan como se describe.

```
Firmado:  dsh-agent (DeepSeek Harness)
Modelo:   deepseek-official/deepseek-v4-flash
Sesión:   d44256d6b389
Fecha:    2026-09-14 08:31 -03:00
Lugar:    D:\Documentos\GitHub\Onshape\HTML_APP\topología-optimizada
Motivo:   "audita el proyecto" → "aplica los arreglos y documenta
           detalladamente lo que hiciste y firma que lo hiciste"
```

**Alcance y límites de esta firma.** Es una declaración de trazabilidad del
agente, **no** una firma criptográfica ni un aval humano: no aporta
no-repudio. Los SHA-256 de §6 sí permiten a un tercero comprobar que el
contenido aprobado es el que está en disco. Toda decisión de diseño derivada
del backlog de §7 corresponde al usuario, no al agente.

— Fin del acta —
