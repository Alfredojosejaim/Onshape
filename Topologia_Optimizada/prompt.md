EJECUTA AHORA UNA VERIFICACIÓN FINAL Y EXCLUSIVA DEL CARGADO DE KRATOS.

1. Cierra cualquier terminal/proceso Python actualmente abierto.

2. Abre una TERMINAL NUEVA e independiente.

3. Activa exactamente el entorno Python que utiliza el proyecto.

4. Ejecuta DOS VECES, desde esa terminal nueva, una prueba mínima que verifique exclusivamente:

   - versión de Python;
   - versión de Kratos;
   - `import KratosMultiphysics`;
   - `StructuralMechanicsApplication`;
   - `OptimizationApplication`.

5. Cada ejecución debe comenzar desde un proceso Python completamente nuevo. No reutilices módulos previamente cargados.

6. La salida debe indicar explícitamente:

   [PASS] KratosMultiphysics
   [PASS] StructuralMechanicsApplication
   [PASS] OptimizationApplication

   o `[FAIL]` indicando el error exacto correspondiente.

7. Guarda la salida REAL y completa de ambas ejecuciones como evidencia dentro de:

   `experimentos/kratos_topopt_poc/`

   Por ejemplo:

   `kratos_import_test_run1.txt`
   `kratos_import_test_run2.txt`

8. NO uses resultados anteriores como evidencia y NO generes manualmente los resultados.

9. NO ejecutes todavía:
   - FEA;
   - SIMP;
   - Topological Optimization;
   - Gmsh;
   - ningún experimento científico adicional.

10. NO modifiques:
   - `README.md`;
   - `metodología.md`;
   - `prompt.md`;
   - código productivo;
   - arquitectura principal.

11. Actualiza únicamente la documentación del PoC si es necesario para indicar que las dos pruebas fueron ejecutadas y sus resultados.

12. Al terminar, responde únicamente con:
   - resultado de la primera ejecución;
   - resultado de la segunda ejecución;
   - versión de Python;
   - versión de Kratos;
   - confirmación de si las tres importaciones funcionaron en AMBAS ejecuciones.

OBJETIVO:

Demostrar de forma reproducible que:

`import KratosMultiphysics`

y sus aplicaciones necesarias funcionan correctamente desde procesos Python independientes.

Si ambas ejecuciones pasan, considera RESUELTO el problema de carga de DLL y DETENTE.

No continúes con FEA/SIMP hasta recibir nuevas instrucciones.