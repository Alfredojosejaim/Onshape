# PRUEBA DECISIVA DE KRATOS MULTIPHYSICS
## Validación FEA 3D + preparación real para SIMP

### OBJETIVO

Determinar experimentalmente si Kratos Multiphysics puede ser utilizado como núcleo FEA de nuestra aplicación standalone de optimización topológica.

Esta es una prueba de DECISIÓN ARQUITECTÓNICA.

El resultado debe permitir decidir:

    ¿ADOPTAMOS KRATOS COMO SOLVER FEA?
    
o:

    ¿DESCARTAMOS KRATOS Y DESARROLLAMOS NUESTRO PROPIO SOLVER?

NO modificar la arquitectura principal todavía.

NO desarrollar funcionalidades de la aplicación.

NO implementar la interfaz gráfica.

NO integrar Onshape ni ningún otro CAD.

Trabajar exclusivamente dentro de:

    experimentos/kratos_topopt_poc/

---

# 1. REGLA FUNDAMENTAL

No declarar que Kratos es viable simplemente porque:

- importa correctamente;
- ejecuta un ejemplo;
- genera una malla;
- resuelve un problema FEA.

La decisión debe basarse en si Kratos permite construir nuestro flujo:

    CAD/STEP
       ↓
    Gmsh
       ↓
    Tet4
       ↓
    Kratos FEA
       ↓
    desplazamientos
       ↓
    tensiones
       ↓
    compliance
       ↓
    sensibilidades
       ↓
    actualización de densidades
       ↓
    SIMP

y si podemos acceder a los datos necesarios sin introducir una arquitectura excesivamente compleja o incompatible con nuestra aplicación standalone.

---

# 2. PRIMERA PRUEBA — GMSH → KRATOS

Utilizar Gmsh para generar una malla volumétrica Tet4.

La geometría debe ser independiente de Onshape.

Utilizar una geometría sencilla y reproducible.

Por ejemplo:

    viga en voladizo rectangular.

Verificar:

- nodos;
- conectividad;
- elementos tetraédricos;
- condiciones de frontera;
- carga.

El flujo debe ser:

    Gmsh
      ↓
    malla Tet4
      ↓
    Kratos

No utilizar formatos intermedios innecesarios si pueden evitarse.

Documentar exactamente cómo se realiza la conversión.

---

# 3. SEGUNDA PRUEBA — FEA 3D REAL

Resolver en Kratos una viga en voladizo 3D.

Geometría:

    L = 100 mm
    sección = 10 mm × 10 mm

Material:

    Aluminio
    E = 68.9 GPa
    ν = 0.33

Carga:

    Fz = -100 N

Condición de frontera:

    una cara completamente restringida.

Resolver mediante elementos Tet4.

Obtener:

- desplazamientos nodales;
- desplazamiento máximo;
- tensiones;
- energía de deformación;
- compliance.

---

# 4. VALIDACIÓN ANALÍTICA

Comparar el desplazamiento máximo obtenido por Kratos contra la solución analítica correspondiente.

Calcular:

    error_relativo =
    |δ_FEA - δ_analítica| / |δ_analítica|

No modificar parámetros para forzar coincidencia.

Documentar:

- valor analítico;
- valor FEA;
- error;
- tamaño de malla;
- número de nodos;
- número de elementos.

---

# 5. PRUEBA DE CONVERGENCIA

Ejecutar al menos tres niveles de refinamiento:

    malla gruesa
    malla media
    malla fina

Para cada una registrar:

- número de nodos;
- número de Tet4;
- desplazamiento máximo;
- error relativo.

Determinar si el resultado converge hacia la solución analítica.

No declarar éxito únicamente porque una malla produce <5% de error.

Debe observarse una tendencia razonable de convergencia.

---

# 6. ACCESO A LOS DATOS INTERNOS

Esta es una de las pruebas MÁS IMPORTANTES.

Determinar si desde Python podemos obtener directamente:

    K
    u
    F

o, como mínimo, todos los datos necesarios para reconstruir las cantidades necesarias para SIMP.

Investigar experimentalmente el acceso a:

- grados de libertad;
- desplazamientos;
- fuerzas;
- matriz de rigidez;
- contribuciones elementales;
- energía de deformación;
- tensiones;
- variables de elemento.

NO asumir que una API existe simplemente porque aparece en documentación.

Demostrarlo mediante código ejecutado.

---

# 7. PRUEBA CRÍTICA — ENERGÍA POR ELEMENTO

Para SIMP necesitamos evaluar:

    ce = ueᵀ Ke ue

para cada elemento.

Determinar si Kratos permite obtener:

- ue;
- Ke;
- energía elemental;
- o una cantidad equivalente suficiente para calcular la sensibilidad.

La prueba debe realizarse sobre una malla real.

Documentar exactamente:

    ¿qué objeto de Kratos proporciona el dato?

y:

    ¿cómo se obtiene desde Python?

---

# 8. PRUEBA DE SENSIBILIDAD

Determinar si podemos calcular la sensibilidad de compliance necesaria para SIMP:

    dc/dρe

Utilizar la formulación correspondiente al método SIMP.

No es suficiente con mencionar una función de Kratos.

Debe existir una demostración ejecutable.

Comparar, cuando sea posible, la sensibilidad analítica con una aproximación por diferencias finitas:

    dc/dρ ≈ [c(ρ+Δρ)-c(ρ-Δρ)]/(2Δρ)

para uno o varios elementos.

Documentar el error.

---

# 9. PRUEBA DE ACTUALIZACIÓN DE DENSIDADES

Implementar dentro del PoC un experimento mínimo donde:

    ρe

pueda modificarse entre iteraciones.

No es necesario realizar todavía una optimización topológica completa.

El objetivo es demostrar que podemos:

1. definir densidades;
2. modificar la rigidez efectiva;
3. resolver nuevamente;
4. obtener compliance;
5. obtener sensibilidad.

Por ejemplo:

    ρ = 1.0

después:

    ρ = 0.8

y posteriormente:

    ρ = 0.5

Comprobar que el comportamiento estructural cambia coherentemente.

---

# 10. PRUEBA DE BUCLE SIMP MÍNIMO

Si las pruebas anteriores funcionan, implementar un pequeño bucle:

    inicializar ρ
          ↓
    aplicar penalización
          ↓
    resolver FEA
          ↓
    calcular compliance
          ↓
    calcular sensibilidad
          ↓
    actualizar ρ
          ↓
    repetir

No buscar todavía un resultado industrial.

El objetivo es demostrar que Kratos puede participar REALMENTE en el ciclo SIMP.

---

# 11. RESTRICCIÓN DE VOLUMEN

Demostrar que el vector:

    ρ

puede actualizarse respetando aproximadamente una fracción de volumen objetivo.

Ejemplo:

    volumen_objetivo = 40%

No es necesario implementar el algoritmo de optimización definitivo.

Solo demostrar que el flujo de densidades es técnicamente compatible con una restricción de volumen.

---

# 12. EVALUAR PERFORMANCE

Registrar:

- número de elementos;
- tiempo de mallado;
- tiempo FEA;
- tiempo de extracción de resultados;
- tiempo de actualización de densidades;
- tiempo total por iteración.

No optimizar prematuramente.

El objetivo es detectar si la arquitectura es razonablemente viable.

---

# 13. EVALUAR COMPLEJIDAD DE INTEGRACIÓN

Documentar honestamente:

### Ventajas

Qué nos aporta Kratos.

### Desventajas

Qué debemos adaptar.

### Dependencias

Qué necesita la aplicación.

### Acceso Python

Qué podemos controlar directamente.

### SIMP

Qué partes podemos implementar nosotros y cuáles puede proporcionar Kratos.

### Escalabilidad

Qué ocurre al aumentar la cantidad de elementos.

### Distribución

Qué implicaría distribuir Kratos junto con nuestra aplicación standalone.

---

# 14. CRITERIOS DE DECISIÓN

Evaluar los siguientes puntos:

| Criterio | Resultado requerido |
|---|---|
| FEA 3D Tet4 | Debe funcionar |
| Condiciones de frontera | Debe funcionar |
| Cargas | Debe funcionar |
| Desplazamientos | Accesibles |
| Tensiones | Accesibles |
| Compliance | Calculable |
| Datos elementales | Accesibles |
| Sensibilidades SIMP | Calculables |
| Actualización de densidades | Posible |
| Bucle iterativo | Posible |
| Restricción de volumen | Posible |
| Gmsh → Kratos | Reproducible |
| Python | Control suficiente |
| Rendimiento | Aceptable |
| Integración standalone | Razonable |

---

# 15. CLASIFICACIÓN FINAL

El resultado debe clasificarse exclusivamente como:

## A — ADOPTAR KRATOS

Si cumple las necesidades FEA + SIMP y su integración es razonable.

## B — ADOPTAR KRATOS CON LIMITACIONES

Si cumple las necesidades principales pero requiere una adaptación importante y conocida.

## C — DESCARTAR KRATOS

Solo si existe una limitación técnica concreta que impida utilizarlo como núcleo FEA/SIMP de nuestra aplicación.

NO clasificarlo como C por:

- dificultad de aprendizaje;
- documentación imperfecta;
- necesidad de escribir código adicional;
- preferencias personales;
- que un ejemplo sea complejo.

Debe existir una incompatibilidad técnica real.

---

# 16. REGLA CONTRA FALSOS POSITIVOS

Un ejemplo estándar de Kratos NO cuenta como demostración de compatibilidad SIMP.

Cada capacidad crítica debe probarse mediante código ejecutado.

Distinguir claramente:

    DOCUMENTADO

    INFERIDO

    PROBADO

    NO PROBADO

---

# 17. DOCUMENTACIÓN

Crear o actualizar dentro del PoC:

    RESUMEN_DECISION_KRATOS.md

Debe contener:

1. objetivo;
2. entorno;
3. metodología;
4. pruebas realizadas;
5. resultados;
6. errores;
7. tiempos;
8. limitaciones;
9. acceso a datos;
10. compatibilidad con SIMP;
11. problemas encontrados;
12. decisión final.

Incluir referencias a los scripts y resultados utilizados como evidencia.

---

# 18. AISLAMIENTO ABSOLUTO

NO modificar:

- README.md
- metodología.md
- prompt.md
- código productivo
- arquitectura principal.

NO crear todavía:

- integración con Onshape;
- plugin CAD;
- interfaz gráfica;
- backend definitivo;
- API definitiva;
- sistema de importación definitivo.

Todo debe permanecer dentro del PoC.

---

# 19. VEREDICTO FINAL

Al terminar, escribir claramente:

# VEREDICTO

    A — ADOPTAR KRATOS

o

    B — ADOPTAR KRATOS CON LIMITACIONES

o

    C — DESCARTAR KRATOS

Después explicar en términos técnicos EXACTAMENTE por qué.

El objetivo de esta prueba no es demostrar que Kratos es bueno.

El objetivo