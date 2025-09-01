import requests
import pandas as pd
from typing import List, Tuple
import urllib.parse
import os
import time
import math

class OSMMapGenerator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'OptimizadorRutas/1.0'})
    
    def generar_mapa_estatico(self, coordenadas: List[Tuple[float, float]], 
                            ruta: List[int], output_path: str) -> bool:
        """Genera mapa estático usando OpenStreetMap - Versión robusta"""
        try:
            print("🗺️  Intentando generar mapa estático OSM...")
            
            # Intentar con el servicio principal
            if self._generar_con_osm_directo(coordenadas, ruta, output_path):
                return True
                
            # Si falla, intentar con método alternativo
            if self._generar_mapa_alternativo(coordenadas, ruta, output_path):
                return True
                
            # Como último recurso, generar HTML
            return self._generar_mapa_html(coordenadas, ruta, output_path)
            
        except Exception as e:
            print(f"❌ Error generando mapa: {e}")
            return self._generar_archivo_coordenadas(coordenadas, ruta, output_path)
    
    def _generar_con_osm_directo(self, coordenadas: List[Tuple[float, float]], 
                               ruta: List[int], output_path: str) -> bool:
        """Intenta con el servicio directo de OSM"""
        try:
            # Preparar marcadores
            marcadores = []
            for i, (lat, lon) in enumerate(coordenadas):
                color = "red" if i == 0 else "blue"
                marcadores.append(f"{lon},{lat},{$color}_{i+1}")
            
            # Preparar polyline de la ruta
            puntos_ruta = []
            for idx in ruta:
                lat, lon = coordenadas[idx]
                puntos_ruta.append(f"{lon},{lat}")
            
            polyline = ";".join(puntos_ruta)
            
            # Parámetros para el mapa estático
            center_lat, center_lon = self._calcular_centro(coordenadas)
            
            params = {
                'center': f"{center_lat},{center_lon}",
                'zoom': '13',
                'size': '800x600',
                'maptype': 'mapnik',
                'markers': '|'.join(marcadores[:10]),  # Limitar marcadores
                'path': f'color:green|weight:4|{polyline}'
            }
            
            url = f"https://staticmap.openstreetmap.de/staticmap.php?{urllib.parse.urlencode(params)}"
            print(f"🌍 URL generada: {url[:100]}...")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Mapa OSM generado: {output_path}")
            return True
            
        except Exception as e:
            print(f"⚠️  Servicio OSM directo falló: {e}")
            return False
    
    def _generar_mapa_alternativo(self, coordenadas: List[Tuple[float, float]], 
                                ruta: List[int], output_path: str) -> bool:
        """Método alternativo para generar mapas"""
        try:
            # Usar un servicio de tiles directamente
            import matplotlib.pyplot as plt
            from matplotlib.offsetbox import OffsetImage, AnnotationBbox
            import matplotlib.image as mpimg
            
            # Crear figura
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Extraer coordenadas
            lons = [lon for lat, lon in coordenadas]
            lats = [lat for lat, lon in coordenadas]
            
            # Calcular bounds para el mapa
            margin = 0.01
            lon_min, lon_max = min(lons) - margin, max(lons) + margin
            lat_min, lat_max = min(lats) - margin, max(lats) + margin
            
            # Configurar ejes
            ax.set_xlim(lon_min, lon_max)
            ax.set_ylim(lat_min, lat_max)
            ax.set_aspect('equal')
            
            # Dibujar ruta
            ruta_lons = [lons[i] for i in ruta]
            ruta_lats = [lats[i] for i in ruta]
            ax.plot(ruta_lons, ruta_lats, 'r-', linewidth=2, label='Ruta optimizada')
            
            # Marcar puntos
            ax.scatter(lons, lats, c='blue', s=50, alpha=0.7, label='Puntos')
            
            # Marcar inicio y fin
            ax.scatter(lons[0], lats[0], c='green', s=200, marker='o', label='Inicio')
            ax.scatter(lons[-1], lats[-1], c='red', s=200, marker='s', label='Fin')
            
            # Añadir labels
            for i, (lat, lon) in enumerate(coordenadas):
                if i == 0 or i == len(coordenadas)-1 or i % 5 == 0:
                    ax.annotate(f'{i+1}', (lon, lat), xytext=(5, 5), 
                              textcoords='offset points', fontsize=8)
            
            ax.set_xlabel('Longitud')
            ax.set_ylabel('Latitud')
            ax.set_title('Ruta Optimizada - OpenStreetMap')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Mapa alternativo generado: {output_path}")
            return True
            
        except ImportError:
            print("⚠️  matplotlib no disponible para mapa alternativo")
            return False
        except Exception as e:
            print(f"⚠️  Mapa alternativo falló: {e}")
            return False
    
    def _generar_mapa_html(self, coordenadas: List[Tuple[float, float]], 
                         ruta: List[int], output_path: str) -> bool:
        """Genera mapa HTML interactivo con Leaflet"""
        try:
            html_path = output_path.replace('.png', '.html')
            
            # Crear contenido HTML
            html_content = self._crear_html_leaflet(coordenadas, ruta)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Mapa HTML generado: {html_path}")
            print("💡 Abre este archivo en tu navegador para ver el mapa interactivo")
            return True
            
        except Exception as e:
            print(f"❌ Error generando HTML: {e}")
            return False
    
    def _crear_html_leaflet(self, coordenadas: List[Tuple[float, float]], 
                          ruta: List[int]) -> str:
        """Crea HTML con Leaflet para mapa interactivo"""
        # Generar JavaScript para marcadores
        marcadores_js = []
        for i, (lat, lon) in enumerate(coordenadas):
            color = "green" if i == 0 else "red" if i == len(coordenadas)-1 else "blue"
            marcadores_js.append(f"""
                L.marker([{lat}, {lon}], {{
                    icon: L.icon({{
                        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34]
                    }})
                }}).addTo(map).bindPopup('Punto {i+1}<br>Lat: {lat:.6f}<br>Lon: {lon:.6f}');
            """)
        
        # Generar polyline de la ruta
        polyline_points = ", ".join([f"[{lat}, {lon}]" for lat, lon in coordenadas])
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Ruta Optimizada - OpenStreetMap</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <style>
        #map {{ height: 600px; width: 100%; }}
        body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
        .info {{ padding: 10px; background: white; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🗺️ Ruta Optimizada - OpenStreetMap</h1>
    <div class="info">
        <strong>Puntos:</strong> {len(coordenadas)} | 
        <strong>Ruta:</strong> {len(ruta)} paradas
    </div>
    <div id="map"></div>
    
    <script>
        // Inicializar mapa
        var map = L.map('map').setView([{coordenadas[0][0]}, {coordenadas[0][1]}], 13);
        
        // Capa de OpenStreetMap
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 18
        }}).addTo(map);
        
        // Agregar marcadores
        {''.join(marcadores_js)}
        
        // Agregar polyline de la ruta
        var polyline = L.polyline([{polyline_points}], {{
            color: 'blue',
            weight: 4,
            opacity: 0.7,
            smoothFactor: 1
        }}).addTo(map);
        
        // Ajustar vista para mostrar toda la ruta
        map.fitBounds(polyline.getBounds());
    </script>
</body>
</html>"""
    
    def _generar_archivo_coordenadas(self, coordenadas: List[Tuple[float, float]], 
                                  ruta: List[int], output_path: str) -> bool:
        """Genera archivo de texto con coordenadas como último recurso"""
        try:
            txt_path = output_path.replace('.png', '.txt')
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write("RUTA OPTIMIZADA - COORDENADAS\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("ORDEN DE VISITA:\n")
                f.write("-" * 30 + "\n")
                for i, idx in enumerate(ruta):
                    lat, lon = coordenadas[idx]
                    f.write(f"{i+1}. Lat: {lat:.6f}, Lon: {lon:.6f}\n")
                
                f.write("\nTODAS LAS COORDENADAS:\n")
                f.write("-" * 30 + "\n")
                for i, (lat, lon) in enumerate(coordenadas):
                    f.write(f"{i+1}. {lat:.6f}, {lon:.6f}\n")
                
                f.write(f"\nEnlace Google Maps:\n")
                f.write(self.generar_enlace_google_maps(coordenadas, ruta))
            
            print(f"✅ Archivo de coordenadas generado: {txt_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error crítico: No se pudo generar ningún output - {e}")
            return False
    
    def generar_enlace_google_maps(self, coordenadas: List[Tuple[float, float]], 
                                 ruta: List[int]) -> str:
        """Genera enlace para Google Maps (SIEMPRE funciona)"""
        try:
            waypoints = []
            for idx in ruta[:8]:  # Google limita a 8 waypoints
                lat, lon = coordenadas[idx]
                waypoints.append(f"{lat},{lon}")
            
            return f"https://www.google.com/maps/dir/{'/'.join(waypoints)}"
            
        except Exception as e:
            print(f"⚠️  Error generando enlace Google: {e}")
            return "https://www.google.com/maps"
    
    def _calcular_centro(self, coordenadas: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calcula el centro de las coordenadas"""
        if not coordenadas:
            return 0, 0
        lats = [lat for lat, lon in coordenadas]
        lons = [lon for lat, lon in coordenadas]
        return sum(lats)/len(lats), sum(lons)/len(lons)

# Función de prueba
def probar_generador():
    print("🧪 Probando generador OSM...")
    
    # Coordenadas de ejemplo en Guadalajara
    coordenadas = [
        (20.6667, -103.3333),
        (20.6777, -103.3444), 
        (20.6888, -103.3555),
        (20.6999, -103.3666)
    ]
    ruta = [0, 2, 1, 3]
    
    generador = OSMMapGenerator()
    
    # Probar generación de mapa
    generador.generar_mapa_estatico(coordenadas, ruta, "prueba_mapa.png")
    
    # Probar enlace Google Maps
    enlace = generador.generar_enlace_google_maps(coordenadas, ruta)
    print(f"🔗 Enlace Google Maps: {enlace}")

if __name__ == "__main__":
    probar_generador()