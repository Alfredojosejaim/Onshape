import os
import sys
import requests
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv(find_dotenv())

# Leer credenciales y IDs de Onshape
access_key = os.getenv('ACCESS_KEY') or os.getenv('ONSHAPE_ACCESS_KEY')
secret_key = os.getenv('SECRET_KEY') or os.getenv('ONSHAPE_SECRET_KEY')
did = os.getenv('DID')
wid = os.getenv('WID')
mid = os.getenv('MID') or os.getenv('EID')

# Validar credenciales requeridas
if not all([access_key, secret_key, did, wid, mid]):
    print("❌ ERROR: Faltan credenciales o IDs en el archivo .env")
    print("   Variables requeridas: ACCESS_KEY, SECRET_KEY, DID, WID, MID/EID")
    sys.exit(1)

# Inicializar sesión global de peticiones para Onshape
session = requests.Session()

def setup_session():
    """Configura las credenciales de autenticación para la API."""
    session.auth = (access_key, secret_key)
    session.headers.update({'Accept': 'application/vnd.onshape.v2+json'})
    return session

def verificar_conexion() -> bool:
    """Verifica si las llaves y la conexión al servidor de Onshape son correctas."""
    # URL oficial de la API de Onshape para obtener detalles del documento
    url = f'https://cad.onshape.com/api/documents/d/{did}'
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 401:
            print("❌ Error 401: Credenciales inválidas o expiradas")
            return False
        elif response.status_code == 404:
            print("❌ Error 404: Documento no encontrado (verifica DID)")
            return False
        elif response.status_code == 200:
            return True
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print("❌ Timeout: La conexión tardó demasiado")
        return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def obtener_configuracion_optimizacion():
    """Descarga e interpreta los parámetros de fuerza y masa configurados en el CAD."""
    # CORREGIDO: URL reparada con el dominio correcto y estructura limpia
    url = f'https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{mid}/configuration'

    try:
        response = session.get(url)
        if response.status_code == 200:
            config_data = response.json()
            fuerza = None
            objetivo_masa = None
            direccion_z = None

            # Onshape organiza las configuraciones actuales dentro de 'currentConfiguration'
            if 'currentConfiguration' in config_data:
                for param in config_data['currentConfiguration']:
                    pid = param.get('parameterId')
                    pval = param.get('parameterValue')

                    if pid == 'fuerza' or pid == '#fuerza':
                        fuerza = pval
                    elif pid == 'objetivo_masa' or pid == '#objetivo_masa':
                        objetivo_masa = pval
                    elif pid == 'direccion_z' or pid == '#direccion_z':
                        direccion_z = pval

            print("\n=== VALORES LEÍDOS DESDE ONSHAPE ===")
            print(f'-> Magnitud de la fuerza: {fuerza if fuerza else "No detectada"}')
            print(f'-> Objetivo de masa: {objetivo_masa if objetivo_masa else "No detectado"}')
            print(f'-> Dirección Z: {direccion_z if direccion_z else "No detectada"}')
        else:
            print(f'Error al obtener configuración. Código de error HTTP: {response.status_code}')
    except Exception as e:
        print(f"Error al procesar la solicitud: {e}")

# Bloque de ejecución principal
if __name__ == '__main__':
    print("Iniciando el sistema de comunicación...")
    setup_session()

    print("Enviando señal de prueba a Onshape...")
    codigo_respuesta = verificar_conexion()
    print(f"Respuesta del servidor: {codigo_respuesta}")

    if codigo_respuesta == 200:
        print("¡Conexión establecida con éxito!")
        obtener_configuracion_optimizacion()
    else:
        print("\n[ALERTA] No se pudo conectar. Asegúrate de:")
        print("1. Haber puesto tus llaves reales en el archivo .env")
        print("2. Que los IDs (DID, WID, MID) en el .env coincidan con la URL de")
