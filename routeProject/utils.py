import pandas as pd
from typing import List
import os
import math

def crear_directorios():
    """Crea los directorios necesarios para el proyecto"""
    directorios = ['datos/entrada', 'datos/salida', 'mapas']
    
    for directorio in directorios:
        os.makedirs(directorio, exist_ok=True)
    
    print("Directorios creados/existen")

def filtrar_por_zona(df: pd.DataFrame, zona: str) -> pd.DataFrame:
    """Filtra el DataFrame por zona (case insensitive y con trim)"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Buscar la columna Zona
    columnas_zona = [col for col in df.columns if col.lower() == 'zona']
    
    if not columnas_zona:
        print("No se encontró columna 'Zona' en el CSV")
        if hasattr(df, 'columns'):
            print(f"Columnas disponibles: {', '.join(df.columns)}")
        return pd.DataFrame()
    
    columna_zona = columnas_zona[0]
    
    # Hacer la búsqueda case insensitive y con trim
    try:
        df_filtrado = df[df[columna_zona].astype(str).str.strip().str.lower() == zona.strip().lower()].copy()
        
        if df_filtrado.empty:
            print(f"No se encontraron registros para la zona: '{zona}'")
            if columna_zona in df.columns:
                zonas_disponibles = df[columna_zona].astype(str).str.strip().unique()
                print(f"Zonas disponibles: {zonas_disponibles}")
        
        return df_filtrado
        
    except Exception as e:
        print(f"Error filtrando por zona: {e}")
        return pd.DataFrame()

# ✅ NUEVA FUNCIÓN NECESARIA
def filtrar_por_colonia(df: pd.DataFrame, colonia: str) -> pd.DataFrame:
    """Filtra el DataFrame por colonia (case insensitive y con trim)"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Buscar la columna Colonia
    columnas_colonia = [col for col in df.columns if col.lower() == 'colonia']
    
    if not columnas_colonia:
        print("No se encontró columna 'Colonia' en el CSV")
        return df  # Retornar el DataFrame original si no hay columna Colonia
    
    columna_colonia = columnas_colonia[0]
    
    # Hacer la búsqueda case insensitive y con trim
    try:
        df_filtrado = df[df[columna_colonia].astype(str).str.strip().str.lower() == colonia.strip().lower()].copy()
        
        if df_filtrado.empty:
            print(f"No se encontraron registros para la colonia: '{colonia}'")
            if columna_colonia in df.columns:
                colonias_disponibles = df[columna_colonia].astype(str).str.strip().unique()
                print(f"Colonias disponibles: {colonias_disponibles}")
        
        return df_filtrado
        
    except Exception as e:
        print(f"Error filtrando por colonia: {e}")
        return df  # Retornar el DataFrame original en caso de error

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
        print("No hay datos para mostrar")
        return
    
    print(f"\nRuta Optimizada ({len(ruta)} paradas):")
    
    # Identificar puntos lejanos (más de 50km del centro)
    coordenadas = list(zip(df['lat'], df['lon']))
    puntos_lejanos = set()
    
    if len(coordenadas) > 1:
        # Calcular centroide
        lats = [lat for lat, lon in coordenadas]
        lons = [lon for lat, lon in coordenadas]
        centro_lat = sum(lats) / len(lats)
        centro_lon = sum(lons) / len(lons)
        
        for i, (lat, lon) in enumerate(coordenadas):
            # Calcular distancia aproximada
            dist = calcular_distancia_haversine(lat, lon, centro_lat, centro_lon)
            if dist > 50:  # Más de 50km
                puntos_lejanos.add(i)
    
    for i, idx in enumerate(ruta):
        try:
            # Buscar columnas
            cuenta = df.iloc[idx].get('Cuenta', df.iloc[idx].get('cuenta', 'N/A'))
            domicilio_limpio = df.iloc[idx].get('domicilio_limpio', '')
            domicilio_original = df.iloc[idx].get('Domicilio', df.iloc[idx].get('domicilio', 'N/A'))
            
            domicilio = domicilio_limpio if domicilio_limpio else domicilio_original
            
            if idx in puntos_lejanos:
                print(f"  {i+1}. {cuenta} - {domicilio} (lejano)")
            else:
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
    
    print("Verificando conectividad con servicios de mapas...")
    
    for servicio, url in servicios.items():
        try:
            # Verificar DNS primero
            socket.gethostbyname(url.split('//')[1].split('/')[0])
            
            # Verificar conexión HTTP
            response = requests.get(url, timeout=5)
            status = "En línea" if response.status_code == 200 else "Problemas"
            print(f"   {servicio}: {status}")
            
        except socket.gaierror:
            print(f"   {servicio}: Error DNS - Sin conexión a internet")
        except requests.RequestException as e:
            print(f"   {servicio}: Error de conexión - {e}")
        except Exception as e:
            print(f"   {servicio}: Error inesperado - {e}")

def calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia en kilómetros entre dos coordenadas usando la fórmula haversine
    """
    # Radio de la Tierra en kilómetros
    R = 6371.0
    
    # Convertir grados a radianes
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferencias
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    # Fórmula haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distancia = R * c
    return distancia

def obtener_centro_zona(zona: str) -> tuple:
    """
    Devuelve las coordenadas centrales de una zona conocida
    """
    centros_zonas = {
        'guadalajara': (20.6667, -103.3333),
        'zapopan': (20.7167, -103.4000),
        'tonala': (20.6167, -103.2333),
        'tlaquepaque': (20.6333, -103.3167),
        'tlajomulco': (20.4667, -103.4333),
        'jalisco': (20.6667, -103.3333),  
    }
    
    zona_lower = zona.strip().lower()
    for nombre_zona, centro in centros_zonas.items():
        if nombre_zona in zona_lower:
            return centro
    
    # Si no se encuentra, devolver centro de Guadalajara por defecto
    return centros_zonas['guadalajara']