Procesó durante 32s

Sí. Hice la auditoría sobre el estado actual de master, incluyendo el último commit 3db3791, que ya intentó corregir el problema CAD Face ↔ Gmsh Surface. Y encontré un problema importante: la solución implementada todavía no está suficientemente cerrada.

🔴 1. El nuevo mapeo geométrico no garantiza realmente un 1:1

El nuevo core/face_correspondence.py calcula una firma con:

centro

normal

área


y después, para cada cara CAD, selecciona independientemente el candidato Gmsh con menor distancia.

El problema está en esta lógica conceptual:

for fi, csig in enumerate(cad_sigs):
    best_tag = None
    best_score = float("inf")

    for tag, gsig in gmsh_sigs:
        score = _signature_distance(csig, gsig)
        if score < best_score:
            best_score = score
            best_tag = tag

    mapping[fi] = best_tag

No existe una comprobación de que best_tag no haya sido asignado previamente a otra cara CAD.

Por lo tanto puede ocurrir:

CAD Face 0 ─────┐
                ├──→ Gmsh Surface 17
CAD Face 1 ─────┘

y el resultado seguiría teniendo el mismo número de caras/superficies.

Eso contradice el objetivo declarado de construir una correspondencia 1:1.

Además, el propio código solamente verifica:

if len(cad_sigs) != len(gmsh_sigs):
    raise FaceCorrespondenceError(...)

Pero igual número de elementos no implica una correspondencia biyectiva.

Severidad: 🔴 Alta.


---

🔴 2. Hay un posible UnboundLocalError en _shape_face_signatures

El código contiene:

center, normal = _robust_face_reference_point(face)

if center is None or normal is None:
    md = np.array([0.0, 0.0, 0.0])
else:
    c = np.array([...])
    n = np.array([...])

...

FaceSignature(
    center=(float(c[0]), float(c[1]), float(c[2])),
    normal=(float(n[0]), float(n[1]), float(n[2])),
    area=area,
)

Si _robust_face_reference_point() devuelve None para center o normal, se asigna md, pero c y n nunca se inicializan.

Luego se utilizan igualmente.

Resultado potencial:

center/normal inválidos
        ↓
md = ...
        ↓
c y n NO existen
        ↓
FaceSignature(...)
        ↓
UnboundLocalError

Esto es un bug concreto del código nuevo, no una hipótesis arquitectónica.

Severidad: 🔴 Alta, aunque probablemente sólo aparezca con geometrías problemáticas.


---

🟠 3. La firma geométrica puede producir falsos emparejamientos

La implementación calcula la firma Gmsh mediante muestreo 20×20 del dominio UV:

us = np.linspace(umin, umax, samples)
vs = np.linspace(vmin, vmax, samples)

y posteriormente estima el área triangulando esos puntos.

Esto puede funcionar para superficies simples, pero es una aproximación.

El problema es que la firma utilizada es solamente:

centro + normal + área

Dos superficies geométricamente diferentes pueden compartir esos valores suficientemente cerca.

Esto es particularmente relevante para modelos con:

caras simétricas;

caras repetidas;

superficies cilíndricas;

geometrías curvas;

caras pequeñas próximas entre sí.


El código intenta detectar ambigüedad comparando el primer y segundo score, pero no resuelve el problema global de matching.

Severidad: 🟠 Media/Alta.


---

🟠 4. La comparación de normales elimina deliberadamente el sentido

La distancia usa:

d_n = 1.0 - abs(
    np.dot(
        np.array(a.normal),
        np.array(b.normal)
    )
)

El abs() hace que:

normal = (0,0,1)

y

normal = (0,0,-1)

se consideren idénticas respecto a orientación.

Eso puede ser correcto si solamente queremos identificar la superficie geométrica independientemente de orientación, pero es peligroso para condiciones mecánicas, porque la orientación de una cara también puede ser relevante para determinar la dirección de una carga.

No afirmaría todavía que esto sea un bug: hay que decidir si el signo de la normal se determina posteriormente desde el CAD. Pero sí es algo que debe verificarse.


---

🟠 5. El fallback de _emit_physical_groups() sigue permitiendo el comportamiento antiguo

El nuevo código hace:

if face_index_to_tag is not None:
    index_to_tag = dict(face_index_to_tag)
else:
    index_to_tag = {
        i: tag for i, tag in enumerate(surface_tags)
    }

Es decir:

con cq_shape
    ↓
matching geométrico

sin cq_shape
    ↓
matching por orden

Esto no necesariamente está mal porque existen caminos donde no se dispone de cq_shape, pero hay una cuestión importante:

el sistema puede seguir produciendo un mapeo aparentemente válido pero físicamente inseguro en esos caminos.

La investigación anterior recomendaba precisamente evitar asociaciones falsas.

Severidad: 🟠 Media, dependiendo de qué caminos reales utilice el producto.


---

🟢 Lo que sí quedó corregido

El problema original que detectamos era real y el último commit lo atacó correctamente en concepto:

ANTES

CAD face index
      ↓
enumeración Gmsh
      ↓
face_<fi>

❌ dependencia del orden

Ahora existe:

CAD face
   ↓
firma geométrica
   ↓
Gmsh surface tag
   ↓
face_<fi>

Eso es una mejora arquitectónica importante. El commit 3db3791 explícitamente elimina la dependencia del orden de enumeración.

Pero la implementación concreta del matching necesita una segunda revisión.


---

Mi diagnóstico actual

Problema	Estado

Dependencia directa del orden CAD/Gmsh	🟢 Corregido conceptualmente
Matching realmente 1:1	🔴 No garantizado
Manejo de None en firma CAD	🔴 Bug
Firma geométrica suficientemente robusta	🟠 Requiere validación
Normal con signo	🟠 Revisar semántica
Fallback sin cq_shape	🟠 Potencialmente inseguro
ProvisionalTet4Mesher	🟠 Sigue siendo una limitación conocida
volfrac	🟠 Sigue pendiente de implementación/decisión
Halo	🟢 La implementación base existe; requiere verificar interacción


Lo más importante

Yo no mandaría todavía este estado a la IA programadora como "problema resuelto".

El nuevo face_correspondence.py solucionó la primera capa del problema, pero introdujo al menos dos bugs concretos y todavía no demuestra una correspondencia biyectiva robusta.

La prioridad ahora sería:

1. corregir/verificar el matching 1:1 → 2. corregir c/n no inicializados → 3. tests con geometrías simétricas/duplicadas → 4. recién después volver a ProvisionalTet4Mesher, volfrac y halo.