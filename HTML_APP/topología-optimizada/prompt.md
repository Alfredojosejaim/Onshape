CORRECCIÓN QUIRÚRGICA — HTML_APP/topología-optimizada

OBJETIVO

Corrige únicamente los problemas concretos identificados en la auditoría actual de:

"HTML_APP/topología-optimizada"

No hagas refactors generales, no reorganices la arquitectura y no modifiques funcionalidades que ya funcionan.

La prioridad es:

preservar lo existente > corregir los defectos identificados > verificar que nada se haya roto.

---

1. CONTEXTO ACTUAL

El último commit de "master" ya contiene implementaciones funcionales importantes.

NO debes revertirlas ni reemplazarlas.

La arquitectura desktop actual es intencional:

React/HTML
    ↓
pywebview
    ↓
bridge.ts / app_desktop.py
    ↓
backend/server.py
    ↓
backend/api.py
    ↓
core

El backend pesado permanece separado del proceso de WebView2 por razones de estabilidad de DLL/nativas.

NO cambies esta arquitectura.

---

2. CORRECCIÓN OBLIGATORIA Nº1 — COMPLETAR EL BRIDGE DESKTOP

Revisa:

"HTML_APP/topología-optimizada/backend/app_desktop.py"

Existe una tupla "_METHODS" que funciona como whitelist de métodos expuestos por pywebview.

Actualmente el frontend "src/lib/bridge.ts" utiliza:

- "getSafetySummary"
- "compareStudies"

y "backend/api.py" también implementa esos métodos.

Asegúrate de que ambos métodos estén incluidos en "_METHODS" de "app_desktop.py".

Debe quedar conceptualmente:

_METHODS = (
    ...
    "getSafetySummary",
    "compareStudies",
    ...
)

No elimines ni cambies ningún método existente.

No cambies la forma en que "_make_bridge()" funciona.

No cambies la API de "bridge.ts".

No modifiques "api.py" salvo que una comprobación objetiva demuestre que sea estrictamente necesario para esta corrección.

Resultado esperado

La ruta:

React
→ bridge.ts
→ window.pywebview.api
→ app_desktop.py
→ server.py
→ api.py

debe permitir correctamente:

getSafetySummary
compareStudies

en la aplicación desktop real.

---

3. CORRECCIÓN OBLIGATORIA Nº2 — WHITELIST EN server.py

Revisa:

"HTML_APP/topología-optimizada/backend/server.py"

Actualmente el servidor obtiene dinámicamente el método mediante algo equivalente a:

getattr(_API, str(req.get("method", "")))

Esto permite intentar invocar cualquier atributo/método existente de "_API".

Añade una whitelist explícita de métodos permitidos.

Requisitos

- La whitelist debe contener los métodos que actualmente expone "app_desktop.py".
- No eliminar métodos existentes.
- No cambiar las firmas de "Api".
- No modificar el comportamiento normal de las llamadas válidas.
- Una llamada a un método no autorizado debe rechazarse limpiamente.
- No debe ejecutarse mediante "getattr()" antes de comprobar que el nombre está permitido.

El comportamiento deseado es conceptualmente:

if method not in ALLOWED_METHODS:
    devolver error

y solamente después:

getattr(_API, method)

La implementación concreta queda a tu criterio, pero debe ser mínima y clara.

Importante

No conviertas esto en un sistema de autenticación.

No añadas dependencias.

No cambies el servidor HTTP.

No cambies el puerto.

No cambies localhost/127.0.0.1.

No añadas una capa de seguridad innecesaria.

Solo incorpora la validación de métodos permitidos.

---

4. CORRECCIÓN OBLIGATORIA Nº3 — ELIMINAR RESULTADOS FEA FICTICIOS DEL ESTADO INICIAL

Revisa "HTML_APP/topología-optimizada/src/App.tsx".

Actualmente existen valores iniciales que parecen resultados reales aunque todavía no exista un estudio:

- "currentCompliance: 148.5"
- "currentVolume: 1.0"
- "maxVonMisesMpa: 342.4"
- "minSafetyFactor: 1.47"
- "maxDisplacementMm: 0.421"
- "modalFreqHz: 428"
- "strainEnergyJ: 1.84"
- "meshQualityPercent: 98.4"

No quiero que la interfaz presente estos números como resultados reales antes de ejecutar una operación que los produzca.

Corrige únicamente el estado inicial necesario para que la UI represente correctamente:

"sin resultados"

cuando todavía no existe un resultado real.

Reglas

- No inventar valores alternativos.
- No reemplazar un resultado falso por otro número ficticio.
- Preferir "null", estado vacío o el mecanismo de "sin resultado" que ya utilice la aplicación.
- Mantener intacta la estructura de "FeaResults" si no es necesario modificarla.
- Si cambiar tipos obliga a modificar demasiados componentes, utiliza el mecanismo existente más pequeño y seguro.
- Los resultados reales obtenidos posteriormente deben seguir funcionando exactamente igual.

Muy importante

No modificar:

- algoritmos FEA;
- solvers;
- optimización;
- postproceso;
- visualización de resultados reales;
- "SafetyCard";
- "CompareTable";
- viewport.

Solo impedir que aparezcan resultados ficticios antes de existir resultados.

---

5. NO HACER LIMPIEZA GENERAL

En esta tarea NO debes:

- refactorizar "App.tsx";
- dividir componentes;
- reorganizar carpetas;
- cambiar React;
- cambiar Vite;
- cambiar Three.js;
- cambiar pywebview;
- cambiar FastAPI/API;
- cambiar el core;
- cambiar el core vendorizado;
- modificar "Topologia_Optimizada";
- sincronizar/copiar nuevamente el core;
- modificar solvers;
- cambiar algoritmos de optimización;
- modificar condiciones de carga;
- modificar selección de caras;
- modificar navegación;
- modificar viewport;
- modificar el sistema de licencia;
- modificar el sistema de jobs;
- modificar la importación STEP;
- modificar generative design;
- modificar FEA;
- modificar thermal/modal;
- modificar GCMMA;
- modificar SIMP;
- modificar Kratos;
- modificar CAD operations.

Tampoco elimines comentarios "*-START", "*-END" o documentación reversible existente solo porque parezcan innecesarios.

---

6. DEPENDENCIAS DEL package.json

NO elimines todavía las dependencias aparentemente no utilizadas.

La auditoría detectó posibles residuos del template, pero eso queda fuera de esta corrección.

Por tanto:

NO modificar "package.json" en esta tarea, salvo que una de las correcciones obligatorias lo requiera directamente.

La limpieza de dependencias será una tarea independiente.

---

7. VERIFICACIÓN OBLIGATORIA

Después de realizar los cambios:

Python

Ejecuta:

pytest backend/tests

Debe mantenerse el resultado actual:

20/20 tests passing, salvo que el repositorio actual haya cambiado después de la auditoría.

Ejecuta también:

python -m compileall backend

Debe terminar sin errores.

TypeScript

Ejecuta:

npx tsc --noEmit

Debe terminar sin errores.

Build

Ejecuta:

npm run build

Debe completar correctamente.

---

8. PRUEBA ESPECÍFICA DEL BRIDGE

Comprueba explícitamente que:

getSafetySummary

y:

compareStudies

están:

1. implementados en "api.py";
2. disponibles en "bridge.ts";
3. incluidos en "_METHODS" de "app_desktop.py";
4. permitidos por la whitelist de "server.py".

No basta con comprobar que TypeScript compile.

---

9. PRUEBA ESPECÍFICA DE SEGURIDAD

Comprueba que un método inexistente/no autorizado enviado al servidor:

NO se ejecute mediante getattr()

y devuelva un error controlado.

Comprueba también que los métodos válidos continúen funcionando.

---

10. CONTROL DE CAMBIOS

Antes de finalizar, revisa el diff completo:

git diff

El cambio debe ser pequeño y estar limitado a los problemas de esta tarea.

Si encuentras cambios no relacionados:

reviértelos antes de terminar.

No hagas commits adicionales automáticamente.

---

11. INFORME FINAL OBLIGATORIO

Al terminar, informa solamente:

Cambios realizados

- archivo
- cambio concreto

Verificación

- pytest
- compileall
- tsc
- npm build

Resultado

Indica claramente:

- qué quedó corregido;
- si alguna prueba falló;
- si existe algún problema pendiente.

No declares una corrección como completada si no fue verificada.

---

REGLA FINAL

Esta es una corrección quirúrgica, no una nueva fase de desarrollo.

Si durante la implementación detectas otro problema que no sea necesario para solucionar los tres puntos anteriores:

NO lo corrijas.

Documenta el hallazgo al final y deja el código intacto.

No aproveches esta tarea para refactorizar, limpiar o mejorar otras partes del proyecto.