import pandas as pd
from geocodificador import Geocodificador
from optimizador_rutas import OptimizadorRutas
from generador_mapas import GeneradorMapas
from utils import crear_directorios, filtrar_por_zona, dividir_por_notificadores, mostrar_ruta, filtrar_por_colonia
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
    parser.add_argument('--radio-maximo', type=int, default=25,
                       help='Radio máximo en km para considerar coordenadas válidas (default: 25)')
    parser.add_argument('--colonia', type=str, default='',
                       help='Colonia específica dentro de la zona (opcional)')
    parser.add_argument('--punto-inicio', type=str, default='',
                       help='Dirección para punto de inicio personalizado (opcional)')
    parser.add_argument('--usar-coordenadas', action='store_true',
                       help='Usar coordenadas existentes en el CSV (si disponibles)')
    
    args = parser.parse_args()
    
    try:
        print("Iniciando optimización de rutas con OpenStreetMap...")
        print(f"Archivo: {args.archivo}")
        print(f"Zona: {args.zona}")
        print(f"Radio máximo: {args.radio_maximo} km")
        
        if args.colonia:
            print(f"Colonia: {args.colonia}")
        
        if args.punto_inicio:
            print(f"Punto de inicio: {args.punto_inicio}")
        
        if args.cuentas_por_notificador > 0:
            print(f"Cuentas por notificador: {args.cuentas_por_notificador}")
        else:
            print(f"Modo: Ruta única")
        
        if args.usar_coordenadas:
            print("Usando coordenadas existentes del CSV")
        
        # Filtro por zona
        print(f"\nFiltrando datos para la zona: {args.zona}...")
        df_original = pd.read_csv(args.archivo, encoding='utf-8')
        df_filtrado = filtrar_por_zona(df_original, args.zona)
        
        if df_filtrado.empty:
            print(f"No se encontraron datos para la zona: {args.zona}")
            print("Verifica que el nombre de la zona coincida exactamente")
            return
        
        # Filtro por colonia si se especificó
        if args.colonia:
            print(f"Filtrando por colonia: {args.colonia}...")
            df_filtrado = filtrar_por_colonia(df_filtrado, args.colonia)
            
            if df_filtrado.empty:
                print(f"No se encontraron datos para la colonia: {args.colonia}")
                return
        
        print(f"{len(df_filtrado)} domicilios encontrados")
        
        # Guardar CSV filtrado temporalmente
        archivo_filtrado = f"datos/salida/filtrado_{args.zona}"
        if args.colonia:
            archivo_filtrado += f"_{args.colonia.replace(' ', '_')}"
        archivo_filtrado += ".csv"
        
        df_filtrado.to_csv(archivo_filtrado, index=False, encoding='utf-8')
        print(f"Datos filtrados guardados en: {archivo_filtrado}")
        
        # Geocodificación (solo si no se usan coordenadas existentes)
        if args.usar_coordenadas and geocodificador._tiene_coordenadas(df_filtrado):
            print("Procesando archivo con coordenadas mixtas...")
            archivo_procesado = archivo_filtrado.replace('filtrado', 'procesado')
            df = geocodificador.procesar_csv_mixto(archivo_filtrado, archivo_procesado)
        else:
            print("Geocodificando direcciones...")
            archivo_geocodificado = archivo_filtrado.replace('filtrado', 'geocodificado')
            df = geocodificador.procesar_csv(archivo_filtrado, archivo_geocodificado)
        
        # Verificar que hay datos para optimizar
        if df.empty:
            print("No hay direcciones válidas para optimizar después del filtrado")
            print("Revisa el archivo de fallos en datos/salida/")
            return
        
        # Geocodificar punto de inicio si se especificó
        punto_inicio_index = None
        if args.punto_inicio:
            print(f"Geocodificando punto de inicio: {args.punto_inicio}")
            lat, lon, nombre = geocodificador.geocodificar_punto_inicial(args.punto_inicio)
            if lat and lon:
                print(f"Punto inicial geocodificado: {nombre}")
                # Encontrar el punto más cercano en el dataset
                from utils import calcular_distancia_haversine
                min_dist = float('inf')
                for idx, row in df.iterrows():
                    dist = calcular_distancia_haversine(lat, lon, row['lat'], row['lon'])
                    if dist < min_dist:
                        min_dist = dist
                        punto_inicio_index = idx
                print(f"Punto de inicio asignado: {df.iloc[punto_inicio_index]['Domicilio']}")
            else:
                print("No se pudo geocodificar el punto de inicio, usando punto por defecto")
        
        # Optimizar rutas
        if args.cuentas_por_notificador > 0:
            # Modo múltiples notificadores
            chunks = dividir_por_notificadores(df, args.cuentas_por_notificador)
            todas_rutas = []
            datos_rutas = []  # Para el CSV final
            
            print(f"\nGenerando {len(chunks)} rutas para {len(chunks)} notificadores...")
            
            for i, chunk in enumerate(chunks):
                print(f"\nProcesando Notificador {i+1} ({len(chunk)} cuentas)...")
                
                # Verificar que el chunk no esté vacío
                if len(chunk) == 0:
                    print(f"Notificador {i+1} sin direcciones válidas - saltando")
                    continue
                
                # Optimizar ruta para este chunk
                try:
                    rutas_chunk = optimizador.optimizar_ruta(chunk, 1)
                    
                    # Verificar que se optimizó correctamente
                    if not rutas_chunk or len(rutas_chunk) == 0:
                        print(f"No se pudo optimizar ruta para Notificador {i+1}")
                        continue
                    
                    ruta_optimizada = rutas_chunk[0]
                    
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
                            'Colonia': fila.get('Colonia', ''),
                            'lat': fila.get('lat', ''),
                            'lon': fila.get('lon', '')
                        })
                    
                    todas_rutas.append((chunk, ruta_optimizada))
                    
                    # Generar mapa para esta ruta
                    coordenadas = list(zip(chunk['lat'], chunk['lon']))
                    archivo_mapa = f"mapas/ruta_{args.zona}_notificador_{i+1}.png"
                    if generador_mapas.generar_mapa_estatico(coordenadas, ruta_optimizada, archivo_mapa):
                        print(f"Mapa generado: {archivo_mapa}")
                    else:
                        print(f"No se pudo generar mapa para Notificador {i+1}")
                    
                    # Generar enlaces móviles
                    enlace_google = generador_mapas.generar_enlace_google_maps(coordenadas, ruta_optimizada)
                    enlace_osm = generador_mapas.generar_enlace_osm(coordenadas, ruta_optimizada)
                    
                    print(f"Enlace Google Maps: {enlace_google}")
                    print(f"Enlace OSM: {enlace_osm}")
                    
                except Exception as e:
                    print(f"Error optimizando ruta para notificador {i+1}: {e}")
                    continue
            
            # Guardar CSV con todas las rutas
            if datos_rutas:
                df_rutas = pd.DataFrame(datos_rutas)
                archivo_rutas = f"datos/salida/rutas_{args.zona}_{len(chunks)}notificadores.csv"
                df_rutas.to_csv(archivo_rutas, index=False, encoding='utf-8')
                print(f"\nCSV de todas las rutas guardado: {archivo_rutas}")
            else:
                print("No se generaron rutas válidas para ningún notificador")
        
        else:
            # Modo ruta única
            print(f"\nOptimizando ruta única para {len(df)} cuentas...")
            
            try:
                # Forzar punto de inicio si se especificó
                if punto_inicio_index is not None:
                    print(f"Forzando punto de inicio en índice: {punto_inicio_index}")
                    # Reordenar el DataFrame para que el punto de inicio esté primero
                    indices_reordenados = [punto_inicio_index] + [i for i in range(len(df)) if i != punto_inicio_index]
                    df_reordenado = df.iloc[indices_reordenados].reset_index(drop=True)
                    df = df_reordenado
                
                rutas_optimizadas = optimizador.optimizar_ruta(df, 1)
                
                # Verificar que se optimizó correctamente
                if not rutas_optimizadas or len(rutas_optimizadas) == 0:
                    print("No se pudo optimizar la ruta única")
                    return
                
                ruta_optimizada = rutas_optimizadas[0]
                
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
                        'Colonia': fila.get('Colonia', ''),
                        'lat': fila.get('lat', ''),
                        'lon': fila.get('lon', '')
                    })
                
                df_ruta = pd.DataFrame(datos_ruta)
                archivo_rutas = f"datos/salida/ruta_unica_{args.zona}.csv"
                if args.colonia:
                    archivo_rutas = archivo_rutas.replace('.csv', f"_{args.colonia.replace(' ', '_')}.csv")
                df_ruta.to_csv(archivo_rutas, index=False, encoding='utf-8')
                print(f"CSV de ruta guardado: {archivo_rutas}")
                
                # Generar mapa
                coordenadas = list(zip(df['lat'], df['lon']))
                archivo_mapa = f"mapas/ruta_unica_{args.zona}.png"
                if args.colonia:
                    archivo_mapa = archivo_mapa.replace('.png', f"_{args.colonia.replace(' ', '_')}.png")
                if generador_mapas.generar_mapa_estatico(coordenadas, ruta_optimizada, archivo_mapa):
                    print(f"Mapa generado: {archivo_mapa}")
                else:
                    print("No se pudo generar el mapa de la ruta única")
                
                # Generar enlaces móviles
                enlace_google = generador_mapas.generar_enlace_google_maps(coordenadas, ruta_optimizada)
                enlace_osm = generador_mapas.generar_enlace_osm(coordenadas, ruta_optimizada)
                
                print(f"Enlace Google Maps: {enlace_google}")
                print(f"Enlace OSM: {enlace_osm}")
                
            except Exception as e:
                print(f"Error optimizando ruta única: {e}")
                raise
        
        # Limpiar archivo temporal
        if os.path.exists(archivo_filtrado):
            os.remove(archivo_filtrado)
            print(f"Archivo temporal eliminado: {archivo_filtrado}")
        
        print("\n¡Proceso completado exitosamente!")
        print("Resultados guardados en: datos/salida/")
        print("Mapas generados en: mapas/")
        
    except Exception as e:
        print(f"Error en el proceso: {e}")
        raise

if __name__ == "__main__":
    main()