"""Sonda unica de dependencias (solo stdlib).

Sustituye los 4x `pip show` + 3x `python -c "import ..."` del .bat, que
costaban ~10s en cada arranque. Aqui todo corre en UN proceso:
- Requeridos (import rapido, <1s): webview, numpy, scipy.
- Requeridos pesados (SOLO version via importlib.metadata, sin importar
  las DLLs de OCC/VTK/Qt que tardarian segundos): PySide6, vtk.
- Opcionales (idem, sin importar): cadquery, gmsh.

Salida: lineas [OK]/[FALTA]/[AVISO] para el usuario.
Exit 0 = requeridos presentes (opcionales pueden faltar).
Exit 1 = falta algo requerido.
"""
from __future__ import annotations

import sys


def _have_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _have_dist(name: str) -> str | None:
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return None


def main() -> int:
    missing: list[str] = []

    print('[3/6] Paquetes Python obligatorios...')
    for mod in ('webview', 'numpy', 'scipy'):
        if _have_import(mod):
            print(f'  OK: {mod}.')
        else:
            print(f'  [FALTA] {mod} no importable.')
            missing.append(mod)
    for dist in ('PySide6', 'vtk'):
        ver = _have_dist(dist)
        if ver:
            print(f'  OK: {dist} {ver} (instalado, sin importar DLLs).')
        else:
            print(f'  [FALTA] {dist} no instalado.')
            missing.append(dist)

    if missing:
        print(f'  [FALTA] Paquetes Python no instalados:{" ".join(missing)}')
        print('  INSTALAR - elige una opcion:')
        print('    python -m pip install -r backend\\requirements.txt')
        print('    python -m pip install "pywebview>=4.4" "numpy>=1.24.0" "scipy>=1.11.0"')
        return 1
    print('  OK: pywebview + numpy + scipy + PySide6 + vtk.')

    print()
    print('[4/6] Paquetes Python opcionales (STEP y malla)...')
    opt_missing = [d for d in ('cadquery', 'gmsh') if _have_dist(d) is None]
    if opt_missing:
        print(f'  [AVISO] No estan:{" ".join(opt_missing)}'
              ' - la app abre igual, pero fallara importar STEP o mallar.')
        print('  INSTALAR cuando lo necesites:')
        print('    python -m pip install "cadquery>=2.3.0" "gmsh>=4.13.0"')
    else:
        print('  OK: cadquery + gmsh.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
