# routeProject/generador_mapas.py
import pandas as pd
from typing import List, Tuple
import matplotlib.pyplot as plt

class GeneradorMapas:
    def __init__(self):
        pass
    
    def generar_mapa_estatico(self, coordenadas: List[Tuple[float, float]], 
                            ruta: List[int], output_path: str) -> bool:
        """Genera un mapa estático usando matplotlib como alternativa"""
        try:
            print("🗺️  Generando mapa estático con matplotlib...")
            
            # Extraer coordenadas en el orden de la ruta
            lats = [coordenadas[idx][0] for idx in ruta]
            lons = [coordenadas[idx][1] for idx in ruta]
            
            # Crear figura
            plt.figure(figsize=(12, 8))
            
            # Graficar la ruta
            plt.plot(lons, lats, 'o-', color='#3498db', linewidth=3, markersize=8, 
                    markerfacecolor='white', markeredgewidth=2, markeredgecolor='#3498db')
            
            # Marcar puntos importantes
            plt.plot(lons[0], lats[0], 'o', color='#2ecc71', markersize=12, 
                    label='Inicio', markerfacecolor='white', markeredgewidth=3)
            plt.plot(lons[-1], lats[-1], 'o', color='#e74c3c', markersize=12, 
                    label='Fin', markerfacecolor='white', markeredgewidth=3)
            
            # Añadir números a los puntos
            for i, (lat, lon) in enumerate(zip(lats, lons)):
                plt.annotate(str(i+1), (lon, lat), xytext=(5, 5), 
                           textcoords='offset points', fontsize=9, 
                           fontweight='bold', color='#2c3e50')
            
            # Configuración del gráfico
            plt.xlabel('Longitud', fontsize=12, fontweight='bold')
            plt.ylabel('Latitud', fontsize=12, fontweight='bold')
            plt.title('Ruta Optimizada de Entrega', fontsize=16, fontweight='bold', pad=20)
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Ajustar márgenes
            plt.tight_layout()
            
            # Guardar la imagen
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"Mapa generado exitosamente: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generando mapa con matplotlib: {e}")
            return self.generar_mapa_simple(coordenadas, ruta, output_path)
    
    def generar_mapa_simple(self, coordenadas: List[Tuple[float, float]], 
                          ruta: List[int], output_path: str) -> bool:
        try:
            print("Generando mapa simple alternativo...")
            return self._generar_mapa_texto(coordenadas, ruta, output_path)
        except Exception as e:
            print(f"Error en fallback de mapa: {e}")
            return False
    
    def _generar_mapa_texto(self, coordenadas: List[Tuple[float, float]], 
                          ruta: List[int], output_path: str) -> bool:
        #Genera un archivo de texto con las coordenadas
        try:
            txt_path = output_path.replace('.png', '.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write("RUTA OPTIMIZADA - COORDENADAS\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("ORDEN DE VISITA:\n")
                f.write("-" * 20 + "\n")
                for i, idx in enumerate(ruta):
                    lat, lon = coordenadas[idx]
                    f.write(f"{i+1}. Lat: {lat:.6f}, Lon: {lon:.6f}\n")
                
                f.write(f"\nEnlace Google Maps:\n")
                f.write(self.generar_enlace_google_maps(coordenadas, ruta))
                f.write(f"\n\nEnlace OSM:\n")
                f.write(self.generar_enlace_osm(coordenadas, ruta))
            
            print(f"Archivo de coordenadas generado: {txt_path}")
            return True
            
        except Exception as e:
            print(f"Error crítico generando archivo: {e}")
            return False
    
    def generar_enlace_google_maps(self, coordenadas: List[Tuple[float, float]], 
                                 ruta: List[int]) -> str:
        #Genera enlace para abrir en Google Maps app
        waypoints = []
        for idx in ruta:
            lat, lon = coordenadas[idx]
            waypoints.append(f"{lat},{lon}")
        
        return f"https://www.google.com/maps/dir/{'/'.join(waypoints)}"
    
    def generar_enlace_osm(self, coordenadas: List[Tuple[float, float]], 
                         ruta: List[int]) -> str:
        #Genera enlace para abrir en apps de OSM
        waypoints = []
        for idx in ruta:
            lat, lon = coordenadas[idx]
            waypoints.append(f"{lat},{lon}")
        
        return f"https://www.openstreetmap.org/directions?engine=osrm_car&route={';'.join(waypoints)}"
    
    def generar_csv_ruta(self, df: pd.DataFrame, rutas: List[List[int]], 
                       output_path: str) -> pd.DataFrame:
        #Genera CSV con las rutas optimizadas
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