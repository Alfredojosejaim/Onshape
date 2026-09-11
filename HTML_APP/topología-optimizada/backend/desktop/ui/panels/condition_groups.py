"""condition_groups - agrupación visual de condiciones por pieza.

Helper compartido por DesignTree (nodos "Condiciones — Pieza_X" con badges
de valor) y Timeline (modo ramificado: una columna por pieza convergiendo
en el nodo Optimizar compartido).

La "pieza" de una condición se deriva de su SelectionSet existente
(CadEntityRef con solid_id / model_id); para caras sin sólido directo se
usa un ``part_resolver`` opcional ``(face_index, model_id) -> label`` que
típicamente delega en ``CADService.resolve_solid_for_face``. Sin resolver,
se agrupa por model_id ("General" si tampoco hay).

Colores semánticos (theme.json, ya reservados):
  LOAD (Carga)        -> force naranja
  ELASTICITY          -> constraint violeta
  OBSTRUCTION/PROTECTED (resto) -> sin color propio (texto por defecto)
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from core.cad_entity import CadEntityRef, EntityType
from core.conditions import ConditionType

try:
    from desktop.ui.style import FORCE, CONSTRAINT
except Exception:  # pragma: no cover - style siempre disponible en la app
    FORCE, CONSTRAINT = "#f59e0b", "#8b5cf6"


#: Resolvedor cara -> etiqueta de pieza. Devuelve None si no puede resolver.
PartResolver = Callable[[Optional[int], Optional[str]], Optional[str]]

#: Resolvedor ref completa -> etiqueta de pieza (más expresivo; preferido).
RefResolver = Callable[[CadEntityRef], Optional[str]]

#: Grupo sin pieza atribuible.
UNGROUPED_LABEL = "General"

#: Tipos con color semántico propio en theme.json.
TYPE_COLORS: Dict[ConditionType, str] = {
    ConditionType.LOAD: FORCE,
    ConditionType.ELASTICITY: CONSTRAINT,
}


def condition_color_hex(cond) -> Optional[str]:
    """Color semántico de la condición (None = texto por defecto)."""
    ctype = getattr(cond, "condition_type", None)
    if isinstance(cond, dict):
        try:
            ctype = ConditionType(cond.get("condition_type", ""))
        except Exception:
            ctype = None
    return TYPE_COLORS.get(ctype)


def condition_badge(cond) -> str:
    """Badge de valor por instancia (magnitud / flex / offset / conteo)."""
    get = (lambda k, d=None: cond.get(k, d)) if isinstance(cond, dict) \
        else (lambda k, d=None: getattr(cond, k, d))
    ctype = getattr(cond, "condition_type", None)
    if isinstance(cond, dict):
        try:
            ctype = ConditionType(cond.get("condition_type", ""))
        except Exception:
            ctype = None
    if ctype == ConditionType.LOAD:
        mag, unit = get("magnitude"), get("unit", "N") or "N"
        ind = get("indeterminate", True)
        if mag is None or ind:
            return "s/valor"
        try:
            return f"{float(mag):g} {unit}"
        except (TypeError, ValueError):
            return "s/valor"
    if ctype == ConditionType.ELASTICITY:
        flex = get("flex_range_mm")
        if flex is None:
            return "s/valor"
        try:
            return f"{float(flex):g} mm"
        except (TypeError, ValueError):
            return "s/valor"
    if ctype == ConditionType.OBSTRUCTION:
        off = get("offset_mm")
        if off is not None:
            try:
                return f"offset {float(off):g} mm"
            except (TypeError, ValueError):
                pass
        sel = cond.selection() if hasattr(cond, "selection") else None
        n = sel.count if sel is not None else 0
        return f"{n} cuerpo" if n == 1 else f"{n} cuerpos"
    if ctype == ConditionType.PROTECTED_REGION:
        sel = cond.selection() if hasattr(cond, "selection") else None
        n = sel.count if sel is not None else 0
        return f"{n} cara" if n == 1 else f"{n} caras"
    return ""


def condition_label(cond) -> str:
    """Etiqueta de una instancia: ``nombre [tipo] · badge``."""
    if isinstance(cond, dict):
        name = cond.get("name", "?")
        ctype_val = cond.get("condition_type", "?")
    else:
        name = getattr(cond, "name", "?")
        ctype = getattr(cond, "condition_type", None)
        ctype_val = ctype.value if ctype is not None else "?"
    label = f"{name}  [{ctype_val}]"
    badge = condition_badge(cond)
    if badge:
        label += f"  ·  {badge}"
    return label


def _ref_part_key(ref: CadEntityRef,
                  ref_resolver: Optional[RefResolver] = None,
                  part_resolver: Optional[PartResolver] = None) -> Optional[str]:
    if ref_resolver is not None:
        try:
            label = ref_resolver(ref)
        except Exception:
            label = None
        if label:
            return str(label)
    if ref.entity_type == EntityType.SOLID and ref.solid_id:
        return str(ref.solid_id)
    if ref.entity_type == EntityType.FACE and part_resolver is not None:
        try:
            label = part_resolver(ref.face_index, ref.model_id)
        except Exception:
            label = None
        if label:
            return str(label)
    return ref.model_id or None


def condition_part_key(cond,
                        ref_resolver: Optional[RefResolver] = None,
                        part_resolver: Optional[PartResolver] = None) -> str:
    """Clave de pieza de una condición (primera entidad resoluble)."""
    sel = cond.selection() if hasattr(cond, "selection") else None
    entities = list(sel.entities) if sel is not None else []
    for ref in entities:
        key = _ref_part_key(ref, ref_resolver, part_resolver)
        if key:
            return key
    # Sin entidades resolubles: grupo general (estable y predecible).
    return UNGROUPED_LABEL


def group_conditions_by_part(
    conditions: list,
    ref_resolver: Optional[RefResolver] = None,
    part_resolver: Optional[PartResolver] = None,
) -> List[Tuple[str, list]]:
    """Agrupa condiciones por pieza preservando orden de aparición.

    Devuelve ``[(etiqueta_pieza, [condiciones]), ...]``. Sin resolvedor,
    las caras caen a model_id/"General" y los sólidos a su solid_id.
    """
    groups: Dict[str, list] = {}
    order: List[str] = []
    for cond in conditions or []:
        key = condition_part_key(cond, ref_resolver, part_resolver)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(cond)
    return [(k, groups[k]) for k in order]


__all__ = [
    "UNGROUPED_LABEL",
    "TYPE_COLORS",
    "condition_badge",
    "condition_color_hex",
    "condition_label",
    "condition_part_key",
    "group_conditions_by_part",
]
