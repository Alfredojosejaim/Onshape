CORRECCIÓN P0.1 — INTEGRACIÓN DE CARGAS, MALLA Y HALO

Audita primero el estado actual del repositorio y lee completamente:

"investigación_traceback.md"

Ese archivo contiene la investigación técnica realizada sobre los problemas detectados en la integración de cargas superficiales, correspondencia CAD/Gmsh, mesher provisional, halo y semántica de "volfrac".

OBJETIVO

Implementar las correcciones necesarias según las conclusiones de "investigación_traceback.md", integrándolas con la arquitectura existente.

No vuelvas a investigar desde cero ni cambies la arquitectura salvo que la investigación demuestre que es estrictamente necesario.

Debes corregir y verificar:

1. Correspondencia CAD Face ↔ Gmsh Surface
   
   - Garantizar que una cara CAD seleccionada utilice exclusivamente los elementos superficiales correspondientes a esa misma cara.
   - No depender de un orden de enumeración que no esté garantizado.
   - Mantener correctamente el flujo:
     "CAD Face → Gmsh Surface → Triángulos → Pesos tributarios → Fuerza nodal".

2. ProvisionalTet4Mesher
   
   - Corregir la integración de los triángulos de frontera si la investigación confirma que actualmente no llegan correctamente al cálculo de cargas superficiales.
   - Mantener fallback uniforme únicamente cuando realmente no exista información geométrica suficiente.
   - No ocultar errores de correspondencia mediante fallbacks silenciosos.

3. Distribución de cargas
   
   - Mantener distribución mediante área tributaria cuando existan triángulos superficiales válidos.
   - Garantizar conservación exacta de la fuerza total.
   - Mantener comportamiento físicamente equivalente entre FEA local y Kratos.

4. Halo automático
   
   - Corregir cualquier problema demostrado en la investigación.
   - El halo debe poder aplicarse alrededor de nodos asociados a cargas y apoyos.
   - Debe combinarse correctamente con "ProtectedRegion".
   - Debe seguir siendo configurable y desactivable.
   - El radio automático debe basarse en el tamaño real de los elementos, no en "filter_radius".
   - No proteger regiones arbitrariamente grandes.

5. Semántica de "volfrac"
   
   - Aplicar la decisión técnica establecida en "investigación_traceback.md".
   - Mantener una semántica coherente cuando existen regiones protegidas, halo y regiones void.
   - Agregar o actualizar tests para que esta semántica quede explícitamente garantizada.

RESTRICCIONES

No:

- reconstruir la arquitectura;
- reemplazar SIMP;
- reemplazar el FEA local;
- reemplazar Kratos;
- incorporar OptimizationApplication;
- incorporar MMA/GCMMA;
- incorporar Heaviside;
- crear nuevas condiciones innecesarias;
- rediseñar la UI;
- eliminar funcionalidades existentes;
- modificar código no relacionado con estos problemas.

Reutiliza las abstracciones existentes.

TESTS OBLIGATORIOS

Después de implementar:

- tests específicos de correspondencia CAD/Gmsh;
- tests de cargas superficiales mediante área tributaria;
- conservación de fuerza total;
- fallback cuando corresponda;
- paridad FEA local/Kratos;
- halo de cargas;
- halo de apoyos;
- combinación halo + regiones protegidas;
- configuración/desactivación del halo;
- semántica de "volfrac";
- regresión de toda la funcionalidad existente.

Ejecuta primero los tests afectados y después la suite completa.

Si un test existente contradice la semántica técnicamente correcta determinada por la investigación, corrígelo justificadamente; no modifiques la implementación simplemente para hacer pasar el test.

CRITERIO DE FINALIZACIÓN

No consideres terminada la tarea porque los tests pasen.

La tarea queda cerrada solamente cuando:

- la investigación de "investigación_traceback.md" fue aplicada;
- la correspondencia CAD/Gmsh es físicamente segura;
- las cargas superficiales utilizan correctamente áreas tributarias cuando corresponde;
- la fuerza total se conserva;
- FEA local y Kratos mantienen la misma semántica;
- el halo funciona según lo especificado;
- "volfrac" tiene una semántica explícita y testeada;
- la suite completa continúa pasando.

Al finalizar, informa:

1. Problemas encontrados.
2. Causa raíz de cada uno.
3. Correcciones realizadas.
4. Archivos modificados.
5. Tests agregados/modificados.
6. Resultado de tests dirigidos.
7. Resultado de la suite completa.
8. Limitaciones que permanezcan.