import requests
import pandas as pd
from typing import List, Tuple
from config import STATIC_MAP_URL
import urllib.parse

class GeneradorMapas:
    def __init__(self):
        self.session = requests.Session()
    
    def generar_mapa_estatico(self, coordenadas: List[Tuple[float, float]], 
                            ruta: List[int], output_path: str) -> bool:
        """Genera un mapa estático con la ruta usando OpenStreetMap"""
        try:
            # Crear marcadores
            marcadores = []
            for i, (lat, lon) in enumerate(coordenadas):
                color = "red" if i == 0 else "blue"
                marcador = f"{lon},{lat},red_{i+1}" if i == 0 else f"{lon},{lat},blue_{i+1}"
                marcadores.append(marcador)
            
            # Crear polyline de la ruta
            puntos_ruta = []
            for idx in ruta:
                lat, lon = coordenadas[idx]
                puntos_ruta.append(f"{lon},{lat}")
            
            polyline = ",".join(puntos_ruta)
            
            # Construir URL para el servicio de mapas estáticos
            center_lat, center_lon = coordenadas[0]
            
            params = {
                'center': f"{center_lat},{center_lon}",
                'zoom': '13',
                'size': '800x600',
                'maptype': 'mapnik',
                'markers': '|'.join(marcadores),
                'path': f'color:green|weight:5|{polyline}'
            }
            
            url = f"{STATIC_MAP_URL}?{urllib.parse.urlencode(params)}"
            
            # Descargar imagen
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
            
        except Exception as e:
            print(f"❌ Error generando mapa estático: {e}")
            # Fallback: generar mapa simple con marcadores
            return self.generar_mapa_simple(coordenadas, ruta, output_path)
    
    def generar_mapa_simple(self, coordenadas: List[Tuple[float, float]], 
                          ruta: List[int], output_path: str) -> bool:
        """Genera un mapa simple como fallback"""
        try:
            # Solo marcadores básicos
            marcadores = []
            for i, (lat, lon) in enumerate(coordenadas):
                color = "red" if i == 0 else "blue"
                marcador = f"{lon},{lat},{color}_{i+1}"
                marcadores.append(marcador)
            
            center_lat, center_lon = coordenadas[0]
            
            params = {
                'center': f"{center_lat},{center_lon}",
                'zoom': '13',
                'size': '800x600',
                'maptype': 'mapnik',
                'markers': '|'.join(marcadores)
            }
            
            url = f"{STATIC_MAP_URL}?{urllib.parse.urlencode(params)}"
            
            response = self.session.get(url, timeout=30)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            print(f"❌ Error en fallback de mapa: {e}")
            return False
    
    def generar_enlace_google_maps(self, coordenadas: List[Tuple[float, float]], 
                                 ruta: List[int]) -> str:
        """Genera enlace para abrir en Google Maps app"""
        waypoints = []
        for idx in ruta:
            lat, lon = coordenadas[idx]
            waypoints.append(f"{lat},{lon}")
        
        return f"https://www.google.com/maps/dir/{'/'.join(waypoints)}"
    
    def generar_enlace_osm(self, coordenadas: List[Tuple[float, float]], 
                         ruta: List[int]) -> str:
        """Genera enlace para abrir en apps de OSM"""
        waypoints = []
        for idx in ruta:
            lat, lon = coordenadas[idx]
            waypoints.append(f"{lat},{lon}")
        
        return f"https://www.openstreetmap.org/directions?engine=osrm_car&route={';'.join(waypoints)}"
    
    def generar_csv_ruta(self, df: pd.DataFrame, rutas: List[List[int]], 
                       output_path: str) -> pd.DataFrame:
        """Genera CSV con las rutas optimizadas"""
        datos_salida = []
        
        for i, ruta in enumerate(rutas):
            for orden, idx in enumerate(ruta):
                fila_original = df.iloc[idx].to_dict()
                datos_salida.append({
                    'notificador_id': i + 1,
                    'orden_parada': orden + 1,
                    'id': fila_original['id'],
                    'domicilio_original': fila_original['domicilio'],
                    'domicilio_limpio': fila_original.get('domicilio_limpio', ''),
                    'lat': fila_original['lat'],
                    'lon': fila_original['lon'],
                    'zona': fila_original['zona']
                })
        
        df_salida = pd.DataFrame(datos_salida)
        df_salida.to_csv(output_path, index=False, encoding='utf-8')
        return df_salida