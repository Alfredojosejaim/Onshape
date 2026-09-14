"""Lectores de mallas de superficie (STL/OBJ/PLY/3MF) — numpy + stdlib.

Sin OCC/CadQuery: un STL/OBJ/PLY/3MF no es un B-Rep y no pasa por el
``StepAdapter``. El resultado es geometria cruda ``(vertices, triangles)``
que el ``CADService`` envuelve en un ``CADModel`` de tipo ``MESH`` (un
solido ``solid_0``, sin caras B-Rep): la conversion a solido real la hace
el usuario con sus herramientas; aqui solo se importa, se diagnostica y
se repara la malla.

Fail-loud: formato desconocido, archivo vacio, cero triangulos o indices
fuera de rango lanzan ``MeshIOError`` (nunca se devuelve una malla
silenciosamente vaciada o truncada).
"""

from __future__ import annotations

import io
import struct
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple

import numpy as np


class MeshIOError(ValueError):
    """Formato de malla no soportado o archivo invalido (fail-loud)."""


MESH_FORMATS = ("stl", "obj", "ply", "3mf")
MESH_EXTENSIONS = {".stl": "stl", ".obj": "obj",
                   ".ply": "ply", ".3mf": "3mf"}

# Unidades -> milimetros (el core trabaja en mm). STL/OBJ son adimensionales
# y se asumen en mm; PLY igual; 3MF trae atributo de unidad explicito.
_UNIT_TO_MM = {
    "millimeter": 1.0, "millimetre": 1.0, "mm": 1.0,
    "centimeter": 10.0, "centimetre": 10.0, "cm": 10.0,
    "meter": 1000.0, "metre": 1000.0, "m": 1000.0,
    "inch": 25.4, "in": 25.4,
    "foot": 304.8, "ft": 304.8,
    "micron": 1e-3, "micrometer": 1e-3, "micrometre": 1e-3,
}


def detect_mesh_format(data: bytes, filename: str = "") -> str:
    """Detecta ``stl`` | ``obj`` | ``ply`` | ``3mf`` | ``step`` | ``unknown``.

    Contenido primero, extension como desempate: un ``.stl`` cuyo contenido
    no parsea como malla no se acepta por la extension (fail-loud).
    """
    head = bytes(data[:8]) if data else b""
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    ext_hint = MESH_EXTENSIONS.get(ext)

    if head[:2] == b"PK":
        # ZIP: 3MF si contiene un modelo 3D; si no, desconocido (nunca STEP).
        try:
            with zipfile.ZipFile(io.BytesIO(bytes(data))) as zf:
                names = [n.lower() for n in zf.namelist()]
            if any(n.endswith(".model") for n in names):
                return "3mf"
        except Exception:
            pass
        return "unknown"
    if head[:3] == b"ply":
        return "ply"
    if data is not None and len(data) >= 8 and bytes(data[:8]).startswith(b"ISO-1030"):
        return "step"
    if data:
        stripped = data.lstrip() if isinstance(data, (bytes, bytearray)) else b""
        if stripped[:5].lower() == b"solid" and (
                b"facet" in data[:1 << 20] or b"endsolid" in data[:1 << 20]):
            return "stl"  # ASCII
        if len(data) >= 84:
            try:
                n = struct.unpack_from("<I", data, 80)[0]
            except struct.error:
                n = None
            # Binario exacto, o con bytes extra al final (algunos
            # exportadores agregan terminador). Un STL binario cuyo nombre
            # empieza con "solid" cae aqui si no tiene "facet".
            if n is not None and n > 0 and len(data) >= 84 + 50 * n:
                return "stl"
        # OBJ: lineas "v x y z" y "f i j k" (texto).
        try:
            sample = data[:1 << 20].decode("ascii", errors="strict").splitlines()
        except (UnicodeDecodeError, ValueError):
            sample = []
        has_v = has_f = False
        for ln in sample[:2000]:
            s = ln.strip()
            if s.startswith("v ") and not has_v:
                parts = s.split()
                if len(parts) >= 4:
                    try:
                        float(parts[1]); float(parts[2]); float(parts[3])
                        has_v = True
                    except ValueError:
                        pass
            elif s.startswith("f ") and not has_f:
                has_f = True
            if has_v and has_f:
                return "obj"
    # Sin evidencia de contenido: la extension sola no basta (fail-loud).
    if ext_hint:
        return ext_hint if _extension_content_hint_ok(data, ext_hint) else "unknown"
    return "unknown"


def _extension_content_hint_ok(data: bytes, hint: str) -> bool:
    """La extension solo confirma, nunca diagnostica: exige rasgos minimos."""
    if not data:
        return False
    if hint == "obj":
        try:
            txt = data[:4096].decode("ascii", errors="strict")
        except (UnicodeDecodeError, ValueError):
            return False
        return any(ln.strip().startswith(("v ", "f ")) for ln in txt.splitlines()[:200])
    if hint == "ply":
        return bytes(data[:3]) == b"ply"
    if hint == "stl":
        return len(data) >= 84
    if hint == "3mf":
        return bytes(data[:2]) == b"PK"
    return False


# --------------------------------------------------------------------- STL ---

def _read_stl_binary(data: bytes) -> Tuple[np.ndarray, np.ndarray]:
    n = struct.unpack_from("<I", data, 80)[0]
    if n <= 0 or len(data) < 84 + 50 * n:
        raise MeshIOError(f"STL binario inconsistente: declara {n} triangulos "
                          f"pero el buffer trae {len(data)} bytes")
    rec = np.frombuffer(data, dtype=np.uint8, count=50 * n, offset=84)
    rec = rec.reshape(n, 50)
    # 12 floats (normal + 3 vertices) + 2 bytes atributo por registro.
    floats = rec[:, :48].view("<f4").reshape(n, 12)
    verts = floats[:, 3:12].astype(np.float64).reshape(-1, 3)
    tris = np.arange(n * 3, dtype=np.int64).reshape(n, 3)
    return verts, tris


def _read_stl_ascii(data: bytes) -> Tuple[np.ndarray, np.ndarray]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise MeshIOError(f"STL ASCII con bytes no ASCII: {exc}") from exc
    coords = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("vertex"):
            parts = s.split()
            if len(parts) != 4:
                raise MeshIOError(f"STL ASCII: linea 'vertex' malformada: {ln.strip()!r}")
            try:
                coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError as exc:
                raise MeshIOError(f"STL ASCII: coordenada invalida: {ln.strip()!r}") from exc
    if not coords or len(coords) % 3 != 0:
        raise MeshIOError(f"STL ASCII sin facetas completas "
                          f"({len(coords)} vertices sueltos)")
    verts = np.asarray(coords, dtype=np.float64)
    tris = np.arange(len(coords), dtype=np.int64).reshape(-1, 3)
    return verts, tris


def read_stl(data: bytes) -> Tuple[np.ndarray, np.ndarray]:
    """STL binario o ASCII (auto-deteccion por contenido, no por extension)."""
    data = bytes(data)
    is_ascii = data.lstrip()[:5].lower() == b"solid" and (
        b"facet" in data[:1 << 20] or b"endsolid" in data[:1 << 20])
    if is_ascii:
        return _read_stl_ascii(data)
    return _read_stl_binary(data)


# --------------------------------------------------------------------- OBJ ---

def _obj_index(tok: str, n_verts: int) -> int:
    """Indice OBJ (1-based, admite negativos relativos) -> 0-based."""
    base = tok.split("/")[0]
    try:
        i = int(base)
    except ValueError as exc:
        raise MeshIOError(f"OBJ: indice de cara invalido: {tok!r}") from exc
    if i > 0:
        j = i - 1
    elif i < 0:
        j = n_verts + i
    else:
        raise MeshIOError("OBJ: indice de cara 0 (los indices son 1-based)")
    if not 0 <= j < n_verts:
        raise MeshIOError(f"OBJ: indice de cara {i} fuera de rango "
                          f"({n_verts} vertices)")
    return j


def read_obj(data: bytes) -> Tuple[np.ndarray, np.ndarray]:
    """OBJ: solo geometria (v/f). Materiales, grupos y normales se ignoran.

    Poligonos de N lados se triangularizan en abanico (fan). Fallan en
    explicito: caras con <3 vertices, indices fuera de rango, cero caras.
    """
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except Exception as exc:
            raise MeshIOError(f"OBJ no decodificable como texto: {exc}") from exc
    verts = []
    tris = []
    for lineno, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("v "):
            parts = s.split()
            if len(parts) < 4:
                raise MeshIOError(f"OBJ linea {lineno}: vertice incompleto: {s!r}")
            try:
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError as exc:
                raise MeshIOError(f"OBJ linea {lineno}: coordenada invalida: {s!r}") from exc
        elif s.startswith("f "):
            parts = s.split()[1:]
            if len(parts) < 3:
                raise MeshIOError(f"OBJ linea {lineno}: cara con <3 vertices: {s!r}")
            idx = [_obj_index(t, len(verts)) for t in parts]
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
    if not verts:
        raise MeshIOError("OBJ sin vertices ('v ')")
    if not tris:
        raise MeshIOError("OBJ sin caras ('f ')")
    return (np.asarray(verts, dtype=np.float64),
            np.asarray(tris, dtype=np.int64))


# --------------------------------------------------------------------- PLY ---

_PLY_TYPES = {"char": "i1", "uchar": "u1", "short": "i2", "ushort": "u2",
              "int": "i4", "uint": "u4", "float": "f4", "double": "f8"}


def _parse_ply_header(data: bytes):
    """Devuelve (format, vertex_count, vertex_props, face_count, list_count_type, list_index_type, body_offset)."""
    end = data.find(b"end_header")
    if end < 0:
        raise MeshIOError("PLY sin 'end_header'")
    header = data[:end].decode("ascii", errors="strict").splitlines()
    body_off = end + len(b"end_header")
    # Salta el fin de linea tras end_header.
    if data[body_off:body_off + 2] == b"\r\n":
        body_off += 2
    elif data[body_off:body_off + 1] in (b"\n", b"\r"):
        body_off += 1
    fmt = None
    elements = []
    cur = None
    for ln in header:
        parts = ln.strip().split()
        if not parts or parts[0] == "ply" or parts[0] == "comment":
            continue
        if parts[0] == "format":
            fmt = parts[1]
        elif parts[0] == "element":
            cur = {"name": parts[1], "count": int(parts[2]), "props": []}
            elements.append(cur)
        elif parts[0] == "property" and cur is not None:
            cur["props"].append(parts[1:])
    if fmt not in ("ascii", "binary_little_endian", "binary_big_endian"):
        raise MeshIOError(f"PLY con formato no soportado: {fmt!r}")
    if fmt == "binary_big_endian":
        raise MeshIOError("PLY binary_big_endian no soportado "
                          "(usar ascii o binary_little_endian)")
    verts_el = next((e for e in elements if e["name"] == "vertex"), None)
    faces_el = next((e for e in elements if e["name"] == "face"), None)
    if verts_el is None or faces_el is None:
        raise MeshIOError("PLY sin elementos 'vertex' + 'face'")
    vnames = [p[-1] for p in verts_el["props"] if len(p) == 2]
    if not all(k in vnames for k in ("x", "y", "z")):
        raise MeshIOError("PLY: vertices sin propiedades x/y/z")
    list_prop = next((p for p in faces_el["props"]
                      if p[0] == "list"), None)
    if list_prop is None:
        raise MeshIOError("PLY: caras sin propiedad 'list'")
    return (fmt, verts_el, faces_el, list_prop[1], list_prop[2], body_off)


def read_ply(data: bytes) -> Tuple[np.ndarray, np.ndarray]:
    """PLY ascii y binary_little_endian (vertex x/y/z + face list)."""
    data = bytes(data)
    fmt, verts_el, faces_el, count_t, index_t, body_off = _parse_ply_header(data)
    nv, nf = verts_el["count"], faces_el["count"]
    if nv <= 0 or nf <= 0:
        raise MeshIOError(f"PLY vacio: {nv} vertices, {nf} caras")
    if fmt == "ascii":
        body = data[body_off:].decode("ascii", errors="strict").splitlines()
        if len(body) < nv + nf:
            raise MeshIOError("PLY ascii truncado (menos lineas que vertex+face)")
        vlines = body[:nv]
        ncols = len(verts_el["props"])
        try:
            flat = np.fromstring(" ".join(vlines), sep=" ", dtype=np.float64)
        except ValueError as exc:
            raise MeshIOError(f"PLY ascii: vertices no numericos: {exc}") from exc
        if flat.size != nv * ncols:
            raise MeshIOError("PLY ascii: columnas de vertice inconsistentes")
        vtab = flat.reshape(nv, ncols)
        vnames = [p[-1] for p in verts_el["props"] if len(p) == 2]
        ix, iy, iz = vnames.index("x"), vnames.index("y"), vnames.index("z")
        verts = vtab[:, [ix, iy, iz]]
        flines = body[nv:nv + nf]
        # Via rapida: todas las caras "3 i j k".
        if all(ln.strip().split(" ", 1)[0] == "3" for ln in flines):
            try:
                fflat = np.fromstring(" ".join(flines), sep=" ", dtype=np.int64)
            except ValueError as exc:
                raise MeshIOError(f"PLY ascii: caras no numericas: {exc}") from exc
            if fflat.size != nf * 4:
                raise MeshIOError("PLY ascii: caras inconsistentes")
            tris = fflat.reshape(nf, 4)[:, 1:4]
        else:  # n-gonos: fan.
            tris = []
            for lineno, ln in enumerate(flines):
                parts = ln.strip().split()
                try:
                    nums = [int(x) for x in parts]
                except ValueError as exc:
                    raise MeshIOError(f"PLY ascii linea de cara no numerica: {ln!r}") from exc
                if len(nums) < 4 or nums[0] != len(nums) - 1 or nums[0] < 3:
                    raise MeshIOError(f"PLY ascii: cara malformada: {ln!r}")
                idx = nums[1:]
                if any(i < 0 or i >= nv for i in idx):
                    raise MeshIOError(f"PLY ascii: indice fuera de rango: {ln!r}")
                for k in range(1, len(idx) - 1):
                    tris.append((idx[0], idx[k], idx[k + 1]))
            tris = np.asarray(tris, dtype=np.int64)
    else:  # binary_little_endian
        vtypes = [_PLY_TYPES.get(p[0]) for p in verts_el["props"] if len(p) == 2]
        if any(t is None for t in vtypes):
            raise MeshIOError("PLY binario: tipo de vertice no soportado")
        vnames = [p[-1] for p in verts_el["props"] if len(p) == 2]
        vdt = np.dtype([(f"c{i}", "<" + t) for i, t in enumerate(vtypes)])
        vtab = np.frombuffer(data, dtype=vdt, count=nv, offset=body_off)
        ix, iy, iz = vnames.index("x"), vnames.index("y"), vnames.index("z")
        verts = np.column_stack([vtab[f"c{ix}"], vtab[f"c{iy}"],
                                 vtab[f"c{iz}"]]).astype(np.float64)
        foff = body_off + nv * vdt.itemsize
        cdt = np.dtype("<" + _PLY_TYPES[count_t])
        idt = np.dtype("<" + _PLY_TYPES[index_t])
        # Via rapida estandar: count u1 + 3x int32. El byte de conteo
        # rompe el alineado, asi que se lee con stride explicito.
        if count_t == "uchar" and index_t in ("int", "uint"):
            from numpy.lib.stride_tricks import as_strided
            stride = 1 + 3 * idt.itemsize
            flat = np.frombuffer(data, dtype=np.uint8,
                                 count=nf * stride, offset=foff)
            counts = flat[0::stride]
            if not bool((counts == 3).all()):
                raise MeshIOError("PLY binario: caras no triangulares "
                                  "(usar ascii o triangularizar)")
            idx_bytes = as_strided(flat[1:], shape=(nf, 3 * idt.itemsize),
                                   strides=(stride, 1))
            tris = np.array(idx_bytes.view(idt).reshape(nf, 3),
                            dtype=np.int64)
        else:  # conteo/indice no estandar: lectura secuencial explicita.
            tris = []
            pos = foff
            for _ in range(nf):
                c = int(np.frombuffer(data, dtype=cdt, count=1, offset=pos)[0])
                pos += cdt.itemsize
                if c < 3:
                    raise MeshIOError("PLY binario: cara con <3 vertices")
                idx = np.frombuffer(data, dtype=idt, count=c, offset=pos).astype(np.int64)
                pos += c * idt.itemsize
                if bool((idx < 0).any() | (idx >= nv).any()):
                    raise MeshIOError("PLY binario: indice fuera de rango")
                for k in range(1, c - 1):
                    tris.append((int(idx[0]), int(idx[k]), int(idx[k + 1])))
            tris = np.asarray(tris, dtype=np.int64)
    if bool((tris < 0).any() | (tris >= nv).any()):
        raise MeshIOError("PLY: indice de cara fuera de rango")
    return verts, np.ascontiguousarray(tris)


# --------------------------------------------------------------------- 3MF ---

_3MF_NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def read_3mf(data: bytes) -> Tuple[np.ndarray, np.ndarray, float]:
    """3MF: vertices/triangulos de todos los <object> tipo modelo.

    Devuelve (vertices, triangles, unit_scale_mm). Solo malla (sin color,
    materiales ni texturas): la app trabaja solidos, no apariencia.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(bytes(data)))
    except Exception as exc:
        raise MeshIOError(f"3MF no es un ZIP valido: {exc}") from exc
    model_name = next((n for n in zf.namelist()
                       if n.lower().endswith(".model")), None)
    if model_name is None:
        raise MeshIOError("3MF sin archivo *.model")
    try:
        root = ET.fromstring(zf.read(model_name))
    except ET.ParseError as exc:
        raise MeshIOError(f"3MF con XML invalido: {exc}") from exc
    scale = _UNIT_TO_MM.get(str(root.attrib.get("unit", "millimeter")).lower(), 1.0)
    all_v, all_t = [], []
    for obj in root.iter(_3MF_NS + "object"):
        mesh = obj.find(_3MF_NS + "mesh")
        if mesh is None:
            continue
        v_el = mesh.find(_3MF_NS + "vertices")
        t_el = mesh.find(_3MF_NS + "triangles")
        if v_el is None or t_el is None:
            continue
        base = len(all_v)
        for v in v_el.findall(_3MF_NS + "vertex"):
            try:
                all_v.append((float(v.attrib["x"]), float(v.attrib["y"]),
                              float(v.attrib["z"])))
            except (KeyError, ValueError) as exc:
                raise MeshIOError(f"3MF: vertice invalido: {exc}") from exc
        nv = len(all_v) - base
        for t in t_el.findall(_3MF_NS + "triangle"):
            try:
                idx = (int(t.attrib["v1"]), int(t.attrib["v2"]), int(t.attrib["v3"]))
            except (KeyError, ValueError) as exc:
                raise MeshIOError(f"3MF: triangulo invalido: {exc}") from exc
            if any(i < 0 or i >= nv for i in idx):
                raise MeshIOError(f"3MF: indice fuera de rango: {idx}")
            all_t.append((base + idx[0], base + idx[1], base + idx[2]))
    if not all_v or not all_t:
        raise MeshIOError("3MF sin malla (sin <object> con <mesh> valido)")
    verts = np.asarray(all_v, dtype=np.float64) * scale
    return verts, np.asarray(all_t, dtype=np.int64), scale


# ------------------------------------------------------------------ API -----

def read_mesh(data: bytes, filename: str = "") -> Dict[str, object]:
    """Lee STL/OBJ/PLY/3MF por contenido. ``MeshIOError`` si no es malla."""
    data = bytes(data or b"")
    if not data:
        raise MeshIOError("archivo vacio")
    fmt = detect_mesh_format(data, filename)
    if fmt not in MESH_FORMATS:
        raise MeshIOError(
            f"formato no reconocido como malla (detectado: {fmt!r}). "
            f"Soportados: STL, OBJ, PLY, 3MF.")
    if fmt == "stl":
        verts, tris = read_stl(data)
        scale = 1.0
    elif fmt == "obj":
        verts, tris = read_obj(data)
        scale = 1.0
    elif fmt == "ply":
        verts, tris = read_ply(data)
        scale = 1.0
    else:
        verts, tris, scale = read_3mf(data)
    if tris.shape[0] == 0:
        raise MeshIOError(f"{fmt.upper()} sin triangulos")
    if not bool(np.isfinite(verts).all()):
        raise MeshIOError(f"{fmt.upper()} con coordenadas no finitas (NaN/Inf)")
    return {"format": fmt, "vertices": np.ascontiguousarray(verts),
            "triangles": np.ascontiguousarray(tris),
            "num_vertices": int(verts.shape[0]),
            "num_triangles": int(tris.shape[0]),
            "unit_scale_mm": float(scale),
            "name": filename or f"malla.{fmt}"}


def mesh_signed_volume(vertices: np.ndarray, triangles: np.ndarray) -> float:
    """Volumen con signo (teorema de divergencia). ~0 si abierta/degen."""
    v0 = vertices[triangles[:, 0]]
    v1 = vertices[triangles[:, 1]]
    v2 = vertices[triangles[:, 2]]
    return float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)


def mesh_area(vertices: np.ndarray, triangles: np.ndarray) -> float:
    """Area total de la superficie."""
    v0 = vertices[triangles[:, 0]]
    v1 = vertices[triangles[:, 1]]
    v2 = vertices[triangles[:, 2]]
    return float(0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).sum())


def coherent_stride_preview(vertices: np.ndarray, triangles: np.ndarray,
                            max_triangles: int) -> Tuple[np.ndarray, np.ndarray]:
    """Submuestreo coherente para preview: toma 1 de cada k triangulos y
    remapea solo los vertices usados (la conectividad nunca se rompe, a
    diferencia del diezmado por filas de ``_clean``)."""
    m = int(triangles.shape[0])
    if m <= max_triangles:
        return vertices, triangles
    step = max(1, m // max(1, int(max_triangles)))
    sub = np.ascontiguousarray(triangles[::step])
    used, remap = np.unique(sub, return_inverse=True)
    return (np.ascontiguousarray(vertices[used]),
            np.ascontiguousarray(remap.reshape(sub.shape)))
