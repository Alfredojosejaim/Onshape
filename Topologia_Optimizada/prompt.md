# DIAGNÓSTICO DEFINITIVO — KRATOS / WINDOWS / DLL LOADING

## OBJETIVO

El PoC de Kratos Multiphysics quedó bloqueado antes de poder ejecutar FEA porque:

    import KratosMultiphysics

produce un error de Windows relacionado con carga de DLL:

    DLL load failed while importing Kratos
    No se puede encontrar el módulo especificado

Tu tarea ahora NO es investigar TopOpt, SIMP, FEA ni la arquitectura de la aplicación.

Tu única tarea es:

> determinar exactamente por qué KratosMultiphysics no puede cargarse en este entorno Windows y establecer si el problema puede solucionarse mediante una instalación/configuración reproducible.

NO pasar a pruebas FEA/SIMP hasta conseguir que:

    import KratosMultiphysics

funcione correctamente.

---

# 1. REGLA PRINCIPAL

NO declarar:

    "Kratos no es viable"

simplemente porque actualmente no carga.

El resultado puede ser únicamente:

### A — RESUELTO
Kratos carga correctamente.

### B — BLOQUEADO CON CAUSA IDENTIFICADA
Se identificó una dependencia/configuración concreta que impide la carga, pero no pudo resolverse.

### C — NO RESUELTO
Después de agotar sistemáticamente el diagnóstico permitido, no se pudo determinar la causa.

Solo después de este diagnóstico se podrá decidir si continuar con Kratos o descartarlo.

---

# 2. AISLAMIENTO

Trabajar exclusivamente dentro de:

    experimentos/kratos_topopt_poc/

Puedes crear/modificar scripts de diagnóstico dentro de esa carpeta.

NO modificar:

- README.md
- metodología.md
- prompt.md
- código productivo
- arquitectura principal
- otros experimentos

Puedes actualizar:

    RESUMEN_IMPLEMENTACION.md

únicamente para documentar los resultados de este diagnóstico.

---

# 3. PRIMER PASO — AUDITAR EL ENTORNO REAL

Antes de modificar nada, obtener mediante Python y/o comandos de Windows:

- versión exacta de Windows;
- arquitectura del sistema;
- versión de Python;
- arquitectura de Python;
- ubicación real de Python;
- ubicación real de `site-packages`;
- versión instalada de Kratos;
- ubicación real de `KratosMultiphysics`;
- ubicación real de sus DLL;
- PATH actual;
- variables relacionadas con Python;
- Visual C++ Runtime instalado;
- arquitectura de Visual C++ Runtime.

NO utilizar rutas hardcodeadas como:

    C:\Users\XXXX\...

El diagnóstico debe descubrir las rutas reales dinámicamente.

---

# 4. VERIFICAR EL PAQUETE REAL

Desde el mismo Python que ejecutará el proyecto:

1. localizar `KratosMultiphysics`;
2. localizar sus archivos `.pyd`;
3. localizar sus `.dll`;
4. identificar sus versiones;
5. comprobar arquitectura x64/x86;
6. comprobar que Python y Kratos tengan arquitecturas compatibles.

Generar un informe:

    diagnostico_entorno.txt

dentro del PoC.

---

# 5. NO ASUMIR QUE "DLL EXISTE" SIGNIFICA "DLL FUNCIONA"

La existencia física de:

    KratosCore.dll

NO es suficiente.

Determinar qué dependencia concreta está provocando:

    DLL load failed

Utilizar herramientas apropiadas de Windows para analizar dependencias, por ejemplo:

- `dumpbin /DEPENDENTS`, si está disponible;
- herramientas de análisis de dependencias;
- PowerShell;
- Python;
- otras herramientas locales apropiadas.

NO descargar DLL arbitrarias desde Internet.

NO copiar DLL desconocidas desde otras instalaciones.

NO reemplazar archivos del sistema a ciegas.

---

# 6. IDENTIFICAR LA DLL REALMENTE FALTANTE

Determinar, si es posible, la cadena:

    KratosMultiphysics
          ↓
    KratosCore / .pyd
          ↓
    dependencia faltante
          ↓
    dependencia secundaria

Documentar exactamente:

- nombre del archivo;
- ubicación esperada;
- si existe;
- si puede cargarse;
- qué componente depende de ella.

Si el error proviene de una dependencia secundaria, identificarla.

---

# 7. VERIFICAR VISUAL C++ RUNTIME

Comprobar de forma objetiva:

- qué versión de Microsoft Visual C++ Redistributable está instalada;
- arquitectura;
- si corresponde al runtime requerido por la compilación de Kratos;
- si existe algún conflicto.

NO asumir que "Visual C++ Redistributable está instalado" significa que el problema está resuelto.

Documentar evidencia.

---

# 8. VERIFICAR COMPATIBILIDAD PYTHON ↔ KRATOS

Determinar:

- Python utilizado para instalar Kratos;
- Python utilizado para ejecutar el PoC;
- versión;
- arquitectura;
- ABI cuando corresponda.

Confirmar que son exactamente compatibles.

Eliminar cualquier ambigüedad entre:

- Python del sistema;
- Python de VSCode;
- Python del PATH;
- Python utilizado por `pip`.

Ejecutar:

    python -m pip ...

en lugar de asumir que `pip` pertenece al mismo Python.

---

# 9. VERIFICAR INSTALACIÓN

Determinar si la instalación actual de Kratos está corrupta o incompleta.

NO reinstalar inmediatamente.

Primero documentar el estado actual.

Después, si corresponde:

1. desinstalar;
2. limpiar instalación;
3. instalar nuevamente;
4. verificar;
5. probar.

Cada intento debe quedar documentado.

NO realizar una sucesión indiscriminada de instalaciones.

---

# 10. CREAR UN ENTORNO LIMPIO

Si el problema no puede determinarse en el entorno actual:

crear un entorno Python limpio exclusivamente para el PoC.

Por ejemplo:

    .venv_kratos_test/

El entorno debe contener únicamente lo necesario.

Instalar Kratos mediante:

    python -m pip

Registrar exactamente:

- versión de Python;
- versión de pip;
- paquetes instalados;
- versiones.

Después ejecutar:

    import KratosMultiphysics

---

# 11. PRUEBA MÍNIMA OBLIGATORIA

Crear:

    test_kratos_import.py

Debe realizar únicamente:

1. importar `KratosMultiphysics`;
2. imprimir versión;
3. importar `StructuralMechanicsApplication`;
4. importar `OptimizationApplication`.

No ejecutar FEA.

No ejecutar Gmsh.

No ejecutar TopOpt.

El objetivo es exclusivamente verificar la carga de las aplicaciones.

Resultado esperado:

    [PASS] KratosMultiphysics
    [PASS] StructuralMechanicsApplication
    [PASS] OptimizationApplication

---

# 12. PRUEBA DE RUTAS DLL

Si Python no encuentra automáticamente las DLL necesarias:

determinar si es necesario utilizar:

    os.add_dll_directory(...)

o una configuración equivalente.

No aplicar soluciones permanentes al sistema operativo sin necesidad.

Determinar cuál sería la configuración correcta para que la futura aplicación pueda cargar Kratos de forma reproducible.

---

# 13. PROBAR DESDE UN PROCESO LIMPIO

Una vez corregido el entorno:

abrir un proceso Python completamente nuevo.

NO confiar únicamente en un proceso que ya tenía módulos cargados.

Ejecutar:

    python test_kratos_import.py

El resultado debe reproducirse.

---

# 14. PROBAR DESDE EL DIRECTORIO DEL PROYECTO

Después probar:

    python test_kratos_import.py

desde:

    experimentos/kratos_topopt_poc/

y comprobar que funciona sin depender de modificaciones manuales temporales del entorno.

---

# 15. PROBAR REPRODUCIBILIDAD

Cerrar terminal.

Abrir una terminal nueva.

Activar el entorno.

Ejecutar nuevamente.

Después reiniciar VSCode si es necesario.

Volver a ejecutar.

Finalmente ejecutar desde una terminal independiente.

Debe funcionar sin:

- copiar DLL manualmente;
- modificar archivos del sistema;
- abrir una terminal especial;
- ejecutar comandos secretos;
- depender de variables temporales no documentadas.

Si necesita alguna configuración, documentarla explícitamente.

---

# 16. SI SE REQUIERE UNA SOLUCIÓN LOCAL

Si la solución correcta consiste en que nuestra aplicación distribuya o configure las DLL necesarias:

NO implementarlo todavía en la aplicación principal.

Primero demostrar el mecanismo dentro del PoC.

Documentar:

- qué archivos serían necesarios;
- origen legítimo;
- licencia;
- ubicación;
- mecanismo de carga;
- impacto sobre distribución;
- posibles restricciones.

---

# 17. PROHIBICIONES

NO:

- descargar DLL aleatorias;
- copiar DLL desde otra PC;
- copiar DLL de Internet sin verificar procedencia/licencia;
- reemplazar DLL de Windows;
- modificar el registro sin necesidad;
- alterar permanentemente PATH del sistema sin documentarlo;
- ocultar errores;
- utilizar mocks;
- falsificar importaciones;
- editar scripts para simular que Kratos está instalado;
- concluir viabilidad sin conseguir el import real.

---

# 18. CRITERIO DE ÉXITO

El diagnóstico solo se considera RESUELTO si:

    python test_kratos_import.py

produce correctamente:

    KratosMultiphysics → PASS
    StructuralMechanicsApplication → PASS
    OptimizationApplication → PASS

desde un entorno Python reproducible.

---

# 19. SI SE RESUELVE

NO continuar automáticamente con FEA ni TopOpt.

Detenerse después de demostrar:

    import KratosMultiphysics

y documentar:

- causa del problema;
- solución;
- pasos reproducibles;
- versiones;
- dependencias;
- configuración necesaria;
- resultado.

---

# 20. SI NO SE RESUELVE

No declarar automáticamente:

    KRATOS NO VIABLE

En su lugar, determinar cuál de estos casos corresponde:

### CASO 1
Causa identificada y solución conocida.

### CASO 2
Causa identificada pero solución incompatible con nuestra aplicación standalone.

### CASO 3
Dependencia binaria no disponible para nuestro entorno.

### CASO 4
Problema no diagnosticado después de agotar las pruebas razonables.

Explicar exactamente cuál corresponde.

---

# 21. RESUMEN_IMPLEMENTACION.md

Actualizar exclusivamente:

    RESUMEN_IMPLEMENTACION.md

Crear una sección:

# DIAGNÓSTICO DEFINITIVO DE ENTORNO WINDOWS

Debe contener:

## Entorno

Versiones exactas.

## Error original

Mensaje completo.

## Investigación

Pruebas realizadas.

## Dependencia problemática

Si fue identificada.

## Solución

Pasos exactos.

## Reproducibilidad

Indicar si funcionó desde un entorno limpio y una terminal nueva.

## Resultado

Uno de:

    RESUELTO
    BLOQUEADO CON CAUSA IDENTIFICADA
    NO RESUELTO

---

# 22. VEREDICTO

El documento debe terminar con:

## VEREDICTO DEL DIAGNÓSTICO

Y explicar:

### Si funciona:

> Kratos puede cargarse correctamente en el entorno Windows utilizado. El bloqueo de DLL queda resuelto y el PoC puede continuar hacia la validación FEA + SIMP.

### Si no funciona pero existe una incompatibilidad concreta:

> Kratos no puede utilizarse actualmente bajo las condiciones de distribución/configuración requeridas por la aplicación standalone debido a [causa].

### Si no se identifica la causa:

> El diagnóstico no logró determinar la dependencia responsable. Kratos queda bloqueado experimentalmente, pero no se considera demostrado que sea técnicamente inviable.

---

# 23. REGLA FINAL

NO ejecutar nuevamente la validación FEA/SIMP.

NO modificar el README.

NO cambiar la arquitectura.

NO implementar el solver propio todavía.

Este trabajo termina cuando sepamos con evidencia:

    ¿POR QUÉ KRATOS NO CARGA?

y:

    ¿PODEMOS HACER QUE CARGUE DE FORMA REPRODUCIBLE EN WINDOWS?

Ese es el único objetivo de esta ejecución.