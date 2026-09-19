# Instalación de plugins: anti-slop + Thermos

Fecha: 2026-09-19. Máquina origen: Windows + Node 22 / npm 11.

Esto deja ambos plugins funcionando en OpenCode y replica en otra PC con 5 comandos.

## 1. Requisitos

- Node.js 20+ (`node --version`, `npm --version`)
- Git
- Repo clonado con `package.json` del proyecto

## 2. Anti-slop (dmmulroy/anti-slop)

Fuente: https://github.com/dmmulroy/anti-slop
Instalador vía skills.sh: https://www.skills.sh/dmmulroy/anti-slop/install-anti-slop

```powershell
npx -y skills add https://github.com/dmmulroy/anti-slop --skill install-anti-slop -y
node .agents/skills/install-anti-slop/scripts/install.mjs
npm install --save-dev --save-exact oxlint@1.83.0 "@oxlint/plugins@1.83.0"
```

Esto crea:

- `.agents/skills/install-anti-slop/` (skill instalador, con `assets/anti-slop/`, `scripts/install.mjs`, `references/update.md`)
- `tools/oxlint/anti-slop/` (plugin vendoreado: `index.ts`, `rules/`, `shared/`, `effect/`, `vendor/eslint-stylistic/LICENSE` + `UPSTREAM.md`)
- `oxlint.config.ts` (crear con el contenido de abajo si no existe)
- Entradas `oxlint` y `@oxlint/plugins` pineadas en `devDependencies`

`oxlint.config.ts` del proyecto (sin reglas Effect porque no usamos `effect`):

```ts
import { defineConfig } from "oxlint";

export default defineConfig({
  ignorePatterns: [
    ".agent/**",
    ".agents/**",
    ".claude/**",
    ".codex/**",
    ".continue/**",
    ".cursor/**",
    ".gemini/**",
    ".opencode/**",
    ".pi/**",
    ".roo/**",
    ".windsurf/**",
    "tools/oxlint/anti-slop/**",
    "dist/**",
    "node_modules/**",
  ],
  jsPlugins: [
    { name: "anti-slop", specifier: "./tools/oxlint/anti-slop/index.ts" },
  ],
  rules: {
    "oxc/no-accumulating-spread": "error",
    "anti-slop/no-array-filter-map": "error",
    "anti-slop/no-reduce-accumulator-copy": "error",
    "anti-slop/no-chained-type-assertions": "error",
    "anti-slop/no-conditional-empty-object-spread": "error",
    "anti-slop/no-known-value-widening": "error",
    "anti-slop/no-module-mocking": "error",
    "anti-slop/no-object-parameters": "error",
    "anti-slop/no-reflect-apply": "error",
    "anti-slop/no-reflect-get": "error",
    "anti-slop/no-runtime-typeof": "error",
    "anti-slop/no-shape-in-symbol-names": "error",
    "anti-slop/no-unknown-parameters": "error",
    "anti-slop/no-unknown-returns": "error",
    "anti-slop/no-unknown-type-aliases": "error",
    "anti-slop/no-unsafe-dictionary-type": "error",
    "anti-slop/no-widen-then-assert": "error",
    "anti-slop/require-readable-spacing": "error",
    "anti-slop/require-safety-comment-for-type-assertion": "error",
  },
});
```

Verificar:

```powershell
npx oxlint
npx tsc --noEmit
```

Nota: `npx oxlint` reporta errores estrictos en código existente
(`faces.ts`, `camera3d.ts`, `Header.tsx`). Es lo esperado; no se corrigió
código porque la instalación no incluye migración/limpieza.

**Estado 2026-09-19 (limpieza completa autorizada): 0 errores.**
Se corrigieron los 309: `src/lib/guards.ts` (predicados `isRecord`,
`isNumber`, `isFiniteNumber`, `isString`, `isBoolean`, `isBridgeFunction`,
`isJsonValue`), `JsonValue`/`JsonRecord` en `types.ts`, frontera tipada en
`bridge.ts` (envelope `Ok` con `error?`/`mock?`, payloads por método) y
`realdata.ts` sin `unknown`/`typeof`/`as`. Decisiones documentadas:
- `no-runtime-typeof` con `{ allowInTypeGuards: true }` (opción oficial del
  plugin): el único `typeof` vive en los predicados de `guards.ts`.
- `onshape` en `navigation.ts` con `oxlint-disable-next-line`: el nombre lo
  exige el backend (`core/navigation.py`) y la marca; renombrarlo rompería
  `getNavProfiles`/`setNavProfile`.

Actualizar después (preservando customizaciones): leer
`.agents/skills/install-anti-slop/references/update.md` y seguir ese
procedimiento, no reinstalar con `--force`.

## 3. Thermos (cursor/plugins, plugin de Cursor adaptado a OpenCode)

Fuente: https://github.com/cursor/plugins (`thermos/`)
Skills vía: `npx skills add https://github.com/cursor/plugins --skill <nombre>`

```powershell
npx -y skills add https://github.com/cursor/plugins --skill thermos -y
npx -y skills add https://github.com/cursor/plugins --skill thermo-nuclear-review -y
npx -y skills add https://github.com/cursor/plugins --skill thermo-nuclear-code-quality-review -y
```

Esto crea:

- `.agents/skills/thermos/` (orquestador: lanza las 2 revisiones en paralelo y sintetiza)
- `.agents/skills/thermo-nuclear-review/` (rúbrica bugs/seguridad/breaking/devex)
- `.agents/skills/thermo-nuclear-code-quality-review/` (rúbrica mantenibilidad, regla 1k líneas, spaghetti, code-judo)

Los 2 subagentes del plugin (`thermos/agents/*.md`) se portaron a OpenCode
copiando el cuerpo y añadiendo `mode: subagent` en el frontmatter:

- `.opencode/agent/thermo-nuclear-review-subagent.md`
- `.opencode/agent/thermo-nuclear-code-quality-review-subagent.md`

Equivalente manual sin `skills` CLI: sparse-checkout de `thermos/` y copia
de `thermos/skills/*` a `.agents/skills/` + `thermos/agents/*` a
`.opencode/agent/` con `mode: subagent`.

Uso: pedir revisión `thermos`; el agente junta `git diff` + contenidos y
lanza ambos subagentes en paralelo vía Task, luego sintetiza.

## 4. Pegamento OpenCode

`opencode.json` en la raíz (ya existe en el repo):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": {
    "paths": [".agents/skills"]
  }
}
```

Evita duplicar skills en `.opencode/skills/`.

## 5. Réplica completa en otra PC (orden)

```powershell
git clone <repo> ; cd <repo>
npm install
npx -y skills add https://github.com/dmmulroy/anti-slop --skill install-anti-slop -y
node .agents/skills/install-anti-slop/scripts/install.mjs
npm install --save-dev --save-exact oxlint@1.83.0 "@oxlint/plugins@1.83.0"
npx -y skills add https://github.com/cursor/plugins --skill thermos -y
npx -y skills add https://github.com/cursor/plugins --skill thermo-nuclear-review -y
npx -y skills add https://github.com/cursor/plugins --skill thermo-nuclear-code-quality-review -y
```

Los archivos `oxlint.config.ts`, `opencode.json`, `.opencode/agent/thermo-*.md`
ya vienen del repo vía git; solo hay que reinstalar `node_modules`.
Luego reiniciar OpenCode (la config se carga al arrancar, no en caliente).

## 6. Archivos del repo que lo prueban

- `oxlint.config.ts`, `opencode.json`, `package.json` (devDeps oxlint)
- `tools/oxlint/anti-slop/`, `.agents/skills/*/`, `.opencode/agent/thermo-*.md`
- `skills-lock.json` (lo genera el CLI `skills`; commiteado para trazabilidad)
