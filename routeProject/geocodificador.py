import pandas as pd
import requests
import time
import re
from typing import List, Tuple, Optional

try:
    from config import NOMINATIM_URL, GEOCODING_DELAY, USER_AGENT
except ImportError:
    # Valores por defecto si config.py no existe
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    GEOCODING_DELAY = 1.0
    USER_AGENT = "OptimizadorRutas/1.0"

class Geocodificador:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
    
    def limpiar_direccion(self, direccion: str) -> str:
        """Limpia y normaliza una dirección"""
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
        """Limpia un campo de texto general"""
        if pd.isna(texto):
            return ""
        texto = str(texto).strip().title()
        texto = re.sub(r'\s+', ' ', texto)
        return texto
    
    def geocodificar_direccion(self, direccion: str, colonia: str = None, cp: str = None, zona: str = None) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Geocodifica una dirección usando Nominatim (OSM) con información adicional"""
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
                query_partes.append("Jalisco")  # ¡CAMBIAR POR TU ESTADO!
            
            # 4. Estado (si no se usó la zona como ciudad)
            if not zona or str(zona).strip().lower() == "foráneos":
                query_partes.append("Jalisco")  # ¡CAMBIAR POR TU ESTADO!
            
            # 5. CP (si existe) - al final
            if cp and pd.notna(cp) and str(cp).strip():
                cp_limpio = str(cp).strip()
                query_partes.append(cp_limpio)
            
            # 6. País
            query_partes.append("México")
            
            query_completa = ', '.join([parte for parte in query_partes if parte])
            
            print(f"🔍 Buscando: {query_completa}")  # Para debugging
            
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
                
                print(f"✅ Encontrado: {display_name} (tipo: {tipo})")
                
                return lat, lon, display_name
            else:
                print(f"⚠️  No se pudo geocodificar: {query_completa}")
                
                # Intentar versión más simple (usando zona como ciudad)
                if zona and str(zona).strip().lower() != "foráneos":
                    query_simple = f"{direccion_limpia}, {zona}, Jalisco, México"
                else:
                    query_simple = f"{direccion_limpia}, Jalisco, México"
                
                print(f"🔄 Intentando versión simple: {query_simple}")
                
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
                    print(f"✅ Encontrado con versión simple: {display_name}")
                    return lat, lon, display_name
                
                return None, None, None
                    
        except Exception as e:
            print(f"❌ Error geocodificando '{direccion}': {e}")
            return None, None, None
    
    def procesar_csv(self, archivo_entrada: str, archivo_salida: str) -> pd.DataFrame:
        """Procesa un archivo CSV completo con información adicional"""
        print("📖 Leyendo archivo CSV...")
        df = pd.read_csv(archivo_entrada)
        
        # Estandarizar nombres de columnas
        df.columns = df.columns.str.strip().str.title()
        
        # Verificar columnas disponibles
        columnas = df.columns.str.lower().tolist()
        tiene_colonia = 'colonia' in columnas
        tiene_cp = any(col in columnas for col in ['cp', 'codigo postal', 'código postal'])
        
        print(f"🔍 Columnas detectadas: {', '.join(df.columns)}")
        if tiene_colonia:
            print("✅ Colonia detectada")
        if tiene_cp:
            print("✅ Código Postal detectado")
        
        print("🧹 Limpiando y geocodificando direcciones...")
        
        resultados = []
        for i, fila in df.iterrows():
            if i > 0:
                time.sleep(GEOCODING_DELAY)
            
            # Extraer información adicional
            colonia = fila['Colonia'] if tiene_colonia else None
            cp = fila['Cp'] if tiene_cp else None
            
            resultado = self.geocodificar_direccion(fila['Domicilio'], colonia, cp)
            resultados.append(resultado)
            
            if i % 5 == 0 and i > 0:
                print(f"📍 Geocodificadas {i}/{len(df)} direcciones...")
        
        # Agregar resultados al DataFrame
        df[['lat', 'lon', 'domicilio_limpio']] = resultados
        df_limpio = df.dropna(subset=['lat', 'lon']).copy()
        
        # Guardar también los que fallaron para revisión
        df_fallidos = df[df['lat'].isna()].copy()
        if not df_fallidos.empty:
            archivo_fallidos = archivo_salida.replace('.csv', '_fallidos.csv')
            df_fallidos.to_csv(archivo_fallidos, index=False, encoding='utf-8')
            print(f"📝 {len(df_fallidos)} direcciones no geocodificadas guardadas en: {archivo_fallidos}")
            
            # Mostrar algunas direcciones que fallaron
            print("\n⚠️  Algunas direcciones que no se pudieron geocodificar:")
            for i, fila in df_fallidos.head(5).iterrows():
                print(f"   - {fila['Domicilio']}")
            if len(df_fallidos) > 5:
                print(f"   - ... y {len(df_fallidos) - 5} más")
        
        # Guardar resultados exitosos
        df_limpio.to_csv(archivo_salida, index=False, encoding='utf-8')
        
        print(f"\n✅ Geocodificación completada. {len(df_limpio)}/{len(df)} direcciones procesadas exitosamente.")
        print(f"💾 Resultados guardados en: {archivo_salida}")
        
        if not df_fallidos.empty:
            print(f"💾 Direcciones fallidas guardadas en: {archivo_fallidos}")
            print("💡 Sugerencia: Revise las direcciones fallidas y agregue Colonia o CP para mejor precisión")
        
        return df_limpio

def geocodificar_lote(self, df: pd.DataFrame) -> List[Tuple[Optional[float], Optional[float], Optional[str]]]:
    """Geocodifica un lote de direcciones respetando los límites de OSM"""
    resultados = []
    
    # Verificar columnas disponibles
    columnas = df.columns.str.lower().tolist()
    tiene_colonia = any(col in columnas for col in ['colonia', 'colonias'])
    tiene_cp = any(col in columnas for col in ['cp', 'codigo postal', 'código postal', 'zip', 'zip code'])
    tiene_zona = 'zona' in columnas
    
    print(f"🔍 Columnas detectadas: {', '.join(df.columns)}")
    if tiene_colonia:
        print("✅ Colonia detectada")
    if tiene_cp:
        print("✅ Código Postal detectado")
    if tiene_zona:
        print("✅ Zona detectada")
    
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
            print(f"📍 Geocodificadas {i}/{len(df)} direcciones...")
    
    return resultados

# Función adicional para uso directo del script
def procesar_archivo_csv(archivo_entrada: str, archivo_salida: str = None):
    """Función conveniente para procesar un archivo CSV directamente"""
    if archivo_salida is None:
        archivo_salida = archivo_entrada.replace('.csv', '_geocodificado.csv')
    
    geocodificador = Geocodificador()
    return geocodificador.procesar_csv(archivo_entrada, archivo_salida)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Geocodificador de direcciones usando OpenStreetMap')
    parser.add_argument('--entrada', required=True, help='Archivo CSV de entrada')
    parser.add_argument('--salida', help='Archivo CSV de salida (opcional)')
    
    args = parser.parse_args()
    
    procesar_archivo_csv(args.entrada, args.salida)