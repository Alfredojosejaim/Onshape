# proyectos/

Una subcarpeta por proyecto u objetivo activo.

- Nombrá cada proyecto con un slug corto y estable, sin espacios ni tildes:
  `proyectos/nombre-proyecto/`.
- Estructura mínima de cada proyecto:

  ```
  proyectos/<nombre-proyecto>/
  ├── estado.md       # snapshot: qué se hizo, qué falta, decisiones abiertas
  ├── notas/          # (opcional) notas de trabajo del día a día
  └── entregables/    # (opcional) archivos finales producidos
  ```

- `estado.md` es lo primero que la IA debe leer al retomar un proyecto.
  Mantenerlo corto y actualizado vale más que tenerlo exhaustivo.
- Un proyecto inactivo no se borra: queda como historial. Solo se archiva
  si el usuario lo pide explícitamente.
- No mezclar dos proyectos distintos en la misma carpeta.

Ver `/AGENTS.md` para las reglas completas y la plantilla de proyecto en
`_plantilla/`.
