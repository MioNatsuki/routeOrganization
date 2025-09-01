import pandas as pd
import requests
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import List, Tuple
from config import OSRM_URL

class OptimizadorRutas:
    def __init__(self):
        self.session = requests.Session()
    
    def obtener_matriz_tiempos(self, coordenadas: List[Tuple[float, float]]) -> List[List[int]]:
        """Obtiene matriz de tiempos de viaje usando OSRM"""
        try:
            # Formatear coordenadas para OSRM: "lon,lat;lon,lat;..."
            coordenadas_str = ';'.join([f"{lon},{lat}" for lat, lon in coordenadas])
            
            url = f"{OSRM_URL}/{coordenadas_str}"
            params = {
                'annotations': 'duration',
                'sources': ';'.join([str(i) for i in range(len(coordenadas))]),
                'destinations': ';'.join([str(i) for i in range(len(coordenadas))])
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # OSRM devuelve la matriz de duraciones en segundos
            duraciones = data['durations']
            
            # Convertir a minutos enteros
            matriz_tiempos = []
            for fila in duraciones:
                fila_minutos = [int(round(duration / 60)) if duration is not None else 0 for duration in fila]
                matriz_tiempos.append(fila_minutos)
            
            return matriz_tiempos
            
        except Exception as e:
            print(f"❌ Error obteniendo matriz de OSRM: {e}")
            print("🔄 Usando matriz de distancias euclidianas como fallback...")
            return self._matriz_distancias_euclidianas(coordenadas)
    
    def _matriz_distancias_euclidianas(self, coordenadas: List[Tuple[float, float]]) -> List[List[int]]:
        """Matriz de distancias euclidianas (fallback)"""
        n = len(coordenadas)
        matriz = [[0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    lat1, lon1 = coordenadas[i]
                    lat2, lon2 = coordenadas[j]
                    # Distancia euclidiana aproximada en metros
                    dist = math.sqrt((lat1-lat2)**2 + (lon1-lon2)**2) * 111000
                    matriz[i][j] = int(dist)
        
        return matriz
    
    def optimizar_ruta(self, df: pd.DataFrame, num_vehiculos: int = 1) -> List[List[int]]:
        """Optimiza la ruta usando VRP"""
        coordenadas = list(zip(df['lat'], df['lon']))
        
        # Crear modelo de datos
        data = {}
        data['num_vehiculos'] = num_vehiculos
        data['depot'] = 0
        data['matriz_tiempos'] = self.obtener_matriz_tiempos(coordenadas)
        
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
        
        # Configurar solver
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.seconds = 30
        
        # Resolver
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            return self._extraer_rutas(manager, routing, solution, data['num_vehiculos'])
        else:
            raise Exception("No se encontró solución para el VRP")
    
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