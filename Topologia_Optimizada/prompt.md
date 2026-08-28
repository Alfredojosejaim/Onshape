Repite la prueba E2E del motor FEA utilizando exclusivamente el archivo STEP real `cono.step` como entrada de geometría.

No generes ninguna geometría sintética o alternativa (caja, cilindro, cubo, etc.) para reemplazar la geometría del STEP.

El flujo que debes comprobar es:

cono.step
↓
Importación STEP
↓
Modelo interno
↓
Mallado de esa geometría real
↓
Análisis FEA
↓
Solver Kratos
↓
Resultados
↓
Salida del motor

La geometría utilizada por el mallador debe provenir del `cono.step`.

No utilices mocks, geometría artificial ni datos ficticios como sustituto de ninguna parte del flujo.

No modifiques la implementación para solucionar problemas durante la prueba.

Si el STEP real no puede atravesar alguna etapa, DETENTE y registra el error completo siguiendo el protocolo de `metodologia.md`. No intentes solucionarlo mediante ensayo y error.

Si la prueba se completa correctamente, documenta el comando utilizado, el archivo de entrada, los resultados obtenidos y la evidencia de que el `cono.step` atravesó el flujo completo.

No crees archivos de documentación adicionales.