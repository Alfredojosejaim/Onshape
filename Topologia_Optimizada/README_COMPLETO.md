# 🔬 Topología Optimizada - Sistema Completo

## 📋 Descripción

Sistema integral de **optimización topológica 3D** para Onshape que integra:

1. **FeatureScript** - Captura parámetros geométricos en Onshape
2. **App Extension** - Panel lateral para control desde Onshape
3. **Motor TopOpt** - Solver SIMP de optimización topológica
4. **Backend FastAPI** - API REST para procesamiento
5. **Geometry Processor** - Descarga y análisis de STEP desde Onshape

---

## 🚀 Instalación Rápida

### 1. Clonar y entrar al directorio

```bash
cd D:\Documentos\GitHub\Onshape\Topologia_Optimizada
```

### 2. Instalar dependencias

```bash
pip install -e .
```

Esto instala todos los paquetes definidos en `pyproject.toml`:
- FastAPI, Uvicorn, Pydantic
- NumPy, SciPy, scikit-fem
- CadQuery, OCP
- Y más...

### 3. Configurar credenciales en `.env`

```bash
# Copiar desde archivo existente si lo tienes
# Asegúrate de completar:
ONSHAPE_ACCESS_KEY=tu_access_key
ONSHAPE_SECRET_KEY=tu_secret_key
DID=document_id
WID=workspace_id
MID=part_studio_id
```

### 4. Iniciar el servidor

```bash
python api_server.py
```

Deberías ver:

```
============================================================
  🚀 INICIANDO SERVIDOR DE OPTIMIZACIÓN TOPOLÓGICA
============================================================
Versión: 1.0.0
Motor: TopOpt SIMP
Backend: FastAPI + Uvicorn
Puerto: 8000

✓ Credenciales de Onshape configuradas correctamente

📚 Documentación disponible en:
  - API Docs: http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc
  - Health: http://localhost:8000/health
============================================================
```

---

## 🧪 Pruebas de Integración

En otra terminal, ejecuta los tests:

```bash
python test_api.py
```

Esto verifica:
- ✓ Conectividad del servidor
- ✓ Aceptación de solicitudes de optimización
- ✓ Monitoreo de estado con polling
- ✓ Documentación de API
- ✓ Listado de trabajos

---

## 📦 Componentes del Sistema

### 1. `master_topology_input.fs` (FeatureScript)

Crea un Custom Feature en Onshape que:
- Permite seleccionar caras de anclaje
- Define carga (cara, dirección, magnitud)
- Configura parámetros de optimización
- Serializa todo en JSON persistente

**Cómo usar en Onshape:**
1. Abre Part Studio
2. Insert → Custom feature → "Master Topology Input"
3. Selecciona caras y parámetros
4. Confirma el feature

### 2. `app-extension.html` (Panel Lateral)

Panel interactivo que:
- Lee el JSON del FeatureScript
- Muestra parámetros cargados
- Botón "Optimizar" para enviar al backend
- Monitorea progreso en tiempo real
- Muestra resultados

**Registro en Onshape:**
1. Settings → App Extensions → Create New
2. Name: "Optimización Topológica"
3. URL: `http://localhost:8001/app-extension.html`
4. Habilitar para Part Studios

### 3. `api_server.py` (Backend FastAPI)

API REST principal con endpoints:

#### `POST /api/optimize`
Inicia una optimización topológica.

**Payload:**
```json
{
  "documentId": "abc123",
  "workspaceId": "def456",
  "elementId": "ghi789",
  "topologyConfig": {
    "schemaVersion": "1.0",
    "anchors": [
      {"index": 0, "area": 12.5}
    ],
    "loads": [
      {
        "direction": {"x": 0, "y": 0, "z": -1},
        "magnitude": 100,
        "unit": "newton"
      }
    ],
    "optimization": {
      "volumeFraction": 0.30,
      "maxIterations": 100
    }
  }
}
```

**Respuesta:**
```json
{
  "status": "queued",
  "message": "Optimización encolada...",
  "jobId": "job_a1b2c3d4",
  "data": {...}
}
```

#### `GET /api/optimize/status?jobId=job_a1b2c3d4`
Obtiene el estado de una optimización.

**Respuesta:**
```json
{
  "job_id": "job_a1b2c3d4",
  "status": "processing",
  "progress": 65,
  "message": "TopOpt: Iter 45, Cambio=0.0234",
  "result": null
}
```

#### `GET /health`
Verifica que el servidor esté disponible.

#### `GET /api/docs`
Documentación de los endpoints.

### 4. `topopt_solver.py` (Motor de Optimización)

Implementa el algoritmo **SIMP** (Solid Isotropic Material with Penalization):

```python
from topopt_solver import TopOptSolver

solver = TopOptSolver(
    nelx=20,      # Elementos en X
    nely=20,      # Elementos en Y
    volfrac=0.3,  # Fracción de volumen objetivo
    penalization=3.0  # Factor de penalización
)

results = solver.solve(
    forces=forces_array,
    supports=supports_array,
    max_iterations=100,
    tolerance=0.01,
    callback=progress_callback
)
```

**Características:**
- ✓ Algoritmo SIMP clásico
- ✓ Filtrado de sensibilidades
- ✓ Método de bisección para actualización de densidades
- ✓ Convergencia adaptativa
- ✓ Callback de progreso en tiempo real

### 5. `geometry_processor.py` (Procesador de Geometría)

Descarga y procesa geometría desde Onshape:

```python
from geometry_processor import GeometryProcessor

processor = GeometryProcessor(session, did, wid, eid)

# Pipeline completo
result = processor.process_full_pipeline(
    target_element_size=1.0,
    output_file="optimized.step"
)

# Acceso a:
# - result['mesh']['nodes']
# - result['mesh']['elements']
# - result['boundary_conditions']
# - result['properties']
```

**Funciones:**
- Descarga Part Studio en STEP
- Obtiene propiedades (volumen, área, centroides)
- Genera mesh de FEA
- Identifica condiciones de contorno
- Reconstruye geometría optimizada

---

## 🔄 Flujo Completo de Ejecución

```
┌─────────────────┐
│  Usuario en     │
│  Onshape        │
└────────┬────────┘
         │
         ├─ 1. Inserta Feature "Master Topology Input"
         ├─ 2. Selecciona geometría y parámetros
         ├─ 3. Abre panel App Extension
         │
         ↓
┌─────────────────────┐
│  App Extension      │
│  (Panel Lateral)    │
└────────┬────────────┘
         │
         ├─ 4. Lee JSON del FeatureScript
         ├─ 5. Muestra parámetros
         ├─ 6. Usuario clica "Optimizar"
         │
         ↓ HTTP POST
┌─────────────────────────────┐
│  API FastAPI                │
│  /api/optimize              │
└────────┬────────────────────┘
         │
         ├─ 7. Valida datos
         ├─ 8. Crea Job ID único
         ├─ 9. Lanza optimización en background
         │
         ↓
┌─────────────────────────────┐
│  Optimización en Background │
│  (ejecutar_optimizacion)    │
└────────┬────────────────────┘
         │
         ├─ 10. Descarga Part Studio (STEP)
         ├─ 11. Genera mesh de FEA
         ├─ 12. Identifica condiciones de contorno
         │
         ↓
┌─────────────────────────────┐
│  TopOpt Solver              │
│  (SIMP Algorithm)           │
└────────┬────────────────────┘
         │
         ├─ 13. Itera distribución de densidades
         ├─ 14. Minimiza compliance
         ├─ 15. Respeta fracción de volumen
         ├─ 16. Reporta progreso cada iteración
         │
         ↓
┌─────────────────────────────┐
│  Reconstrucción de Geometría│
│  Geometry Processor         │
└────────┬────────────────────┘
         │
         ├─ 17. Extrae elementos activos
         ├─ 18. Convierte a geometría STEP
         ├─ 19. Suaviza con NURBS
         │
         ↓
┌─────────────────────────────┐
│  Resultado Disponible       │
│  en Job Status              │
└─────────────────────────────┘
         │
         ├─ 20. App Extension consulta /api/optimize/status
         ├─ 21. Muestra progreso 0-100%
         ├─ 22. Cuando completa, muestra resultado
         ├─ 23. Proporciona descarga de geometría
         ↓
┌─────────────────┐
│  Usuario        │
│  Descarga STEP  │
│  Importa en     │
│  Onshape        │
└─────────────────┘
```

---

## 📊 Monitoreo en Tiempo Real

La App Extension actualiza el progreso continuamente:

```
⟳ Leyendo datos del Feature...
✓ Datos del Feature cargados correctamente
⟳ Enviando solicitud al servidor...
⟳ Descargando y procesando geometría...
TopOpt: Iter 1, Cambio=0.2451
TopOpt: Iter 2, Cambio=0.1823
TopOpt: Iter 3, Cambio=0.0954
...
TopOpt: Iter 45, Cambio=0.0089
✓ Optimización completada exitosamente

RESULTADO:
- Iteraciones completadas: 45
- Compliance final: 1234.56
- Fracción de volumen: 0.30
- Elementos activos: 1456 / 8000
```

---

## 🛠️ Desarrollo y Extensiones

### Agregar nuevo solver

Crea `solver_tu_motor.py`:

```python
class TuSolver:
    def solve(self, domain, loads, constraints, params):
        # Tu lógica
        pass
```

Modifica `api_server.py` para usar tu solver.

### Integrar Gmsh para meshing

Actualmente usa mesh simplificado. Para producción:

```python
import gmsh

gmsh.initialize()
gmsh.open("geometry.step")
gmsh.model.mesh.generate(3)  # 3D mesh
gmsh.write("mesh.msh")
gmsh.finalize()
```

### Exportar resultados optimizados

En `geometry_processor.py`, mejorar:

```python
def reconstruct_step_from_densities(self, densities, ...):
    # Usar CadQuery/OCP para construir sólido
    from cadquery import Workplane
    # Crear geometría suave
```

---

## 📚 API Interactiva

Accede a la documentación interactiva:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Prueba los endpoints directamente desde el navegador.

---

## 🐛 Troubleshooting

### "❌ Credenciales inválidas"
```bash
# Obtén nuevas claves en:
# https://cad.onshape.com/api

# Actualiza .env y reinicia servidor
```

### "❌ No se conecta a Onshape"
```bash
# Verifica que los IDs sean correctos:
# https://cad.onshape.com/documents/{DID}/w/{WID}/e/{EID}

# Prueba conectividad:
python -c "import requests; r=requests.get('https://cad.onshape.com/api/documents/d/{DID}', auth=('key', 'secret')); print(r.status_code)"
```

### "⏳ La optimización es muy lenta"
```python
# Reduce el dominio:
nelx, nely = 10, 10  # En lugar de 20, 20

# Reduce iteraciones:
maxIterations = 50  # En lugar de 100

# Aumenta tamaño de elemento:
target_element_size = 2.0  # En lugar de 1.0
```

### "❌ Error de CORS"
El CORS ya está configurado para aceptar todas las orígenes. Si persiste:

```python
# En api_server.py, ajusta:
allow_origins=["https://cad.onshape.com"]
```

---

## 📞 Soporte

Revisa los logs:

```bash
# Terminal con api_server.py
# Busca mensajes con [job_XXX]
[2024-01-15 10:30:45] [job_a1b2c3d4] Iniciando optimización
[2024-01-15 10:30:46] [job_a1b2c3d4] Descargando Part Studio
[2024-01-15 10:31:02] [job_a1b2c3d4] Iter 1/100: Cambio=0.2451
...
```

---

## 📄 Archivos Creados Hoy

```
topologia_optimizada.py          (original - sin cambios)
master_topology_input.fs         ✅ ACTUALIZADO - FeatureScript mejorado
app-extension.html               ✅ NUEVO - Panel Onshape
api_server.py                    ✅ NUEVO - Backend integrado
topopt_solver.py                 ✅ NUEVO - Motor TopOpt SIMP
geometry_processor.py            ✅ NUEVO - Procesador de STEP
manifest.json                    ✅ NUEVO - Configuración App
test_api.py                      ✅ NUEVO - Suite de tests
INTEGRACION_APP_EXTENSION.md     ✅ NUEVO - Guía integración
pyproject.toml                   ✅ ACTUALIZADO - Dependencias
```

---

## 🎯 Próximos Pasos (Roadmap)

- [ ] Integrar Gmsh para meshing automático
- [ ] Agregar restricciones de manufactura (desmoldeo, espesores mín.)
- [ ] Soporte para optimización 3D completa
- [ ] Visualización 3D en tiempo real
- [ ] Base de datos para historial de optimizaciones
- [ ] Exportar a formatos CAD adicionales (IGES, Parasolid)
- [ ] Machine learning para sugerir parámetros óptimos

---

**¡Sistema listo para optimizar estructuras en Onshape!** 🚀

