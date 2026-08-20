# 🔗 Integración: FeatureScript + App Extension + Backend Python

## 📋 Descripción General

Este sistema de 3 capas permite optimizar topológicamente estructuras en Onshape:

```
┌─────────────────────┐
│  FeatureScript      │  ← Selecciona geometría y parámetros
│  (master_topology   │
│   _input.fs)        │
└──────────┬──────────┘
           │ JSON serializado
           ↓
┌─────────────────────┐
│  App Extension      │  ← Panel lateral en Onshape
│  (app-extension    │
│   .html)            │
└──────────┬──────────┘
           │ HTTP POST
           ↓
┌─────────────────────┐
│  Backend Python     │  ← Ejecuta optimización (FastAPI)
│  (api_server.py)    │
└─────────────────────┘
```

---

## 🛠️ Instalación y Configuración

### 1. Archivos Necesarios

✅ Ya creados:
- `master_topology_input.fs` — FeatureScript actualizado
- `app-extension.html` — Panel de control
- `api_server.py` — Backend FastAPI
- `manifest.json` — Configuración de la App Extension

### 2. Configurar Variables de Entorno

Actualiza tu `.env`:

```bash
# Credenciales de Onshape API
ONSHAPE_ACCESS_KEY=tu_access_key_aquí
ONSHAPE_SECRET_KEY=tu_secret_key_aquí

# IDs del documento (obtener de la URL de Onshape)
# https://cad.onshape.com/documents/{DID}/w/{WID}/e/{EID}
DID=documentIdAqui
WID=workspaceIdAqui
MID=partStudioIdAqui

# Configuración del servidor (para desarrollo local)
API_URL=http://localhost:8000/api/optimize
```

### 3. Instalar Dependencias

```bash
pip install fastapi uvicorn pydantic requests python-dotenv
```

### 4. Iniciar el Backend

```bash
python api_server.py
```

Deberías ver:
```
🚀 Iniciando servidor de Optimización Topológica...
✓ Credenciales configuradas correctamente
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 📦 Registrar la App Extension en Onshape

### Opción A: Desarrollo Local (recomendado primero)

1. **Hospedar localmente** (solo si Onshape permite acceso a localhost):
```bash
# En otra terminal, sirve los archivos
python -m http.server 8001
```

2. **En Onshape**, ir a **Settings > App Extensions** y crear nuevo:
   - **Name**: "Optimización Topológica"
   - **App URL**: `http://localhost:8001/app-extension.html?documentId={docId}&workspaceId={wId}&elementId={eId}`

### Opción B: Producción (con servidor remoto)

1. **Subir archivos a un servidor** (AWS S3, GitHub Pages, etc.):
   ```bash
   aws s3 cp app-extension.html s3://tu-bucket/
   ```

2. **En Onshape**, usar:
   - **App URL**: `https://tu-dominio.com/app-extension.html?documentId={docId}&workspaceId={wId}&elementId={eId}`

3. **Actualizar App Extension** con URL real del backend:
   - En el panel: Ingresa `https://tu-backend.com/api/optimize`

---

## 🔄 Flujo de Ejecución

### 1. Usuario en Onshape:
```
1. Abre un Part Studio
2. Abre el Feature "Master Topology Input"
3. Selecciona caras de anclaje (azules)
4. Selecciona cara de carga (roja)
5. Define dirección y magnitud de la carga
6. Define parámetros de optimización (fracción de volumen, iteraciones)
7. Confirma el feature → se genera JSON con los parámetros
```

### 2. En el Panel (App Extension):
```
1. El panel se abre automáticamente en el sidebar derecho
2. Botón "Actualizar" → Lee el atributo del FeatureScript
3. Verifica que los datos se carguen correctamente
4. Ingresa URL del backend (o usa la predefinida)
5. Clica "Optimizar" → Se envía JSON al servidor Python
```

### 3. En el Backend Python:
```
1. Recibe solicitud HTTP POST con todos los parámetros
2. Valida los datos
3. Descarga la geometría del Part Studio desde la API de Onshape
4. Ejecuta análisis de elementos finitos (FEA)
5. Ejecuta optimización topológica
6. Retorna resultado (Job ID para polling, o STEP directo)
```

---

## 📡 Estructura de Datos JSON

El FeatureScript genera y serializa este JSON:

```json
{
  "schemaVersion": "1.0",
  "loads": [
    {
      "directionX": 0.0,
      "directionY": 0.0,
      "directionZ": -1.0,
      "magnitude": 100,
      "unit": "newton"
    }
  ],
  "optimization": {
    "volumeFraction": 0.30,
    "maxIterations": 100
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🧪 Pruebas

### 1. Probar Backend Localmente

```bash
# Terminal 1: Iniciar servidor
python api_server.py

# Terminal 2: Hacer solicitud de prueba
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "documentId": "test_doc",
    "workspaceId": "test_ws",
    "elementId": "test_elem",
    "topologyConfig": {
      "schemaVersion": "1.0",
      "loads": [{
        "directionX": 0,
        "directionY": 0,
        "directionZ": -1,
        "magnitude": 100,
        "unit": "newton"
      }],
      "optimization": {
        "volumeFraction": 0.30,
        "maxIterations": 100
      }
    }
  }'
```

Respuesta esperada:
```json
{
  "status": "processing",
  "message": "Optimización iniciada correctamente",
  "jobId": "job_a1b2c3d4",
  "data": {
    "config_recibida": { ... },
    "documentId": "test_doc",
    "next_step": "Descargando geometría y ejecutando FEA"
  }
}
```

### 2. Probar en Onshape

1. Crear Part Studio test con geometría simple
2. Insertar Feature "Master Topology Input"
3. Seleccionar caras y parámetros
4. Abrir el panel (App Extension)
5. Verificar que se carguen los datos
6. Clica "Optimizar" y verifica que el backend reciba la solicitud

---

## ⚠️ Problemas Comunes

### "❌ Cliente de Onshape no inicializado"
- **Causa**: Los parámetros de query string no se pasan correctamente
- **Solución**: Verifica que la URL de la App Extension incluya `?documentId={docId}&workspaceId={wId}&elementId={eId}`

### "❌ No se encontró el Feature"
- **Causa**: El FeatureScript no se ha ejecutado en el Part Studio
- **Solución**: 
  1. Abre el Part Studio
  2. Inserta el Feature "Master Topology Input"
  3. Completa los parámetros
  4. Haz clic derecho y confirma

### "❌ Error HTTP 401: Credenciales inválidas"
- **Causa**: Las claves de API de Onshape son incorrectas o han expirado
- **Solución**:
  1. Genera nuevas claves en [Onshape Account Settings](https://cad.onshape.com/api)
  2. Actualiza `.env` con las nuevas claves
  3. Reinicia el servidor

### "❌ CORS error"
- **Causa**: El navegador bloquea la solicitud por origen diferente
- **Solución**: El backend ya tiene CORS configurado para `*`. Si persiste, verifica:
  - Que `app-extension.html` se sirva desde HTTPS en producción
  - Que el backend también esté en HTTPS

---

## 🚀 Próximos Pasos

## Estado real del MVP

El backend conserva la descarga real de STEP y propiedades de Onshape, pero no
presenta mallas, FEA, resultados TopOpt ni STEP reconstruidos cuando no existe
un adaptador real configurado. En esos casos el job queda `pending` con un
codigo explicito (`MESHER_REQUIRED`, `FEA_SOLVER_REQUIRED`, etc.).

Los jobs se persisten en `jobs.sqlite3` (configurable con `JOB_DB_PATH`).
Las API keys solo se leen en el backend desde `.env`; copia `.env.example` y
no subas el archivo `.env`.

La App Extension no llama directamente a la API de Onshape. Necesita un
adaptador SDK registrado externamente que exponga el contexto del documento y
`getFeatureData`; si esa capacidad no esta disponible, el panel muestra
`REQUIERE CONFIGURACION EXTERNA`. Los parametros de URL solo son fallback de
debug (`debug=1`). Para usarla desde Onshape, publica el panel y el backend
por HTTPS (por ejemplo, mediante un tunel local).

El timestamp se solicita al runtime de FeatureScript con
`getCurrentDateTime()`. Debe verificarse al publicar el FeatureScript en la
version de Onshape elegida; si ese runtime no expone la funcion, requiere un
adaptador externo de timestamp y no debe sustituirse por una fecha fija.

1. **Integrar el motor de optimización**:
   - Implementar PyTopo3D o TopOpt en `api_server.py`
   - Descargar geometría STEP desde Onshape
   - Ejecutar análisis FEA y optimización

2. **Polling de estado**:
   - Implementar queue (Redis/Celery) para tareas de larga duración
   - Endpoint `/api/optimize/status` para monitorear progreso

3. **Retorno de resultados**:
   - Guardar geometría optimizada como STEP
   - Subir el resultado de vuelta a Onshape
   - Insertar el feature optimizado en la línea de tiempo

4. **Mejoras de UI**:
   - Visualización del progreso en tiempo real
   - Visor 3D del resultado antes de importar
   - Historial de optimizaciones

---

## 📞 Soporte

Para problemas específicos:

1. **FeatureScript**: Revisa la consola de Onshape (Help > Debug Console)
2. **Backend**: Revisa logs de `api_server.py`
3. **Comunicación**: Abre Developer Tools del navegador (F12) y revisa Network tab

Archivos creados hoy:
- ✅ `master_topology_input.fs` (actualizado)
- ✅ `app-extension.html` (nuevo)
- ✅ `api_server.py` (nuevo)
- ✅ `manifest.json` (nuevo)
