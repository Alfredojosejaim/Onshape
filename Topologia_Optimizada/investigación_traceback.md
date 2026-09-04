--- /tmp/original_face_correspondence.py	2026-09-04 17:41:22.870640127 +0000
+++ Topologia_Optimizada/core/face_correspondence.py	2026-09-04 17:41:22.800090820 +0000
@@ -20,6 +20,7 @@
 
 import cadquery as cq
 import numpy as np
+from scipy.optimize import linear_sum_assignment
 
 from core.geometry import _robust_face_reference_point
 
@@ -46,10 +47,17 @@
     """Build the geometric signature of every ``shape.Faces()[fi]``."""
     signatures: List[FaceSignature] = []
     faces = shape.Faces()
-    for face in faces:
+    for fi, face in enumerate(faces):
         center, normal = _robust_face_reference_point(face)
         if center is None or normal is None:
-            md = np.array([0.0, 0.0, 0.0])
+            logger.warning(
+                "CAD face %d: _robust_face_reference_point returned None; "
+                "falling back to a degraded (0,0,0)/(0,0,1) signature. This "
+                "face is at high risk of an ambiguous or wrong match.",
+                fi,
+            )
+            c = np.array([0.0, 0.0, 0.0])
+            n = np.array([0.0, 0.0, 1.0])
         else:
             c = np.array([float(center.x), float(center.y), float(center.z)])
             n = np.array([float(normal.x), float(normal.y), float(normal.z)])
@@ -177,32 +185,67 @@
     cad_sigs = _shape_face_signatures(shape)
     gmsh_sigs = _gmsh_surface_signatures(gmsh)
 
-    if len(cad_sigs) != len(gmsh_sigs):
+    n = len(cad_sigs)
+    if n != len(gmsh_sigs):
         raise FaceCorrespondenceError(
-            f"Count mismatch between CAD faces ({len(cad_sigs)}) and "
+            f"Count mismatch between CAD faces ({n}) and "
             f"Gmsh surfaces ({len(gmsh_sigs)}); cannot build a 1:1 mapping."
         )
 
-    mapping: Dict[int, int] = {}
+    gmsh_tags = [tag for tag, _ in gmsh_sigs]
+
+    # Full pairwise distance matrix: cost[fi, gj] = distance(cad face fi,
+    # gmsh surface gmsh_tags[gj]).
+    cost = np.empty((n, n), dtype=float)
     for fi, csig in enumerate(cad_sigs):
-        best_tag = None
-        best_score = float("inf")
-        second_score = float("inf")
-        for tag, gsig in gmsh_sigs:
-            score = _signature_distance(csig, gsig)
-            if score < best_score:
-                second_score = best_score
-                best_score = score
-                best_tag = tag
-            elif score < second_score:
-                second_score = score
-        if second_score <= best_score * (1.0 + tol):
+        for gj, (_, gsig) in enumerate(gmsh_sigs):
+            cost[fi, gj] = _signature_distance(csig, gsig)
+
+    # Global optimal 1:1 assignment (Hungarian algorithm). Unlike a per-face
+    # argmin, this guarantees a true bijection: no two CAD faces can end up
+    # pointing at the same Gmsh surface, because linear_sum_assignment solves
+    # for the assignment that minimizes total cost across ALL faces at once,
+    # with each column (Gmsh surface) used at most once.
+    row_ind, col_ind = linear_sum_assignment(cost)
+    assigned_gj = {fi: gj for fi, gj in zip(row_ind, col_ind)}
+
+    mapping: Dict[int, int] = {}
+    for fi in range(n):
+        gj = assigned_gj[fi]
+        assigned_score = cost[fi, gj]
+
+        # Sort this face's distances to every Gmsh surface to find its own
+        # best/second-best candidate, independent of what the global
+        # assignment above picked for other faces.
+        row_sorted = np.sort(cost[fi, :])
+        local_best, local_second = row_sorted[0], row_sorted[1] if n > 1 else float("inf")
+
+        if local_second <= local_best * (1.0 + tol):
+            raise AmbiguousFaceCorrespondenceError(
+                f"CAD face {fi} ({cad_sigs[fi]}) is ambiguous: two Gmsh "
+                f"surfaces match within tolerance (best={local_best:.3g}, "
+                f"second={local_second:.3g}). Refusing to guess the "
+                "correspondence."
+            )
+
+        if assigned_score > local_best * (1.0 + tol):
+            # This face was NOT given its own nearest match: some other face
+            # had an even stronger claim on that surface and won it in the
+            # global optimum. That is a symptom of duplicate/symmetric
+            # geometry (e.g. two congruent faces) rather than a safe
+            # coincidence, so we refuse to guess rather than silently
+            # assigning a worse match.
             raise AmbiguousFaceCorrespondenceError(
-                f"CAD face {fi} ({csig}) is ambiguous: two Gmsh surfaces match "
-                f"within tolerance (best={best_score:.3g}, second={second_score:.3g}). "
-                "Refusing to guess the correspondence."
+                f"CAD face {fi} ({cad_sigs[fi]}) could not be matched to its "
+                f"own nearest Gmsh surface (best={local_best:.3g}) because "
+                f"another CAD face has an equal or stronger claim on it "
+                f"(assigned={assigned_score:.3g}). This indicates duplicate "
+                "or symmetric geometry that the signature cannot "
+                "disambiguate. Refusing to guess the correspondence."
             )
-        mapping[fi] = best_tag
+
+        mapping[fi] = gmsh_tags[gj]
+
     return mapping