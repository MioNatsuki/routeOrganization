import pandas as pd
import requests
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import List, Tuple, Optional
import time
import numpy as np

class OptimizadorRutas:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30
    
    def _calcular_distancia_haversine(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        # Radio de la Tierra en km
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
        
        return R * c
    
    def _filtrar_puntos_lejanos(self, coordenadas: List[Tuple[float, float]], 
                              max_distancia_km: float = 25) -> List[int]:
        """Identifica puntos que están muy lejos del centroide (más de 25km)"""
        if len(coordenadas) <= 1:
            return []
        
        # Calcular centroide
        lats = [lat for lat, lon in coordenadas]
        lons = [lon for lat, lon in coordenadas]
        centro_lat = sum(lats) / len(lats)
        centro_lon = sum(lons) / len(lons)
        
        puntos_lejanos = []
        for i, (lat, lon) in enumerate(coordenadas):
            distancia = self._calcular_distancia_haversine((centro_lat, centro_lon), (lat, lon))
            if distancia > max_distancia_km:
                puntos_lejanos.append(i)
                print(f"Punto {i+1} está a {distancia:.1f} km del centro - Marcado como NO LOCALIZABLE")
        
        return puntos_lejanos
    
    def _matriz_distancias_euclidianas(self, coordenadas: List[Tuple[float, float]]) -> List[List[int]]:
        #Matriz de distancias euclidianas optimizada con numpy
        n = len(coordenadas)
        if n == 0:
            return []
        
        # Convertir a arrays de numpy para cálculo vectorizado
        lats = np.array([coord[0] for coord in coordenadas])
        lons = np.array([coord[1] for coord in coordenadas])
        
        # Crear matriz de distancias
        matriz = np.zeros((n, n), dtype=int)
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distancia_km = self._calcular_distancia_haversine(
                        (lats[i], lons[i]), (lats[j], lons[j])
                    )
                    # Convertir distancia a tiempo (assuming 40 km/h average speed)
                    tiempo_minutos = int((distancia_km / 40) * 60)
                    matriz[i, j] = max(1, tiempo_minutos)  # Mínimo 1 minuto
        
        return matriz.tolist()
    
    def obtener_matriz_tiempos(self, coordenadas: List[Tuple[float, float]]) -> List[List[int]]:
        try:
            # Si hay pocas coordenadas, usar matriz euclidiana (más rápido)
            if len(coordenadas) <= 2:
                return self._matriz_distancias_euclidianas(coordenadas)
            
            # Formatear coordenadas para OSRM
            coordenadas_str = ';'.join([f"{lon},{lat}" for lat, lon in coordenadas])
            
            url = f"http://router.project-osrm.org/table/v1/driving/{coordenadas_str}"
            params = {
                'annotations': 'duration',
            }
            
            print(f"Solicitando matriz OSRM para {len(coordenadas)} puntos...")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'durations' not in data:
                raise ValueError("OSRM no devolvió matriz de duraciones")
            
            duraciones = data['durations']
            
            # Convertir segundos a minutos enteros
            matriz_tiempos = []
            for fila in duraciones:
                fila_minutos = [int(round(duration / 60)) if duration is not None else 9999 for duration in fila]
                matriz_tiempos.append(fila_minutos)
            
            print("Matriz OSRM obtenida exitosamente")
            return matriz_tiempos
            
        except Exception as e:
            print(f"Error obteniendo matriz de OSRM: {e}")
            print("Usando matriz de distancias euclidianas...")
            return self._matriz_distancias_euclidianas(coordenadas)
    
    def optimizar_ruta(self, df: pd.DataFrame, num_vehiculos: int = 1) -> Optional[List[List[int]]]:
        if df.empty:
            print("DataFrame vacío - No hay datos para optimizar")
            return None
        
        coordenadas = list(zip(df['lat'], df['lon']))
        
        print(f"Optimizando ruta con {len(coordenadas)} puntos...")
        
        # Filtrar puntos lejanos (no incluirlos en la ruta)
        puntos_lejanos = self._filtrar_puntos_lejanos(coordenadas, max_distancia_km=25)
        puntos_validos = [i for i in range(len(coordenadas)) if i not in puntos_lejanos]
        
        if not puntos_validos:
            print("No hay puntos válidos dentro del radio de 40km")
            return None
        
        # Usar solo puntos válidos para la optimización
        coords_validos = [coordenadas[i] for i in puntos_validos]
        df_validos = df.iloc[puntos_validos].copy().reset_index(drop=True)
        
        print(f"Optimizando {len(puntos_validos)} puntos válidos...")
        
        # Crear modelo de datos
        data = {}
        data['num_vehiculos'] = num_vehiculos
        data['depot'] = 0  # Primer punto como depósito
        data['matriz_tiempos'] = self.obtener_matriz_tiempos(coords_validos)
        
        if not data['matriz_tiempos']:
            print("No se pudo generar matriz de tiempos")
            return None
        
        # Configurar OR-Tools
        manager = pywrapcp.RoutingIndexManager(
            len(data['matriz_tiempos']), data['num_vehiculos'], data['depot'])
        routing = pywrapcp.RoutingModel(manager)
        
        def tiempo_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['matriz_tiempos'][from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(tiempo_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Agregar restricción de tiempo máximo por vehículo (opcional)
        dimension_name = 'Time'
        routing.AddDimension(
            transit_callback_index,
            0,  # sin tiempo de espera
            480,  # tiempo máximo por vehículo (8 horas)
            True,  # empezar en 0
            dimension_name)
        time_dimension = routing.GetDimensionOrDie(dimension_name)
        
        # Configurar solver
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.seconds = 30  # 30 segundos máximo
        
        # Resolver
        print("Resolviendo problema de ruteo...")
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            print("Solución óptima encontrada")
            rutas = self._extraer_rutas(manager, routing, solution, data['num_vehiculos'])
            
            # Convertir índices de ruta a índices originales del DataFrame
            rutas_finales = []
            for ruta in rutas:
                ruta_final = [puntos_validos[i] for i in ruta]
                rutas_finales.append(ruta_final)
            
            return rutas_finales
        else:
            print("No se encontró solución óptima")
            return None
    
    def _extraer_rutas(self, manager, routing, solution, num_vehiculos: int) -> List[List[int]]:
        """Extrae las rutas ordenadas de la solución"""
        rutas = []
        for vehiculo_id in range(num_vehiculos):
            index = routing.Start(vehiculo_id)
            ruta = []
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                ruta.append(node_index)
                index = solution.Value(routing.NextVar(index))
            rutas.append(ruta)
        return rutas
    
    def optimizar_ruta_simple(self, coordenadas: List[Tuple[float, float]]) -> List[int]:
        """Optimización simple para casos con pocos puntos"""
        if len(coordenadas) <= 1:
            return list(range(len(coordenadas)))
        
        # Para pocos puntos, usar algoritmo simple
        matriz = self._matriz_distancias_euclidianas(coordenadas)
        
        # Algoritmo del vecino más cercano
        visitados = set()
        ruta = [0]  # Empezar desde el primer punto
        visitados.add(0)
        
        current = 0
        while len(visitados) < len(coordenadas):
            next_node = None
            min_dist = float('inf')
            
            for i in range(len(coordenadas)):
                if i not in visitados and matriz[current][i] < min_dist:
                    min_dist = matriz[current][i]
                    next_node = i
            
            if next_node is not None:
                ruta.append(next_node)
                visitados.add(next_node)
                current = next_node
        
        return ruta