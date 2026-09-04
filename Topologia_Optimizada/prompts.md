\# IMPLEMENTAR P0 — DISTRIBUCIÓN FÍSICA DE CARGAS Y HALO DE PROTECCIÓN



Trabaja sobre el estado REAL actual de `master`.



Usa como referencia técnica:

`recomendaciones\_topologia\_optimizada.md`



El documento identifica dos brechas P0. Implementa únicamente esas dos mejoras.



NO hagas refactorizaciones generales, NO cambies la arquitectura y NO implementes los puntos P1/P2 del documento.



\## 1. Distribución de cargas por área tributaria



Actualmente las cargas distribuidas se reparten uniformemente entre nodos.



Implementa una distribución ponderada por área tributaria para las cargas cuya magnitud total ya está definida.



Requisitos:



\- reutilizar la triangulación real de la cara/malla cuando esté disponible;

\- asignar a cada nodo un peso proporcional al área tributaria que representa;

\- conservar exactamente la magnitud total de la carga;

\- mantener fallback uniforme cuando no exista información geométrica suficiente;

\- aplicar la misma semántica al motor local y a Kratos;

\- evitar duplicar la lógica entre motores;

\- no modificar el tratamiento de `PRESSURE`: debe continuar rechazándose explícitamente porque todavía no existe integración de presión × área.



Primero identifica dónde se encuentra actualmente la información de triangulación y dónde se centraliza la conversión de condiciones a cargas. Integra la solución en esos puntos existentes en lugar de crear una capa paralela innecesaria.



\## 2. Halo automático alrededor de cargas y apoyos



Implementa en `SIMPsolver` un mecanismo para preservar automáticamente los elementos cercanos a:



\- nodos de aplicación de cargas;

\- nodos de restricciones/apoyos.



El halo debe:



\- marcar esos elementos como preservados/no optimizables;

\- unirse con cualquier región preservada existente;

\- no eliminar ni reemplazar `set\_preserved\_elements()` / `set\_void\_elements()`;

\- tener un radio configurable;

\- disponer de un valor por defecto razonable basado en el tamaño/filtro de la malla;

\- permitir desactivarlo cuando sea necesario para compatibilidad o comparación;

\- ejecutarse antes de comenzar las iteraciones SIMP.



Integra el mecanismo en `GenerativeDesignEngine` usando los nodos que ya obtiene al resolver las condiciones.



NO protejas arbitrariamente todo el borde del modelo. El halo debe derivarse de los nodos reales asociados a cargas y restricciones.



\## 3. Compatibilidad



Preservar:



\- arquitectura actual;

\- `ConditionManager`;

\- `LoadCondition`;

\- `ElasticityCondition`;

\- `ProtectedRegion`;

\- `ObstructionCondition`;

\- motor SIMP existente;

\- motor FEA local;

\- adaptador Kratos;

\- reconstrucción B-Rep;

\- pipeline desktop.



No sustituir el solver SIMP por Kratos.

No implementar MMA/GCMMA.

No implementar proyección Heaviside.

No implementar nuevas condiciones.

No modificar la UI salvo que sea estrictamente necesario para exponer una configuración ya prevista.



\## 4. Validación obligatoria



Crear o ampliar tests para demostrar:



1\. una carga distribuida conserva exactamente la fuerza total;

2\. una distribución ponderada produce pesos distintos cuando las áreas tributarias son distintas;

3\. el fallback uniforme funciona cuando no existe triangulación;

4\. local y Kratos reciben la misma distribución física;

5\. `PRESSURE` continúa produciendo un error explícito;

6\. el halo preserva elementos alrededor de cargas;

7\. el halo preserva elementos alrededor de apoyos;

8\. el halo se combina correctamente con regiones preservadas existentes;

9\. el radio configurable funciona;

10\. el halo puede desactivarse;

11\. los tests existentes de FEA/SIMP/Kratos continúan pasando.



No modificar tests para ocultar fallos.



\## 5. Documentación



Actualizar `PROJECT\_STATUS.md` únicamente si la implementación cambia realmente el estado documentado.



No modificar la investigación ni `recomendaciones\_topologia\_optimizada.md`.



\## 6. Resultado



Al finalizar informa:



\- archivos modificados;

\- arquitectura reutilizada;

\- implementación de distribución por área;

\- implementación del halo;

\- tests nuevos/modificados;

\- resultado completo de tests;

\- compatibilidad local/Kratos;

\- cualquier limitación que permanezca.



Criterio de éxito:



\*\*las dos brechas P0 quedan implementadas y verificadas sin introducir una nueva arquitectura ni alterar funcionalidades ya cerradas.\*\*

