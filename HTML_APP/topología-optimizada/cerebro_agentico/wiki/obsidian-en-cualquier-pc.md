# Obsidian + cerebro en cualquier PC

Qué sabemos: cómo dejar este vault funcionando idéntico en otra máquina
a partir de un `git clone`, sin copiar nada a mano.

## Qué viaja con el repo (versionado en GitHub)

Dentro de `cerebro_agentico/.obsidian/`:

- `core-plugins.json` — plugins activos: graph, backlinks, templates,
  outgoing-links, file-explorer, búsqueda, command-palette, etc.
- `templates.json` — carpeta de plantillas: `proyectos/_plantilla`
  (ruta relativa, por eso es portable).
- `app.json`, `appearance.json` — ajustes base del vault.

## Qué NO viaja (a propósito, por PC y por usuario)

- `workspace.json`, `workspace-mobile.json` — layout de paneles abiertos.
- `hotkeys.json` — atajos personales.
- Están ignorados en `.gitignore` del proyecto.
- El registro de vaults de Obsidian (`%APPDATA%/obsidian/obsidian.json`)
  es local a cada PC: guarda rutas absolutas y no se versiona.

## Setup en una PC nueva (3 pasos)

1. Instalar Obsidian (`winget install --id Obsidian.Obsidian`).
2. Clonar el repo de GitHub.
3. En Obsidian: *Open folder as vault* → `cerebro_agentico/`.
   Los plugins y la carpeta de plantillas ya vienen configurados.

## Uso

- *Graph view* (`Ctrl+G` con una nota abierta): mapa de `[[enlaces]]`
  entre `wiki/` y `proyectos/`.
- Panel *Backlinks* (`Ctrl+P` → "Backlinks: Show backlinks"): quién cita
  la nota actual.
- *Templates*: `Ctrl+P` → "Templates: Insert template" → `estado.md`
  para arrancar un proyecto nuevo en `proyectos/<slug>/`.
