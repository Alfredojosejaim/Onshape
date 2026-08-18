c### 📐 Arquitectura del Sistema a Documentar
El sistema utiliza un enfoque híbrido debido a las limitaciones de aislamiento de FeatureScript:
1. FRONTEND NATIVO (Onshape FeatureScript): Un Custom Feature en la línea de tiempo (Feature List) que permite al usuario seleccionar geométricamente caras de anclaje, caras de carga y magnitudes. Dibuja vectores gráficos de depuración en el entorno 3D.
2. INTERFAZ DE USUARIO (Onshape App Extension): Un panel lateral embebido en JavaScript que expone el botón de "Calcular Optimización" y se comunica bidireccionalmente entre el cliente de Onshape y nuestra API externa.
3. BACKEND / API (Python + FastAPI): Servidor que recibe la llamada de la extensión, consulta la API REST de Onshape mediante "Get Part Studio Features" para extraer el JSON de restricciones, descarga el archivo geométrico (.STEP/.X_T), ejecuta la optimización topológica tridimensional y devuelve el sólido suavizado de vuelta a Onshape.
4. MOTOR DE OPTIMIZACIÓN (Código Abierto): Basado en PyTopo3D / TopOpt (DTU) para el cálculo del elemento finito (FEA) y la distribución de densidades, junto con CadQuery / OpenCASCADE para la reconstrucción de superficies sólidas (NURBS/STEP).

### 📝 Tareas Inmediatas a Realizar (Fase 1: Documentación Base)
Genera el primer borrador de la documentación técnica estructurado en los siguientes apartados:
1. ESPECIFICACIÓN DEL ESQUEMA JSON: Define la estructura exacta del esquema de datos que el FeatureScript guardará en la línea de tiempo y que la API REST de Python deberá parsear (identificadores de entidades de caras, vectores de dirección x/y/z, magnitudes y parámetros de optimización como fracción de volumen u objetivos de cumplimiento).
2. FLUJO DE DATOS SECUENCIAL: Describe paso a paso (desde la selección de la cara en Onshape hasta el retorno del archivo STEP optimizado) cómo viajan los tokens de autenticación de la API, las ID de los documentos y los archivos geométricos intermedios.
3. ARQUITECTURA DE ENDPOINTS DE LA API: Define la firma de los endpoints clave de FastAPI requeridos para iniciar, monitorear el estado del cálculo (polling) y confirmar la inserción geométrica.

### 🛑 Reglas de Ejecución y Proceso de Consulta Obligatorio
* Sé extremadamente técnico y específico. Evita generalidades. Proporciona ejemplos de código simulados (mockups de código) donde sea necesario para ilustrar los puntos de integración.
* ANTES de desarrollar secciones donde encuentres lagunas de información, detén tu ejecución al final de la respuesta y formúlame un listado de preguntas críticas bajo el encabezado "🔍 CONSULTAS TÉCNICAS REQUERIDAS".

Pregúntame específicamente sobre:
- Preferencias de control de mallas (densidad de vóxeles o resolución).
- Estrategia de autenticación deseada (OAuth2 de Onshape o API Keys directas para desarrollo local).
- Manejo de zonas de no-diseño (si los anclajes deben mantenerse intactos como geometría sólida original en el resultado final).
- Cualquier otra restricción física (ej. restricciones de manufactura como desmoldeo o impresión 3D) que deba prever el backend.

Comienza generando la estructura inicial de la documentación y preséntame las primeras preguntas de aclaración que necesites para asegurar el éxito de la arquitectura.