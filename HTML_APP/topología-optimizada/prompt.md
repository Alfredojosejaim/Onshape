Procesó durante 23s

Sí. Hice una nueva comprobación directamente sobre el estado actual de master.

Resultado de la auditoría

Los 3 problemas que habíamos identificado están corregidos.

1. getSafetySummary y compareStudies

Ya están incluidos en _METHODS de backend/app_desktop.py.

También están incluidos en la whitelist del servidor.



2. Whitelist de server.py

Ahora el servidor comprueba method contra ALLOWED_METHODS antes de ejecutar getattr(_API, method).

Un método no autorizado se rechaza limpiamente.

Esto corrige exactamente el problema señalado en la auditoría anterior.



3. Resultados ficticios iniciales

Se eliminaron los valores ficticios de FEA.

El estado inicial ahora usa null, por lo que la interfaz puede mostrar —/sin resultados.

La optimización inicia con historiales vacíos y compliance en 0.

También se modificó RightPanel para no intentar hacer .toFixed() sobre valores inexistentes.




Y sobre el mock: quedó aplicada la opción que elegimos

El mock no fue eliminado.

Quedó como fallback de demo, pero anclado a su propio estado en lugar de depender permanentemente de 148.5 como valor inicial. Además, la regla documentada es:

> sin estudio real → sin resultados;
con estudio real → resultados reales;
sin bridge → mock únicamente después de iniciar la simulación/demo.



Eso coincide con la opción 1: anclado al estado real/propio, que habíamos elegido.

⚠️ Una observación importante

Hay una pequeña inconsistencia documental que no considero motivo para tocar código ahora: la regla dice que el mock debe estar etiquetado MOCK-FALLBACK, pero en el fragmento revisado no puedo confirmar que esa etiqueta sea visible en la interfaz. Sí puedo confirmar que el comportamiento del mock fue modificado y documentado como fallback.

Por lo tanto, mi valoración actual es:

🟢 Correcciones solicitadas: OK.
🟢 No veo necesidad de otro refactor por estos puntos.
🟡 Quedan los problemas de backlog anteriores, que no deberían mezclarse con esta corrección.

Y algo importante: no voy a declarar que las pruebas pasan nuevamente solo porque el commit anterior las pasó. En el estado actual puedo verificar el código y los cambios del commit, pero no tengo una ejecución nueva de pytest, TypeScript y build en este momento.