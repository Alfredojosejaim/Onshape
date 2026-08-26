# POC TÉCNICO AISLADO — KRATOS + TOPOLOGICAL OPTIMIZATION 3D

## OBJETIVO

Realizar una prueba de concepto técnica, completamente aislada del desarrollo principal del proyecto, para determinar si Kratos Multiphysics puede utilizarse como motor FEA + optimización topológica SIMP para nuestra futura aplicación standalone.

Esta tarea NO consiste en integrar Kratos al proyecto principal.

El único objetivo es demostrar mediante código ejecutable y resultados verificables si el siguiente flujo funciona:

Gmsh
→ malla volumétrica Tet4
→ Kratos Structural Mechanics
→ OptimizationApplication
→ SIMP
→ análisis estructural
→ compliance / strain energy
→ sensibilidades
→ actualización de densidades
→ iteraciones de optimización
→ resultado optimizado

---

# 1. REGLAS ABSOLUTAS

1. Trabaja exclusivamente dentro de una carpeta experimental aislada:

   `experimentos/kratos_topopt_poc/`

2. Si la carpeta no existe, créala.

3. NO modificar:
   - código productivo existente;
   - arquitectura principal;
   - README;
   - metodología.md;
   - prompt.md;
   - informes de investigación;
   - documentación histórica;
   - archivos de configuración del proyecto principal.

4. NO eliminar archivos existentes.

5. NO mover archivos existentes.

6. NO integrar Kratos todavía al pipeline principal.

7. NO crear funcionalidades de la aplicación gráfica.

8. NO desarrollar todavía el importador STEP definitivo.

9. NO implementar conexión con ningún CAD.

10. NO implementar Onshape, FeatureScript, API de Onshape ni plugins.

11. NO asumir que una capacidad funciona simplemente porque existe en la documentación.

Toda capacidad relevante debe probarse mediante código ejecutable o demostrarse directamente mediante código oficial de Kratos.

---

# 2. PRIMERA TAREA — AUDITAR EL ENTORNO

Antes de escribir código:

1. Revisar el sistema operativo.
2. Revisar versión de Python disponible.
3. Verificar si Kratos Multiphysics está instalado.
4. Verificar versión exacta.
5. Verificar si `OptimizationApplication` está disponible.
6. Verificar si `StructuralMechanicsApplication` está disponible.
7. Verificar si Gmsh está disponible.
8. Verificar si la API Python de Gmsh está disponible.

Si alguna dependencia no está instalada:

- NO modificar el entorno global innecesariamente.
- Preferir un entorno virtual aislado para el PoC.
- Documentar exactamente qué fue instalado.
- Registrar las versiones utilizadas.

Crear, si es necesario:

`experimentos/kratos_topopt_poc/requirements.txt`

o la configuración equivalente que permita reproducir el entorno.

---

# 3. ESTRUCTURA DEL POC

Crear una estructura clara y mínima similar a:

experimentos/
└── kratos_topopt_poc/
    ├── README.md
    ├── requirements.txt              (si aplica)
    ├── run_poc.py
    ├── generate_mesh.py
    ├── model/
    │   └── ...
    ├── results/
    │   └── ...
    └── logs/
        └── ...

La estructura puede modificarse si existe una alternativa técnicamente mejor, pero debe mantenerse completamente aislada.

---

# 4. MODELO DE PRUEBA

Construir un modelo estructural 3D extremadamente simple y reproducible.

Usar preferentemente una viga en voladizo:

- longitud: 100 mm
- sección: 10 mm × 10 mm
- material: aluminio
- Young: 68.9 GPa
- Poisson: 0.33
- carga vertical en el extremo libre: -100 N

La geometría debe ser suficientemente sencilla para poder comprobar físicamente los resultados.

La prueba debe utilizar elementos tetraédricos lineales de 4 nodos (Tet4), siempre que Kratos permita configurar correctamente el caso.

---

# 5. MALLADO

Utilizar Gmsh para generar una malla volumétrica tetraédrica.

Verificar explícitamente:

- cantidad de nodos;
- cantidad de elementos;
- tipo de elemento;
- conectividad;
- dimensiones;
- grupos físicos necesarios.

El script debe permitir regenerar la malla.

No utilizar una malla preexistente que impida reproducir el experimento.

---

# 6. IMPORTACIÓN A KRATOS

Implementar el flujo:

Gmsh
→ modelo FEM
→ Kratos ModelPart

Verificar explícitamente que Kratos recibe:

- nodos;
- elementos;
- conectividad;
- propiedades;
- material;
- condiciones de contorno;
- carga.

Mostrar en consola un resumen del modelo cargado.

Ejemplo:

Nodes: XXXX
Elements: XXXX
DOFs: XXXX
Material: ...
Element type: ...

---

# 7. PRUEBA FEA SIN OPTIMIZACIÓN

ANTES de probar SIMP, demostrar que Kratos puede resolver correctamente el problema estructural básico.

Resolver:

K u = F

Obtener:

- desplazamientos;
- reacción;
- strain energy / compliance si está disponible.

Registrar:

- desplazamiento máximo;
- ubicación;
- reacción total;
- compliance o strain energy.

Comparar el desplazamiento del extremo libre con la solución analítica de una viga en voladizo.

Calcular:

error_relativo =
abs(FEM - analítica) / abs(analítica)

No declarar éxito únicamente porque Kratos terminó sin errores.

El resultado debe ser numéricamente razonable.

---

# 8. PRUEBA DE OPTIMIZATIONAPPLICATION

Verificar mediante código que la instalación actual de Kratos dispone realmente de:

`OptimizationApplication`

y de los componentes relacionados con SIMP.

Investigar directamente en la instalación/código de Kratos qué clases, controles, responses y algorithms están disponibles.

Prestar especial atención a:

- SimpControl;
- LinearStrainEnergyResponseFunction;
- filtros;
- controles de densidad;
- sensitivities;
- algorithms de optimización.

No asumir nombres de clases basándose exclusivamente en documentación antigua.

---

# 9. PRUEBA SIMP

Construir el caso mínimo posible de optimización topológica.

La variable de diseño debe ser una densidad elemental:

ρ ∈ [ρ_min, 1]

Utilizar una formulación SIMP equivalente a:

E(ρ) = E0 · ρ^p

con:

- p = 3 inicialmente;
- densidad mínima pequeña para evitar singularidad.

Verificar que el Young efectivo realmente depende de la densidad.

IMPORTANTE:

No implementar manualmente un SIMP paralelo si Kratos ya proporciona `SimpControl`.

La finalidad de esta prueba es precisamente verificar cuánto del ciclo puede realizar Kratos de forma nativa.

---

# 10. RESPONSE

Utilizar, si es compatible con el caso:

`LinearStrainEnergyResponseFunction`

o el mecanismo actual equivalente.

Demostrar que se puede obtener una respuesta estructural apropiada para optimización.

Registrar:

- valor inicial;
- valor después de cada iteración;
- valor final.

La respuesta debe mostrar comportamiento físicamente coherente.

---

# 11. SENSIBILIDADES

Verificar que el flujo de optimización puede calcular las sensibilidades necesarias.

Comprobar específicamente:

- sensibilidad respecto de la variable de diseño;
- propagación a través de SIMP;
- compatibilidad con el filtro;
- existencia de valores finitos;
- ausencia de NaN/Inf.

Mostrar estadísticas:

min
max
mean
cantidad de valores no finitos

---

# 12. FILTRO

Si `OptimizationApplication` permite utilizar un filtro compatible con este caso:

implementarlo.

Verificar:

- que se aplica;
- que modifica las sensibilidades o variable de diseño según corresponda;
- que no produce valores inválidos.

Documentar exactamente qué filtro se utilizó y por qué.

---

# 13. ACTUALIZACIÓN DE DENSIDADES

Demostrar que las densidades cambian durante las iteraciones.

Registrar por iteración:

Iteration
Objective
Volume fraction
Min density
Max density
Mean density
Change

Ejemplo:

Iteration 0
Objective: ...
Volume: ...
Mean density: ...

Iteration 1
...

La optimización debe mostrar evolución real.

NO aceptar como prueba una simulación que simplemente ejecute el solver varias veces sin modificar las densidades.

---

# 14. RESTRICCIÓN DE VOLUMEN

Implementar una restricción de volumen si la infraestructura actual de Kratos lo permite.

Objetivo inicial:

volumen final ≈ 30–50 % del volumen inicial.

Verificar cuantitativamente:

V_final / V_inicial

y registrar el resultado.

Si Kratos no dispone exactamente del mecanismo esperado:

- investigar la alternativa oficial actual;
- implementarla solamente si es necesario para completar el PoC;
- documentar claramente qué parte pertenece a Kratos y qué parte fue desarrollada específicamente para la prueba.

---

# 15. ITERACIONES

Ejecutar suficientes iteraciones para comprobar que existe una optimización real.

No es necesario obtener una pieza industrialmente óptima.

El objetivo es demostrar:

ρ inicial
→ FEA
→ response
→ sensitivity
→ filter
→ update
→ ρ nueva
→ FEA
→ ...

y comprobar que el objetivo estructural evoluciona.

---

# 16. RESULTADO VISUAL

Generar algún resultado visual mínimo que permita observar la distribución final de densidades.

Puede utilizarse:

- VTK;
- GiD;
- ParaView;
- archivo compatible con herramientas de visualización.

No desarrollar interfaz gráfica.

El objetivo únicamente es poder comprobar visualmente que existe una distribución de material resultante.

---

# 17. VALIDACIÓN

La prueba debe comprobar como mínimo:

### A. FEA

¿Kratos resuelve correctamente el modelo Tet4?

### B. SIMP

¿La rigidez depende realmente de la densidad?

### C. Sensibilidades

¿Se calculan correctamente?

### D. Optimización

¿Las densidades evolucionan?

### E. Volumen

¿Puede controlarse la fracción de material?

### F. Convergencia

¿La función objetivo evoluciona razonablemente?

### G. Resultado

¿La distribución final tiene sentido físico?

---

# 18. PRUEBA DE REPRODUCIBILIDAD

El PoC debe poder ejecutarse desde cero mediante un comando claramente documentado.

Por ejemplo:

`python run_poc.py`

o el mecanismo apropiado.

Una ejecución limpia debe:

1. generar la malla;
2. cargarla;
3. ejecutar FEA;
4. ejecutar optimización;
5. guardar resultados;
6. producir logs.

No depender de archivos temporales creados manualmente.

---

# 19. DOCUMENTACIÓN DEL POC

Crear exclusivamente dentro de:

`experimentos/kratos_topopt_poc/README.md`

la documentación del experimento.

Debe contener:

## Entorno

- OS
- Python
- Kratos
- Gmsh
- versiones

## Componentes probados

Lista exacta de aplicaciones/clases utilizadas.

## Arquitectura del PoC

Explicar el flujo real.

## Resultados

Tabla con:

| Prueba | Resultado | Evidencia |
|---|---|---|
| Gmsh Tet4 | PASS/FAIL | ... |
| Importación Kratos | PASS/FAIL | ... |
| FEA | PASS/FAIL | ... |
| SIMP | PASS/FAIL | ... |
| Sensibilidad | PASS/FAIL | ... |
| Filtro | PASS/FAIL | ... |
| Restricción volumen | PASS/FAIL | ... |
| Iteraciones | PASS/FAIL | ... |
| Resultado final | PASS/FAIL | ... |

## Limitaciones

Registrar cualquier cosa que no haya podido demostrarse.

## Conclusión

Clasificar el resultado como:

- VIABLE
- VIABLE CON LIMITACIONES
- NO VIABLE

No utilizar lenguaje ambiguo.

---

# 20. REGLA CRÍTICA SOBRE RESULTADOS

NO declarar:

"Kratos sirve para nuestro proyecto"

simplemente porque las APIs existan.

La conclusión debe basarse exclusivamente en lo que haya sido ejecutado y demostrado.

Distinguir claramente:

### VERIFICADO

Funcionó mediante ejecución real.

### CONFIRMADO POR CÓDIGO/DOCUMENTACIÓN OFICIAL

Existe en la versión utilizada, pero no fue necesario utilizarlo en el PoC.

### NO VERIFICADO

No pudo demostrarse.

### NO DISPONIBLE

La capacidad no existe o no pudo utilizarse.

---

# 21. COMPARACIÓN FINAL

Al terminar, responder dentro del README del PoC:

### ¿Kratos puede reemplazar nuestro solver FEA propio?

### ¿Kratos puede ejecutar Tet4 3D?

### ¿Kratos puede ejecutar SIMP?

### ¿Kratos puede calcular compliance/strain energy?

### ¿Kratos puede calcular sensibilidades?

### ¿Kratos puede realizar iteraciones de optimización?

### ¿Kratos puede controlar la fracción de volumen?

### ¿Qué debemos programar nosotros?

### ¿Qué seguiría dependiendo de Gmsh?

### ¿Qué parte debería quedar dentro de nuestra aplicación?

---

# 22. NO TOMAR DECISIONES DE ARQUITECTURA PRINCIPAL

El resultado de este experimento NO debe modificar todavía:

- README principal;
- metodología;
- arquitectura;
- roadmap;
- Hito 2;
- Hito 3;
- dependencias principales;
- código productivo.

El PoC solamente debe proporcionar evidencia para tomar esa decisión posteriormente.

---

# 23. AUDITORÍA FINAL

Antes de terminar:

1. Revisar `git diff`.
2. Confirmar que todos los cambios están exclusivamente dentro de:

   `experimentos/kratos_topopt_poc/`

3. Si se modificó accidentalmente cualquier archivo fuera de esa carpeta:
   - revertir esos cambios;
   - NO borrar trabajo previo.

4. Confirmar que el PoC puede ejecutarse nuevamente.

5. Confirmar que no existen dependencias ocultas.

6. Confirmar que todos los resultados importantes están documentados.

7. Confirmar que no se modificó ninguna documentación principal.

---

# RESULTADO ESPERADO

Al finalizar debes entregar:

1. PoC funcional aislado.
2. Código reproducible.
3. Modelo Tet4 3D.
4. FEA funcionando.
5. SIMP probado.
6. Sensibilidades probadas.
7. Iteraciones de optimización.
8. Restricción de volumen, si es técnicamente posible.
9. Resultados numéricos.
10. Resultado visual.
11. README del PoC con toda la evidencia.
12. Conclusión objetiva sobre la viabilidad de Kratos.

NO integres Kratos al proyecto principal.

NO diseñes la interfaz gráfica.

NO desarrolles plugins.

NO trabajes todavía con Onshape ni con ningún otro CAD.

La única misión es responder con evidencia experimental:

"¿Podemos utilizar Kratos como motor FEA + optimización topológica de nuestra aplicación standalone?"