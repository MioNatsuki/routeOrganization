import pandas as pd
from geocodificador import Geocodificador
from optimizador_rutas import OptimizadorRutas
from generador_mapas import GeneradorMapas
from utils import crear_directorios, filtrar_por_zona, dividir_por_notificadores, mostrar_ruta
import argparse
from typing import List
import os

def main():
    crear_directorios()
    
    # Inicializar componentes
    geocodificador = Geocodificador()
    optimizador = OptimizadorRutas()
    generador_mapas = GeneradorMapas()
    
    # Procesar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Optimizador de Rutas de Entrega')
    parser.add_argument('--archivo', required=True, help='Archivo CSV de entrada')
    parser.add_argument('--zona', required=True, help='Zona a optimizar')
    parser.add_argument('--cuentas-por-notificador', type=int, default=0, 
                       help='Número de cuentas por notificador (0 para ruta única)')
    
    args = parser.parse_args()
    
    try:
        print("🚀 Iniciando optimización de rutas con OpenStreetMap...")
        print(f"📁 Archivo: {args.archivo}")
        print(f"📍 Zona: {args.zona}")
        
        if args.cuentas_por_notificador > 0:
            print(f"👥 Cuentas por notificador: {args.cuentas_por_notificador}")
        else:
            print(f"👥 Modo: Ruta única para toda la zona")
        
        # Filtro por zona
        print(f"\n📋 Filtrando datos para la zona: {args.zona}...")
        df_original = pd.read_csv(args.archivo)
        df_zona_filtrado = filtrar_por_zona(df_original, args.zona)
        
        if df_zona_filtrado.empty:
            print(f"❌ No se encontraron datos para la zona: {args.zona}")
            print("💡 Verifica que el nombre de la zona coincida exactamente")
            return
        
        print(f"📍 {len(df_zona_filtrado)} domicilios encontrados en {args.zona}")
        
        # Guardar CSV filtrado temporalmente
        archivo_filtrado = f"datos/salida/filtrado_{args.zona}.csv"
        df_zona_filtrado.to_csv(archivo_filtrado, index=False, encoding='utf-8')
        print(f"💾 Datos filtrados guardados en: {archivo_filtrado}")
        
        # Geocodificador de zona filtrada
        archivo_geocodificado = f"datos/salida/geocodificado_{args.zona}.csv"
        df = geocodificador.procesar_csv(archivo_filtrado, archivo_geocodificado)
        
        # Optimizar rutas
        if args.cuentas_por_notificador > 0:
            # Modo múltiples notificadores
            chunks = dividir_por_notificadores(df, args.cuentas_por_notificador)
            todas_rutas = []
            datos_rutas = []  # Para el CSV final
            
            print(f"\n🛣️  Generando {len(chunks)} rutas para {len(chunks)} notificadores...")
            
            for i, chunk in enumerate(chunks):
                print(f"\n📋 Procesando Notificador {i+1} ({len(chunk)} cuentas)...")
                
                # Optimizar ruta para este chunk
                try:
                    rutas_chunk = optimizador.optimizar_ruta(chunk, 1)  # 1 vehículo por chunk
                    ruta_optimizada = rutas_chunk[0] if rutas_chunk else list(range(len(chunk)))
                    
                    # Mostrar resultados por notificador
                    mostrar_ruta(ruta_optimizada, chunk)
                    
                    # Guardar datos para CSV
                    for orden, idx in enumerate(ruta_optimizada):
                        fila = chunk.iloc[idx].to_dict()
                        datos_rutas.append({
                            'notificador_id': i + 1,
                            'orden_parada': orden + 1,
                            'ID': fila.get('ID', ''),
                            'Cuenta': fila.get('Cuenta', ''),
                            'Domicilio_Original': fila.get('Domicilio', ''),
                            'Domicilio_Limpio': fila.get('domicilio_limpio', ''),
                            'Zona': fila.get('Zona', ''),
                            'lat': fila.get('lat', ''),
                            'lon': fila.get('lon', '')
                        })
                    
                    todas_rutas.append((chunk, ruta_optimizada))
                    
                    # Generar mapa para esta ruta
                    coordenadas = list(zip(chunk['lat'], chunk['lon']))
                    archivo_mapa = f"mapas/ruta_{args.zona}_notificador_{i+1}.png"
                    if generador_mapas.generar_mapa_estatico(coordenadas, ruta_optimizada, archivo_mapa):
                        print(f"🗺️  Mapa generado: {archivo_mapa}")
                    
                    # Generar enlaces móviles
                    enlace_google = generador_mapas.generar_enlace_google_maps(coordenadas, ruta_optimizada)
                    enlace_osm = generador_mapas.generar_enlace_osm(coordenadas, ruta_optimizada)
                    
                    print(f"📱 Enlace Google Maps: {enlace_google}")
                    print(f"🗺️  Enlace OSM: {enlace_osm}")
                    
                except Exception as e:
                    print(f"❌ Error optimizando ruta para notificador {i+1}: {e}")
                    continue
            
            # Guardar CSV con todas las rutas
            if datos_rutas:
                df_rutas = pd.DataFrame(datos_rutas)
                archivo_rutas = f"datos/salida/rutas_{args.zona}_{len(chunks)}notificadores.csv"
                df_rutas.to_csv(archivo_rutas, index=False, encoding='utf-8')
                print(f"\n💾 CSV de todas las rutas guardado: {archivo_rutas}")
        
        else:
            # Modo ruta única
            print(f"\n🛣️  Optimizando ruta única para {len(df)} cuentas...")
            
            try:
                rutas_optimizadas = optimizador.optimizar_ruta(df, 1)
                ruta_optimizada = rutas_optimizadas[0] if rutas_optimizadas else list(range(len(df)))
                
                # Mostrar resultados
                mostrar_ruta(ruta_optimizada, df)
                
                # Guardar CSV
                datos_ruta = []
                for orden, idx in enumerate(ruta_optimizada):
                    fila = df.iloc[idx].to_dict()
                    datos_ruta.append({
                        'orden_parada': orden + 1,
                        'ID': fila.get('ID', ''),
                        'Cuenta': fila.get('Cuenta', ''),
                        'Domicilio_Original': fila.get('Domicilio', ''),
                        'Domicilio_Limpio': fila.get('domicilio_limpio', ''),
                        'Zona': fila.get('Zona', ''),
                        'lat': fila.get('lat', ''),
                        'lon': fila.get('lon', '')
                    })
                
                df_ruta = pd.DataFrame(datos_ruta)
                archivo_rutas = f"datos/salida/ruta_unica_{args.zona}.csv"
                df_ruta.to_csv(archivo_rutas, index=False, encoding='utf-8')
                print(f"💾 CSV de ruta guardado: {archivo_rutas}")
                
                # Generar mapa
                coordenadas = list(zip(df['lat'], df['lon']))
                archivo_mapa = f"mapas/ruta_unica_{args.zona}.png"
                if generador_mapas.generar_mapa_estatico(coordenadas, ruta_optimizada, archivo_mapa):
                    print(f"🗺️  Mapa generado: {archivo_mapa}")
                
                # Generar enlaces móviles
                enlace_google = generador_mapas.generar_enlace_google_maps(coordenadas, ruta_optimizada)
                enlace_osm = generador_mapas.generar_enlace_osm(coordenadas, ruta_optimizada)
                
                print(f"📱 Enlace Google Maps: {enlace_google}")
                print(f"🗺️  Enlace OSM: {enlace_osm}")
                
            except Exception as e:
                print(f"❌ Error optimizando ruta única: {e}")
                raise
        
        # Limpiar archivo temporal
        if os.path.exists(archivo_filtrado):
            os.remove(archivo_filtrado)
            print(f"🧹 Archivo temporal eliminado: {archivo_filtrado}")
        
        print("\n✅ Proceso completado exitosamente!")
        
    except Exception as e:
        print(f"❌ Error en el proceso: {e}")
        raise

if __name__ == "__main__":
    main()