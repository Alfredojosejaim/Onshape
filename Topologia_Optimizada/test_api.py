#!/usr/bin/env python3
"""
Script de prueba para la API de Optimización Topológica.
Verifica que todos los componentes funcionen correctamente.
"""

import requests
import json
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def print_header(text: str):
    """Imprime un encabezado."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_step(step: int, text: str):
    """Imprime un paso."""
    print(f"  [{step}] {text}")

def test_health():
    """Prueba el endpoint /health."""
    print_header("TEST 1: Verificar salud de la API")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        
        print_step(1, f"Status Code: {response.status_code}")
        print_step(2, f"API Status: {data['status']}")
        print_step(3, f"Credenciales: {'✓ Configuradas' if data['credenciales_configuradas'] else '✗ No configuradas'}")
        
        if response.status_code == 200:
            print("\n  ✓ API respondiendo correctamente\n")
            return True
        else:
            print(f"\n  ✗ Error HTTP {response.status_code}\n")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  ✗ No se puede conectar al servidor")
        print("    Asegúrate de que el servidor está ejecutándose:")
        print("    $ python api_server.py\n")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return False


def test_optimization():
    """Prueba el endpoint /api/optimize."""
    print_header("TEST 2: Enviar solicitud de optimización")
    
    # Payload de prueba
    payload = {
        "documentId": "test_doc_123",
        "workspaceId": "test_ws_456",
        "elementId": "test_elem_789",
        "topologyConfig": {
            "schemaVersion": "1.0",
            "anchors": [
                {"index": 0, "area": 12.5},
                {"index": 1, "area": 15.3}
            ],
            "loads": [
                {
                    "direction": {"x": 0.0, "y": 0.0, "z": -1.0},
                    "magnitude": 100,
                    "unit": "newton"
                }
            ],
            "optimization": {
                "volumeFraction": 0.30,
                "maxIterations": 10
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
    }
    
    try:
        print_step(1, "Enviando solicitud POST...")
        response = requests.post(
            f"{BASE_URL}/api/optimize",
            json=payload,
            timeout=10
        )
        
        data = response.json()
        
        print_step(2, f"Status Code: {response.status_code}")
        print_step(3, f"Status: {data['status']}")
        print_step(4, f"Job ID: {data.get('jobId', 'N/A')}")
        print_step(5, f"Mensaje: {data['message']}")
        
        if response.status_code == 200 and data.get('jobId'):
            print("\n  ✓ Solicitud aceptada\n")
            return data.get('jobId')
        else:
            print(f"\n  ✗ Error: {data.get('message', 'Unknown error')}\n")
            return None
            
    except requests.exceptions.Timeout:
        print("  ✗ Timeout en la solicitud\n")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return None


def test_status(job_id: str):
    """Prueba el endpoint /api/optimize/status."""
    print_header("TEST 3: Monitorear estado de la optimización")
    
    if not job_id:
        print("  ✗ No hay Job ID para monitorear\n")
        return False
    
    try:
        for i in range(10):  # Polling durante 10 intentos
            print_step(1, f"Intentando obtener estado (intento {i+1}/10)...")
            
            response = requests.get(
                f"{BASE_URL}/api/optimize/status",
                params={"jobId": job_id},
                timeout=5
            )
            
            data = response.json()
            
            status = data['status']
            progress = data['progress']
            message = data['message']
            
            print_step(2, f"Status: {status}")
            print_step(3, f"Progreso: {progress}%")
            print_step(4, f"Mensaje: {message[:50]}...")
            
            if status == "completed":
                print_step(5, "✓ Optimización completada")
                print_step(6, f"Resultado: {json.dumps(data.get('result', {}), indent=2)}")
                print("\n  ✓ Monitoreo completado\n")
                return True
            elif status == "failed":
                print_step(5, f"✗ Error: {data.get('message', 'Unknown error')}")
                print("\n  ✗ La optimización falló\n")
                return False
            
            if i < 9:
                time.sleep(2)  # Esperar 2 segundos antes del siguiente intento
        
        print_step(5, "⏳ La optimización aún está en progreso")
        print("\n  ⚠ Timeout: Sigue siendo consultable con el Job ID\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return False


def test_docs():
    """Prueba la documentación de API."""
    print_header("TEST 4: Verificar documentación")
    
    try:
        print_step(1, "Obteniendo especificación de API...")
        response = requests.get(f"{BASE_URL}/api/docs", timeout=5)
        
        data = response.json()
        print_step(2, f"Nombre: {data.get('nombre', 'N/A')}")
        print_step(3, f"Versión: {data.get('version', 'N/A')}")
        print_step(4, f"Endpoints documentados: {len(data.get('endpoints', {}))}")
        
        print("\n  ✓ Documentación disponible\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return False


def test_jobs_list():
    """Prueba el endpoint /api/jobs."""
    print_header("TEST 5: Listar trabajos")
    
    try:
        response = requests.get(f"{BASE_URL}/api/jobs", timeout=5)
        data = response.json()
        
        total = data.get('total_jobs', 0)
        print_step(1, f"Trabajos totales: {total}")
        
        if total > 0:
            for job_id, job_info in list(data.get('jobs', {}).items())[:3]:
                print_step(2, f"Job {job_id[:12]}... - Status: {job_info['status']} ({job_info['progress']}%)")
        
        print("\n  ✓ Listado de trabajos disponible\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n")
    print("   ╔════════════════════════════════════════════════════════════╗")
    print("   ║   TESTS DE API - OPTIMIZACIÓN TOPOLÓGICA                   ║")
    print("   ║   Verifica integración completa TopOpt + Onshape          ║")
    print("   ╚════════════════════════════════════════════════════════════╝")
    
    results = {}
    
    # Test 1: Health
    results['health'] = test_health()
    if not results['health']:
        print("\n❌ El servidor no está disponible. Inicia con: python api_server.py\n")
        return 1
    
    # Test 2: Optimization request
    job_id = test_optimization()
    results['optimization'] = job_id is not None
    
    # Test 3: Status monitoring
    if job_id:
        results['status'] = test_status(job_id)
    else:
        results['status'] = False
    
    # Test 4: Documentation
    results['docs'] = test_docs()
    
    # Test 5: Jobs list
    results['jobs'] = test_jobs_list()
    
    # Summary
    print_header("RESUMEN DE TESTS")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  [{status}] {test_name.upper()}")
    
    print(f"\n  Total: {passed}/{total} tests pasados\n")
    
    if passed == total:
        print("  🎉 ¡TODOS LOS TESTS PASARON!\n")
        return 0
    else:
        print("  ⚠ Algunos tests fallaron. Revisa los errores arriba.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
