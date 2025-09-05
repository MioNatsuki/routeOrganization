#routeproject/geocodificador.py
import pandas as pd
import requests
import time
import re
from typing import List, Tuple, Optional
from math import radians, sin, cos, sqrt, atan2

try:
    from config import NOMINATIM_URL, GEOCODING_DELAY, USER_AGENT
except ImportError:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    GEOCODING_DELAY = 1.0
    USER_AGENT = "OptimizadorRutas/1.0"

class Geocodificador:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
        # Centros de zonas predefinidos (zonas predefinidas para pensiones)
        self.centros_zonas = {
            'guadalajara': (20.6667, -103.3333),
            'zapopan': (20.7167, -103.4000),
            'tonala': (20.6167, -103.2333),
            'tlaquepaque': (20.6333, -103.3167),
            'tlajomulco': (20.4667, -103.4333)
        }
    
    def _calcular_distancia_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia en km usando fórmula haversine"""
        R = 6371  # Radio de la Tierra en km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _esta_dentro_radio_permitido(self, lat: float, lon: float, zona: str) -> Tuple[bool, float]:
        #Verifica si las coordenadas están dentro del radio de 25km del centro de la zona
        if not zona or pd.isna(zona):
            return True, 0.0
        
        zona_limpia = str(zona).strip().lower()
        
        # Buscar centro de la zona (coincidencia parcial)
        centro_encontrado = None
        for nombre_zona, centro in self.centros_zonas.items():
            if nombre_zona in zona_limpia:
                centro_encontrado = centro
                break
        
        if not centro_encontrado:
            # Si no se encuentra la zona, usar centro por defecto de Guadalajara
            centro_encontrado = self.centros_zonas['guadalajara']
        
        centro_lat, centro_lon = centro_encontrado
        distancia = self._calcular_distancia_km(lat, lon, centro_lat, centro_lon)
        
        return distancia <= 25, distancia
    
    def limpiar_direccion(self, direccion: str) -> str:
        if pd.isna(direccion):
            return ""
        
        # Limpieza básica
        direccion_limpia = direccion.strip().title()
        
        # Remover múltiples espacios y caracteres especiales
        direccion_limpia = re.sub(r'\s+', ' ', direccion_limpia)
        direccion_limpia = re.sub(r'[^\w\s,#.-]', '', direccion_limpia)
        
        # Correcciones comunes más específicas
        correcciones = {
            'Avenida ': 'Av. ',
            'Avenida': 'Av.',
            'Calle ': 'Cll. ',
            'Calle': 'Cll.',
            'Carrera ': 'Cra. ',
            'Carrera': 'Cra.',
            'Numero': 'No.',
            'Número': 'No.',
            'Colonia': 'Col.',
            'Col ': 'Col. ',
            ' #': ' No. ',
        }
        
        for viejo, nuevo in correcciones.items():
            direccion_limpia = direccion_limpia.replace(viejo, nuevo)
        
        return direccion_limpia
    
    def limpiar_campo(self, texto) -> str:
        if pd.isna(texto):
            return ""
        texto = str(texto).strip().title()
        texto = re.sub(r'\s+', ' ', texto)
        return texto
    
    def geocodificar_direccion(self, direccion: str, colonia: str = None, cp: str = None, zona: str = None) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        direccion_limpia = self.limpiar_direccion(direccion)
        
        if not direccion_limpia:
            return None, None, None
        
        try:
            # Construir query en formato MEXICANO para OSM
            query_partes = []
            
            # 1. Primero la dirección principal
            query_partes.append(direccion_limpia)
            
            # 2. Luego la colonia (si existe)
            if colonia and pd.notna(colonia) and str(colonia).strip():
                colonia_limpia = self.limpiar_campo(colonia)
                query_partes.append(colonia_limpia)
            
            # 3. Usar la ZONA como ciudad (excepto si es "Foráneos")
            if zona and pd.notna(zona) and str(zona).strip().lower() != "foráneos":
                zona_limpia = self.limpiar_campo(zona)
                query_partes.append(zona_limpia)
            else:
                # Si es Foráneos o no hay zona, usar estado directamente
                query_partes.append("Jalisco")  # Se puede cambiar por cualquier Estado
            
            # 4. Estado (si no se usó la zona como ciudad)
            if not zona or str(zona).strip().lower() == "foráneos":
                query_partes.append("Jalisco")  # Se puede cambiar por cualquier Estado
            
            # 5. CP (si existe) - al final
            if cp and pd.notna(cp) and str(cp).strip():
                cp_limpio = str(cp).strip()
                query_partes.append(cp_limpio)
            
            # 6. País
            query_partes.append("México")
            
            query_completa = ', '.join([parte for parte in query_partes if parte])
            
            print(f"Buscando: {query_completa}")  # Para debugging
            
            params = {
                'q': query_completa,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'mx',
                'addressdetails': 1
            }
            
            response = self.session.get(NOMINATIM_URL, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                display_name = data[0]['display_name']
                tipo = data[0].get('type', 'desconocido')
                
                print(f"Encontrado: {display_name} (tipo: {tipo})")
                
                dentro_radio, distancia = self._esta_dentro_radio_permitido(lat, lon, zona)
                if not dentro_radio:
                    print(f"Coordenada fuera de radio: {distancia:.1f} km de centro de {zona}")
                    return None, None, f"NO LOCALIZABLE - Fuera de radio ({distancia:.1f} km)"
                
                return lat, lon, display_name
            else:
                print(f"No se pudo geocodificar: {query_completa}")
                
                # Intentar versión más simple (usando zona como ciudad)
                if zona and str(zona).strip().lower() != "foráneos":
                    query_simple = f"{direccion_limpia}, {zona}, Jalisco, México"
                else:
                    query_simple = f"{direccion_limpia}, Jalisco, México"
                
                print(f"Intentando versión simple: {query_simple}")
                
                params_simple = {
                    'q': query_simple,
                    'format': 'json',
                    'limit': 1,
                    'countrycodes': 'mx'
                }
                
                response_simple = self.session.get(NOMINATIM_URL, params=params_simple, timeout=15)
                data_simple = response_simple.json()
                
                if data_simple:
                    lat = float(data_simple[0]['lat'])
                    lon = float(data_simple[0]['lon'])
                    display_name = data_simple[0]['display_name']
                    print(f"Encontrado con versión simple: {display_name}")
                    return lat, lon, display_name
                
                return None, None, None
                    
        except Exception as e:
            print(f"Error geocodificando '{direccion}': {e}")
            return None, None, None
    
    def procesar_csv(self, archivo_entrada: str, archivo_salida: str) -> pd.DataFrame:
        print("Leyendo archivo CSV...")
        df = pd.read_csv(archivo_entrada)
        
        # Estandarizar nombres de columnas
        df.columns = df.columns.str.strip().str.title()
        
        # Verificar columnas disponibles
        columnas = df.columns.str.lower().tolist()
        tiene_colonia = 'colonia' in columnas
        tiene_cp = any(col in columnas for col in ['cp', 'codigo postal', 'código postal'])
        tiene_zona = 'zona' in columnas
        
        print(f"Columnas detectadas: {', '.join(df.columns)}")
        if tiene_colonia:
            print("Colonia detectada")
        if tiene_cp:
            print("Código Postal detectado")
        if tiene_zona:
            print("Zona detectada")
        
        print("Limpiando y geocodificando direcciones...")
        
        resultados = []
        for i, fila in df.iterrows():
            if i > 0:
                time.sleep(GEOCODING_DELAY)
            
            # Extraer información adicional
            colonia = fila['Colonia'] if tiene_colonia else None
            cp = fila['Cp'] if tiene_cp else None
            zona = fila['Zona'] if tiene_zona else None
            
            resultado = self.geocodificar_direccion(fila['Domicilio'], colonia, cp, zona)
            resultados.append(resultado)
            
            if i % 5 == 0 and i > 0:
                print(f"Geocodificadas {i}/{len(df)} direcciones...")
        
        # Agregar resultados al DataFrame
        df[['lat', 'lon', 'domicilio_limpio']] = resultados
        
        # Clasificar resultados en tres categorías
        df['estado_geocodificacion'] = 'exitoso'
        
        # 1. Fallos de geocodificación (coordenadas nulas)
        mask_fallos = df['lat'].isna() | df['lon'].isna()
        df.loc[mask_fallos, 'estado_geocodificacion'] = 'fallo_geocodificacion'
        
        # 2. Fuera de radio (NO LOCALIZABLE en domicilio_limpio)
        mask_fuera_radio = df['domicilio_limpio'].str.contains('NO LOCALIZABLE', na=False)
        df.loc[mask_fuera_radio, 'estado_geocodificacion'] = 'fuera_radio'
        
        # 3. Éxitos (el resto)
        mask_exitosos = (~mask_fallos) & (~mask_fuera_radio)
        df.loc[mask_exitosos, 'estado_geocodificacion'] = 'exitoso'
        
        # Guardar TODOS los fallos en un archivo unificado
        df_fallidos = df[df['estado_geocodificacion'] != 'exitoso'].copy()
        if not df_fallidos.empty:
            archivo_fallidos = archivo_salida.replace('.csv', '_fallidos.csv')
            
            # Agregar columna de razón del fallo
            df_fallidos['razon_fallo'] = 'desconocida'
            df_fallidos.loc[df_fallidos['estado_geocodificacion'] == 'fallo_geocodificacion', 'razon_fallo'] = 'No se pudo geocodificar'
            df_fallidos.loc[df_fallidos['estado_geocodificacion'] == 'fuera_radio', 'razon_fallo'] = 'Fuera del radio de 40km'
            
            df_fallidos.to_csv(archivo_fallidos, index=False, encoding='utf-8')
            print(f"{len(df_fallidos)} direcciones no localizables guardadas en: {archivo_fallidos}")
            
            # Mostrar estadísticas
            fallos_geocodificacion = len(df_fallidos[df_fallidos['estado_geocodificacion'] == 'fallo_geocodificacion'])
            fuera_radio = len(df_fallidos[df_fallidos['estado_geocodificacion'] == 'fuera_radio'])
            
            print(f"   - {fallos_geocodificacion} fallos de geocodificación")
            print(f"   - {fuera_radio} direcciones fuera del radio permitido")
        
        # Guardar solo los resultados exitosos
        df_exitosos = df[df['estado_geocodificacion'] == 'exitoso'].copy()
        df_exitosos.to_csv(archivo_salida, index=False, encoding='utf-8')
        
        print(f"\nGeocodificación completada.")
        print(f"   ✓ {len(df_exitosos)} direcciones válidas y dentro del radio")
        print(f"   ✗ {len(df_fallidos)} direcciones con problemas")
        print(f"   Tasa de éxito: {(len(df_exitosos)/len(df)*100):.1f}%")
        print(f"   Resultados válidos guardados en: {archivo_salida}")
        
        if not df_fallidos.empty:
            print(f"   Reporte de problemas en: {archivo_fallidos}")
            print("\n  Sugerencias:")
            print("   - Revisar las direcciones fallidas en el archivo de reporte")
            print("   - Para 'Fuera de radio': verificar que la zona sea correcta")
            print("   - Para 'No geocodificado': agregar Colonia o CP para mejor precisión")
        
        return df_exitosos

#Cuando se hace por cuentas x notificador
def geocodificar_lote(self, df: pd.DataFrame) -> List[Tuple[Optional[float], Optional[float], Optional[str]]]:
    resultados = []
    
    # Verificar columnas disponibles
    columnas = df.columns.str.lower().tolist()
    tiene_colonia = any(col in columnas for col in ['colonia', 'colonias'])
    tiene_cp = any(col in columnas for col in ['cp', 'codigo postal', 'código postal', 'zip', 'zip code'])
    tiene_zona = 'zona' in columnas
    
    print(f"Columnas detectadas: {', '.join(df.columns)}")
    if tiene_colonia:
        print("Colonia detectada")
    if tiene_cp:
        print("Código Postal detectado")
    if tiene_zona:
        print("Zona detectada")
    
    for i, fila in df.iterrows():
        if i > 0:
            time.sleep(GEOCODING_DELAY)
        
        # Extraer información adicional
        colonia = fila['Colonia'] if tiene_colonia and 'Colonia' in df.columns else None
        if not colonia and tiene_colonia:
            for col in df.columns:
                if 'colonia' in col.lower():
                    colonia = fila[col]
                    break
        
        cp = fila['CP'] if tiene_cp and 'CP' in df.columns else None
        if not cp and tiene_cp:
            for col in df.columns:
                if any(nombre in col.lower() for nombre in ['cp', 'codigo postal', 'zip']):
                    cp = fila[col]
                    break
        
        zona = fila['Zona'] if tiene_zona and 'Zona' in df.columns else None
        if not zona and tiene_zona:
            for col in df.columns:
                if 'zona' in col.lower():
                    zona = fila[col]
                    break
        
        resultado = self.geocodificar_direccion(fila['Domicilio'], colonia, cp, zona)
        resultados.append(resultado)
        
        if i % 5 == 0 and i > 0:
            print(f"Geocodificadas {i}/{len(df)} direcciones...")
    
    return resultados