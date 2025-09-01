import pandas as pd
from typing import List
import os

def crear_directorios():
    """Crea los directorios necesarios para el proyecto"""
    directorios = ['datos/entrada', 'datos/salida', 'mapas']
    
    for directorio in directorios:
        os.makedirs(directorio, exist_ok=True)
    
    print("✅ Directorios creados/existen")

def filtrar_por_zona(df: pd.DataFrame, zona: str) -> pd.DataFrame:
    """Filtra el DataFrame por zona (case insensitive y con trim)"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Buscar la columna Zona (puede estar en diferentes casos)
    columnas_zona = [col for col in df.columns if col.lower() == 'zona']
    
    if not columnas_zona:
        print("❌ No se encontró columna 'Zona' en el CSV")
        if hasattr(df, 'columns'):
            print(f"🔍 Columnas disponibles: {', '.join(df.columns)}")
        return pd.DataFrame()
    
    columna_zona = columnas_zona[0]
    
    # Hacer la búsqueda case insensitive y con trim
    try:
        df_filtrado = df[df[columna_zona].astype(str).str.strip().str.lower() == zona.strip().lower()].copy()
        
        if df_filtrado.empty:
            print(f"⚠️  No se encontraron registros para la zona: '{zona}'")
            if columna_zona in df.columns:
                zonas_disponibles = df[columna_zona].astype(str).str.strip().unique()
                print(f"💡 Zonas disponibles: {zonas_disponibles}")
        
        return df_filtrado
        
    except Exception as e:
        print(f"❌ Error filtrando por zona: {e}")
        return pd.DataFrame()

def dividir_por_notificadores(df: pd.DataFrame, cuentas_por_notificador: int) -> List[pd.DataFrame]:
    """Divide el DataFrame en chunks para cada notificador"""
    if df is None or df.empty:
        return []
    
    chunks = []
    total_cuentas = len(df)
    
    for i in range(0, total_cuentas, cuentas_por_notificador):
        chunk = df.iloc[i:i + cuentas_por_notificador].copy()
        chunks.append(chunk)
    
    return chunks

def mostrar_ruta(ruta: List[int], df: pd.DataFrame):
    """Muestra una ruta específica con formato legible"""
    if not ruta or df is None or df.empty:
        print("❌ No hay datos para mostrar")
        return
    
    print(f"\n📋 Ruta Optimizada ({len(ruta)} paradas):")
    for i, idx in enumerate(ruta):
        try:
            # Buscar columnas (pueden tener diferentes nombres)
            cuenta = df.iloc[idx].get('Cuenta', df.iloc[idx].get('cuenta', 'N/A'))
            domicilio_limpio = df.iloc[idx].get('domicilio_limpio', '')
            domicilio_original = df.iloc[idx].get('Domicilio', df.iloc[idx].get('domicilio', 'N/A'))
            
            domicilio = domicilio_limpio if domicilio_limpio else domicilio_original
            
            print(f"  {i+1}. {cuenta} - {domicilio}")
        except Exception as e:
            print(f"  {i+1}. Error mostrando punto: {e}")

def verificar_estructura_csv(df: pd.DataFrame):
    """Verifica que el CSV tenga la estructura correcta"""
    if df is None or df.empty:
        return False, "El DataFrame está vacío"
    
    columnas_obligatorias = ['Domicilio', 'Zona']
    columnas_opcionales = ['ID', 'Cuenta', 'Colonia', 'CP']
    
    columnas_faltantes = []
    for col in columnas_obligatorias:
        if col not in df.columns:
            columnas_faltantes.append(col)
    
    if columnas_faltantes:
        return False, f"Columnas obligatorias faltantes: {', '.join(columnas_faltantes)}"
    
    return True, "Estructura correcta"

def verificar_servicios_internet():
    """Verifica si los servicios de mapas están disponibles"""
    import requests
    import socket
    
    servicios = {
        'OpenStreetMap Nominatim': 'https://nominatim.openstreetmap.org',
        'OSRM Routing': 'http://router.project-osrm.org',
        'Static Maps': 'https://staticmap.openstreetmap.de'
    }
    
    print("🔍 Verificando conectividad con servicios de mapas...")
    
    for servicio, url in servicios.items():
        try:
            # Verificar DNS primero
            socket.gethostbyname(url.split('//')[1].split('/')[0])
            
            # Verificar conexión HTTP
            response = requests.get(url, timeout=5)
            status = "✅ En línea" if response.status_code == 200 else "⚠️  Problemas"
            print(f"   {servicio}: {status}")
            
        except socket.gaierror:
            print(f"   {servicio}: ❌ Error DNS - Sin conexión a internet")
        except requests.RequestException as e:
            print(f"   {servicio}: ❌ Error de conexión - {e}")
        except Exception as e:
            print(f"   {servicio}: ❌ Error inesperado - {e}")